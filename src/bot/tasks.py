import logging
import os
import requests

from celery import shared_task
from django.utils import timezone

from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from bot.models import ChatUser, PDFUpload, Request, Validation
from sciarticle.settings import SOURCE_SERVER_URL
from sciarticle.settings import SEARCH_CHAT_ID

from .utils import async_download_pdf

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is not set in environment variables")
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

PDF_FILE = './pdf_files'
os.makedirs(PDF_FILE, exist_ok=True)

DOI_REGEX = r"10\.\d{4,9}[\s][-._;()\s:A-Za-z0-9]+"


@shared_task
def request_pdf_task(chat_id, message_id, doi, message_search_id):
    chat_user, _ = ChatUser.objects.get_or_create(
        telegram_id=chat_id,
        defaults={'username': f"user_{chat_id}", 'is_in_bot': True}
    )

    # Проверка на наличие в базе даных запроса по DOI у пользователя
    if Request.objects.filter(
        chat_id=chat_id,
        doi=doi,
        status__in=('pending', 'completed')
    ).exists():
        logger.info(
            f"Repeated request from user in chat_id={chat_id}: don't save to db"
        )
        return
    
    is_duplicate = Request.objects.filter(
        doi=doi,
        status=('pending')
    ).exists()

    request_obj = Request.objects.create(
        doi=doi,
        status='pending',
        chat_id=chat_id,
        user=chat_user,
        message_id=message_id,
        message_search_id=message_search_id
    )
    logger.info(f"Request recorded in the db {request_obj}")

    # Проверка на наличие в базе данных запроса по DOI от разных пользователей и запись в бд при наличии
    if is_duplicate:
        return {'code': 'repeated request', 'id': request_obj.id}

    # Если статьи нет в базе данных
    return {'code': 'new request', 'id': request_obj.id}


@shared_task
def run_check():
    # Ищем все запросы, которые уже устарели, но статус еще не сменился
    expired_requests = Request.objects.filter(
        expires_at__lt=timezone.now(),
        status='pending'
    ).order_by('id')
    logger.info(
        f"Update request status {expired_requests} on 'expired'"
    )
    for request in expired_requests:
        data = {
            'message_id': request.message_id,
            'chat_id': request.chat_id,
            'message_search_id': request.message_search_id,
            'doi': request.doi
        }

        try:
            # Отправляем запрос на сервер первого бота
            response = requests.post(
               f"{SOURCE_SERVER_URL}/api/request-pdf-expired/", data=data
            )
            logger.info(f"{response} received")
            if response.status_code == 204:
                Request.objects.filter(
                    doi=request.doi,
                    status='pending'
                ).update(status='expired')
                logger.info(
                    f"All requests with DOI={request.doi} are expired"
                )
            else:
                logger.error(
                    f"Service is not available:{response.status_code}"
                )

        except Exception as e:
            logger.error(f"En error occurred while sending request: {e}")
    return True


async def check_pdf_file(file_id, file_name, user_id, message_id, doi):
    """
    Проверяет есть ли запрос на эту статью по DOI. 
    Сохраняет файл. 
    Отправляет сообщение, с просьбой проверить PDF.
    """
    try:
        # Проверяем есть ли в базе данных запрос со статусом - в ожидании
        request = await Request.objects.filter(doi=doi, status='pending').afirst()
        # Если запроса нет, то сообщение с pdf - удалять
        if not request:
            logger.info(f"No request with status pending for article with DOI: {doi}")
            await bot.delete_message(chat_id=SEARCH_CHAT_ID, message_id=message_id)
            return
        
        # Проверяем есть ли в базе данных уже файл с таким именем и состоянием в проверке
        pdf_file = await PDFUpload.objects.filter(request=request, state='uploaded').afirst()
        if pdf_file:
            logger.info(f"File for {request} has already been uploaded and is awaiting verification")
            await bot.delete_message(chat_id=SEARCH_CHAT_ID, message_id=message_id)
            return

        file_path = os.path.join(PDF_FILE, file_name)
        result = await async_download_pdf(bot, file_id, file_path)

        if not result:
            logger.warning(f"Failed to save file: {file_name}")
            return

        # Записываем в бд информацию о файле
        user, _ = await ChatUser.objects.aget_or_create(
            telegram_id=user_id,
            defaults={'username': f"user_{user_id}", 'is_in_bot': True}
        )

        pdf_upload = await PDFUpload.objects.acreate(
            file_id=file_id,
            request=request,
            user=user,
            message_id=message_id,
            state='uploaded',
            path=file_path
        )
        logger.info(f"PDF information is recorded in the db {pdf_upload}")

        # Если есть запрос на статью с таким DOI отправляется сообщение с кнопками в ответ на PDF
        message = await bot.send_message(
            chat_id=SEARCH_CHAT_ID,
            text="Пожалуйста, проверьте PDF",
            reply_to_message_id=message_id,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Всё верно", callback_data=f"PDF_CORRECT_{doi}"),
                    InlineKeyboardButton("❌ PDF неверный", callback_data=f"PDF_INCORRECT_{doi}")
                ]
            ])
        )
        pdf_upload.reply_to_message_id = message.id
        await pdf_upload.asave()

        logger.info(f"Verification message sent for article, DOI: {doi}")
    except Exception as e:
        logger.error(f"Error processing PDF with file_name = {file_name}, DOI = {doi}: {e}")


