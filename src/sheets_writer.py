import logging
import datetime

import gspread
from google.oauth2 import service_account
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound, APIError

from .config import GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH
from .sheet_stats import update_monthly_stats

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HEADERS = ["Timestamp", "UserID", "Amount", "Category", "Description"]

def _get_gspread_client():
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    try:
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH,
            scopes=scopes
        )
        client = gspread.authorize(credentials)
        return client
    except FileNotFoundError:
        logger.error(f"Service account credentials file not found at {GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH}")
    except Exception as e:
        logger.error(f"Failed to authenticate with Google Sheets API: {e}")
    return None

def write_expenses_to_sheet(expenses: list[dict], spreadsheet_id: str) -> dict | None:
    """
    Writes expenses to the appropriate monthly sheet and returns the updated stats.

    Args:
        expenses: A list of expense dictionaries.
        spreadsheet_id: The Google Sheet ID.

    Returns:
        A dictionary containing the updated stats {'total': ..., 'limit': ..., 'left': ...}
        or None if an error occurred.
    """
    if not expenses:
        logger.warning("No expenses to write to sheet")
        return None

    client = _get_gspread_client()
    if not client:
        logger.error("Google Sheets client authentication failed.")
        return None

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except SpreadsheetNotFound:
        logger.error(f"Spreadsheet with ID '{spreadsheet_id}' not found.")
        return None
    except APIError as e:
        logger.error(f"API error when accessing spreadsheet: {e}")
        return None

    # Get month and year from first expense's timestamp
    first_expense = expenses[0]
    timestamp = first_expense.get("timestamp")
    if not isinstance(timestamp, datetime.datetime):
        logger.error("First expense timestamp is not a datetime object")
        return None
        
    sheet_name = timestamp.strftime('%m-%Y')  # Format: MM-YYYY

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except WorksheetNotFound:
        logger.info(f"Worksheet '{sheet_name}' not found. Creating new monthly sheet.")
        try:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="10")
            worksheet.append_row(HEADERS)
        except APIError as e:
            logger.error(f"Failed to create worksheet '{sheet_name}': {e}")
            return None
    except APIError as e:
        logger.error(f"API error when accessing worksheet: {e}")
        return None

    # Check headers
    try:
        existing_headers = worksheet.row_values(1)
    except APIError as e:
        logger.error(f"API error when reading headers: {e}")
        return None
    except Exception:
        existing_headers = []

    if existing_headers != HEADERS:
        if not existing_headers:
            try:
                worksheet.append_row(HEADERS)
                logger.info("Inserted headers into empty worksheet.")
            except APIError as e:
                logger.error(f"Failed to insert headers: {e}")
                return None
        else:
            try:
                worksheet.insert_row(HEADERS, 1)
                logger.info("Prepended headers to worksheet.")
            except APIError as e:
                logger.error(f"Failed to prepend headers: {e}")
                return None

    # Prepare data rows
    formatted_data = []
    for expense in expenses:
        timestamp = expense.get("timestamp")
        if isinstance(timestamp, datetime.datetime):
            timestamp_str = timestamp.strftime('%d/%m/%Y %H:%M:%S')
        else:
            timestamp_str = str(timestamp) if timestamp is not None else ""

        row = [
            timestamp_str,
            str(expense.get("user_id", "")),
            expense.get("amount", ""),
            expense.get("category", ""),
            expense.get("description", "")
        ]
        formatted_data.append(row)

    try:
        worksheet.append_rows(formatted_data, value_input_option='USER_ENTERED')
        logger.info(f"Successfully appended {len(formatted_data)} expense records to sheet '{sheet_name}'.")
        
        # Update stats after appending data and get the results
        stats = update_monthly_stats(worksheet)

        return stats # Return the stats dictionary
    except APIError as e:
        logger.error(f"Failed to append expenses to sheet: {e}")
        return None