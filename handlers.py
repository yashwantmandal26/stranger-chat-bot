import html
import logging
import random
from typing import Any
from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import account_age
import config
import database
import games
import icebreakers
from games import RPS_EMOJIS, duel_games, solo_games
from keyboards import (
    get_age_keyboard,
    get_chat_reply_keyboard,
    get_games_menu_keyboard,
    get_gender_keyboard,
    get_idle_reply_keyboard,
    get_invite_keyboard,
    get_math_puzzle_keyboard,
    get_number_guess_keyboard,
    get_partner_disconnected_keyboard,
    get_profile_keyboard,
    get_report_reasons_keyboard,
    get_rps_keyboard,
    get_search_keyboard,
    get_welcome_keyboard,
)
from match_queue import match_queue
from quotes import get_partner_ended_text, get_random_motivational_quote

logger = logging.getLogger(__name__)

router = Router(name="base_handlers")

HELP_TEXT = (
    "📖 <b>Stranger Chat Bot — Command Guide</b>\n"
    "━━━━━━━━━━━━━━━━━━━\n"
    "• <b>/find</b> — 🔍 Search for a partner (opposite gender preferred)\n"
    "• <b>/next</b> — ⏭️ Skip current stranger & find someone new\n"
    "• <b>/stop</b> — ⏹️ End active chat or cancel queue search\n"
    "• <b>/games</b> — 🎮 Play fun mini-games (Solo & Partner duels)\n"
    "• <b>/icebreaker</b> — 🎲 Send a fun conversation starter\n"
    "• <b>/profile</b> — 👤 View your anonymous profile card\n"
    "• <b>/gender</b> — 👤 View or change your gender preference\n"
    "• <b>/age</b> — 🎂 View or change your age range\n"
    "• <b>/report</b> — 🚨 Report inappropriate partner\n"
    "• <b>/invite</b> — 🚀 Share the bot with your friends\n"
    "• <b>/help</b> — ❓ Show this help guide\n"
    "• <b>/start</b> — 🔄 View bot status & main menu\n"
    "━━━━━━━━━━━━━━━━━━━\n"
    "🛡️ <i>All chats are 100% anonymous. Be respectful and have fun!</i>"
)


def format_gender_display(gender: Any) -> str:
    """Formats gender string into an aesthetic badge with emoji."""
    g = str(gender or "").lower().strip()
    if g == "male":
        return "Male 👨"
    elif g == "female":
        return "Female 👩"
    elif g == "prefer_not_to_say":
        return "Prefer not to say 🎭"
    return "Not specified 👤"


def format_age_display(age_range: Any) -> str:
    """Formats age range string into an aesthetic badge with emoji."""
    a = str(age_range or "").lower().strip()
    if a == "below_18":
        return "Below 18 🐣"
    elif a in ("18-25", "18_25"):
        return "18–25 ✨"
    elif a in ("25-35", "25_35"):
        return "25–35 💼"
    elif a in ("40+", "40_plus", "40"):
        return "40+ 🌟"
    return "Not specified"


def get_match_found_text(partner_gender: Any, partner_age: Any) -> str:
    """Returns aesthetic match notification card detailing partner's gender & age."""
    g_display = format_gender_display(partner_gender)
    a_display = format_age_display(partner_age)
    return (
        "🎉 <b>Partner Found!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Gender:</b> {g_display}\n"
        f"🎂 <b>Age:</b> {a_display}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<i>Say hello 👋 to start chatting!</i>"
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
    # Admin is never banned
    if from_user.id == config.ADMIN_ID:
        return db_user, False
    return db_user, bool(db_user.get("is_banned"))


@router.message(CommandStart())
@router.message(F.text.lower().in_({"start", "/start"}))
async def handle_start(message: Message) -> None:
    """
    Handles /start command:
    1. Verifies Telegram account age.
    2. Handles banned accounts.
    3. Checks if user is in an active chat with quick restart button.
    4. Displays aesthetic welcome card with rules, action buttons, and persistent mobile menu.
    """
    from_user = message.from_user
    if not from_user:
        return

    tg_id = from_user.id
    logger.info("Handling /start for user_id=%s (username=@%s)", tg_id, from_user.username)

    db_user, is_banned = await get_or_register_user(from_user)

    if is_banned and tg_id != config.ADMIN_ID:
        await message.answer(
            "🛡️ <b>Account Notice</b>\n\n"
            "Your account is restricted from matchmaking.\n"
            "If you believe this is in error, please try again later."
        )
        return

    # If currently in an active chat, offer clear choices
    if await database.get_active_session(tg_id):
        active_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⏹️ End Chat & Start Fresh", callback_data="cb_end_and_restart"),
                    InlineKeyboardButton(text="⏭️ Next Stranger", callback_data="cb_start_find"),
                ]
            ]
        )
        await message.answer(
            "💬 <b>You are currently chatting with someone!</b>\n\n"
            "• Tap <b>⏹️ End Chat & Start Fresh</b> to leave and open the main menu.\n"
            "• Tap <b>⏭️ Next Stranger</b> to skip to a new partner.",
            reply_markup=active_kb,
        )
        return

    safe_first_name = html.escape(from_user.first_name) if from_user.first_name else ""
    name_display = f" <b>{safe_first_name}</b>" if safe_first_name else ""
    user_gender = db_user.get("gender", "unknown")
    user_age = db_user.get("age_range", "unknown")

    gender_display = format_gender_display(user_gender)
    age_display = format_age_display(user_age)

    gender_status = (
        f"👤 <b>Gender:</b> {gender_display}\n"
        if user_gender in ("male", "female", "prefer_not_to_say")
        else "👤 <b>Gender:</b> <i>Not set (tap Set Gender below)</i>\n"
    )
    age_status = (
        f"🎂 <b>Age Range:</b> {age_display}\n"
        if user_age in ("below_18", "18-25", "25-35", "40+")
        else "🎂 <b>Age Range:</b> <i>Not set (tap Set Age below)</i>\n"
    )

    welcome_text = (
        f"👋 <b>Welcome to Stranger Chat{name_display}!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Connect and chat anonymously with verified people worldwide. "
        "No names, no profiles — pure authentic connection.\n\n"
        "📜 <b>Community Rules:</b>\n"
        "• Be kind & respectful to strangers.\n"
        "• No spam, advertisements, or external links.\n"
        "• Strictly no NSFW, explicit, or illegal content.\n"
        "⚠️ <i>Violations result in an immediate permanent ban.</i>\n\n"
        f"{gender_status}"
        f"{age_status}"
        "━━━━━━━━━━━━━━━━━━━\n"
        "👉 <i>Tap <b>🔍 Find a Stranger</b> to start chatting!</i>"
    )

    try:
        await message.answer(
            welcome_text,
            reply_markup=get_welcome_keyboard(),
        )
    except Exception as e:
        logger.warning("Failed to send welcome card: %s", e)
        await message.answer(
            "👋 Welcome to Stranger Chat!\n\nTap /find to search for a partner.",
            reply_markup=get_idle_reply_keyboard(),
        )
        return

    try:
        await message.answer(
            "💡 <i>Use the quick action buttons below anytime:</i>",
            reply_markup=get_idle_reply_keyboard(),
        )
    except Exception as e:
        logger.warning("Failed to send idle reply keyboard: %s", e)


