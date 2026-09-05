# 🎭 Stranger Chat Bot

A high-performance, asynchronous Telegram bot built with **Python 3.10+**, **aiogram 3.x**, and **aiosqlite**. Connects strangers worldwide for 100% anonymous, safe, and real-time conversations.

---

## ✨ Features

- **🛡️ Safety First Account Verification**: Automatically estimates Telegram account age on `/start`. Accounts younger than 30 days are blocked to prevent spam and bot farms.
- **👫 Opposite-Gender Matchmaking**: Pairs users based on gender preference (`male` <-> `female`) via a lock-protected priority virtual queue.
- **⭐ VIP Priority Queue**: Premium users receive priority matching ahead of free users.
- **🕵️ 100% Anonymous Forwarding**: Messages and media (text, photos, voice notes, stickers, videos, GIFs, documents, video notes) are copied directly via Telegram's `copy_message` without revealing user profiles or forward headers.
- **⏭️ Fast Skip & Exit**: `/next` disconnects and instantly puts the user back in line for a new partner; `/stop` ends the chat immediately.
- **⏳ Inactivity Auto-Closer**: Background async worker checks every 30 seconds and closes conversations idle for 10+ minutes.
- **📊 Admin Dashboard (`/stats`)**: Displays total users, gender breakdown, active chats, and live queue status (restricted to `ADMIN_ID`).
- **🚀 Viral Share (`/invite`)**: Generates pre-written messages with a one-tap Telegram share button.
- **🛡️ Global Error Resilience**: Comprehensive `@dp.error()` handler ensures the bot catches unexpected runtime exceptions without crashing.

---

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **Framework**: [`aiogram 3.x`](https://docs.aiogram.dev/)
- **Database**: [`aiosqlite`](https://github.com/omnilib/aiosqlite) (Async SQLite with WAL mode)
- **Configuration**: [`python-dotenv`](https://github.com/theskumar/python-dotenv)

---

## 📁 Project Structure

```
├── .env.example              # Template environment variables
├── .gitignore                 # Protects secrets, local databases, and caches
├── account_age.py             # User ID milestone interpolation & age estimator
├── config.py                  # App configuration loader
├── database.py                # Async SQLite operations and schema setup
├── inactivity.py              # 10-minute inactivity cleaner background task
├── keyboards.py               # Inline keyboards (Gender, Search, Welcome, Share)
├── main.py                    # Bot runner, command menu, and error handler
├── match_queue.py             # Thread-safe asyncio virtual queue manager
├── requirements.txt           # Python dependencies
└── data/
    └── id_checkpoints.json    # Telegram user ID milestone dataset
```

---

## 🚀 Getting Started

### 1. Clone & Setup Environment

```bash
git clone <your-repo-url>
cd TelegramCHATbot
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file based on `.env.example`:

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=your_numeric_telegram_user_id
ADMIN_UPI_ID=your_upi_id@bank
DB_PATH=stranger_chat.db
MIN_ACCOUNT_AGE_DAYS=30
```

### 4. Run the Bot

```bash
python main.py
```

---

## 🤖 Bot Commands

| Command | Description |
|---|---|
| `/start` | View welcome greeting, rules, and status |
| `/find` | Search for an opposite-gender partner |
| `/next` | Skip current stranger and find a new partner |
| `/stop` | End active chat or cancel queue search |
| `/gender` | View or change your gender preference |
| `/invite` | Share the bot with friends via Telegram |
| `/help` | Display command guide and community rules |
| `/stats` | *(Admin only)* View live bot analytics and queue stats |

---

## 📄 License

MIT License. Free for personal and commercial use.
