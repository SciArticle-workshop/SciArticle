import logging
import os
import requests
import asyncio

from celery import shared_task
from django.utils import timezone
from django.db import IntegrityError

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
        status=('pending')
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


def send_request(request):
    data = {
            'message_id': request.message_id,
            'chat_id': request.chat_id,
            'message_search_id': request.message_search_id
        }
    try:
        # Отправляем запрос на сервер первого бота
        response = requests.post(
            f"{SOURCE_SERVER_URL}/api/request-pdf-expired/", data=data
        )
        logger.info(f"{response} received")
        if response.status_code == 204:
            logger.info("Information about request/requests sent successfully")
            return True
        else:
            logger.error(
                f"Service is not available:{response.status_code}"
            )
            return False

    except Exception as e:
        logger.error(f"En error occurred while sending request: {e}")
        return False


async def new_send_request(request):
    new_request = await Request.objects.filter(
                    doi=request.doi,
                    status=('pending')
                ).order_by('id').afirst()
    data = {
            'doi': new_request.doi,
        }
    try:
        # Отправляем запрос на сервер первого бота
        response = requests.post(
            f"{SOURCE_SERVER_URL}/api/new_request-pdf/", data=data
        )
        logger.info(f"{response} received")
        if response.status_code == 200:
            new_request.message_search_id = response.json()['message_id']
            await new_request.asave()
            logger.info("Information about not found request")
            return True
        else:
            logger.error(
                f"Service is not available:{response.status_code}"
            )
            return False

    except Exception as e:
        logger.error(f"En error occurred while sending request: {e}")
        return False


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
        is_ok = send_request(request)
        if is_ok:
            Request.objects.filter(
                doi=request.doi,
                status='pending'
            ).update(status='expired')
    return True


async def check_pdf_file(file_id, file_name, user_id, message_id, doi):
    """
    Проверяет есть ли запрос на эту статью по DOI.
    Сохраняет файл.
    Отправляет сообщение, с просьбой проверить PDF.
    """
    try:
        # Проверяем есть ли в базе данных запрос со статусом - в ожидании
        request = await Request.objects.filter(
            doi=doi, status='pending'
        ).afirst()
        # Если запроса нет, то сообщение с pdf - удалять
        if not request:
            logger.info(
                f"No request with status pending for article with DOI: {doi}"
            )
            await bot.delete_message(
                chat_id=SEARCH_CHAT_ID,
                message_id=message_id
            )
            return
        # Проверяем есть ли в базе данных уже файл с таким именем и состоянием в проверке
        pdf_file = await PDFUpload.objects.filter(
            request=request,
            state='uploaded'
        ).afirst()
        if pdf_file:
            logger.info(
                f"File for {request} has already been uploaded and is awaiting verification"
            )
            await bot.delete_message(
                chat_id=SEARCH_CHAT_ID,
                message_id=message_id
            )
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

        # Отправляем post-запрос в SciSourceBot (нужно удалить сообщение с запросом на статью)
        send_request(request)

        # Если есть запрос на статью с таким DOI отправляется сообщение с кнопками в ответ на PDF
        message = await bot.send_message(
            chat_id=SEARCH_CHAT_ID,
            text="Пожалуйста, проверьте PDF",
            reply_to_message_id=message_id,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ Всё верно",
                        callback_data=f"vote_valid:{pdf_upload.id}"
                    ),
                    InlineKeyboardButton(
                        "❌ PDF неверный",
                        callback_data=f"vote_invalid:{pdf_upload.id}"
                    )
                ]
            ])
        )
        pdf_upload.reply_to_message_id = message.id
        await pdf_upload.asave()
        logger.info(f"Verification message sent for article, DOI: {doi}")
    except Exception as e:
        logger.error(
            f"Error processing PDF with file_name={file_name}, DOI={doi}: {e}"
        )


def send_pdf(pdfupload):
    request = pdfupload.request
    data = {
        'message_id': pdfupload.message_id,
        'chat_id': request.chat_id,
        'doi': request.doi
    }
    with open(pdfupload.path, 'rb') as f:
        files = {
            'file': ('document.pdf', f, 'application/pdf')
        }

        response = requests.post(
            f"{SOURCE_SERVER_URL}/api/upload-pdf/",
            data=data,
            files=files
        )
        if response.status_code == 200:
            logger.info("File and data sent successfully")
        else:
            logger.error(
                f"Service is not available:{response.status_code}"
            )


