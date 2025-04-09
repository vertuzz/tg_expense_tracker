import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from . import config
from .handlers import start, handle_message, error_handler, set_spreadsheet_id
from .database import init_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Start the Telegram Expense Tracker bot."""
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("ERROR: Please set your TELEGRAM_BOT_TOKEN in environment or config.py")
        return

    init_db()

    # Create the Telegram application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setsheet", set_spreadsheet_id))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_message))

    # Register error handler
    application.add_error_handler(error_handler)

    logger.info("Starting bot polling...")
    application.run_polling()

if __name__ == "__main__":
    main()