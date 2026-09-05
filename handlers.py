import logging
from typing import Any
from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

import account_age
import config
import database
from keyboards import (
    get_gender_keyboard,
    get_invite_keyboard,
    get_search_keyboard,
    get_welcome_keyboard,
)
from match_queue import match_queue

logger = logging.getLogger(__name__)

router = Router(name="base_handlers")

HELP_TEXT = (
    "📖 <b>Stranger Chat Bot — Command Guide</b>\n\n"
    "• <b>/find</b> — 🔍 Search for an opposite-gender stranger\n"
    "• <b>/next</b> — ⏭️ Skip current stranger & find someone new\n"
    "• <b>/stop</b> — ⏹️ End active chat or cancel queue search\n"
    "• <b>/gender</b> — 👤 View or change your gender preference\n"
    "• <b>/invite</b> — 🚀 Share the bot with your friends\n"
    "• <b>/help</b> — ❓ Show this help guide\n"
    "• <b>/start</b> — 🔄 View bot status & main menu\n\n"
    "🛡️ <i>All chats are 100% anonymous. Be respectful and have fun!</i>"
)


async def get_or_register_user(from_user) -> tuple[dict[str, Any], bool]:
    """
    Retrieves user from SQLite or auto-registers them seamlessly.
    Returns (db_user, is_banned).
    """
    db_user = await database.get_user(from_user.id)
    if not db_user:
        is_allowed, age_days, est_date = account_age.check_account_age(
            tg_id=from_user.id,
            min_days=config.MIN_ACCOUNT_AGE_DAYS,
        )
        db_user = await database.upsert_user(
            tg_id=from_user.id,
            username=from_user.username,
            account_created_at=est_date.isoformat(),
            is_banned=0 if is_allowed else 1,
        )
    return db_user, bool(db_user.get("is_banned"))


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """
    Handles /start command:
    1. Verifies Telegram account age (<30 days blocked with polite notice).
    2. Handles banned accounts.
    3. Displays upgraded welcome greeting with rules and action buttons.
    """
    from_user = message.from_user
    if not from_user:
        return

    tg_id = from_user.id
    logger.info("Handling /start for user_id=%s (username=@%s)", tg_id, from_user.username)

    db_user, is_banned = await get_or_register_user(from_user)

    if is_banned:
        await message.answer(
            "🛡️ <b>Account Safety Notice</b>\n\n"
            "To maintain a safe and spam-free environment for everyone, Stranger Chat requires "
            f"your Telegram account to be at least <b>{config.MIN_ACCOUNT_AGE_DAYS} days old</b>.\n\n"
            "Please come back once your account reaches 30 days of age. We appreciate your understanding!"
        )
        return

    # If currently in an active chat
    if await database.get_active_session(tg_id):
        await message.answer(
            "💬 <b>You are currently chatting with someone!</b>\n\n"
            "• Type <b>/next</b> to skip to a new partner.\n"
            "• Type <b>/stop</b> to end the chat."
        )
        return

    # Upgraded Welcome Greeting with rules & action buttons
    name_display = f" <b>{from_user.first_name}</b>" if from_user.first_name else ""
    user_gender = db_user.get("gender", "unknown")
    gender_status = (
        f"\n👤 <b>Your Gender:</b> {user_gender.title()}"
        if user_gender in ("male", "female")
        else ""
    )

    welcome_text = (
        f"👋 <b>Welcome to Stranger Chat{name_display}!</b>\n\n"
        "Connect and chat anonymously with verified people worldwide. "
        "No names, no profiles — pure connection.\n\n"
        "📜 <b>Community Rules:</b>\n"
        "• Be respectful to strangers.\n"
        "• No spam, advertisements, or external links.\n"
        "• Strictly no NSFW, explicit, or illegal content.\n"
        "⚠️ <i>Violations result in an immediate permanent ban.</i>\n"
        f"{gender_status}\n\n"
        "Choose an option below to begin:"
    )

    await message.answer(welcome_text, reply_markup=get_welcome_keyboard())


@router.message(Command("help"))
async def handle_help_command(message: Message) -> None:
    """Displays a clean menu of all commands."""
    await message.answer(HELP_TEXT)