@router.callback_query(F.data == "cb_end_and_restart")
async def handle_end_and_restart(callback: CallbackQuery) -> None:
    """Closes current session and redisplays the start welcome menu."""
    await callback.answer("Chat ended.")
    if not callback.from_user or not callback.message:
        return
    tg_id = callback.from_user.id
    session = await database.close_session_for_user(tg_id)
    if session:
        partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
        try:
            await callback.bot.send_message(
                chat_id=partner_id,
                text=get_partner_ended_text(),
                reply_markup=get_partner_disconnected_keyboard(),
            )
        except Exception:
            pass
    await handle_start(callback.message)


@router.message(Command("help"))
@router.message(F.text == "❓ Help")
async def handle_help_command(message: Message) -> None:
    """Displays a clean menu of all commands."""
    await message.answer(HELP_TEXT, reply_markup=get_idle_reply_keyboard())


@router.callback_query(F.data == "cb_help")
async def handle_help_callback(callback: CallbackQuery) -> None:
    """Displays the help menu when requested via inline button."""
    await callback.answer()
    if callback.message:
        await callback.message.answer(HELP_TEXT, reply_markup=get_idle_reply_keyboard())


@router.message(Command("invite"))
@router.message(F.text == "🚀 Invite Friends")
async def handle_invite_command(message: Message) -> None:
    """Provides a viral shareable invite message and a one-tap Telegram share button."""
    bot_user = (await message.bot.get_me()).username or "StrangersChattingBot"
    invite_text = (
        "🚀 <b>Invite Friends to Stranger Chat!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Share this link with your friends or Telegram groups:\n\n"
        f"<i>\"⚡ I'm chatting with new people worldwide on this free anonymous bot! Join here: t.me/{bot_user}\"</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Tap the button below to share directly with friends:"
    )
    await message.answer(invite_text, reply_markup=get_invite_keyboard(bot_user))


