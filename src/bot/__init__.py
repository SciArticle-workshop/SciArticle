from django.conf import settings
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters


def setup_bot():
    """Set up the Telegram bot with all handlers."""
    # Import handlers here to avoid circular imports
    from src.bot.handlers.callback_handlers import handle_pdf_verification
    from src.bot.handlers.handlers import handle_pdf_file

    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    # ... (other command handlers)

    # File handlers
    application.add_handler(MessageHandler(filters.Document.ALL, handle_pdf_file))

    # Callback handlers
    application.add_handler(CallbackQueryHandler(handle_pdf_verification, pattern=r"^pdf_verify_"))

    return application


def get_bot_application():
    """Get or create the bot application instance."""
    # This helps avoid circular imports and defers initialization
    return setup_bot()
