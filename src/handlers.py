import logging
import re
import json
import telegram
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from .llm_parser import parse_expense_data, parse_expense_image_data
from .sheets_writer import write_expenses_to_sheet
from .database import User, get_db_session
from .config import GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH

logger = logging.getLogger(__name__)


async def _ensure_user_exists(user: telegram.User) -> None:
    session = get_db_session()
    try:
        existing_user = session.query(User).filter(User.id == user.id).first()
        if not existing_user:
            new_user = User(id=user.id, first_name=user.first_name)
            session.add(new_user)
            session.commit()
            logger.info(f"Added new user: {user.id} ({user.first_name})")
    finally:
        session.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    # Handle user creation
    user = update.effective_user
    await _ensure_user_exists(user)

    # Try to get service account email from credentials
    try:
        with open(GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH, 'r') as f:
            creds = json.load(f)
        service_account_email = creds['client_email']
    except FileNotFoundError:
        service_account_email = "[Could not load email - check bot configuration]"
        logger.error(f"Credentials file not found at {GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH}")
    except json.JSONDecodeError:
        service_account_email = "[Could not load email - invalid JSON format]"
        logger.error(f"Invalid JSON in credentials file at {GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH}")
    except KeyError:
        service_account_email = "[Could not load email - missing client_email]"
        logger.error(f"Missing client_email in credentials file at {GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH}")
    except Exception as e:
        service_account_email = "[Could not load email - unknown error]"
        logger.error(f"Error reading credentials: {e}")

    # Escape special characters for MarkdownV2
    def escape_markdown(text):
        # Escape all MarkdownV2 special characters with double backslashes
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

    message_text = fr"""
    *Welcome to Expense Tracker Bot\!* 🎉

    Here's how to get started:

    1️⃣ *Find your Google Sheet ID*:
    \- Open your Google Sheet
    \- The ID is in the URL: `https://docs\.google\.com/spreadsheets/d/YOUR\_SHEET\_ID/edit`

    2️⃣ *Set your Sheet ID*:
    Use the command:
    `/setsheet YOUR\_SHEET\_ID`
    or
    `/setsheet https://docs\.google\.com/spreadsheets/d/YOUR\_SHEET\_ID/edit`

    3️⃣ *Share your Sheet*:
    \- Click "Share" in your Google Sheet
    \- Add this email as *Editor*:
    `{escape_markdown(service_account_email)}`

    After setup, you can:
    \- Send text expenses like "Lunch $15"
    \- Or send receipt photos 📸

    Let's get started\! 💰
"""
    await update.message.reply_text(message_text, parse_mode=ParseMode.MARKDOWN_V2)
    await update.message.reply_text(service_account_email)

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
    
    session = get_db_session()
    try:
        user_record = session.query(User).filter(User.id == user.id).first()
        if not user_record or not user_record.spreadsheet_id:
            await message.reply_text("❌ Error: Please set your Google Sheet ID first using the /setsheet command.")
            logger.error(f"No spreadsheet_id set for user {user.id}")
            return
            
        # Try writing expenses and get stats
        stats = write_expenses_to_sheet(expense_dicts, spreadsheet_id=user_record.spreadsheet_id)
        if stats is None:
            await message.reply_text("❌ Error: Could not save expenses to Google Sheet. Please check configuration and sheet access.")
            return
    finally:
        session.close()

    details = "\n".join(
        f"• {e['amount']:.2f} in '{e['category']}'" + (f" ({e['description']})" if e.get('description') else "")
        for e in expense_dicts
    )
    
    # Prepare stats message
    stats_message = f"\n\n📊 Monthly Status:\n  Total: {stats.get('total', 'N/A')}\n  Limit: {stats.get('limit', 'N/A')}\n  Left:  {stats.get('left', 'N/A')}"

    await message.reply_text(f"✅ Added {len(expense_dicts)} expense(s) to Google Sheet:\n{details}{stats_message}")

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
        
        session = get_db_session()
        try:
            user_record = session.query(User).filter(User.id == user.id).first()
            if not user_record or not user_record.spreadsheet_id:
                await message.reply_text("❌ Error: Please set your Google Sheet ID first using the /setsheet command.")
                logger.error(f"No spreadsheet_id set for user {user.id}")
                return
                
            # Try writing expenses and get stats
            stats = write_expenses_to_sheet(expense_dicts, spreadsheet_id=user_record.spreadsheet_id)
            if stats is None:
                await message.reply_text("❌ Error: Could not save expenses to Google Sheet. Please check configuration and sheet access.")
                return
        finally:
            session.close()

        details = "\n".join(
            f"• {e['amount']:.2f} in '{e['category']}'" + (f" ({e['description']})" if e.get('description') else "")
            for e in expense_dicts
        )
        
        # Prepare stats message
        stats_message = f"\n\n📊 Monthly Status:\n  Total: {stats.get('total', 'N/A')}\n  Limit: {stats.get('limit', 'N/A')}\n  Left:  {stats.get('left', 'N/A')}"

        await message.reply_text(f"✅ Added {len(expense_dicts)} expense(s) from the image to Google Sheet:\n{details}{stats_message}")
    except Exception as e:
        logger.error(f"Error processing photo message: {e}", exc_info=True)
        await message.reply_text("❌ An error occurred while processing the image.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text or photo messages by dispatching to appropriate handlers."""
    message = update.message
    user = message.from_user
    
    # Check if user exists in database, create if not
    await _ensure_user_exists(user)

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

async def set_spreadsheet_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /setsheet command to update user's Google Sheet ID."""
    user = update.effective_user
    logger.info(f"Received /setsheet command from {user.id}")
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /setsheet <your_spreadsheet_id>")
        return
    
    input_value = context.args[0]
    # Check if input is a Google Sheet URL and extract ID if so
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", input_value)
    spreadsheet_id = match.group(1) if match else input_value
    session = get_db_session()
    try:
        db_user = session.query(User).filter(User.id == user.id).first()
        if not db_user:
            await update.message.reply_text("❌ Error: Could not find your user record. Please send any message first to register.")
            logger.error(f"User {user.id} not found in database")
            return
            
        db_user.spreadsheet_id = spreadsheet_id
        session.commit()
        await update.message.reply_text("✅ Spreadsheet ID updated successfully!")
        logger.info(f"Updated spreadsheet_id for user {user.id}")
    except Exception as e:
        await update.message.reply_text("❌ Error: Could not update spreadsheet ID. Please try again.")
        logger.error(f"Error updating spreadsheet_id for user {user.id}: {e}", exc_info=True)
    finally:
        session.close()