@router.message(Command("stats"))
async def handle_stats_command(message: Message) -> None:
    """Admin-only dashboard command showing user counts, age demographics, active chats, and queue status."""
    from_user = message.from_user
    if not from_user:
        return

    if from_user.id != config.ADMIN_ID:
        await message.answer("⛔ Access denied. This command is restricted to administrators.")
        return

    db_stats = await database.get_stats()
    queue_stats = await match_queue.get_stats()

    stats_text = (
        "📊 <b>Stranger Chat Bot — Admin Dashboard</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "👥 <b>User Statistics:</b>\n"
        f"• Total Users: <b>{db_stats['total_users']}</b>\n"
        f"• Male: <b>{db_stats['male_users']}</b> | Female: <b>{db_stats['female_users']}</b>\n"
        f"• Prefer Not to Say: <b>{db_stats.get('prefer_not_to_say_users', 0)}</b>\n\n"
        "🎂 <b>Age Demographics:</b>\n"
        f"• Below 18: <b>{db_stats.get('age_below_18', 0)}</b>\n"
        f"• 18–25: <b>{db_stats.get('age_18_25', 0)}</b>\n"
        f"• 25–35: <b>{db_stats.get('age_25_35', 0)}</b>\n"
        f"• 40+: <b>{db_stats.get('age_40_plus', 0)}</b>\n\n"
        "💬 <b>Chats & Activity:</b>\n"
        f"• Active Chat Sessions: <b>{db_stats['active_chats']}</b>\n\n"
        "⏳ <b>Matchmaking Queue:</b>\n"
        f"• Total Waiting: <b>{queue_stats['total']}</b>\n"
        f"• Males in Queue: <b>{queue_stats['males']}</b>\n"
        f"• Females in Queue: <b>{queue_stats['females']}</b>\n"
        f"• Prefer Not to Say: <b>{queue_stats.get('prefer_not_to_say', 0)}</b>\n"
        f"• VIP Premium Waiting: <b>{queue_stats['premiums']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(stats_text)


async def build_profile_card(from_user, db_user: dict[str, Any]) -> str:
    """Builds the aesthetic profile card text."""
    _, age_days, _ = account_age.check_account_age(from_user.id)
    user_gender = format_gender_display(db_user.get("gender"))
    user_age = format_age_display(db_user.get("age_range"))
    is_premium = await database.is_premium_active(from_user.id)
    plan_badge = "⭐ VIP Member (Priority Queue)" if is_premium else "Standard Member (Free)"
    chats_count = db_user.get("chat_count", 0)
    strikes = db_user.get("strikes", 0)
    reputation = "⭐️⭐️⭐️⭐️⭐️ Excellent" if strikes == 0 else f"⚠️ Caution ({strikes} strikes)"

    return (
        "👤 <b>Your Stranger Chat Profile</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Anonymous ID:</b> <code>#SC-{str(from_user.id)[-6:]}</code>\n"
        f"⚧️ <b>Gender:</b> {user_gender}\n"
        f"🎂 <b>Age Range:</b> {user_age}\n"
        f"⭐ <b>Membership:</b> {plan_badge}\n"
        f"⏳ <b>Account Age:</b> ~{age_days} days (Verified ✅)\n"
        f"💬 <b>Chats Completed:</b> {chats_count}\n"
        f"🛡️ <b>Reputation:</b> {reputation}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<i>Update your preferences anytime using buttons below:</i>"
    )


@router.message(Command("profile"))
@router.message(Command("me"))
@router.message(F.text == "👤 Profile")
async def handle_profile_command(message: Message) -> None:
    """Displays the user's sleek anonymous profile card."""
    from_user = message.from_user
    if not from_user:
        return

    db_user, is_banned = await get_or_register_user(from_user)
    if is_banned:
        await message.answer("⛔ Your account is suspended.")
        return

    profile_card = await build_profile_card(from_user, db_user)
    await message.answer(profile_card, reply_markup=get_profile_keyboard())


@router.callback_query(F.data == "cb_open_profile")
async def handle_open_profile_callback(callback: CallbackQuery) -> None:
    """Displays the user's sleek anonymous profile card from inline buttons."""
    await callback.answer()
    if not callback.from_user or not callback.message:
        return

    db_user, is_banned = await get_or_register_user(callback.from_user)
    if is_banned:
        await callback.message.answer("⛔ Your account is suspended.")
        return

    profile_card = await build_profile_card(callback.from_user, db_user)
    try:
        await callback.message.edit_text(profile_card, reply_markup=get_profile_keyboard())
    except Exception:
        await callback.message.answer(profile_card, reply_markup=get_profile_keyboard())


@router.message(Command("icebreaker"))
@router.message(F.text.in_({"🎲 Icebreakers", "🎲 Send Icebreaker"}))
async def handle_icebreaker(message: Message) -> None:
    """Sends a friendly conversation starter directly into the chat like a normal question."""
    from_user = message.from_user
    if not from_user:
        return

    partner_id = await database.get_partner_id(from_user.id)
    icebreaker_question = icebreakers.get_random_icebreaker()

    if not partner_id:
        # User is idle; show a clean prompt
        await message.answer(
            f"💡 <b>Conversation starter idea:</b>\n\n{icebreaker_question}\n\n"
            "👉 Tap <b>🔍 Find Stranger</b> to start chatting!",
            reply_markup=get_idle_reply_keyboard(),
        )
        return

    # In active chat: send question directly as normal text (no decorative designs)
    await message.answer(
        f"💬 <i>You asked:</i>\n{icebreaker_question}",
        reply_markup=get_chat_reply_keyboard(),
    )
    try:
        await message.bot.send_message(
            chat_id=partner_id,
            text=icebreaker_question,
            reply_markup=get_chat_reply_keyboard(),
        )
    except Exception as e:
        logger.warning("Failed to send icebreaker to partner %s: %s", partner_id, e)


@router.callback_query(F.data == "cb_get_icebreaker")
async def handle_icebreaker_callback(callback: CallbackQuery) -> None:
    """Inline callback returning a friendly icebreaker."""
    await callback.answer()
    icebreaker_question = icebreakers.get_random_icebreaker()
    if callback.message:
        await callback.message.answer(
            f"💡 <b>Conversation starter:</b>\n\n{icebreaker_question}",
            reply_markup=get_idle_reply_keyboard(),
        )


# =========================================================
# 🎮 MINI GAMES HANDLERS (SOLO & PARTNER DUELS)
# =========================================================
@router.message(Command("game"))
@router.message(Command("games"))
@router.message(F.text.in_({"🎮 Mini Games", "🎮 Play Game"}))
async def handle_games_command(message: Message) -> None:
    """Displays the interactive mini-games hub (adapted for solo or partner duel)."""
    from_user = message.from_user
    if not from_user:
        return

    active_session = await database.get_active_session(from_user.id)
    is_in_chat = active_session is not None

    if is_in_chat:
        menu_text = (
            "🎮 <b>Partner Game Room</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Challenge your stranger partner to a real-time mini-game!\n\n"
            "• ⚡ <b>Math Speed Duel:</b> First to solve wins!\n"
            "• ✊ <b>RPS Duel:</b> Simultaneous hidden moves!\n"
            "• 🔢 <b>Number Guess Race:</b> First to crack 0–9 wins!\n"
            "• 🎲 <b>Dice Roll Duel:</b> Roll higher than your partner!\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Tap an option below to start:"
        )
    else:
        menu_text = (
            "🎮 <b>Mini Games Arcade</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Enjoy quick games while waiting for a match!\n\n"
            "• 🔢 <b>Guess the Number (0–9)</b>\n"
            "• 🧮 <b>Math Speed Puzzle (+, -, ×, ÷)</b>\n"
            "• ✊ <b>Rock-Paper-Scissors</b> (vs Bot)\n"
            "• 🎲 <b>Lucky Dice Roll</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Select a game to play:"
        )

    await message.answer(
        menu_text,
        reply_markup=get_games_menu_keyboard(is_in_chat=is_in_chat),
    )


@router.callback_query(F.data == "cb_game:menu")
async def handle_game_menu_callback(callback: CallbackQuery) -> None:
    """Returns to the games hub menu."""
    await callback.answer()
    if not callback.from_user or not callback.message:
        return

    active_session = await database.get_active_session(callback.from_user.id)
    is_in_chat = active_session is not None

    menu_text = (
        "🎮 <b>Partner Game Room</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Challenge your partner to a live mini-game!"
        if is_in_chat
        else "🎮 <b>Mini Games Arcade</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Select a game to play solo:"
    )
    try:
        await callback.message.edit_text(
            menu_text,
            reply_markup=get_games_menu_keyboard(is_in_chat=is_in_chat),
        )
    except Exception as e:
        logger.warning("Failed to edit game menu: %s", e)


@router.callback_query(F.data == "cb_game:solo_menu")
async def handle_solo_menu_callback(callback: CallbackQuery) -> None:
    """Opens solo games menu even when inside chat."""
    await callback.answer()
    if callback.message:
        try:
            await callback.message.edit_text(
                "🕹️ <b>Solo Games Arcade</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "Pick a solo game below:",
                reply_markup=get_games_menu_keyboard(is_in_chat=False),
            )
        except Exception as e:
            logger.warning("Failed to edit solo menu: %s", e)


# --- Solo: Guess Number ---
@router.callback_query(F.data == "cb_game:solo_guess")
async def handle_solo_guess_start(callback: CallbackQuery) -> None:
    """Starts a solo number guessing game (0-9)."""
    await callback.answer()
    if not callback.from_user or not callback.message:
        return

    solo_games.start_guess(callback.from_user.id)
    guess_text = (
        "🔢 <b>Guess the Number (0–9)!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "I'm thinking of a secret digit between <b>0</b> and <b>9</b>.\n"
        "Tap a number below to make your guess:"
    )
    guess_kb = get_number_guess_keyboard(prefix="cb_solo_guess")
    try:
        await callback.message.edit_text(guess_text, reply_markup=guess_kb)
    except Exception:
        await callback.message.answer(guess_text, reply_markup=guess_kb)


@router.callback_query(F.data.startswith("cb_solo_guess:"))
async def handle_solo_guess_check(callback: CallbackQuery) -> None:
    """Processes a solo guess digit."""
    if not callback.from_user or not callback.message:
        return

    guess_digit = int(callback.data.split(":")[1])
    result, attempts, target = solo_games.check_guess(callback.from_user.id, guess_digit)

    if result == "correct":
        await callback.answer("🎉 Correct! You won!", show_alert=True)
        win_text = (
            f"🎉 <b>BULLSEYE!</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"The secret number was <b>{target}</b>!\n"
            f"You cracked it in <b>{attempts}</b> attempt(s)! 🏆\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Play again or choose another game:"
        )
        win_kb = get_games_menu_keyboard(is_in_chat=False)
        try:
            await callback.message.edit_text(win_text, reply_markup=win_kb)
        except Exception:
            await callback.message.answer(win_text, reply_markup=win_kb)
    elif result == "higher":
        await callback.answer(f"⬆️ Secret number is HIGHER than {guess_digit}!", show_alert=False)
        high_text = (
            f"🔢 <b>Guess the Number (0–9)</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"Your guess: <b>{guess_digit}</b> (Too low! ⬆️)\n"
            f"Attempts so far: <b>{attempts}</b>\n\n"
            "Try another digit below:"
        )
        high_kb = get_number_guess_keyboard(prefix="cb_solo_guess")
        try:
            await callback.message.edit_text(high_text, reply_markup=high_kb)
        except Exception:
            await callback.message.answer(high_text, reply_markup=high_kb)
    else:  # lower
        await callback.answer(f"⬇️ Secret number is LOWER than {guess_digit}!", show_alert=False)
        low_text = (
            f"🔢 <b>Guess the Number (0–9)</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"Your guess: <b>{guess_digit}</b> (Too high! ⬇️)\n"
            f"Attempts so far: <b>{attempts}</b>\n\n"
            "Try another digit below:"
        )
        low_kb = get_number_guess_keyboard(prefix="cb_solo_guess")
        try:
            await callback.message.edit_text(low_text, reply_markup=low_kb)
        except Exception:
            await callback.message.answer(low_text, reply_markup=low_kb)


# --- Solo: Math Puzzle ---
@router.callback_query(F.data == "cb_game:solo_math")
async def handle_solo_math_start(callback: CallbackQuery) -> None:
    """Starts a solo math arithmetic puzzle."""
    await callback.answer()
    if not callback.from_user or not callback.message:
        return

    puzzle = solo_games.start_math(callback.from_user.id)
    math_text = (
        f"🧮 <b>Math Speed Puzzle</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"Solve: <b>{puzzle.question}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Select the correct answer:"
    )
    math_kb = get_math_puzzle_keyboard(puzzle.options, prefix="cb_solo_math")
    try:
        await callback.message.edit_text(math_text, reply_markup=math_kb)
    except Exception:
        await callback.message.answer(math_text, reply_markup=math_kb)


@router.callback_query(F.data.startswith("cb_solo_math:"))
async def handle_solo_math_check(callback: CallbackQuery) -> None:
    """Checks the selected solo math answer."""
    if not callback.from_user or not callback.message:
        return

    chosen_ans = int(callback.data.split(":")[1])
    is_correct, answer = solo_games.check_math(callback.from_user.id, chosen_ans)

    if is_correct:
        await callback.answer("🌟 Correct answer!", show_alert=False)
        status_text = f"✅ <b>Brilliant!</b> <b>{chosen_ans}</b> is correct! 🌟"
    else:
        await callback.answer(f"❌ Incorrect! Correct was {answer}", show_alert=False)
        status_text = f"❌ <b>Not quite!</b> Correct answer was <b>{answer}</b>."

    next_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Next Puzzle", callback_data="cb_game:solo_math")],
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )
    math_res_text = (
        f"🧮 <b>Math Puzzle Result</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"{status_text}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Ready for another one?"
    )
    try:
        await callback.message.edit_text(math_res_text, reply_markup=next_kb)
    except Exception:
        await callback.message.answer(math_res_text, reply_markup=next_kb)


