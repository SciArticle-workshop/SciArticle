import re
import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.tasks import check_pdf_file
from sciarticle.settings import DOI_REGEX_WITH_SPACE, SEARCH_CHAT_ID

logger = logging.getLogger(__name__)


def get_doi_from_filename(name: str):
    """Извлекает DOI (/ заменен на ' ') из названия файла и преобразет в правильный формат (c /)."""
    doi_in_filename = name.rsplit('.', 1)[0].strip()
    match = re.search(DOI_REGEX_WITH_SPACE, doi_in_filename)
    if match:
        doi_in_name = match.group(0)
        return doi_in_name.replace(' ', '/')


async def pdf_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    # Проверяем, что пользователь отправил именно pdf файл
    if not document or document.mime_type != 'application/pdf':
        logger.warning("Sent not pdf file")
        return
    file_id = document.file_id
    file_name = document.file_name
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    username = update.message.from_user.username

    # Получаем DOI из имени файла (уже приведенный к правельному формату)
    doi = get_doi_from_filename(file_name)
    # Если имя файла не соответствует формату, то удаляем сообщение с этим файлом
    if not doi:
        logger.warning("File name must contain DOI")
        try:
            await context.bot.delete_message(chat_id=SEARCH_CHAT_ID,
                                             message_id=message_id)
            logger.info(
                f"Message: {message_id} removed because file name is incorrect"
            )
        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
        return

    await check_pdf_file(file_id=file_id,
                         file_name=file_name,
                         user_id=user_id,
                         message_id=message_id,
                         username=username,
                         doi=doi)
