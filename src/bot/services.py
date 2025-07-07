import logging
import os

from django.db import IntegrityError
from django.utils import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.utils import get_bot
from bot.models import (
    ChatUser,
    Config,
    Count,
    Notification,
    PDFUpload,
    Request,
    Subscription,
    Validation,
)
from sciarticle.settings import BOT_NAME_SCISOURCE, PDF_FILES, SEARCH_CHAT_ID

from .scisource_client import (
    award_subscription,
    check_is_user,
    renew_request,
    send_count,
    send_pdf,
    send_request,
)
from .utils import async_download_pdf, form_word

logger = logging.getLogger(__name__)

bot = get_bot()


async def new_send_request(request):
    """Ищет в бд существующий запрос с тем же doi и статусом - в ожидании."""
    new_request = (
        await Request.objects.filter(
            doi=request.doi, status=('pending')).order_by('id').afirst()
    )

    result = renew_request(new_request)
    if result:
        await new_request.asave()
    return result


async def check_pdf_file(
    file_id, file_name, user_id, message_id, username, doi
):
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
                f'No request with status pending for article with DOI: {doi}'
            )
            await bot.delete_message(
                chat_id=SEARCH_CHAT_ID, message_id=message_id
            )
            return
        # Проверяем есть ли в базе данных уже файл с таким именем и
        # состоянием в проверке
        pdf_file = await PDFUpload.objects.filter(
            request=request, state='uploaded'
        ).afirst()

        if pdf_file:
            logger.info(
                f'File for {request} has already been uploaded and is awaiting verification'
            )
            await bot.delete_message(
                chat_id=SEARCH_CHAT_ID, message_id=message_id
            )
            return

        file_path = os.path.join(PDF_FILES, file_name)
        result = await async_download_pdf(bot, file_id, file_path)

        if not result:
            logger.warning(f'Failed to save file: {file_name}')
            return

        # Записываем в бд информацию о файле
        user, _ = await ChatUser.objects.aget_or_create(
            telegram_id=user_id,
            defaults={'username': username or f'user_{user_id}'},
        )

        pdf_upload = await PDFUpload.objects.acreate(
            file_id=file_id,
            request=request,
            user=user,
            message_id=message_id,
            state='uploaded',
            path=file_path,
        )
        logger.info(f'PDF information is recorded in the db {pdf_upload}')

        # Отправляем post-запрос в SciSourceBot
        # (нужно удалить сообщение с запросом на статью)
        send_request(request)
        await send_verification_message(pdf_upload)

        await send_thank_message(user, action='upload')
    except Exception as e:
        logger.error(
            f'Error processing PDF with file_name={file_name}, DOI={doi}: {e}'
        )


async def delete_message_and_file(pdfupload, delete_file):
    """
    В случает если, pdf был признан невалидным.
    Удаляет сообщение и его reply в общем чате.
    Удаляет файл из папки, где хранятся файлы.
    Обновляет статус объекта PDFUpload на 'deleted' и сохраняет.
    """
    logger.info(f'Удаляем {pdfupload.message_id} в чате {SEARCH_CHAT_ID}')
    try:
        bot = get_bot()
        await bot.delete_messages(
            chat_id=SEARCH_CHAT_ID,
            message_ids=[
                int(pdfupload.message_id),
                int(pdfupload.reply_to_message_id),
            ],
        )
    except Exception as e:
        logger.error(f'Problem with telegram server: {e}')

    if delete_file:
        file_path = pdfupload.path
        # Проверяем есть ли файл, если есть - удаляем
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f'File deleted: {file_path}')
        else:
            logger.warning(f'File not found: {file_path}')

    pdfupload.state = 'deleted'
    await pdfupload.asave()
    logger.info(
        f'Message deleted: {pdfupload.message_id} (PDF ID: {pdfupload.id})'
    )


async def delete_message(chat_id, message_id):
    """Обертка над функцией delete_message с новым экземпляром бота."""
    bot = get_bot()
    await bot.delete_message(chat_id=chat_id, message_id=message_id)