# --- Solo: Rock Paper Scissors ---
@router.callback_query(F.data == "cb_game:solo_rps")
async def handle_solo_rps_start(callback: CallbackQuery) -> None:
    """Prompts move selection for solo RPS."""
    await callback.answer()
    if not callback.message:
        return

    rps_text = (
        "✊ <b>Rock-Paper-Scissors (vs Bot)</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Choose your move:"
    )
    rps_kb = get_rps_keyboard(prefix="cb_solo_rps")
    try:
        await callback.message.edit_text(rps_text, reply_markup=rps_kb)
    except Exception:
        await callback.message.answer(rps_text, reply_markup=rps_kb)


@router.callback_query(F.data.startswith("cb_solo_rps:"))
async def handle_solo_rps_play(callback: CallbackQuery) -> None:
    """Plays RPS round against the Bot."""
    await callback.answer()
    if not callback.message:
        return

    user_move = callback.data.split(":")[1]
    bot_move, outcome = solo_games.play_rps(user_move)

    u_emoji = RPS_EMOJIS.get(user_move, user_move)
    b_emoji = RPS_EMOJIS.get(bot_move, bot_move)
    round_id = random.randint(100, 999)

    if outcome == "win":
        res_text = "🎉 <b>YOU WIN!</b> 🏆"
    elif outcome == "lose":
        res_text = "🤖 <b>BOT WINS!</b> Better luck next time!"
    else:
        res_text = "🤝 <b>IT'S A TIE!</b> Great minds think alike."

    again_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Play Again", callback_data="cb_game:solo_rps")],
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )
    result_text = (
        f"✊ <b>Rock-Paper-Scissors Match</b> (Round #{round_id})\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Your Move:</b> {u_emoji}\n"
        f"🤖 <b>Bot's Move:</b> {b_emoji}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"{res_text}"
    )
    try:
        await callback.message.edit_text(result_text, reply_markup=again_kb)
    except Exception:
        await callback.message.answer(result_text, reply_markup=again_kb)


# --- Solo: Lucky Dice Roll ---
@router.callback_query(F.data == "cb_game:solo_dice")
async def handle_solo_dice(callback: CallbackQuery) -> None:
    """Rolls a 6-sided dice against the Bot."""
    await callback.answer()
    if not callback.message:
        return

    u_roll, b_roll, outcome = solo_games.roll_dice()
    roll_id = random.randint(100, 999)
    if outcome == "win":
        res = "🎉 <b>You rolled higher and won!</b> 🏆"
    elif outcome == "lose":
        res = "🤖 <b>Bot rolled higher!</b>"
    else:
        res = "🤝 <b>Equal rolls — It's a draw!</b>"

    dice_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎲 Roll Again", callback_data="cb_game:solo_dice"),
                InlineKeyboardButton(text="🎲 3D Dice", callback_data="cb_game:animated_dice"),
            ],
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )
    result_text = (
        f"🎲 <b>Lucky Dice Roll</b> (Roll #{roll_id})\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>You rolled:</b> 🎲 <b>{u_roll}</b>\n"
        f"🤖 <b>Bot rolled:</b> 🎲 <b>{b_roll}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"{res}"
    )
    try:
        await callback.message.edit_text(result_text, reply_markup=dice_kb)
    except Exception:
        await callback.message.answer(result_text, reply_markup=dice_kb)


@router.callback_query(F.data == "cb_game:animated_dice")
async def handle_animated_dice(callback: CallbackQuery) -> None:
    """Sends an authentic animated 3D physics dice."""
    await callback.answer()
    if not callback.message:
        return

    await callback.message.answer("🎲 <b>Rolling 3D Physics Dice...</b>")
    dice_msg = await callback.message.answer_dice(emoji="🎲")
    score = dice_msg.dice.value if dice_msg.dice else random.randint(1, 6)

    again_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Roll Again", callback_data="cb_game:animated_dice")],
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )
    await callback.message.answer(
        f"🎯 You rolled a <b>{score}</b>! 🌟",
        reply_markup=again_kb,
    )


