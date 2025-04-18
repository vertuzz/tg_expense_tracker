import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

# OpenRouter API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "YOUR_OPENROUTER_API_KEY")

# OpenRouter API URL
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")

# LLM Model
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-4-maverick:free")

# Site URL and Name for OpenRouter headers
YOUR_SITE_URL = os.getenv("YOUR_SITE_URL", "http://localhost")
YOUR_SITE_NAME = os.getenv("YOUR_SITE_NAME", "TelegramExpenseBot")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///user_data.db")

# Google Sheets Configuration
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH = os.getenv("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH", "creds.json")  # Path to your service account JSON key file

# Expense Categories
EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "Utilities",
    "Entertainment",
    "Shopping",
    "Health",
    "Groceries",
    "Rent/Mortgage",
    "Subscriptions",
    "Other"
]