@router.callback_query(F.data == "cb_help")
async def handle_help_callback(callback: CallbackQuery) -> None:
    """Displays the help menu when requested via inline button."""
    await callback.answer()
    if callback.message:
        await callback.message.answer(HELP_TEXT)


@router.message(Command("invite"))
async def handle_invite_command(message: Message) -> None:
    """Provides a shareable invite message and a one-tap Telegram share button."""
    bot_user = (await message.bot.get_me()).username or "StrangersChattingBot"
    invite_text = (
        "🚀 <b>Invite Friends to Stranger Chat!</b>\n\n"
        "Share this link with your friends to grow our anonymous community:\n\n"
        f"<i>\"I'm chatting with new people worldwide on this free anonymous bot! Join here: t.me/{bot_user}\"</i>\n\n"
        "Tap the button below to share directly in Telegram:"
    )
    await message.answer(invite_text, reply_markup=get_invite_keyboard(bot_user))


@router.message(Command("stats"))
async def handle_stats_command(message: Message) -> None:
    """Admin-only dashboard command showing user counts, active chats, and queue status."""
    from_user = message.from_user
    if not from_user:
        return

    if from_user.id != config.ADMIN_ID:
        await message.answer("⛔ Access denied. This command is restricted to administrators.")
        return

    db_stats = await database.get_stats()
    queue_stats = await match_queue.get_stats()

    stats_text = (
        "📊 <b>Stranger Chat Bot — Admin Dashboard</b>\n\n"
        "👥 <b>User Statistics:</b>\n"
        f"• Total Users: <b>{db_stats['total_users']}</b>\n"
        f"• Male Users: <b>{db_stats['male_users']}</b>\n"
        f"• Female Users: <b>{db_stats['female_users']}</b>\n\n"
        "💬 <b>Chats & Activity:</b>\n"
        f"• Active Chat Sessions: <b>{db_stats['active_chats']}</b>\n\n"
        "⏳ <b>Matchmaking Queue:</b>\n"
        f"• Total Waiting: <b>{queue_stats['total']}</b>\n"
        f"• Males in Queue: <b>{queue_stats['males']}</b>\n"
        f"• Females in Queue: <b>{queue_stats['females']}</b>\n"
        f"• VIP Premium Waiting: <b>{queue_stats['premiums']}</b>"
    )
    await message.answer(stats_text)


@router.message(Command("gender"))
async def handle_gender_command(message: Message) -> None:
    """Allows user to view or update their gender selection."""
    from_user = message.from_user
    if not from_user:
        return

    db_user, is_banned = await get_or_register_user(from_user)
    if is_banned:
        await message.answer("⛔ Your account is suspended.")
        return

    current_gender = db_user.get("gender", "unknown").title()
    await message.answer(
        f"👤 <b>Gender Preference</b>\n\n"
        f"Current selection: <b>{current_gender}</b>\n\n"
        "Choose an option below to update your gender:",
        reply_markup=get_gender_keyboard(),
    )