# =========================================================
# ⚔️ PARTNER DUELS HANDLERS
# =========================================================
@router.callback_query(F.data == "cb_game:duel_math")
async def handle_duel_math_start(callback: CallbackQuery) -> None:
    """Launches a live Math Speed Duel between both partners in chat, or solo if alone."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    session = await database.get_active_session(tg_id)
    if not session:
        await handle_solo_math_start(callback)
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    puzzle = await duel_games.start_math_duel(session["id"], tg_id, partner_id)
    await callback.answer("⚡ Math duel started!")

    duel_text = (
        "⚡ <b>MATH SPEED DUEL!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"First player to solve wins:\n\n"
        f"👉 <b>{puzzle.question}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Tap the correct answer:"
    )
    duel_kb = get_math_puzzle_keyboard(puzzle.options, prefix="cb_duel_math")

    try:
        await callback.message.edit_text(duel_text, reply_markup=duel_kb)
    except Exception:
        await callback.message.answer(duel_text, reply_markup=duel_kb)

    try:
        await callback.bot.send_message(chat_id=partner_id, text=duel_text, reply_markup=duel_kb)
    except Exception as e:
        logger.warning("Failed to send math duel to partner %s: %s", partner_id, e)


@router.callback_query(F.data.startswith("cb_duel_math:"))
async def handle_duel_math_answer(callback: CallbackQuery) -> None:
    """Evaluates a player's answer in a live Math Speed Duel."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    chosen_ans = int(callback.data.split(":")[1])

    session = await database.get_active_session(tg_id)
    if not session:
        await callback.answer("Chat session ended.", show_alert=True)
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    status, winner_id, correct_ans = await duel_games.submit_math_answer(
        session["id"], tg_id, chosen_ans
    )

    if status == "winner":
        await callback.answer("🏆 You answered first and won!", show_alert=True)
        duel_math_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⚡ Play Math Again", callback_data="cb_game:duel_math")],
                [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
            ]
        )
        win_card = (
            "🏆 <b>MATH DUEL COMPLETE!</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Correct Answer: <b>{correct_ans}</b>\n"
            "⚡ <b>Winner:</b> Your partner was quick and solved it first! 🥇\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "<i>Tap below to play again or open menu:</i>"
        )
        my_win_card = (
            "🏆 <b>MATH DUEL COMPLETE!</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Correct Answer: <b>{correct_ans}</b>\n"
            "⚡ <b>Winner:</b> YOU solved it first! 🥇 Great speed!\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "<i>Tap below to play again or open menu:</i>"
        )
        try:
            await callback.message.edit_text(my_win_card, reply_markup=duel_math_kb)
        except Exception:
            await callback.message.answer(my_win_card, reply_markup=duel_math_kb)

        try:
            await callback.bot.send_message(chat_id=partner_id, text=win_card, reply_markup=duel_math_kb)
        except Exception as e:
            logger.warning("Failed to notify math duel partner %s: %s", partner_id, e)

    elif status == "wrong":
        await callback.answer(f"❌ {chosen_ans} is incorrect! Try another option!", show_alert=False)
    elif status == "already_finished":
        await callback.answer(f"Round already won! Answer was {correct_ans}.", show_alert=True)
    else:
        await callback.answer("Game expired.", show_alert=False)


@router.callback_query(F.data == "cb_game:duel_rps")
async def handle_duel_rps_start(callback: CallbackQuery) -> None:
    """Launches a hidden-move RPS duel between both partners, or solo if alone."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    session = await database.get_active_session(tg_id)
    if not session:
        await handle_solo_rps_start(callback)
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    await duel_games.start_rps_duel(session["id"], tg_id, partner_id)
    await callback.answer("✊ RPS duel started!")

    rps_duel_text = (
        "✊ <b>ROCK-PAPER-SCISSORS DUEL!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Tap your secret move below.\n"
        "<i>Moves stay hidden until both players choose!</i>"
    )
    rps_kb = get_rps_keyboard(prefix="cb_duel_rps")

    try:
        await callback.message.edit_text(rps_duel_text, reply_markup=rps_kb)
    except Exception:
        await callback.message.answer(rps_duel_text, reply_markup=rps_kb)

    try:
        await callback.bot.send_message(chat_id=partner_id, text=rps_duel_text, reply_markup=rps_kb)
    except Exception as e:
        logger.warning("Failed to send rps duel to partner %s: %s", partner_id, e)


@router.callback_query(F.data.startswith("cb_duel_rps:"))
async def handle_duel_rps_move(callback: CallbackQuery) -> None:
    """Registers player's move in an RPS duel and reveals when both are locked in."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    selected_move = callback.data.split(":")[1]

    session = await database.get_active_session(tg_id)
    if not session:
        await callback.answer("Chat session ended.", show_alert=True)
        return

    is_finished, moves, winner_id = await duel_games.submit_rps_move(
        session["id"], tg_id, selected_move
    )

    if not is_finished:
        move_emoji = RPS_EMOJIS.get(selected_move, selected_move)
        await callback.answer(f"Locked in {move_emoji}! Waiting for partner...", show_alert=True)
        try:
            await callback.message.edit_text(
                f"✊ <b>RPS Move Locked:</b> {move_emoji}\n\n"
                "⏳ <i>Waiting for your partner to make their choice...</i>"
            )
        except Exception:
            pass
        return

    # Both players moved: reveal!
    u1 = session["user1_id"]
    u2 = session["user2_id"]
    m1_name = RPS_EMOJIS.get(moves.get(u1, "rock"), "❓")
    m2_name = RPS_EMOJIS.get(moves.get(u2, "rock"), "❓")

    if winner_id is None:
        result_title = "🤝 <b>IT'S A DRAW!</b> Both chose the same move!"
    else:
        winner_tag = "You won! 🏆" if winner_id == tg_id else "Partner won! 🎉"
        result_title = f"🏆 <b>RESULT:</b> {winner_tag}"

    results_text = (
        "✊ <b>RPS DUEL RESULTS!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"• Player 1: {m1_name}\n"
        f"• Player 2: {m2_name}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"{result_title}\n\n"
        "<i>Tap below to play again or open menu:</i>"
    )

    duel_rps_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✊ Play RPS Again", callback_data="cb_game:duel_rps")],
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )

    await callback.answer("Round complete!", show_alert=False)
    try:
        await callback.message.edit_text(results_text, reply_markup=duel_rps_kb)
    except Exception:
        await callback.message.answer(results_text, reply_markup=duel_rps_kb)

    partner_id = u2 if u1 == tg_id else u1
    try:
        await callback.bot.send_message(chat_id=partner_id, text=results_text, reply_markup=duel_rps_kb)
    except Exception as e:
        logger.warning("Failed to send RPS result to %s: %s", partner_id, e)


