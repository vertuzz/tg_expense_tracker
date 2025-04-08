# Telegram Expense Tracker

A simple Telegram bot to track personal expenses using SQLite, SQLAlchemy, and LLM parsing.

## Features

- Add expenses via text messages, parsed with an LLM (OpenRouter API).
- **Supports parsing multiple expenses from a single message.** The bot uses an LLM to extract multiple expenses from one text input, returning a list of expenses with amount, category (mapped to predefined categories), optional description, and optional date.
- Stores data in SQLite via SQLAlchemy ORM.
- Modular, clean architecture following SOLID principles.

## Project Structure

```
bot.py               # Main entry point: initializes and runs the bot
config.py            # Loads configuration from environment variables
config.py.example    # Example config file
crud.py              # Database CRUD operations
database.py          # SQLAlchemy engine, session, and init_db()
handlers.py          # Telegram command and message handlers
llm_parser.py        # LLM API interaction logic
models.py            # SQLAlchemy ORM models (Expense)
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

## Database Models

### Expense

| Column        | Type        | Description                               |
|---------------|-------------|-------------------------------------------|
| `id`          | Integer     | Primary key, autoincrement                |
| `user_id`     | Integer     | Telegram user ID, indexed                 |
| `amount`      | Float       | Expense amount, required                  |
| `category`    | String(50)  | Expense category, required                |
| `description` | String      | Optional description                      |
| `timestamp`   | DateTime    | Defaults to current UTC timestamp         |

## Database Initialization

The database is initialized automatically when running the bot via:

```python
from database import init_db
init_db()
```

## Setup

1. Install dependencies:

```
pip install -r requirements.txt
```

2. Set environment variables or configure `config.py`.

3. Run the bot:

```
python bot.py
```

## Notes

- The database uses SQLite (`expenses.db`).
- Designed for easy extension with more models (e.g., Income).