@router.callback_query(F.data.startswith("cb_gender:"))
async def handle_gender_callback(callback: CallbackQuery) -> None:
    """Processes gender selection callbacks from inline buttons."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    selected_gender = callback.data.split(":")[1]

    if selected_gender not in ("male", "female"):
        await callback.answer("Invalid selection.", show_alert=True)
        return

    await database.update_user_gender(tg_id, selected_gender)
    await callback.answer(f"Gender updated to {selected_gender.title()}!")

    try:
        await callback.message.edit_text(
            f"✅ <b>Gender set to {selected_gender.title()}!</b>\n\n"
            "You are now ready to chat anonymously.\n\n"
            "👉 Tap <b>/find</b> to start searching for an opposite-gender partner!\n"
            "👉 Tap <b>/gender</b> if you ever need to change your preference."
        )
    except Exception as e:
        logger.warning("Failed to edit callback message: %s", e)


@router.callback_query(F.data == "cb_start_find")
async def handle_start_find_callback(callback: CallbackQuery) -> None:
    """Handles the 'Find a Stranger' button from the welcome message."""
    if not callback.from_user or not callback.message:
        return

    await callback.answer()
    await execute_find_flow(callback.message, callback.from_user)


@router.message(Command("find"))
async def handle_find_command(message: Message) -> None:
    """Handles /find command."""
    from_user = message.from_user
    if not from_user:
        return

    await execute_find_flow(message, from_user)


async def execute_find_flow(message: Message, from_user) -> None:
    """Core matchmaking execution logic shared between /find and inline button."""
    tg_id = from_user.id
    db_user, is_banned = await get_or_register_user(from_user)

    if is_banned:
        await message.answer("⛔ Your account is suspended from Stranger Chat.")
        return

    # Edge Case: User already in active chat
    active_session = await database.get_active_session(tg_id)
    if active_session:
        await message.answer(
            "You are already chatting with someone! Type /next to skip or /stop to end."
        )
        return

    gender = db_user.get("gender", "unknown")
    if gender not in ("male", "female"):
        await message.answer(
            "⚠️ <b>Gender Required</b>\n\n"
            "Please select your gender before searching so we can match you with the right partner:",
            reply_markup=get_gender_keyboard(),
        )
        return

    # Check if already waiting in queue
    if await match_queue.is_in_queue(tg_id):
        await message.answer(
            "⏳ <b>Already in Queue!</b>\n\n"
            "You are currently waiting for a match. Please wait a moment while we find someone for you.",
            reply_markup=get_search_keyboard(),
        )
        return

    # Check premium status
    is_premium = await database.is_premium_active(tg_id)

    # Attempt match or enqueue
    partner_id, matched = await match_queue.find_match_or_enqueue(
        tg_id=tg_id,
        gender=gender,
        is_premium=is_premium,
    )

    if matched and partner_id:
        partner_notice = (
            "🎉 <b>Partner Found!</b>\n\n"
            "You are now connected with a stranger! Say hello 👋\n\n"
            "<i>Your identity is completely anonymous. Enjoy your conversation!</i>\n\n"
            "<b>Chat Commands:</b>\n"
            "• <b>/next</b> — Skip and find a new partner\n"
            "• <b>/stop</b> — End the current chat"
        )
        await message.answer(partner_notice)

        try:
            await message.bot.send_message(chat_id=partner_id, text=partner_notice)
        except Exception as e:
            logger.error("Failed to notify matched partner %s: %s", partner_id, e)
    else:
        vip_tag = " ⭐ <i>(VIP Priority Queue)</i>" if is_premium else ""
        tip = (
            ""
            if is_premium
            else "\n\n💡 <i>Tip: Premium members get VIP priority in the queue! Type /premium to learn more.</i>"
        )
        await message.answer(
            f"🔍 <b>Searching for a partner...</b>{vip_tag}\n\n"
            f"Looking for an opposite-gender stranger to connect with.{tip}\n\n"
            "Please wait, or tap below to cancel search.",
            reply_markup=get_search_keyboard(),
        )


@router.message(Command("next"))
async def handle_next_command(message: Message) -> None:
    """
    Handles /next command:
    - Ends current session immediately.
    - Notifies partner: '👋 Stranger has disconnected.'
    - Re-enqueues user: 'Searching for a new stranger...'
    - If not in chat, replies: 'You are not in an active chat.'
    """
    from_user = message.from_user
    if not from_user:
        return

    tg_id = from_user.id
    db_user, is_banned = await get_or_register_user(from_user)

    if is_banned:
        await message.answer("⛔ Your account is suspended.")
        return

    closed_session = await database.close_session_for_user(tg_id)

    if not closed_session:
        await message.answer("You are not in an active chat.")
        return

    partner_id = (
        closed_session["user2_id"]
        if closed_session["user1_id"] == tg_id
        else closed_session["user1_id"]
    )

    try:
        await message.bot.send_message(
            chat_id=partner_id,
            text="👋 <b>Stranger has disconnected.</b>\n\nType <b>/find</b> to find a new stranger!",
        )
    except Exception as e:
        logger.warning("Failed to notify disconnected partner %s: %s", partner_id, e)

    await match_queue.remove_user(tg_id)

    gender = db_user.get("gender", "unknown")
    if gender not in ("male", "female"):
        await message.answer(
            "⚠️ Please select your gender first using /gender to find a match."
        )
        return

    is_premium = await database.is_premium_active(tg_id)
    new_partner_id, matched = await match_queue.find_match_or_enqueue(
        tg_id=tg_id,
        gender=gender,
        is_premium=is_premium,
    )

    if matched and new_partner_id:
        partner_notice = (
            "🎉 <b>Partner Found!</b>\n\n"
            "You are now connected with a stranger! Say hello 👋\n\n"
            "<i>Your identity is completely anonymous. Enjoy your conversation!</i>\n\n"
            "<b>Chat Commands:</b>\n"
            "• <b>/next</b> — Skip and find a new partner\n"
            "• <b>/stop</b> — End the current chat"
        )
        await message.answer(partner_notice)
        try:
            await message.bot.send_message(chat_id=new_partner_id, text=partner_notice)
        except Exception as e:
            logger.error("Failed to notify new matched partner %s: %s", new_partner_id, e)
    else:
        vip_tag = " ⭐ <i>(VIP Priority)</i>" if is_premium else ""
        await message.answer(
            f"🔍 <b>Searching for a new stranger...</b>{vip_tag}\n\n"
            "Looking for an opposite-gender match. Please wait a moment...",
            reply_markup=get_search_keyboard(),
        )


@router.message(Command("stop"))
async def handle_stop_command(message: Message) -> None:
    """
    Handles /stop command:
    - If in active chat: ends session, notifies partner: '👋 Stranger has disconnected.'
      Replies to user: 'Chat ended. Type /find to start again.'
    - If in queue: removes user from queue.
    - If neither: replies: 'You are not in an active chat.'
    """
    from_user = message.from_user
    if not from_user:
        return

    tg_id = from_user.id

    closed_session = await database.close_session_for_user(tg_id)
    if closed_session:
        partner_id = (
            closed_session["user2_id"]
            if closed_session["user1_id"] == tg_id
            else closed_session["user1_id"]
        )

        try:
            await message.bot.send_message(
                chat_id=partner_id,
                text="👋 <b>Stranger has disconnected.</b>\n\nType <b>/find</b> to start again.",
            )
        except Exception as e:
            logger.warning("Failed to notify partner %s on /stop: %s", partner_id, e)

        await match_queue.remove_user(tg_id)
        await message.answer("Chat ended. Type /find to start again.")
        return

    removed_from_queue = await match_queue.remove_user(tg_id)
    if removed_from_queue:
        await message.answer(
            "❌ <b>Search Cancelled</b>\n\n"
            "You have been removed from the matchmaking queue.\n"
            "Type <b>/find</b> whenever you wish to search again!"
        )
        return

    await message.answer("You are not in an active chat.")


@router.callback_query(F.data == "cb_cancel_search")
async def handle_cancel_search_callback(callback: CallbackQuery) -> None:
    """Handles inline cancel search button while user is waiting in queue."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    removed = await match_queue.remove_user(tg_id)

    if removed:
        await callback.answer("Search cancelled.")
        try:
            await callback.message.edit_text(
                "❌ <b>Search Cancelled</b>\n\n"
                "You have been removed from the matchmaking queue.\n"
                "Type <b>/find</b> whenever you are ready to search again!"
            )
        except Exception as e:
            logger.warning("Failed to edit cancel search message: %s", e)
    else:
        await callback.answer("You are not currently in the queue.")


@router.message()
async def handle_anonymous_message(message: Message) -> None:
    """
    Core Anonymous Message Forwarding Engine:
    - If user is in an active session, forwards message to partner using copy_to.
      Updates session activity timestamp.
    - If not connected, replies: 'You are not connected to anyone. Use /find to start chatting!'
    """
    from_user = message.from_user
    if not from_user:
        return

    tg_id = from_user.id
    partner_id = await database.get_partner_id(tg_id)

    if not partner_id:
        await message.answer("You are not connected to anyone. Use /find to start chatting!")
        return

    try:
        await message.copy_to(chat_id=partner_id)
        await database.update_session_activity(tg_id)
    except TelegramAPIError as e:
        logger.error(
            "Failed to relay message from user %s to partner %s: %s",
            tg_id,
            partner_id,
            e,
        )
        await database.close_session_for_user(tg_id)
        await message.answer(
            "⚠️ <b>Message could not be delivered.</b>\n\n"
            "Your chat partner has disconnected or blocked the bot.\n"
            "Type <b>/find</b> to find a new partner!"
        )
    except Exception as e:
        logger.error("Unexpected error relaying message: %s", e)
        await message.answer(
            "⚠️ An error occurred while sending your message. Please try again."
        )
