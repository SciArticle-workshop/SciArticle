import logging
import os
import sys

import django
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sciarticle.settings')
django.setup()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
if not TELEGRAM_TOKEN:
    logger.error('TELEGRAM_BOT_TOKEN is not set in environment variables')


from bot.handlers.callback_handlers import handle_vote_callback
from bot.handlers.handlers import pdf_file_handler


def main():
    """Main function to start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(
        MessageHandler(filters.Document.PDF, pdf_file_handler))

    application.add_handler(
        CallbackQueryHandler(handle_vote_callback, pattern='^vote_'))

    async def error_handler(update, context):
        logger.error(f'Update {update} caused error: {context.error}',
                     exc_info=context.error)

    application.add_error_handler(error_handler)

    application.run_polling()

    logger.info('Bot started')


if __name__ == '__main__':
    main()
