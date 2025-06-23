from telegram import Bot

import logging

logger = logging.getLogger(__name__)


async def async_download_pdf(bot: Bot, file_id: str, file_path: str):
    try:
        pdf_file = await bot.get_file(file_id)
        await pdf_file.download_to_drive(custom_path=file_path)
        logger.info(f"File saved to: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        return False


def form_word(N):
    # Для 0 < N <= 100
    if 2 <= N <= 4:
        return 'раза'
    elif 11 <= N <= 14:
        return 'раз'
    elif N >= 22 and 2 <= N % 10 <= 4:
        return 'раза'
    else:
        return 'раз'
