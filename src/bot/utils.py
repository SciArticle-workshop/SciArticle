import os

from telegram import Bot

import logging

logger = logging.getLogger(__name__)


TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
if not TELEGRAM_TOKEN:
    logger.error('TELEGRAM_BOT_TOKEN is not set in environment variables')


def get_bot():
    return Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None


async def async_download_pdf(bot: Bot, file_id: str, file_path: str):
    """Загружает pdf-файл из Telegram и сохраняет его по указанному пути."""
    try:
        pdf_file = await bot.get_file(file_id)
        await pdf_file.download_to_drive(custom_path=file_path)
        logger.info(f'File saved to: {file_path}')
        return True
    except Exception as e:
        logger.error(f'Failed to download file: {e}')
        return False


def form_word(N):
    """Возвращает правильную форму слова."""
    # Для 0 <=0 N < inf
    if 11 <= N % 100 <= 14:
        return 'раз'
    if 2 <= N % 10 <= 4:
        return 'раза'
    return 'раз'
