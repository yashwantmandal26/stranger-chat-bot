import asyncio
import logging
import sys
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, ErrorEvent

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
    """Executes startup actions: DB initialization, command registration, and background tasks."""
    global inactivity_task
    logger.info("Initializing database...")
    await database.init_db()

    # Set up command menu in Telegram
    await set_bot_commands(bot)

    # Start the 10-minute inactivity session cleaner
    inactivity_task = asyncio.create_task(
        run_inactivity_checker(bot, check_interval_seconds=30, timeout_minutes=10)
    )

    bot_info = await bot.get_me()
    logger.info(
        "Stranger Chat Bot started successfully! Username: @%s (ID: %s)",
        bot_info.username,
        bot_info.id,
    )


async def on_shutdown(bot: Bot) -> None:
    """Handles graceful shutdown: cancels background tasks and flushes connections."""
    global inactivity_task
    logger.info("Shutting down bot...")
    if inactivity_task and not inactivity_task.done():
        inactivity_task.cancel()
        try:
            await inactivity_task
        except asyncio.CancelledError:
            logger.info("Inactivity worker cancelled cleanly.")


async def main() -> None:
    """Application entry point."""
    if not config.BOT_TOKEN:
        logger.error(
            "ERROR: BOT_TOKEN is not configured! Please provide your Telegram Bot Token in the .env file."
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

    # Register lifecycle hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        logger.info("Closing bot session...")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
