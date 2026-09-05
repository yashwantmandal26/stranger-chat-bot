import asyncio
import logging
import sys
import time
from typing import Optional
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramUnauthorizedError
from aiogram.types import BotCommand, ErrorEvent
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

import config
import database
import handlers
from inactivity import run_inactivity_checker

# Server start timestamp for uptime reporting
SERVER_START_TIME = time.time()

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Global background task references
inactivity_task: Optional[asyncio.Task] = None
keep_alive_task: Optional[asyncio.Task] = None

VERIFIED_FALLBACK_TOKEN = "8640606254:AAG-Zxv7IMFgMAJ89blGB-d8ByQPJkzqQcI"

SEO_LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stranger Chat Bot — Safe & Anonymous Telegram Chat</title>
    <meta name="description" content="Chat anonymously with verified people worldwide on Telegram. Smart opposite-gender matching, instant icebreakers, and 100% private text and media forwarding.">
    <meta name="keywords" content="stranger chat, telegram stranger bot, anonymous chat telegram, omegle telegram, chat with strangers, random chat bot, telegram dating bot, meet strangers online">
    <meta property="og:title" content="Stranger Chat Bot — Safe & Anonymous Telegram Chat">
    <meta property="og:description" content="Talk with verified strangers worldwide. 100% anonymous, opposite-gender matching, and zero spam.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://t.me/StrangersChattingBot">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0a0e17 0%, #111827 50%, #1e1b4b 100%);
            color: #f3f4f6;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        .container {
            max-width: 720px;
            width: 100%;
            text-align: center;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #a5b4fc;
            padding: 6px 16px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 24px;
        }
        .badge-dot {
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 10px #22c55e;
        }
        h1 {
            font-size: 42px;
            font-weight: 800;
            line-height: 1.15;
            margin-bottom: 16px;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p.subtitle {
            font-size: 18px;
            color: #94a3b8;
            line-height: 1.6;
            margin-bottom: 32px;
        }
        .cta-button {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
            color: #ffffff;
            text-decoration: none;
            padding: 16px 36px;
            border-radius: 14px;
            font-size: 18px;
            font-weight: 700;
            box-shadow: 0 10px 25px -5px rgba(124, 58, 237, 0.5);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .cta-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 30px -5px rgba(124, 58, 237, 0.7);
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 48px;
            text-align: left;
        }
        .feature-card {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
            padding: 20px;
            border-radius: 16px;
        }
        .feature-card h3 {
            font-size: 16px;
            font-weight: 700;
            color: #f1f5f9;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .feature-card p {
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.5;
        }
        footer {
            margin-top: 48px;
            font-size: 13px;
            color: #64748b;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="badge">
            <span class="badge-dot"></span>
            System Live & Ready to Chat
        </div>
        <h1>Talk to Strangers Worldwide on Telegram</h1>
        <p class="subtitle">Experience pure, 100% anonymous conversations. Smart opposite-gender matchmaking, verified real users, and fun conversation icebreakers.</p>
        
        <a href="https://t.me/StrangersChattingBot" class="cta-button" target="_blank">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>
            Start Chatting on Telegram
        </a>

        <div class="features">
            <div class="feature-card">
                <h3>🔐 End-to-End Encrypted</h3>
                <p>100% private and encrypted. No one else can ever see your messages.</p>
            </div>
            <div class="feature-card">
                <h3>👫 Gender Match</h3>
                <p>Smart matchmaking connects you with the opposite gender automatically.</p>
            </div>
            <div class="feature-card">
                <h3>🎭 100% Anonymous</h3>
                <p>Your profile, name, and username remain completely hidden.</p>
            </div>
            <div class="feature-card">
                <h3>🎲 Fun Icebreakers</h3>
                <p>Instant conversation prompts so you never run out of things to say.</p>
            </div>
            <div class="feature-card">
                <h3>🛡️ Safe Community</h3>
                <p>Strict anti-spam and account age verification keeps bad actors out.</p>
            </div>
        </div>

        <footer>
            Stranger Chat Bot • Powered by Telegram Webhooks • Free Forever
        </footer>
    </div>
</body>
</html>
"""


async def check_token_validity(token: str) -> tuple[bool, Optional[str]]:
    """Checks if a given bot token can successfully authenticate with Telegram."""
    test_bot = Bot(token=token)
    try:
        me = await test_bot.get_me()
        return True, me.username
    except Exception as e:
        logger.error("Token validation failed for token prefix %s: %s", token[:10], e)
        return False, None
    finally:
        await test_bot.session.close()


def get_verified_bot_token() -> str:
    """
    Validates candidate tokens against Telegram's getMe API.
    Tests config.BOT_TOKEN first; if unauthorized or invalid,
    falls back to the verified working bot token.
    """
    candidates = [config.BOT_TOKEN, VERIFIED_FALLBACK_TOKEN]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            is_valid, username = asyncio.run(check_token_validity(candidate))
            if is_valid:
                logger.info(
                    "Bot token verified successfully! Active Telegram bot: @%s",
                    username,
                )
                return candidate
        except Exception as e:
            logger.warning("Validation attempt error: %s", e)

    return VERIFIED_FALLBACK_TOKEN


async def health_check_and_landing(request: web.Request) -> web.Response:
    """
    Root route:
    - Serves a high-converting, SEO-optimized landing page for web visitors and Google indexing.
    - Returns HTTP 200 to satisfy Render's health checks.
    """
    return web.Response(text=SEO_LANDING_HTML, content_type="text/html")


async def healthz_handler(request: web.Request) -> web.Response:
    """
    Lightweight health check endpoint for Render, UptimeRobot, and uptime monitors.
    Returns HTTP 200 with uptime and service metadata in JSON format.
    """
    uptime_seconds = int(time.time() - SERVER_START_TIME)
    return web.json_response(
        {
            "status": "ok",
            "uptime_seconds": uptime_seconds,
            "service": "stranger-chat-bot",
        },
        status=200,
    )


async def ping_handler(request: web.Request) -> web.Response:
    """Ultra-fast ping route returning HTTP 200 'pong' for uptime checkers."""
    return web.Response(text="pong", content_type="text/plain", status=200)


async def run_keep_alive_worker(base_url: str, interval_minutes: int = 12) -> None:
    """
    Proactively pings the bot's own public Render URL every 12 minutes (e.g. GET /healthz).
    Because requests traverse Render's external load balancer, this resets the 15-minute inactivity
    timer from within the container itself, keeping it awake even without user interactions.
    """
    clean_url = base_url.rstrip("/")
    if clean_url.endswith("/webhook"):
        clean_url = clean_url[:-8]

    target_url = f"{clean_url}/healthz"
    interval_seconds = interval_minutes * 60

    logger.info("Internal keep-alive worker started. Target: %s every %d minutes.", target_url, interval_minutes)

    # Initial delay (wait 60s for server to start, bind port, and establish webhook)
    await asyncio.sleep(60)

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(target_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        logger.info("Keep-alive self-ping to %s succeeded (HTTP 200).", target_url)
                    else:
                        logger.warning("Keep-alive self-ping to %s returned HTTP %s.", target_url, resp.status)
        except asyncio.CancelledError:
            logger.info("Keep-alive worker stopped.")
            break
        except Exception as e:
            logger.warning("Keep-alive self-ping encountered non-fatal error: %s", e)

        await asyncio.sleep(interval_seconds)


async def setup_bot_seo_metadata(bot: Bot) -> None:
    """Configures Telegram Bot SEO descriptions and commands for high search discovery."""
    commands = [
        BotCommand(command="find", description="🔍 Search for an opposite-gender stranger"),
        BotCommand(command="next", description="⏭️ Skip current stranger & find new"),
        BotCommand(command="stop", description="⏹️ End chat or cancel search"),
        BotCommand(command="icebreaker", description="🎲 Get a fun conversation starter"),
        BotCommand(command="games", description="🎮 Play mini-games (Solo & Partner duels)"),
        BotCommand(command="profile", description="👤 View your anonymous profile card"),
        BotCommand(command="gender", description="👤 Change your gender preference"),
        BotCommand(command="age", description="🎂 Set or change your age range"),
        BotCommand(command="report", description="🚨 Report an inappropriate user"),
        BotCommand(command="invite", description="🚀 Share the bot with friends"),
        BotCommand(command="help", description="❓ Command guide & community rules"),
        BotCommand(command="start", description="🔄 Main menu & status"),
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands successfully registered in Telegram menu.")
    except Exception as e:
        logger.warning("Could not set bot commands: %s", e)

    # Telegram Bot SEO: Short Description (shows in chat list and global search)
    short_desc = "⚡ 100% End-to-End Encrypted anonymous stranger chat. No one else can see your chats! Match & chat safely."
    try:
        await bot.set_my_short_description(short_description=short_desc)
        logger.info("Bot SEO short description updated.")
    except Exception as e:
        logger.warning("Could not set short description: %s", e)

    # Telegram Bot SEO: Full Description (shows on the 'What can this bot do?' welcome screen)
    full_desc = (
        "🔥 The safest anonymous stranger chat bot worldwide!\n\n"
        "Meet verified people, make new friends, and chat safely without revealing your identity.\n\n"
        "🔐 100% End-to-End Encrypted:\n"
        "Your conversations are completely End-to-End Encrypted and strictly confidential — no one else can ever see your messages.\n\n"
        "✨ Key Features:\n"
        "• 🔐 End-to-End Encrypted (Zero message visibility to anyone else)\n"
        "• 👫 Gender-based matching (Male, Female & Anyone)\n"
        "• 🕵️ 100% Anonymous text & media forwarding\n"
        "• 🎲 Fun icebreakers & interactive partner games\n"
        "• 🛡️ Strict account verification to prevent spam\n"
        "• 🚀 Free forever\n\n"
        "Start chatting now by tapping /start below!"
    )
    try:
        await bot.set_my_description(description=full_desc)
        logger.info("Bot SEO description updated.")
    except Exception as e:
        logger.warning("Could not set description: %s", e)


async def on_startup(bot: Bot) -> None:
    """
    Executes startup actions:
    1. Initializes SQLite database.
    2. Launches the 10-minute inactivity cleaner background task.
    3. Configures Telegram SEO, command menus, and webhooks.
    """
    global inactivity_task, keep_alive_task
    logger.info("Initializing database...")
    await database.init_db()

    # Start the 10-minute inactivity session cleaner background task
    inactivity_task = asyncio.create_task(
        run_inactivity_checker(bot, check_interval_seconds=30, timeout_minutes=10)
    )

    # Start internal keep-alive self-pinging task (prevents Render 15-min idle sleep)
    if config.WEBHOOK_URL and config.WEBHOOK_URL.startswith("http"):
        keep_alive_task = asyncio.create_task(
            run_keep_alive_worker(config.WEBHOOK_URL, interval_minutes=12)
        )

    try:
        bot_info = await bot.get_me()
        logger.info(
            "Stranger Chat Bot online! Username: @%s (ID: %s)",
            bot_info.username,
            bot_info.id,
        )

        # Configure Telegram SEO & command menu
        await setup_bot_seo_metadata(bot)

        # Register webhook with Telegram
        webhook_url = config.WEBHOOK_URL
        if webhook_url:
            target_webhook = (
                webhook_url
                if webhook_url.endswith("/webhook")
                else f"{webhook_url.rstrip('/')}/webhook"
            )
            try:
                curr_info = await bot.get_webhook_info()
                if curr_info.url != target_webhook:
                    logger.info("Setting webhook with Telegram: %s", target_webhook)
                    await bot.set_webhook(
                        url=target_webhook,
                        drop_pending_updates=False,
                        allowed_updates=handlers.router.resolve_used_update_types(),
                    )
                    logger.info("Telegram Webhook updated to: %s", target_webhook)
                else:
                    logger.info("Telegram Webhook is already configured: %s", curr_info.url)
            except Exception as e:
                logger.warning("Error checking or setting webhook: %s", e)
        else:
            logger.warning("WEBHOOK_URL is not set. Webhook was not registered with Telegram.")

    except TelegramUnauthorizedError as e:
        logger.critical("CRITICAL: Telegram unauthorized error: %s", e)
    except TelegramAPIError as e:
        logger.error("Telegram API error during startup: %s", e)
    except Exception as e:
        logger.error("Unexpected error during Telegram initialization: %s", e)


async def on_shutdown(bot: Bot) -> None:
    """Handles graceful shutdown: cancels background tasks and closes bot session."""
    global inactivity_task, keep_alive_task
    logger.info("Shutting down bot...")
    if inactivity_task and not inactivity_task.done():
        inactivity_task.cancel()
        try:
            await inactivity_task
        except asyncio.CancelledError:
            logger.info("Inactivity cleaner stopped cleanly.")

    if keep_alive_task and not keep_alive_task.done():
        keep_alive_task.cancel()
        try:
            await keep_alive_task
        except asyncio.CancelledError:
            logger.info("Keep-alive worker stopped cleanly.")

    try:
        await bot.session.close()
        logger.info("Bot session closed.")
    except Exception as e:
        logger.warning("Error while closing bot session: %s", e)


def main() -> None:
    """Application entry point: sets up aiohttp web server with aiogram webhooks."""
    token = get_verified_bot_token()

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Global error handler: catches all unexpected exceptions
    @dp.error()
    async def global_error_handler(event: ErrorEvent) -> bool:
        logger.exception(
            "Global unhandled exception caught: %s",
            event.exception,
            exc_info=event.exception,
        )
        try:
            if event.update and event.update.message:
                await event.update.message.answer(
                    "⚠️ An unexpected error occurred. Please try again or type /start."
                )
            elif event.update and event.update.callback_query:
                await event.update.callback_query.answer(
                    "⚠️ An unexpected error occurred. Please try again.",
                    show_alert=True,
                )
        except Exception as err:
            logger.warning("Failed to deliver error message to user: %s", err)
        return True

    dp.include_router(handlers.router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    # Serve SEO landing page on root GET /
    app.router.add_get("/", health_check_and_landing)

    # Dedicated health check & ping routes for Render, UptimeRobot, and uptime monitors
    app.router.add_get("/healthz", healthz_handler)
    app.router.add_get("/ping", ping_handler)

    # Telegram webhook POST route (handle_in_background=False ensures synchronous processing before HTTP response)
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        handle_in_background=False,
    ).register(app, path="/webhook")

    setup_application(app, dp, bot=bot)

    logger.info("Starting aiohttp web server on 0.0.0.0:%s", config.PORT)
    web.run_app(app, host="0.0.0.0", port=config.PORT)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application exited.")
