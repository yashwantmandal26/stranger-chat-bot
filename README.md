# 🎭 Stranger Chat Bot

A high-performance, asynchronous Telegram bot built with **Python 3.10+**, **aiogram 3.x**, and **aiosqlite**. Connects strangers worldwide for 100% anonymous, safe, and real-time conversations.

---

## ✨ Features

- **🛡️ Safety First Account Verification**: Automatically estimates Telegram account age on `/start`. Accounts younger than 30 days are blocked to prevent spam and bot farms.
- **📱 Persistent Mobile Keyboards**: 1-tap quick action buttons at the bottom of the screen (idle & active chat modes) so users never have to type slash commands.
- **🎲 Icebreaker Engine**: 30+ curated, engaging conversation starter prompts (`/icebreaker` or `🎲 Send Icebreaker`) to keep discussions lively and interesting.
- **👤 Anonymous Profile Card**: Clean badge displaying anonymous ID (`#SC-xxxxxx`), gender, membership tier, verified account age, chat count, and reputation (`/profile`).
- **🚨 Community Moderation**: Instant report button (`/report` or `🚨 Report User`) that records strikes and automatically bans repeat offenders at 3 strikes.
- **👫 Opposite-Gender Matchmaking**: Pairs users based on gender preference (`male` <-> `female`) via a lock-protected priority virtual queue.
- **⭐ VIP Priority Queue**: Premium users receive priority matching ahead of free users.
- **🕵️ 100% Anonymous Forwarding**: Messages and media (text, photos, voice notes, stickers, videos, GIFs, documents, video notes) are copied directly via Telegram's `copy_message` without revealing user profiles or forward headers.
- **⏭️ Fast Skip & Exit**: `/next` disconnects and instantly puts the user back in line for a new partner; `/stop` ends the chat immediately.
- **⏳ Inactivity Auto-Closer**: Background async worker checks every 30 seconds and closes conversations idle for 10+ minutes.
- **📊 Admin Dashboard (`/stats`)**: Displays total users, gender breakdown, active chats, and live queue status (restricted to `ADMIN_ID`).
- **🚀 Viral Share (`/invite`)**: Generates pre-written messages with a one-tap Telegram share button.
- **🌐 Built-in SEO & Web Landing**: Dark-mode glassmorphic HTML landing page served on `GET /` with OpenGraph meta tags, plus automatic Telegram Bot SEO descriptions (`set_my_description`, `set_my_short_description`) for maximum public reach.
- **🛡️ Global Error Resilience**: Comprehensive `@dp.error()` handler ensures the bot catches unexpected runtime exceptions without crashing.

---

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **Framework**: [`aiogram 3.x`](https://docs.aiogram.dev/)
- **Web Server**: [`aiohttp`](https://docs.aiohttp.org/) (Webhook handler & SEO landing page)
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
├── handlers.py                # Bot command & message handlers with persistent keyboards
├── icebreakers.py             # Curated conversation starter prompt engine
├── inactivity.py              # 10-minute inactivity cleaner background task
├── keyboards.py               # Reply and Inline keyboards (Idle, Chat, Gender, Welcome)
├── main.py                    # Webhook server, Telegram & Web SEO, startup lifecycle
├── match_queue.py             # Thread-safe asyncio virtual queue manager
├── requirements.txt           # Python dependencies
└── data/
    └── id_checkpoints.json    # Telegram user ID milestone dataset
```

---

## 🚀 Getting Started

### 1. Clone & Setup Environment

```bash
git clone https://github.com/yashwantmandal26/stranger-chat-bot.git
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
WEBHOOK_URL=https://your-service.onrender.com
PORT=8080
```

### 4. Run the Bot Locally

```bash
python main.py
```

---

## ☁️ Deploy on Render (Free Web Service)

Render's Web Services are **100% free** and act as an HTTP web server:

1. Create a new **Web Service** on [Render](https://dashboard.render.com/).
2. Connect your GitHub repository: `https://github.com/yashwantmandal26/stranger-chat-bot`.
3. Configure settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
4. Add **Environment Variables** in the Render Dashboard:
   - `BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_ID`: Your numeric Telegram ID (`8548848788`)
   - `WEBHOOK_URL`: `https://<your-service-name>.onrender.com`
   - `PORT`: (automatically set by Render, default: `8080`)
5. Click **Deploy Web Service**! Render will build the app, start the aiohttp server, verify the `GET /` health check landing page, and register the webhook with Telegram.

---

## 🤖 Bot Commands & Quick Buttons

| Command | Quick Button | Description |
|---|---|---|
| `/find` | `🔍 Find Stranger` | Search for an opposite-gender partner |
| `/next` | `⏭️ Next Stranger` | Skip current stranger and find a new partner |
| `/stop` | `⏹️ End Chat` | End active chat or cancel queue search |
| `/icebreaker` | `🎲 Send Icebreaker` | Post a fun conversation starter into chat |
| `/profile` | `👤 Profile` | View your anonymous profile card & stats |
| `/gender` | Inline Button | View or change your gender preference |
| `/report` | `🚨 Report User` | Report partner for inappropriate behavior (auto-ban) |
| `/invite` | `🚀 Invite Friends` | Share the bot with friends via Telegram |
| `/help` | `❓ Help` | Display command guide and community rules |
| `/stats` | — | *(Admin only)* View live bot analytics and queue stats |

---

## 📄 License

MIT License. Free for personal and commercial use.