@router.callback_query(F.data == "cb_game:duel_guess")
async def handle_duel_guess_start(callback: CallbackQuery) -> None:
    """Launches a Number Guess Race between both partners, or solo if alone."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    session = await database.get_active_session(tg_id)
    if not session:
        await handle_solo_guess_start(callback)
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    await duel_games.start_guess_duel(session["id"], tg_id, partner_id)
    await callback.answer("🔢 Number race started!")

    guess_duel_text = (
        "🔢 <b>NUMBER GUESS RACE (0–9)!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "A secret number from <b>0</b> to <b>9</b> was chosen.\n"
        "First person to hit the exact number wins!\n\n"
        "Tap your guess below:"
    )
    guess_kb = get_number_guess_keyboard(prefix="cb_duel_guess")

    try:
        await callback.message.edit_text(guess_duel_text, reply_markup=guess_kb)
    except Exception:
        await callback.message.answer(guess_duel_text, reply_markup=guess_kb)

    try:
        await callback.bot.send_message(chat_id=partner_id, text=guess_duel_text, reply_markup=guess_kb)
    except Exception as e:
        logger.warning("Failed to send guess duel to partner %s: %s", partner_id, e)


@router.callback_query(F.data.startswith("cb_duel_guess:"))
async def handle_duel_guess_check(callback: CallbackQuery) -> None:
    """Checks a guess in the live Number Guess Race."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    guess_digit = int(callback.data.split(":")[1])

    session = await database.get_active_session(tg_id)
    if not session:
        await callback.answer("Chat session ended.", show_alert=True)
        return

    status, target, winner_id = await duel_games.submit_guess_duel(
        session["id"], tg_id, guess_digit
    )

    if status == "correct":
        await callback.answer("🎉 Correct! You won the race!", show_alert=True)
        partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]

        duel_guess_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔢 Play Guess Again", callback_data="cb_game:duel_guess")],
                [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
            ]
        )
        my_win_msg = (
            "🎉 <b>BULLSEYE! YOU WON!</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"The secret number was <b>{target}</b>!\n"
            "You guessed it first and won the race! 🥇\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "<i>Tap below to play again or open menu:</i>"
        )
        their_win_msg = (
            "🎉 <b>RACE OVER!</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"The secret number was <b>{target}</b>!\n"
            "Your partner guessed it first and won the race! 🥇\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "<i>Tap below to play again or open menu:</i>"
        )
        try:
            await callback.message.edit_text(my_win_msg, reply_markup=duel_guess_kb)
        except Exception:
            await callback.message.answer(my_win_msg, reply_markup=duel_guess_kb)

        try:
            await callback.bot.send_message(chat_id=partner_id, text=their_win_msg, reply_markup=duel_guess_kb)
        except Exception as e:
            logger.warning("Failed to notify guess duel partner %s: %s", partner_id, e)

    elif status == "higher":
        await callback.answer(f"⬆️ Secret number is HIGHER than {guess_digit}!", show_alert=False)
    elif status == "lower":
        await callback.answer(f"⬇️ Secret number is LOWER than {guess_digit}!", show_alert=False)
    elif status == "already_finished":
        await callback.answer(f"Race already finished! Target was {target}.", show_alert=True)


@router.callback_query(F.data == "cb_game:duel_dice")
async def handle_duel_dice(callback: CallbackQuery) -> None:
    """Rolls a lucky dice for both partners in active chat, or solo if alone."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    session = await database.get_active_session(tg_id)
    if not session:
        await handle_solo_dice(callback)
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    await callback.answer("🎲 Rolling dice for both players...")

    r_me = random.randint(1, 6)
    r_them = random.randint(1, 6)
    duel_id = random.randint(100, 999)

    if r_me > r_them:
        res_me = "🎉 <b>YOU WON!</b> (Your roll was higher) 🏆"
        res_them = "🤖 <b>PARTNER WON!</b> (Their roll was higher)"
    elif r_them > r_me:
        res_me = "🤖 <b>PARTNER WON!</b> (Their roll was higher)"
        res_them = "🎉 <b>YOU WON!</b> (Your roll was higher) 🏆"
    else:
        res_me = "🤝 <b>IT'S A TIE!</b> Both rolled the same!"
        res_them = res_me

    msg_me = (
        f"🎲 <b>LUCKY DICE DUEL!</b> (Duel #{duel_id})\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Your Roll:</b> 🎲 <b>{r_me}</b>\n"
        f"👤 <b>Partner's Roll:</b> 🎲 <b>{r_them}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"{res_me}\n\n"
        "<i>Tap 🎲 Roll Again to roll another pair!</i>"
    )
    msg_them = (
        f"🎲 <b>LUCKY DICE DUEL!</b> (Duel #{duel_id})\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Your Roll:</b> 🎲 <b>{r_them}</b>\n"
        f"👤 <b>Partner's Roll:</b> 🎲 <b>{r_me}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"{res_them}\n\n"
        "<i>Tap 🎲 Roll Again to roll another pair!</i>"
    )

    duel_dice_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Roll Again", callback_data="cb_game:duel_dice")],
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )

    try:
        await callback.message.edit_text(msg_me, reply_markup=duel_dice_kb)
    except Exception:
        await callback.message.answer(msg_me, reply_markup=duel_dice_kb)

    try:
        await callback.bot.send_message(chat_id=partner_id, text=msg_them, reply_markup=duel_dice_kb)
    except Exception as e:
        logger.warning("Failed to send dice duel to %s: %s", partner_id, e)


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

    current_gender = format_gender_display(db_user.get("gender"))
    await message.answer(
        f"👤 <b>Gender Preference</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"Current selection: <b>{current_gender}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Select an option below to update:",
        reply_markup=get_gender_keyboard(),
    )


@router.callback_query(F.data == "cb_open_gender")
async def handle_open_gender_callback(callback: CallbackQuery) -> None:
    """Opens the gender selection keyboard from the welcome or profile message."""
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "👤 <b>Please select your gender preference:</b>\n"
            "Opposite gender is preferred during matching.",
            reply_markup=get_gender_keyboard(),
        )


@router.callback_query(F.data.startswith("cb_gender:"))
async def handle_gender_callback(callback: CallbackQuery) -> None:
    """Processes gender selection callbacks from inline buttons."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    selected_gender = callback.data.split(":")[1]

    if selected_gender not in ("male", "female", "prefer_not_to_say"):
        await callback.answer("Invalid selection.", show_alert=True)
        return

    await database.update_user_gender(tg_id, selected_gender)
    gender_badge = format_gender_display(selected_gender)
    await callback.answer(f"Gender set to {gender_badge}!")

    # Check if age range is set; if not, seamlessly prompt for age range next
    user_data = await database.get_user(tg_id) or {}
    current_age = user_data.get("age_range", "unknown")

    if current_age not in ("below_18", "18-25", "25-35", "40+"):
        try:
            await callback.message.edit_text(
                f"✅ <b>Gender set to {gender_badge}!</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "🎂 <b>Now, please select your age range:</b>\n"
                "This helps your partner know who they are chatting with.",
                reply_markup=get_age_keyboard(),
            )
        except Exception as e:
            logger.warning("Failed to edit callback message: %s", e)
    else:
        try:
            await callback.message.edit_text(
                f"✅ <b>Gender set to {gender_badge}!</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "You are all set to chat anonymously.\n\n"
                "👉 Tap <b>🔍 Find Stranger</b> below to start searching!\n"
                "👉 Tap <b>/gender</b> or <b>/age</b> to update your preferences.",
                reply_markup=get_profile_keyboard(),
            )
        except Exception as e:
            logger.warning("Failed to edit callback message: %s", e)


