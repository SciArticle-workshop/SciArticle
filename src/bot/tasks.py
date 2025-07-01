import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from django.utils import timezone

from bot.utils import get_bot
from bot.models import ChatUser, Notification, PDFUpload, Request
from sciarticle.settings import SEARCH_CHAT_ID

from .scisource_client import check_is_user, send_request, send_thank_message
from .services import delete_message_and_file

logger = logging.getLogger(__name__)

bot = get_bot()


@shared_task
def request_pdf_task(chat_id, message_id, doi, username, message_search_id):
    """
    Обрабатывает запросы на статьи по DOI и сохраняет их в базу данных.
    Проверяет на дубликаты.
    """
    chat_user, _ = ChatUser.objects.get_or_create(
        telegram_id=chat_id, defaults={'username': username}
    )

    # Проверка на наличие в базе даных запроса по DOI у пользователя
    if Request.objects.filter(
        chat_id=chat_id, doi=doi, status=('pending')
    ).exists():
        logger.info(
            f"Repeated request from user in chat_id={chat_id}: don't save to db"
        )
        return None, None

    is_duplicate = Request.objects.filter(doi=doi, status=('pending')).exists()

    # Записываем запрос в бд
    request_obj = Request.objects.create(
        doi=doi,
        status='pending',
        chat_id=chat_id,
        user=chat_user,
        message_id=message_id,
        message_search_id=message_search_id,
    )
    logger.info(f'Request recorded in the db {request_obj}')

    # Проверка на наличие в базе данных запроса по DOI от разных пользователей
    # и запись в бд при наличии
    if is_duplicate:
        return {'code': 'repeated request', 'id': request_obj.id}, request_obj

    # Если статьи нет в базе данных
    return {'code': 'new request', 'id': request_obj.id}, request_obj


@shared_task
def run_check():
    """
    Ищет все запросы, которые истекли,
    но статус еще не сменился (прошло 47 часов).
    """
    expired_requests = Request.objects.filter(
        expires_at__lt=timezone.now(), status='pending'
    ).order_by('id')
    logger.info(f"Update request status {expired_requests} on 'expired'")

    for request in expired_requests:
        is_ok = request.message_search_id == 0 or send_request(request)
        if is_ok:
            Request.objects.filter(doi=request.doi, status='pending').update(
                status='expired'
            )
    return True


@shared_task
def run_check_and_delete_pdf():
    """
    Ищет все pdf файлы, у которых истек срок годности и
    их пора удалить из общего чата (прошло 47 часов).
    """
    files_uploaded = PDFUpload.objects.filter(
        delete_at__lt=timezone.now(), state__in=['uploaded', 'validated']
    ).order_by('id')

    for pdf in files_uploaded:
        try:
            async_to_sync(delete_message_and_file)(
                pdf, pdf.state == 'uploaded'
            )
        except Exception as e:
            logger.error(f'Error deleting message {pdf.message_id}: {e}')


@shared_task
def run_check_and_delete_thank_message():
    """
    Ищет все благодарственные сообщения, срок годности которых истек (1 час).
    Удаляет сообщения из бд. Выполняется логика по удалению этих сообщений
    из общего чата и лички с ботом @SciSourceBot.
    """
    now = timezone.now()
    notifications_expired = Notification.objects.filter(
        delete_at__lt=now
    ).select_related('user')

    for notification in notifications_expired:
        try:
            chat_id = notification.chat_id
            if chat_id == SEARCH_CHAT_ID:
                async_to_sync(bot.delete_message)(
                    chat_id=SEARCH_CHAT_ID,
                    message_id=notification.chat_message_id,
                )
                logger.info(
                    f'Thank message deleted: {notification.chat_message_id}'
                )
                # Вызываем функцию, которая проверяет
                # зашел ли пользователь в бота
                new_result = check_is_user(notification.user)
                # Если пользователь за 1 час так и не зашел в бота за наградой
                if not new_result:
                    count_type = notification.type
                    if count_type == 'upload':
                        # Обнуляем в бд его счетчик загрузок
                        notification.user.upload_count = 0
                    else:
                        # Обнуляем в бд его счетчик проверок
                        notification.user.validation_count = 0
                    notification.user.save()
            else:
                send_thank_message(notification)
            # Удаляем из бд благодарственное сообщение
            notification.delete()
        except Exception as e:
            logger.error(
                f'Failed to delete thank message {notification.chat_message_id}: {e}'
            )
