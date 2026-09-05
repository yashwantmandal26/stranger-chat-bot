import os
from pathlib import Path
from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Load variables from .env file if it exists
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token (from @BotFather)
_raw_token = os.getenv("BOT_TOKEN", "8640606254:AAG-Zxv7IMFgMAJ89blGB-d8ByQPJkzqQcI").strip().strip("'\"")
# Clean up if token was pasted with extra whitespace or adjacent values
if " " in _raw_token:
    _raw_token = _raw_token.split()[0]
BOT_TOKEN: str = _raw_token

# Admin Telegram ID (for administrative commands like /activate and /stats)
_admin_id_raw = os.getenv("ADMIN_ID", "8548848788").strip().strip("'\"")
if " " in _admin_id_raw:
    _admin_id_raw = _admin_id_raw.split()[-1]
ADMIN_ID: int = int(_admin_id_raw) if _admin_id_raw.isdigit() else 8548848788

# Admin UPI ID for premium payments
ADMIN_UPI_ID: str = os.getenv("ADMIN_UPI_ID", "admin@upi").strip().strip("'\"")

# Async SQLite Database file path
DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "stranger_chat.db")).strip().strip("'\"")

# Account age restriction (in days)
MIN_ACCOUNT_AGE_DAYS: int = int(os.getenv("MIN_ACCOUNT_AGE_DAYS", "30").strip().strip("'\""))

# Web Server & Webhook configuration (for Render / cloud deployments)
_port_raw = os.getenv("PORT", "8080").strip().strip("'\"")
PORT: int = int(_port_raw) if _port_raw.isdigit() else 8080

_raw_webhook = os.getenv(
    "WEBHOOK_URL",
    "https://stranger-chat-bot-nc5o.onrender.com",
).strip().strip("'\"")
WEBHOOK_URL: str = _raw_webhook