@router.message(Command("age"))
async def handle_age_command(message: Message) -> None:
    """Allows user to view or update their age range."""
    from_user = message.from_user
    if not from_user:
        return

    db_user, is_banned = await get_or_register_user(from_user)
    if is_banned:
        await message.answer("⛔ Your account is suspended.")
        return

    current_age = format_age_display(db_user.get("age_range"))
    await message.answer(
        f"🎂 <b>Age Range Selection</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"Current selection: <b>{current_age}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Select your age bracket below:",
        reply_markup=get_age_keyboard(),
    )


@router.callback_query(F.data == "cb_open_age")
async def handle_open_age_callback(callback: CallbackQuery) -> None:
    """Opens the age range keyboard from inline buttons."""
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "🎂 <b>Please select your age range:</b>",
            reply_markup=get_age_keyboard(),
        )


@router.callback_query(F.data.startswith("cb_age:"))
async def handle_age_callback(callback: CallbackQuery) -> None:
    """Processes age range selection callbacks from inline buttons."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    selected_age = callback.data.split(":")[1]

    if selected_age not in ("below_18", "18-25", "25-35", "40+"):
        await callback.answer("Invalid selection.", show_alert=True)
        return

    await database.update_user_age_range(tg_id, selected_age)
    age_badge = format_age_display(selected_age)
    await callback.answer(f"Age range set to {age_badge}!")

    try:
        await callback.message.edit_text(
            f"✅ <b>Age range set to {age_badge}!</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Your anonymous profile is complete.\n\n"
            "👉 Tap <b>🔍 Find Stranger</b> below to start chatting!",
            reply_markup=get_profile_keyboard(),
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
@router.message(F.text == "🔍 Find Stranger")
async def handle_find_command(message: Message) -> None:
    """Handles /find command or 'Find Stranger' button."""
    from_user = message.from_user
    if not from_user:
        return

    await execute_find_flow(message, from_user)


async def execute_find_flow(message: Message, from_user) -> None:
    """Core matchmaking execution logic shared between /find and buttons."""
    tg_id = from_user.id
    db_user, is_banned = await get_or_register_user(from_user)

    if is_banned:
        await message.answer("⛔ Your account is suspended from Stranger Chat.")
        return

    # Edge Case: User already in active chat
    active_session = await database.get_active_session(tg_id)
    if active_session:
        await message.answer(
            "💬 <b>You are already chatting with someone!</b>\n\n"
            "• Tap <b>⏭️ Next Stranger</b> to skip\n"
            "• Tap <b>⏹️ End Chat</b> to leave",
            reply_markup=get_chat_reply_keyboard(),
        )
        return

    gender = db_user.get("gender", "unknown")
    if gender not in ("male", "female", "prefer_not_to_say"):
        await message.answer(
            "⚠️ <b>Gender Selection Required</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Please select your gender preference before searching:",
            reply_markup=get_gender_keyboard(),
        )
        return

    age_range = db_user.get("age_range", "unknown")
    if age_range not in ("below_18", "18-25", "25-35", "40+"):
        await message.answer(
            "🎂 <b>Age Range Required</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Please select your age bracket before searching:",
            reply_markup=get_age_keyboard(),
        )
        return

    # Check if already waiting in queue
    if await match_queue.is_in_queue(tg_id):
        await message.answer(
            "⏳ <b>Already Searching!</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "You are currently in line waiting for a match. Please wait a moment or tap Cancel below:",
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
        age_range=age_range,
    )

    if matched and partner_id:
        partner_db = await database.get_user(partner_id) or {}
        notice_for_me = get_match_found_text(
            partner_gender=partner_db.get("gender"),
            partner_age=partner_db.get("age_range"),
        )
        notice_for_partner = get_match_found_text(
            partner_gender=gender,
            partner_age=age_range,
        )
        await message.answer(notice_for_me, reply_markup=get_chat_reply_keyboard())

        try:
            await message.bot.send_message(
                chat_id=partner_id,
                text=notice_for_partner,
                reply_markup=get_chat_reply_keyboard(),
            )
        except Exception as e:
            logger.error("Failed to notify matched partner %s: %s", partner_id, e)
    else:
        vip_tag = " ⭐ <i>(VIP Priority Queue)</i>" if is_premium else ""
        tip = (
            ""
            if is_premium
            else "\n\n💡 <i>Tip: VIP members get priority in the queue! Type /invite to share with friends.</i>"
        )
        await message.answer(
            f"🔍 <b>Searching for a partner...</b>{vip_tag}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"Looking for an opposite-gender stranger (or any waiting stranger).{tip}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Please wait, or tap below to cancel search:",
            reply_markup=get_search_keyboard(),
        )


@router.message(Command("next"))
@router.message(F.text == "⏭️ Next Stranger")
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
        # User not in active chat (e.g. partner already ended chat or user was idle); seamlessly find next!
        await execute_find_flow(message, from_user)
        return

    partner_id = (
        closed_session["user2_id"]
        if closed_session["user1_id"] == tg_id
        else closed_session["user1_id"]
    )

    try:
        await message.bot.send_message(
            chat_id=partner_id,
            text=get_partner_ended_text(),
            reply_markup=get_partner_disconnected_keyboard(),
        )
    except Exception as e:
        logger.warning("Failed to notify disconnected partner %s: %s", partner_id, e)

    await match_queue.remove_user(tg_id)

    gender = db_user.get("gender", "unknown")
    if gender not in ("male", "female", "prefer_not_to_say"):
        await message.answer(
            "⚠️ Please select your gender first using /gender to find a match.",
            reply_markup=get_gender_keyboard(),
        )
        return

    age_range = db_user.get("age_range", "unknown")
    if age_range not in ("below_18", "18-25", "25-35", "40+"):
        await message.answer(
            "🎂 Please select your age bracket first using /age to find a match.",
            reply_markup=get_age_keyboard(),
        )
        return

    is_premium = await database.is_premium_active(tg_id)
    new_partner_id, matched = await match_queue.find_match_or_enqueue(
        tg_id=tg_id,
        gender=gender,
        is_premium=is_premium,
        age_range=age_range,
    )

    if matched and new_partner_id:
        partner_db = await database.get_user(new_partner_id) or {}
        notice_for_me = get_match_found_text(
            partner_gender=partner_db.get("gender"),
            partner_age=partner_db.get("age_range"),
        )
        notice_for_partner = get_match_found_text(
            partner_gender=gender,
            partner_age=age_range,
        )
        await message.answer(notice_for_me, reply_markup=get_chat_reply_keyboard())
        try:
            await message.bot.send_message(
                chat_id=new_partner_id,
                text=notice_for_partner,
                reply_markup=get_chat_reply_keyboard(),
            )
        except Exception as e:
            logger.error("Failed to notify new matched partner %s: %s", new_partner_id, e)
    else:
        vip_tag = " ⭐ <i>(VIP Priority)</i>" if is_premium else ""
        await message.answer(
            f"🔍 <b>Searching for a new stranger...</b>{vip_tag}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Looking for a match. Please wait a moment...",
            reply_markup=get_search_keyboard(),
        )


@router.message(Command("stop"))
@router.message(F.text == "⏹️ End Chat")
async def handle_stop_command(message: Message) -> None:
    """
    Handles /stop command:
    - If in active chat: ends session, notifies partner with motivational quote & options.
      Replies to user with motivational quote & options.
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
                text=get_partner_ended_text(),
                reply_markup=get_partner_disconnected_keyboard(),
            )
        except Exception as e:
            logger.warning("Failed to notify partner %s on /stop: %s", partner_id, e)

        await match_queue.remove_user(tg_id)
        await message.answer(
            "⏹️ <b>Chat ended.</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "✨ <b>Thought of the Moment:</b>\n"
            f"<i>{get_random_motivational_quote()}</i>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Where would you like to go next?",
            reply_markup=get_partner_disconnected_keyboard(),
        )
        return

    removed_from_queue = await match_queue.remove_user(tg_id)
    if removed_from_queue:
        await message.answer(
            "❌ <b>Search Cancelled</b>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "You have been removed from the matchmaking queue.\n"
            "Tap <b>🔍 Find Stranger</b> whenever you wish to search again!",
            reply_markup=get_idle_reply_keyboard(),
        )
        return

    await message.answer(
        "You are not in an active chat.\nTap <b>🔍 Find Stranger</b> to begin!",
        reply_markup=get_idle_reply_keyboard(),
    )


