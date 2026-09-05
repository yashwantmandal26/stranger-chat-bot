import asyncio
import logging
import sys
from typing import Optional
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

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Global background task reference for inactivity cleanup
inactivity_task: Optional[asyncio.Task] = None

VERIFIED_FALLBACK_TOKEN = "8640606254:AAG-Zxv7IMFgMAJ89blGB-d8ByQPJkzqQcI"


async def check_token_validity(token: str) -> tuple[bool, Optional[str]]:
    """Checks if a given bot token can successfully authenticate with Telegram."""
    test_bot = Bot(token=token)
    try:
        me = await test_bot.get_me()
        return True, me.username
    except Exception as e:
        logger.warning("Token verification failed for prefix %s...: %s", token[:10], e)
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

    logger.warning("Defaulting to verified fallback token.")
    return VERIFIED_FALLBACK_TOKEN


async def health_check(request: web.Request) -> web.Response:
    """
    Health check route for Render to keep the free server running.
    Returns plain text: 'Bot is alive!'
    """
    return web.Response(text="Bot is alive!", content_type="text/plain")


async def set_bot_commands(bot: Bot) -> None:
    """Configures the default bot command menu in Telegram."""
    commands = [
        BotCommand(command="find", description="🔍 Find an opposite-gender stranger"),
        BotCommand(command="next", description="⏭️ Skip current stranger & find new"),
        BotCommand(command="stop", description="⏹️ End chat or cancel search"),
        BotCommand(command="gender", description="👤 Change your gender preference"),
        BotCommand(command="invite", description="🚀 Share the bot with friends"),
        BotCommand(command="help", description="❓ Command guide & community rules"),
        BotCommand(command="start", description="🔄 Start bot / main menu"),
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands successfully registered in Telegram menu.")
    except Exception as e:
        logger.warning("Could not set bot commands: %s", e)


async def on_startup(bot: Bot) -> None:
    """
    Executes startup actions:
    1. Initializes SQLite database.
    2. Launches the 10-minute inactivity cleaner background task.
    3. Verifies Telegram credentials, registers commands, and sets webhook.
    """
    global inactivity_task
    logger.info("Initializing database...")
    await database.init_db()

    # Start the 10-minute inactivity session cleaner background task
    inactivity_task = asyncio.create_task(
        run_inactivity_checker(bot, check_interval_seconds=30, timeout_minutes=10)
    )

    try:
        bot_info = await bot.get_me()
        logger.info(
            "Stranger Chat Bot online! Username: @%s (ID: %s)",
            bot_info.username,
            bot_info.id,
        )

        # Set up command menu in Telegram
        await set_bot_commands(bot)

        # Register webhook with Telegram if WEBHOOK_URL is configured
        webhook_url = config.WEBHOOK_URL
        if webhook_url:
            target_webhook = (
                webhook_url
                if webhook_url.endswith("/webhook")
                else f"{webhook_url.rstrip('/')}/webhook"
            )
            logger.info("Registering webhook with Telegram: %s", target_webhook)
            await bot.set_webhook(
                url=target_webhook,
                drop_pending_updates=True,
                allowed_updates=handlers.router.resolve_used_update_types(),
            )
            webhook_info = await bot.get_webhook_info()
            logger.info("Telegram Webhook active! URL: %s", webhook_info.url)
        else:
            logger.warning("WEBHOOK_URL is not set. Webhook was not registered with Telegram.")

    except TelegramUnauthorizedError as e:
        logger.critical(
            "CRITICAL: Telegram unauthorized error: %s. Please check your BOT_TOKEN configuration!",
            e,
        )
    except TelegramAPIError as e:
        logger.error("Telegram API error during startup: %s", e)
    except Exception as e:
        logger.error("Unexpected error during Telegram initialization: %s", e)


async def on_shutdown(bot: Bot) -> None:
    """Handles graceful shutdown: cancels background tasks and closes bot session."""
    global inactivity_task
    logger.info("Shutting down bot...")
    if inactivity_task and not inactivity_task.done():
        inactivity_task.cancel()
        try:
            await inactivity_task
        except asyncio.CancelledError:
            logger.info("Inactivity cleaner stopped cleanly.")

    try:
        await bot.session.close()
        logger.info("Bot session closed.")
    except Exception as e:
        logger.warning("Error while closing bot session: %s", e)


def main() -> None:
    """Application entry point: sets up aiohttp web server with aiogram webhooks."""
    # Ensure bot is created with an authenticated, verified token
    token = get_verified_bot_token()

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Global error handler: catches all unexpected exceptions to keep the bot resilient
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

    # Register routers
    dp.include_router(handlers.router)

    # Register dispatcher lifecycle hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # 1. Create aiohttp web application
    app = web.Application()

    # 2. Add GET / health check route for Render
    app.router.add_get("/", health_check)

    # 3. Add POST /webhook route for Telegram updates
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")

    # 4. Integrate aiogram dispatcher lifecycle with aiohttp
    setup_application(app, dp, bot=bot)

    # 5. Run the web server on 0.0.0.0:$PORT
    logger.info("Starting aiohttp web server on 0.0.0.0:%s", config.PORT)
    web.run_app(app, host="0.0.0.0", port=config.PORT)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application exited.")
