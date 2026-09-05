import os
from pathlib import Path
from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Load variables from .env file if it exists
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token (from @BotFather)
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

# Admin Telegram ID (for administrative commands like /activate)
_admin_id_raw = os.getenv("ADMIN_ID", "0").strip()
ADMIN_ID: int = int(_admin_id_raw) if _admin_id_raw.isdigit() else 0

# Admin UPI ID for premium payments
ADMIN_UPI_ID: str = os.getenv("ADMIN_UPI_ID", "admin@upi").strip()

# Async SQLite Database file path
DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "stranger_chat.db")).strip()

# Account age restriction (in days)
MIN_ACCOUNT_AGE_DAYS: int = int(os.getenv("MIN_ACCOUNT_AGE_DAYS", "30").strip())