async def delete_message_and_file(pdfupload, delete_file):
    logger.info(
        f"Удаляем {pdfupload.message_id} в чате {SEARCH_CHAT_ID}"
    )
    await bot.delete_messages(
        chat_id=SEARCH_CHAT_ID,
        message_ids=[
            int(pdfupload.message_id),
            int(pdfupload.reply_to_message_id)
        ]
    )
    if delete_file:
        file_path = pdfupload.path
        # Проверяем есть ли файл, если есть - удаляем
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"File deleted: {file_path}")
        else:
            logger.warning(f"File not found: {file_path}")

    pdfupload.state = 'deleted'
    await pdfupload.asave()
    logger.info(
        f"Message deleted: {pdfupload.message_id} (PDF ID: {pdfupload.id})"
    )


async def handle_vote_callback_task(
        callback_query_id: str,
        callback_data: str, voter_id: int,
        voter_username: str):
    action, pdf_id_str = callback_data.split(":")
    pdf_id = int(pdf_id_str)
    logger.info(f'vote_callback received: action={action}, pdf_id={pdf_id}')
    try:
        pdf = await PDFUpload.objects.select_related(
            'request', 'user', 'request__user'
        ).aget(id=pdf_id)
    except PDFUpload.DoesNotExist:
        logger.error(
            f"PDFUpload with id {pdf_id} does not exist. Cannot process vote."
        )
        await bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text="Ошибка: PDF не найден.",
            show_alert=True
        )
        return

    req = pdf.request

    if req.user and req.user.telegram_id == voter_id:
        await bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text="Вы не можете голосовать по своему запросу.",
            show_alert=True
        )
        return

    if pdf.user.telegram_id == voter_id:
        await bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text="Вы не можете голосовать за свой PDF.",
            show_alert=True
        )
        return

    voter, _ = await ChatUser.objects.aget_or_create(
        telegram_id=voter_id,
        defaults={'username': voter_username}
    )
    vote_val = (action == "vote_valid")

    try:
        await Validation.objects.acreate(
            pdf_upload=pdf,
            user=voter,
            vote=vote_val,
            voted_at=timezone.now()
        )
    except IntegrityError as e:
        logger.error(f"Error: {e}")
        await bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text="Вы уже голосовали за этот PDF.",
            show_alert=True
        )
        return

    votes = Validation.objects.filter(pdf_upload=pdf)
    votes_true = await votes.filter(vote=True).acount()
    votes_false = await votes.filter(vote=False).acount()
    logger.info(f'votes_true: {votes_true}')
    logger.info(f'votes_false: {votes_false}')

    if votes_true >= 2 or votes_false >= 2:
        pdf.is_valid = votes_true >= 2
        pdf.validated_at = timezone.now()
        await pdf.asave()

        final_text = ""
        if pdf.is_valid:
            final_text = f"✅ PDF был признан валидным. https://doi.org/{req.doi}"
        else:
            final_text = f"❌ PDF был признан невалидным. https://doi.org/{req.doi}"

        try:
            pdf.state = 'validated'
            await pdf.asave()
            await bot.edit_message_text(
                chat_id=SEARCH_CHAT_ID,
                message_id=pdf.reply_to_message_id,
                text=final_text,
                reply_markup=None
            )
            if pdf.is_valid:
                # Отправляем post-запрос (содержимое файл pdf и текстовые данные)
                send_pdf(pdf)
                # Ищем все запросы по этой статье. Так как статья найдена и проверена, то меняем статус запроса на - завершенный
                await Request.objects.filter(
                    doi=pdf.request.doi,
                    status='pending'
                ).aupdate(status='completed')
                logger.info("Update request status on 'completed'")
            else:
                # Удаляем сообщение о невалидном pdf, удаляем pdf файл из папки, где хранятся файлы 
                await delete_message_and_file(pdf, True)
                # Смотрим в бд все запросы по этому doi, находит 1-й активный запрос и передаем post-запросом его doi в @SciSourceBot
                await new_send_request(pdf.request)

        except Exception as e:
            logger.error(
                f"Error editing message caption after validation: {e}"
            )
    await bot.answer_callback_query(
        callback_query_id=callback_query_id, text="Спасибо, ваш голос учтен!"
    )
    return pdf.id


def async_to_sync(awaitable):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(awaitable)


@shared_task
def run_check_and_delete_pdf():
    # Ищем все pdf, которые пора удалить из чата (прошло 47 часов)
    files_uploaded = PDFUpload.objects.filter(
        delete_at__lt=timezone.now(),
        state__in=['uploaded', 'validated']
        ).order_by('id')
    for pdf in files_uploaded:
        try:
            async_to_sync(
                delete_message_and_file(pdf, pdf.state == 'uploaded')
            )
        except Exception as e:
            logger.error(
                f"Error deleting message {pdf.message_id}: {e}"
            )