@shared_task
def handle_vote_callback_task(callback_query_id: str, callback_data: str, voter_id: int, voter_username: str):
    action, pdf_id_str = callback_data.split(":")
    pdf_id = int(pdf_id_str)
    try:
        pdf = PDFUpload.objects.select_related('request', 'user', 'request__user').get(id=pdf_id)
    except PDFUpload.DoesNotExist:
        logger.error(f"PDFUpload with id {pdf_id} does not exist. Cannot process vote.")
        bot.answer_callback_query(callback_query_id=callback_query_id, text="Ошибка: PDF не найден.", show_alert=True)
        return

    req = pdf.request

    if req.user and req.user.telegram_id == voter_id:
        bot.answer_callback_query(callback_query_id=callback_query_id, text="Вы не можете голосовать по своему запросу.", show_alert=True)
        return
    if pdf.user.telegram_id == voter_id:
        bot.answer_callback_query(callback_query_id=callback_query_id, text="Вы не можете голосовать за свой PDF.", show_alert=True)
        return

    voter, _ = ChatUser.objects.get_or_create(
        telegram_id=voter_id,
        defaults={'username': voter_username}
    )
    vote_val = (action == "vote_valid")

    try:
        Validation.objects.create(
            pdf_upload=pdf,
            user=voter,
            vote=vote_val,
            voted_at=timezone.now()
        )
    except IntegrityError: 
        bot.answer_callback_query(callback_query_id=callback_query_id, text="Вы уже голосовали за этот PDF.", show_alert=True)
        return

    votes = Validation.objects.filter(pdf_upload=pdf)
    total_votes = votes.count()

    VALIDATION_THRESHOLD = 3 

    if total_votes >= VALIDATION_THRESHOLD:
        correct_votes = votes.filter(vote=True).count()
        incorrect_votes = total_votes - correct_votes
        
        pdf.is_valid = correct_votes > incorrect_votes
        pdf.validated_at = timezone.now()
        pdf.save() 

        if pdf.chat_message_id and pdf.delete_at:
            current_time = timezone.now()
            if pdf.delete_at > current_time:
                delay_seconds = (pdf.delete_at - current_time).total_seconds()
                if delay_seconds > 0:
                    delete_message_task.apply_async(
                        args=[pdf.request.chat_id, pdf.chat_message_id],
                        countdown=int(delay_seconds) 
                    )
                    logger.info(
                        f"Scheduled deletion for PDF message ID {pdf.chat_message_id} "
                        f"in chat ID {pdf.request.chat_id} in {delay_seconds:.0f} seconds."
                    )
                else:
                    logger.warning(
                        f"PDF message ID {pdf.chat_message_id} in chat ID {pdf.request.chat_id} "
                        f"has a delete_at ({pdf.delete_at}) not in the future. Deleting now."
                    )
                    delete_message_task.delay(pdf.request.chat_id, pdf.chat_message_id)
            else:
                logger.warning(
                    f"PDF message ID {pdf.chat_message_id} in chat ID {pdf.request.chat_id} "
                    f"has a delete_at ({pdf.delete_at}) that is not in the future. Deleting now."
                )
                delete_message_task.delay(pdf.request.chat_id, pdf.chat_message_id)
        else:
            logger.error(
                f"Could not schedule deletion for PDF ID {pdf.id}. "
                f"chat_message_id: {pdf.chat_message_id}, delete_at: {pdf.delete_at}"
            )
        
        final_caption = ""
        if pdf.is_valid:
            final_caption = f"✅ PDF для DOI: {req.doi} был признан валидным."
        else:
            final_caption = f"❌ PDF для DOI: {req.doi} был признан невалидным."

        try:
            bot.edit_message_caption(
                chat_id=req.chat_id,
                message_id=pdf.chat_message_id, 
                caption=final_caption,
                reply_markup=None 
            )
        except Exception as e:
            logger.error(f"Error editing message caption after validation: {e}")

    bot.answer_callback_query(callback_query_id=callback_query_id, text="Спасибо, ваш голос учтен!")
    return pdf.id


@shared_task
def delete_message_task(chat_id, message_id):
    """Deletes a message after a delay, fetching config inside."""
    if not bot:
        logger.error("Bot is not initialized in delete_message_task.")
        return
    try:
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Deleted message {message_id} from chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to delete message {message_id} from chat {chat_id}: {e}")


@shared_task
def schedule_pdf_deletion(chat_id: int, message_id: int, delay: int):
    """Schedules the deletion of a PDF-related message."""
    delete_message_task.apply_async(args=[chat_id, message_id], countdown=delay)
    logger.info(
        f"Scheduled PDF message {message_id} in chat {chat_id} for deletion in {delay} seconds."
    )


@shared_task
def schedule_notification_deletion(chat_id: int, message_id: int, delay: int):
    """Schedules the deletion of a notification message."""
    delete_message_task.apply_async(args=[chat_id, message_id], countdown=delay)
    logger.info(
        f"Scheduled notification message {message_id} in chat {chat_id} for deletion in {delay} seconds."
    )