async def handle_vote_callback_task(
    callback_query_id: str, callback_data: str, voter_id: int, username: str
):
    """
    Проверяет, может ли пользователю голосовать за  PDF.
    Сохраняет голос (валиден / не валиден) в модель Validation.
    Если PDF был признан валиденым, меняет статус запросов на выполненные
    и отправляет файл и данные другому боту.
    Если PDF был признан невалидным — вызывает функцию,
    которая отвечает за удаление.
    """
    bot = get_bot()
    action, pdf_id_str = callback_data.split(':')
    pdf_id = int(pdf_id_str)
    logger.info(f'vote_callback received: action={action}, pdf_id={pdf_id}')
    try:
        pdf = await PDFUpload.objects.select_related(
            'request', 'user', 'request__user'
        ).aget(id=pdf_id)
    except PDFUpload.DoesNotExist:
        logger.error(
            f'PDFUpload with id {pdf_id} does not exist. Cannot process vote.'
        )
        await bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text='Ошибка: PDF не найден.',
            show_alert=True,
        )
        return

    req = pdf.request

    if req.user and req.user.telegram_id == voter_id:
        await bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text='Вы не можете голосовать по своему запросу.',
            show_alert=True,
        )
        return

    if pdf.user.telegram_id == voter_id:
        await bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text='Вы не можете голосовать за свой PDF.',
            show_alert=True,
        )
        return

    voter, _ = await ChatUser.objects.aget_or_create(
        telegram_id=voter_id,
        defaults={'username': username or f'user_{voter_id}'}
    )
    vote_val = action == 'vote_valid'

    try:
        await Validation.objects.acreate(
            pdf_upload=pdf, user=voter, vote=vote_val, voted_at=timezone.now()
        )
    except IntegrityError as e:
        logger.error(f'Error: {e}')
        await bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text='Вы уже голосовали за этот PDF.',
            show_alert=True,
        )
        return

    try:
        await send_thank_message(voter, action='validation')
    except Exception as e:
        logger.error(f'Problem with send_thanks_message: {e}')

    votes = Validation.objects.filter(pdf_upload=pdf)
    votes_true = await votes.filter(vote=True).acount()
    votes_false = await votes.filter(vote=False).acount()
    logger.info(f'votes_true: {votes_true}')
    logger.info(f'votes_false: {votes_false}')

    if votes_true >= 2 or votes_false >= 2:
        pdf.is_valid = votes_true >= 2
        pdf.validated_at = timezone.now()
        await pdf.asave()

        final_text = ''
        if pdf.is_valid:
            final_text = (
                f'✅ PDF был признан валидным. https://doi.org/{req.doi}'
            )
        else:
            final_text = (
                f'❌ PDF был признан невалидным. https://doi.org/{req.doi}'
            )

        try:
            pdf.state = 'validated'
            await pdf.asave()
            await bot.edit_message_text(
                chat_id=SEARCH_CHAT_ID,
                message_id=pdf.reply_to_message_id,
                text=final_text,
                reply_markup=None,
            )
            if pdf.is_valid:
                # Отправляем post-запрос (файл pdf и текстовые данные)
                send_pdf(pdf)
                # Ищем все запросы по этой статье. Так как статья найдена и
                # проверена, то меняем статус запроса на - завершенный
                await Request.objects.filter(
                    doi=pdf.request.doi, status='pending'
                ).aupdate(status='completed')
                logger.info("Update request status on 'completed'")
            else:
                # Удаляем сообщение о невалидном pdf,
                # удаляем pdf файл из папки, где хранятся файлы
                await delete_message_and_file(pdf, True)
                # Смотрим в бд все запросы по этому doi,
                # находит 1-й активный запрос и отправляем запросом его doi
                await new_send_request(pdf.request)

        except Exception as e:
            logger.error(
                f"Error editing message caption after validation: {e}"
            )
    await bot.answer_callback_query(
        callback_query_id=callback_query_id, text="Спасибо, ваш голос учтен!"
    )
    return pdf.id


