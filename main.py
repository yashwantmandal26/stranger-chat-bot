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

    # Connect to Telegram and configure webhooks
    try:
        bot_info = await bot.get_me()
        logger.info(
            "Stranger Chat Bot connected to Telegram! Username: @%s (ID: %s)",
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
            "CRITICAL: Telegram unauthorized error: %s. "
            "Please check that BOT_TOKEN in Render environment variables matches your bot token from @BotFather!",
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
    if not config.BOT_TOKEN:
        logger.error(
            "ERROR: BOT_TOKEN is not configured! Please provide your Telegram Bot Token in the .env file or environment variables."
        )
        sys.exit(1)

    # Initialize Bot instance with HTML parse mode
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Initialize Dispatcher
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
