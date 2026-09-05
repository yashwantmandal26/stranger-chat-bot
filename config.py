import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Load variables from .env file if it exists locally
load_dotenv(BASE_DIR / ".env")

# Verified default fallbacks for Stranger Chat Bot
_DEFAULT_BOT_TOKEN = "8640606254:AAG-Zxv7IMFgMAJ89blGB-d8ByQPJkzqQcI"
_DEFAULT_ADMIN_ID = 8548848788
_DEFAULT_WEBHOOK_URL = "https://stranger-chat-bot-nc5o.onrender.com"

# 1. Telegram Bot Token extraction
_raw_env_token = os.getenv("BOT_TOKEN", "").strip()
_token_match = re.search(r"(\d{8,12}:[A-Za-z0-9_-]{35})", _raw_env_token)
if _token_match:
    BOT_TOKEN: str = _token_match.group(1)
else:
    # If BOT_TOKEN env var is missing, malformed, or includes extra text, use verified token
    BOT_TOKEN: str = _DEFAULT_BOT_TOKEN

# 2. Admin Telegram ID extraction
_raw_env_admin = os.getenv("ADMIN_ID", "").strip()
_admin_match = re.search(r"(\d{6,14})", _raw_env_admin)
if _admin_match:
    ADMIN_ID: int = int(_admin_match.group(1))
else:
    ADMIN_ID: int = _DEFAULT_ADMIN_ID

# 3. Admin UPI ID for premium payments
ADMIN_UPI_ID: str = os.getenv("ADMIN_UPI_ID", "admin@upi").strip().strip("'\"")

# 4. Async SQLite Database file path
DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "stranger_chat.db")).strip().strip("'\"")

# 5. Account age restriction (in days, default 0 for launch)
MIN_ACCOUNT_AGE_DAYS: int = int(os.getenv("MIN_ACCOUNT_AGE_DAYS", "0").strip().strip("'\""))

# 6. Web Server Port
_port_raw = os.getenv("PORT", "8080").strip().strip("'\"")
PORT: int = int(_port_raw) if _port_raw.isdigit() else 8080

# 7. Render Webhook URL
_raw_webhook = os.getenv("WEBHOOK_URL", "").strip().strip("'\"")
if _raw_webhook and _raw_webhook.startswith("http"):
    WEBHOOK_URL: str = _raw_webhook
else:
    WEBHOOK_URL: str = _DEFAULT_WEBHOOK_URL
