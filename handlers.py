import logging
from telegram import Update
from telegram.ext import ContextTypes
from llm_parser import parse_expense_data, parse_expense_image_data
from sheets_writer import write_expenses_to_sheet
from llm_parser import parse_expense_data, parse_expense_image_data

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    await update.message.reply_text('Hello! Send me your expense details or photos of receipts.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text or photo messages."""
    message = update.message
    user = message.from_user
    logger.info(f"Received message from {user.first_name}")

    if message.text:
        logger.info(f"Text message from {user.id}: {message.text}")
        expenses = await parse_expense_data(message.text, user.id)

        if expenses:
            # Convert expenses to dicts if needed
            expense_dicts = [e if isinstance(e, dict) else e.__dict__ for e in expenses]
            success = write_expenses_to_sheet(expense_dicts)
            if success:
                details = "\n".join(
                    f"• {e['amount']:.2f} in '{e['category']}'" + (f" ({e['description']})" if e.get('description') else "")
                    for e in expense_dicts
                )
                await message.reply_text(
                    f"✅ Added {len(expense_dicts)} expense(s) to Google Sheet:\n{details}"
                )
            else:
                await message.reply_text("❌ Error: Could not save expenses to Google Sheet. Please check configuration and sheet access.")
        else:
            await message.reply_text(
                "❌ Error: Could not understand expense details from your message."
            )

    elif message.photo:
        logger.info(f"Received photo message from {user.id}")
        await message.reply_text("⏳ Analyzing image for expenses...")

        photo = message.photo[-1]
        try:
            file = await context.bot.get_file(photo.file_id)
            image_bytes = await file.download_as_bytearray()

            expenses = await parse_expense_image_data(image_bytes=image_bytes, user_id=user.id)

            if expenses:
                expense_dicts = [e if isinstance(e, dict) else e.__dict__ for e in expenses]
                success = write_expenses_to_sheet(expense_dicts)
                if success:
                    await message.reply_text(f"✅ Added {len(expense_dicts)} expense(s) from the image to Google Sheet.")
                else:
                    await message.reply_text("❌ Error: Could not save expenses to Google Sheet. Please check configuration and sheet access.")
            else:
                await message.reply_text("❌ Error: Could not extract expenses from the image. Please ensure it's clear.")
        except Exception as e:
            logger.error(f"Error processing photo message: {e}", exc_info=True)
            await message.reply_text("❌ An error occurred while processing the image.")
    else:
        logger.info("Received non-text/non-photo message.")
        await message.reply_text("Sorry, I can only process text and photo messages for now.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)