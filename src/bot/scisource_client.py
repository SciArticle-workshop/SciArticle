import logging
import requests

from sciarticle.settings import API_SECRET_TOKEN, SOURCE_SERVER_URL

logger = logging.getLogger(__name__)

headers = {
    'X-API-Token': API_SECRET_TOKEN
}


def send_request(request):
    """Отправляет post-запрос с информацией о истекший запросах."""
    data = {
        'message_id': request.message_id,
        'chat_id': request.chat_id,
        'message_search_id': request.message_search_id,
    }
    try:
        # Отправляем запрос на сервер первого бота
        response = requests.post(
            f'{SOURCE_SERVER_URL}/api/request-pdf-expired/',
            data=data,
            headers=headers
        )
        logger.info(f'{response} received')
        if response.status_code == 204:
            logger.info('Information about request/requests sent successfully')
            return True
        else:
            logger.error(f'Service is not available:{response.status_code}')
            return False

    except Exception as e:
        logger.error(f'En error occurred while sending request: {e}')
        return False


def renew_request(new_request):
    """
    Отправляет запрос с информацией для новой публикации запроса в общем чате.
    """
    data = {'doi': new_request.doi}

    try:
        # Отправляем запрос на сервер первого бота
        response = requests.post(
            f'{SOURCE_SERVER_URL}/api/new_request-pdf/',
            data=data,
            headers=headers
        )
        logger.info(f'{response} received')
        if response.status_code == 200:
            new_request.message_search_id = response.json()['message_id']
            logger.info('Information about not found request')
            return True

        logger.error(f'Service is not available:{response.status_code}')
        return False

    except Exception as e:
        logger.error(f'En error occurred while sending request: {e}')
        return False


def check_is_user(user):
    """
    Проверяет наличие пользователя в боте @SciSourceBot (подписан на канал).
    """
    try:
        # Отправляем запрос на сервер первого бота
        response = requests.get(
            f'{SOURCE_SERVER_URL}/api/tg_user/{user.telegram_id}',
            headers=headers
        )
        logger.info(f'{response} received')
        if response.status_code == 200:
            logger.info('User found')
            return True
        else:
            logger.info('User not found')
            return False

    except Exception as e:
        logger.error(f'En error occurred while sending request: {e}')
        return False


def send_count(user, count, count_type, limit):
    """
    Отправляет информацию про загрузки и валидацию пользоватей,
    которые есть в SciSourceBot (состоят в канале).
    """
    data = {
        'count': count,
        'chat_id': user.telegram_id,
        'count_type': count_type,
        'limit': limit,
    }
    try:
        # Отправляем запрос на сервер первого бота
        response = requests.post(
            f'{SOURCE_SERVER_URL}/api/user_counters/',
            data=data,
            headers=headers
        )
        logger.info(f'{response} received')
        if response.status_code == 200:
            logger.info(
                'Information about the upload_count/validation_count of user sent successfully'
            )
            return response.json()
        else:
            logger.error(f'Service is not available:{response.status_code}')
            return None

    except Exception as e:
        logger.error(f'En error occurred while sending request: {e}')
        return None


def send_pdf(pdfupload):
    """Отправляет post-запрос, который содержит файл и данные."""
    request = pdfupload.request
    data = {
        'message_id': pdfupload.message_id,
        'chat_id': request.chat_id,
        'doi': request.doi,
    }
    with open(pdfupload.path, 'rb') as f:
        files = {'file': ('document.pdf', f, 'application/pdf')}

        response = requests.post(
            f'{SOURCE_SERVER_URL}/api/upload-pdf/',
            data=data,
            files=files,
            headers=headers
        )
        if response.status_code == 200:
            logger.info('File and data sent successfully')
        else:
            logger.error(f'Service is not available:{response.status_code}')


def send_thank_message(notification):
    """
    Отправляет post-запрос, содержащий информацию о благодарственных
    сообщениях, которые пора удалить.
    """
    data = {
        'message_id': notification.chat_message_id,
        'chat_id': notification.chat_id,
    }
    try:
        # Отправляем запрос на сервер первого бота
        response = requests.post(
            f'{SOURCE_SERVER_URL}/api/thank_message_delete/',
            data=data,
            headers=headers
        )
        logger.info(f'{response} received')
        if response.status_code == 204:
            logger.info('Information about thank message sent successfully')
            return True
        else:
            logger.error(f'Service is not available:{response.status_code}')
            return False

    except Exception as e:
        logger.error(f'En error occurred while sending request: {e}')
        return False


def award_subscription(chat_user, reason, amount):
    """
    Отправляет запрос на выдачу подписки в основной бот SciSourceBot.
    Получаем ответ с данными о подписке пользователя.
    Записываем информацию в бд.
    """
    # Проверяем, что URL сервера scisource настроен
    if not SOURCE_SERVER_URL:
        logger.error('SCISOURCE_SERVER_URL is not configured in settings.')
        return
    # Формируем URL для API запроса
    api_url = f'{SOURCE_SERVER_URL}/api/grant-subscription/'
    payload = {
        'telegram_id': chat_user.telegram_id,
        'reason': reason,
        'amount': amount,
    }
    # Отправляем POST запрос в scisource для выдачи подписки
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(
            f'Successfully requested subscription for user {chat_user.telegram_id} via API. Status: {response.status_code}'
        )
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(
            f'Failed to request subscription for user {chat_user.telegram_id}. Error: {e}'
        )
