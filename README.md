# Telegram Expense Tracker

A simple Telegram bot to track personal expenses using LLM parsing.

## Features

- Add expenses via text messages, parsed with an LLM (OpenRouter API).
- **Supports parsing multiple expenses from a single message.** The bot uses an LLM to extract multiple expenses from one text input, returning a list of expenses with amount, category (mapped to predefined categories), optional description, and optional date.
- Modular, clean architecture following SOLID principles.

## Project Structure

```
bot.py               # Main entry point: initializes and runs the bot
config.py            # Loads configuration from environment variables
config.py.example    # Example config file
handlers.py          # Telegram command and message handlers
llm_parser.py        # LLM API interaction logic
requirements.txt     # Python dependencies
README.md            # Project documentation
```

## Configuration

Set the following environment variables **or** edit `config.py` (copy from `config.py.example`):

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `OPENROUTER_API_URL`: (optional) Defaults to OpenRouter API URL
- `LLM_MODEL`: (optional) Defaults to `openai/gpt-4o`
- `YOUR_SITE_URL`: (optional) For OpenRouter headers
- `YOUR_SITE_NAME`: (optional) For OpenRouter headers
- `GOOGLE_SHEET_ID`: The ID of your Google Spreadsheet (found in the URL)
- `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH`: Path to your Google Cloud service account JSON key file

### Google Sheets API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable the **Google Sheets API** and **Google Drive API**.
4. Go to **APIs & Services > Credentials**.
5. Click **Create Credentials > Service Account**.
6. Grant it the "Editor" role (or customize permissions).
7. After creating, go to the service account, then **Keys > Add Key > Create new key**, select **JSON**, and download the file.
8. Save this JSON file securely and set the `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH` to its path.
9. Copy the **service account email** and share your Google Sheet with this email (Viewer or Editor access).


## Setup

1. Install dependencies:

```
pip install -r requirements.txt

The required libraries for Google Sheets integration (`gspread`, `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`) are included in `requirements.txt`.
```

2. Set environment variables or configure `config.py`.

3. Run the bot:

```
python bot.py
```

## Notes

- Expenses are now automatically organized into monthly sheets (MM-YYYY format) in Google Sheets.