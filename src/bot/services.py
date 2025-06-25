import logging

from django.conf import settings

import requests

from bot.models import Config

logger = logging.getLogger(__name__)


def check_and_award_subscription(chat_user):
    """Проверяет, достиг ли пользователь порога загрузок (Z) или проверок (H),
    и выдаёт подписку, если достиг.
    """
    config = Config.objects.first()
    if not config:
        return False

    awarded = False

    z = config.uploads_for_subscription
    if z and chat_user.upload_count and chat_user.upload_count % z == 0:
        award_subscription(chat_user, reason="uploads")
        awarded = True

    h = config.validations_for_subscription
    if (
        h
        and chat_user.validation_count
        and chat_user.validation_count % h == 0
    ):
        award_subscription(chat_user, reason="validations")
        awarded = True

    return awarded


def award_subscription(chat_user, reason):
    """
    Отправляет запрос на выдачу подписки в основной бот SciSourceBot.
    """
    # Проверяем, что URL сервера scisource настроен
    if not settings.SCISOURCE_SERVER_URL:
        logger.error("SCISOURCE_SERVER_URL is not configured in settings.")
        return
    # Формируем URL для API запроса
    api_url = f"{settings.SCISOURCE_SERVER_URL}/api/grant-subscription/"
    payload = {"telegram_id": chat_user.telegram_id, "reason": reason}
    # Отправляем POST запрос в scisource для выдачи подписки
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(
            f"Successfully requested subscription for user {chat_user.telegram_id} via API. Status: {response.status_code}"
        )

    except requests.exceptions.RequestException as e:
        logger.error(
            f"Failed to request subscription for user {chat_user.telegram_id}. Error: {e}"
        )