REPORT_REASONS = {
    "nsfw": "Inappropriate / NSFW Content",
    "abuse": "Harassment / Abusive Language",
    "spam": "Spam / Advertising",
    "creepy": "Creepy / Uncomfortable Behavior",
    "other": "Other Policy Violation",
}


@router.message(Command("report"))
@router.message(F.text == "🚨 Report User")
async def handle_report_command(message: Message) -> None:
    """
    Handles /report command:
    - Prompts user to select the reason from a list before reporting.
    """
    from_user = message.from_user
    if not from_user:
        return

    tg_id = from_user.id
    session = await database.get_active_session(tg_id)
    if not session:
        await message.answer(
            "You are not in an active chat to report.",
            reply_markup=get_idle_reply_keyboard(),
        )
        return

    await message.answer(
        "🚨 <b>Report Partner</b>\n\n"
        "Why are you reporting this user? Please select a reason below:",
        reply_markup=get_report_reasons_keyboard(),
    )


@router.callback_query(F.data == "cb_report:cancel")
async def handle_report_cancel(callback: CallbackQuery) -> None:
    """Cancels the report dialog and preserves the active chat."""
    await callback.answer("Report cancelled.")
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            await callback.message.edit_text("Report cancelled. You are still in chat.")


@router.callback_query(F.data.startswith("cb_report:"))
async def handle_report_reason_chosen(callback: CallbackQuery) -> None:
    """
    Processes chosen report reason:
    - Ends active chat session.
    - Records reason and issues strike to partner (auto-bans at 3 strikes).
    - Notifies reporter and reported partner.
    """
    await callback.answer()
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    reason_key = callback.data.split(":")[1]
    reason_label = REPORT_REASONS.get(reason_key, "Policy Violation")

    partner_id, partner_strikes, is_partner_banned = await database.report_partner(
        reporter_id=tg_id, reason=reason_label
    )

    if not partner_id:
        try:
            await callback.message.edit_text("You are no longer in an active chat.")
        except Exception:
            await callback.message.answer(
                "You are no longer in an active chat.",
                reply_markup=get_idle_reply_keyboard(),
            )
        return

    await match_queue.remove_user(tg_id)

    # Feedback to reporter
    reporter_text = (
        "🚨 <b>User Reported & Chat Ended</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Reason:</b> {reason_label}\n"
        "Thank you for helping keep Stranger Chat safe. A moderation strike was recorded.\n\n"
        "👉 Tap <b>🔍 Find Stranger</b> to connect with someone new!"
    )
    try:
        await callback.message.edit_text(reporter_text)
    except Exception:
        await callback.message.answer(reporter_text, reply_markup=get_idle_reply_keyboard())

    # Notification to reported partner
    try:
        penalty_text = (
            "\n⛔ <b>Your account has received 3 strikes and is now permanently banned.</b>"
            if is_partner_banned
            else f"\n⚠️ Warning: You now have {partner_strikes}/3 moderation strikes."
        )
        await callback.bot.send_message(
            chat_id=partner_id,
            text=(
                f"🚨 <b>You were reported by your partner.</b>\n"
                f"<b>Reason:</b> {reason_label}\n"
                f"The chat has ended.{penalty_text}"
            ),
            reply_markup=get_idle_reply_keyboard(),
        )
    except Exception as e:
        logger.warning("Failed to notify reported partner %s: %s", partner_id, e)


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
                "❌ <b>Search Cancelled</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "You have been removed from the matchmaking queue.\n"
                "Tap <b>🔍 Find Stranger</b> below whenever you are ready!",
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
    - If not connected, replies with idle menu reminder.
    """
    from_user = message.from_user
    if not from_user:
        return

    tg_id = from_user.id
    partner_id = await database.get_partner_id(tg_id)

    if not partner_id:
        await message.answer(
            "You are not connected to anyone.\n\n"
            "👉 Tap <b>🔍 Find Stranger</b> below to start chatting!",
            reply_markup=get_idle_reply_keyboard(),
        )
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
            + get_partner_ended_text(),
            reply_markup=get_partner_disconnected_keyboard(),
        )
    except Exception as e:
        logger.error("Unexpected error relaying message: %s", e)
        await message.answer(
            "⚠️ An error occurred while sending your message. Please try again."
        )
