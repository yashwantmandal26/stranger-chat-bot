import asyncio
import logging
from aiogram import Bot

import database
from games import duel_games
from keyboards import get_partner_disconnected_keyboard
from quotes import (
    format_chat_duration,
    get_random_motivational_quote,
    get_session_elapsed_seconds,
)

logger = logging.getLogger(__name__)


async def run_inactivity_checker(
    bot: Bot,
    check_interval_seconds: int = 30,
    timeout_minutes: int = 10,
) -> None:
    """
    Background worker that checks for and closes inactive chat sessions.
    Runs periodically and notifies both partners when a chat expires.
    """
    logger.info(
        "Starting inactivity cleaner: checking every %ss for sessions older than %sm.",
        check_interval_seconds,
        timeout_minutes,
    )
    while True:
        try:
            await asyncio.sleep(check_interval_seconds)
            closed_sessions = await database.get_and_close_inactive_sessions(
                timeout_minutes=timeout_minutes
            )

            for session in closed_sessions:
                duel_games.reset_session(session["id"])
                user1_id = session["user1_id"]
                user2_id = session["user2_id"]
                logger.info(
                    "Closed inactive chat session id=%s between users %s and %s.",
                    session.get("id"),
                    user1_id,
                    user2_id,
                )

                elapsed = get_session_elapsed_seconds(session)
                dur_str = format_chat_duration(elapsed)
                quote = get_random_motivational_quote()
                inactivity_notice = (
                    "⏳ <b>Chat closed due to inactivity.</b>\n\n"
                    f"⏱️ <b>Chat Duration:</b> <b>{dur_str}</b>\n\n"
                    "✨ <b>Thought of the Moment:</b>\n"
                    f"<i>{quote}</i>\n\n"
                    "Where would you like to go next?"
                )

                for uid in (user1_id, user2_id):
                    try:
                        await bot.send_message(
                            chat_id=uid,
                            text=inactivity_notice,
                            reply_markup=get_partner_disconnected_keyboard(),
                        )
                    except Exception as e:
                        logger.debug(
                            "Could not deliver inactivity notice to user %s: %s",
                            uid,
                            e,
                        )
        except asyncio.CancelledError:
            logger.info("Inactivity checker loop cancelled.")
            break
        except Exception as e:
            logger.error("Unexpected error in inactivity checker: %s", e)
