import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import time

from . import config
from .handlers import start, handle_message, error_handler, set_spreadsheet_id
from .database import init_db, get_db_session, User

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send daily expense reminder to all registered users."""
    try:
        session = get_db_session()
        try:
            user_ids = session.query(User.id).all()
            for (user_id,) in user_ids:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="Remember to add your expenses for today!"
                    )
                except Exception as e:
                    logger.error(f"Failed to send reminder to user {user_id}: {e}")
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error in daily reminder job: {e}")

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

    # Schedule daily reminder using application's job queue
    job_queue = application.job_queue
    job_queue.run_daily(
        send_daily_reminder,
        time=time(hour=20, minute=0, second=0),
        job_kwargs={'misfire_grace_time': 15*60}
    )

    logger.info("Starting bot polling...")
    application.run_polling()

if __name__ == "__main__":
    main()