async def validate_broken_pdf(file, doi, request, bot_id, bot_name):
    """Отправляет pdf-файл в общий чат от лица бота."""
    bot = get_bot()
    try:
        filename = file.name
        save_path = os.path.join(PDF_FILES, file.name)
        with open(save_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
            logger.info(f'File saved: {filename}')

    except Exception as e:
        logger.error(f'Error saving file: {e}')

    with open(save_path, 'rb') as f:
        pdf_message = await bot.send_document(
            chat_id=SEARCH_CHAT_ID, document=f, filename=file.name
        )

    # Записываем в бд информацию о загруженном pdf
    user, _ = await ChatUser.objects.aget_or_create(
        telegram_id=bot_id,
        defaults={'username': bot_name},
        is_bot=True,
    )

    pdf_upload = await PDFUpload.objects.acreate(
        file_id='',
        request=request,
        user=user,
        message_id=pdf_message.message_id,
        state='uploaded',
        path=save_path,
    )
    logger.info(f'PDF information is recorded in the db {pdf_upload}')
    await send_verification_message(pdf_upload)


def check_and_award_subscription(chat_user, count):
    """
    Проверяет достиг ли пользователь порога загрузок (Z) или проверок (H).
    Выдаёт подписку, если достиг. Записывает информацию в базу данных.
    """
    config = Config.objects.first()
    if not config:
        return False

    if chat_user.is_bot:
        return False

    if not check_is_user(chat_user):
        return False

    awarded = False

    # количество загрузок - для подписки
    z = config.uploads_for_subscription
    # количество проверок  - для подписки
    h = config.validations_for_subscription

    if z != 0 and count.upload_count >= z:
        # Количество подписок пользователя (в количестве месяцев: 1, 2 и т.д.)
        count_sub_upl = count.upload_count // z
        # оставшееся количество загрузое пользователя
        upl_c_remain = count.upload_count % z
        new_data = award_subscription(chat_user, 'uploads', count_sub_upl)
        if new_data:
            count.upload_count = upl_c_remain
            count.subscriptions_for_upload += count_sub_upl
            count.save()
            awarded = True

    if h != 0 and count.validation_count >= h:
        # Количество подписок пользователя (в количестве месяцев: 1, 2 и т.д.)
        count_sub_val = count.validation_count // h
        # оставшееся количество проверок пользователя
        val_c_remain = count.validation_count % h
        new_data = award_subscription(chat_user, 'validations', count_sub_val)
        if new_data:
            count.validation_count = val_c_remain
            count.subscriptions_for_validation += count_sub_val
            count.save()
            awarded = True

    if awarded:
        Subscription.objects.update_or_create(
            user=chat_user,
            defaults={
                'start_date': new_data['start_at'],
                'end_date': new_data['end_at'],
            },
        )

    return awarded


async def send_verification_message(pdf_upload):
    """Отправляет сообщение с кнопками для голосования по PDF в общий чат."""

    bot = get_bot()
    # Если есть запрос на статью с таким DOI,
    # то отправляется сообщение с кнопками в ответ на PDF
    message = await bot.send_message(
        chat_id=SEARCH_CHAT_ID,
        text=f'Пожалуйста, проверьте PDF. Запрос: https://doi.org/{pdf_upload.request.doi}',
        reply_to_message_id=pdf_upload.message_id,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        '✅ Всё верно',
                        callback_data=f'vote_valid:{pdf_upload.id}',
                    ),
                    InlineKeyboardButton(
                        '❌ PDF неверный',
                        callback_data=f'vote_invalid:{pdf_upload.id}',
                    ),
                ]
            ]
        ),
    )
    pdf_upload.reply_to_message_id = message.message_id
    await pdf_upload.asave()
    logger.info(
        f'Verification message sent for article, DOI: {pdf_upload.request.doi}'
    )


async def send_thank_message(user, action):
    """
    Отправляет благодарственные сообщения пользователям
    за загрузку или проверку PDF.
    Сохраняет информацию в бд.
    """
    # Проверяем наличие юзера в канале
    result = check_is_user(user)
    count = await Count.objects.filter(user=user).afirst()
    N = count.upload_count if action == 'upload' else count.validation_count
    if not result:
        # Отправляем благодарственное сообщение в общий чат
        # для пользователя (не состоит в канале)
        if action == 'upload':
            words_action = 'поделившись исследованием'
        elif action == 'validation':
            words_action = 'проверив исследование'
        text = f'@{user.username}, Вы помогли {N} {form_word(N)} (всего), {words_action}! Зайдите в {BOT_NAME_SCISOURCE} для того, чтобы получить награду.'

        thank_message = await bot.send_message(
            chat_id=SEARCH_CHAT_ID, text=text
        )
        # Сохраняем информацию о блогодарственном сообщении
        # (за загрузку pdf/за проверку pdf) в бд
        notification = Notification(
            user=user,
            chat_id=SEARCH_CHAT_ID,
            chat_message_id=thank_message.message_id,
            type=action,
        )
        await notification.asave()
    elif not user.is_bot:
        config = await Config.objects.afirst()
        if action == 'upload':
            count, limit = count.upload_count, config.uploads_for_subscription
        elif action == 'validation':
            count, limit = (
                count.validation_count,
                config.validations_for_subscription,
            )

        data = send_count(
            user, count=count, count_type=action, limit=limit  # для подписки
        )
        if data['message_id'] > 0:
            # Сохраняем информацию о благодарственном сообщении в бд.
            # Пользователь состоит в канале
            notification = Notification(
                user=user,
                chat_id=data['chat_id'],
                chat_message_id=data['message_id'],
                type=action,
            )
            await notification.asave()
