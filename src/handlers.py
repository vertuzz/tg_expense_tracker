import logging
from telegram import Update
from telegram.ext import ContextTypes
from .llm_parser import parse_expense_data, parse_expense_image_data
from .sheets_writer import write_expenses_to_sheet
from .llm_parser import parse_expense_data, parse_expense_image_data

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    await update.message.reply_text('Hello! Send me your expense details or photos of receipts.')

async def _process_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes text messages containing expense data."""
    message = update.message
    user = message.from_user
    logger.info(f"Text message from {user.id}: {message.text}")
    
    expenses = await parse_expense_data(message.text, user.id)
    if not expenses:
        await message.reply_text("❌ Error: Could not understand expense details from your message.")
        return

    expense_dicts = [e if isinstance(e, dict) else e.__dict__ for e in expenses]
    success = write_expenses_to_sheet(expense_dicts)
    if not success:
        await message.reply_text("❌ Error: Could not save expenses to Google Sheet. Please check configuration and sheet access.")
        return

    details = "\n".join(
        f"• {e['amount']:.2f} in '{e['category']}'" + (f" ({e['description']})" if e.get('description') else "")
        for e in expense_dicts
    )
    await message.reply_text(f"✅ Added {len(expense_dicts)} expense(s) to Google Sheet:\n{details}")

async def _process_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes photo messages containing receipt images."""
    message = update.message
    user = message.from_user
    logger.info(f"Received photo message from {user.id}")
    await message.reply_text("⏳ Analyzing image for expenses...")

    try:
        photo = message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        expenses = await parse_expense_image_data(image_bytes=image_bytes, user_id=user.id)
        if not expenses:
            await message.reply_text("❌ Error: Could not extract expenses from the image. Please ensure it's clear.")
            return

        expense_dicts = [e if isinstance(e, dict) else e.__dict__ for e in expenses]
        success = write_expenses_to_sheet(expense_dicts)
        if not success:
            await message.reply_text("❌ Error: Could not save expenses to Google Sheet. Please check configuration and sheet access.")
            return

        details = "\n".join(
            f"• {e['amount']:.2f} in '{e['category']}'" + (f" ({e['description']})" if e.get('description') else "")
            for e in expense_dicts
        )
        await message.reply_text(f"✅ Added {len(expense_dicts)} expense(s) from the image to Google Sheet:\n{details}")
    except Exception as e:
        logger.error(f"Error processing photo message: {e}", exc_info=True)
        await message.reply_text("❌ An error occurred while processing the image.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text or photo messages by dispatching to appropriate handlers."""
    message = update.message
    user = message.from_user
    logger.info(f"Received message from {user.first_name}")

    if message.text:
        await _process_text_message(update, context)
    elif message.photo:
        await _process_photo_message(update, context)
    else:
        logger.info("Received non-text/non-photo message.")
        await message.reply_text("Sorry, I can only process text and photo messages for now.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)