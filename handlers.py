import asyncio
import html
import logging
import random
import time
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
    get_dice_challenge_keyboard,
    get_duel_rematch_keyboard,
    get_games_menu_keyboard,
    get_gender_keyboard,
    get_guess_waiting_keyboard,
    get_idle_reply_keyboard,
    get_invite_keyboard,
    get_language_keyboard,
    get_math_puzzle_keyboard,
    get_number_guess_keyboard,
    get_partner_disconnected_keyboard,
    get_profile_keyboard,
    get_report_reasons_keyboard,
    get_rps_keyboard,
    get_search_keyboard,
    get_spoiler_toggle_keyboard,
    get_welcome_keyboard,
)
from match_queue import match_queue
from quotes import (
    format_chat_duration,
    get_partner_ended_text,
    get_random_motivational_quote,
    get_session_elapsed_seconds,
    get_user_ended_text,
)

logger = logging.getLogger(__name__)

router = Router(name="base_handlers")

HELP_TEXT = (
    "📖 <b>Stranger Chat — Commands</b>\n\n"
    "• <b>/find</b> — 🔍 Search for a stranger\n"
    "• <b>/next</b> — ⏭️ Skip to next stranger\n"
    "• <b>/stop</b> — ⏹️ End current chat\n"
    "• <b>/games</b> — 🎮 Mini-games & partner duels\n"
    "• <b>/icebreaker</b> — 🎲 Conversation starter\n"
    "• <b>/profile</b> — 👤 View your profile\n"
    "• <b>/gender</b> — 👤 Set gender preference\n"
    "• <b>/age</b> — 🎂 Set age bracket\n"
    "• <b>/language</b> — 🌐 Set preferred language (Optional)\n"
    "• <b>/spoiler</b> — 👁️ Blur sensitive photos & media\n"
    "• <b>/report</b> — 🚨 Report inappropriate user\n"
    "• <b>/invite</b> — 🚀 Invite friends\n"
    "• <b>/help</b> — ❓ Help & commands\n\n"
    "🔐 <b>End-to-End Encrypted:</b> <i>All chats are 100% encrypted & strictly private — no one else can see your messages!</i>\n"
    "🛡️ <i>Be kind, respectful, and keep personal details safe.</i>"
)


LANGUAGE_NAMES = {
    "any": "Any (Global) 🌐",
    "en": "English 🇺🇸",
    "hi": "Hindi 🇮🇳",
    "hinglish": "Hinglish 🇮🇳",
    "es": "Spanish 🇪🇸",
    "ru": "Russian 🇷🇺",
    "ar": "Arabic 🇸🇦",
}


def format_language_display(lang: Any) -> str:
    """Formats language code into an aesthetic badge with emoji."""
    l_code = str(lang or "any").lower().strip()
    return LANGUAGE_NAMES.get(l_code, "Any (Global) 🌐")


def format_gender_display(gender: Any) -> str:
    """Formats gender string into an aesthetic badge with emoji."""
    g = str(gender or "").lower().strip()
    if g == "male":
        return "Male 👨"
    elif g == "female":
        return "Female 👩"
    elif g == "prefer_not_to_say":
        return "Prefer not to say 🎭"
    return "Not set 👤"


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
    return "Not set"


def get_match_found_text(
    partner_gender: Any,
    partner_age: Any,
    partner_lang: Any = "any",
) -> str:
    """Returns aesthetic match notification card detailing partner's gender, age, and language."""
    g_display = format_gender_display(partner_gender)
    a_display = format_age_display(partner_age)
    l_display = format_language_display(partner_lang)
    return (
        "🎉 <b>Connected with a Stranger!</b>\n\n"
        f"• <b>Gender:</b> {g_display}\n"
        f"• <b>Age:</b> {a_display}\n"
        f"• <b>Language:</b> {l_display}\n\n"
        "🔐 <i>End-to-End Encrypted: Only you and your partner can see these messages.</i>\n\n"
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
        f"• <b>Gender:</b> {gender_display}\n"
        if user_gender in ("male", "female", "prefer_not_to_say")
        else "• <b>Gender:</b> <i>Not set (tap Set Gender below)</i>\n"
    )
    age_status = (
        f"• <b>Age:</b> {age_display}\n"
        if user_age in ("below_18", "18-25", "25-35", "40+")
        else "• <b>Age:</b> <i>Not set (tap Set Age below)</i>\n"
    )

    welcome_text = (
        f"👋 <b>Welcome to Stranger Chat{name_display}!</b>\n\n"
        "Connect and chat anonymously with verified people worldwide. "
        "No names, no profiles — pure authentic connection.\n\n"
        "🔐 <b>End-to-End Encrypted:</b> <i>100% private conversations — no one else can see your chats.</i>\n\n"
        f"{gender_status}"
        f"{age_status}\n"
        "💡 <i>Be respectful. No NSFW or spam.</i>\n\n"
        "👉 Tap <b>🔍 Start Chatting</b> to begin!"
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
            "💬 <i>Menu ready below.</i>",
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
        duel_games.reset_session(session["id"])
        elapsed = get_session_elapsed_seconds(session)
        dur_str = format_chat_duration(elapsed)
        partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
        try:
            await callback.bot.send_message(
                chat_id=partner_id,
                text=get_partner_ended_text(dur_str),
                reply_markup=get_partner_disconnected_keyboard(),
            )
        except Exception:
            pass
    await handle_start(callback.message)


@router.message(Command("help"))
@router.message(F.text.in_({"❓ Help", "❓ Help & Rules"}))
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
@router.message(F.text.in_({"🚀 Invite Friends", "🚀 Share Bot"}))
async def handle_invite_command(message: Message) -> None:
    """Provides a viral shareable invite message and a one-tap Telegram share button."""
    bot_user = (await message.bot.get_me()).username or "StrangersChattingBot"
    invite_text = (
        "🚀 <b>Invite Friends to Stranger Chat</b>\n\n"
        "Share this link with your friends or Telegram groups:\n\n"
        f"<i>\"⚡ I'm chatting with new people worldwide on this free anonymous bot! Join here: t.me/{bot_user}\"</i>\n\n"
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
        "📊 <b>Stranger Chat Bot — Admin Dashboard</b>\n\n"
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
        f"• VIP Premium Waiting: <b>{queue_stats['premiums']}</b>"
    )
    await message.answer(stats_text)


async def build_profile_card(from_user, db_user: dict[str, Any]) -> str:
    """Builds the aesthetic profile card text."""
    _, age_days, _ = account_age.check_account_age(from_user.id)
    user_gender = format_gender_display(db_user.get("gender"))
    user_age = format_age_display(db_user.get("age_range"))
    user_lang = format_language_display(db_user.get("language", "any"))
    spoiler_enabled = bool(db_user.get("media_spoiler", 0))
    spoiler_display = "Enabled 👁️" if spoiler_enabled else "Disabled"
    is_premium = await database.is_premium_active(from_user.id)
    plan_badge = "⭐ VIP Member" if is_premium else "Standard (Free)"
    chats_count = db_user.get("chat_count", 0)
    strikes = db_user.get("strikes", 0)
    reputation = "⭐️ 100% Clean" if strikes == 0 else f"⚠️ {strikes} strike(s)"

    return (
        "👤 <b>Anonymous Profile</b>\n\n"
        f"• <b>ID:</b> <code>#SC-{str(from_user.id)[-6:]}</code>\n"
        f"• <b>Gender:</b> {user_gender}\n"
        f"• <b>Age:</b> {user_age}\n"
        f"• <b>Language:</b> {user_lang}\n"
        f"• <b>Media Blur:</b> {spoiler_display}\n"
        f"• <b>Membership:</b> {plan_badge}\n"
        f"• <b>Account Age:</b> ~{age_days} days\n"
        f"• <b>Chats Completed:</b> {chats_count}\n"
        f"• <b>Reputation:</b> {reputation}\n\n"
        "<i>Update your preferences below:</i>"
    )


@router.message(Command("profile"))
@router.message(Command("me"))
@router.message(F.text.in_({"👤 Profile", "👤 My Profile"}))
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
@router.message(F.text.in_({"🎲 Icebreaker", "🎲 Icebreakers", "🎲 Send Icebreaker"}))
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
@router.message(F.text.in_({"🎮 Games", "🎮 Game", "🎮 Mini Games", "🎮 Play Game"}))
async def handle_games_command(message: Message) -> None:
    """Displays the interactive mini-games hub (adapted for solo or partner duel)."""
    from_user = message.from_user
    if not from_user:
        return

    active_session = await database.get_active_session(from_user.id)
    is_in_chat = active_session is not None

    if is_in_chat:
        menu_text = (
            "🎮 <b>Partner Game Room</b>\n\n"
            "Challenge your partner to a real-time mini-game!\n\n"
            "• ⚡ <b>Math Speed Duel:</b> First to solve wins\n"
            "• ✊ <b>RPS Duel:</b> Simultaneous hidden moves\n"
            "• 🔢 <b>Number Guess Race:</b> First to crack 0–9 wins\n"
            "• 🎲 <b>Dice Roll Duel:</b> Highest roll wins\n\n"
            "Choose a game below:"
        )
    else:
        menu_text = (
            "🎮 <b>Mini Games Arcade</b>\n\n"
            "Quick games to play anytime:\n\n"
            "• 🔢 <b>Guess the Number (0–9)</b>\n"
            "• 🧮 <b>Math Speed Puzzle (+, -, ×, ÷)</b>\n"
            "• ✊ <b>Rock-Paper-Scissors</b> (vs Bot)\n"
            "• 🎲 <b>Lucky Dice Roll</b>\n\n"
            "Select a game below:"
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
        "🎮 <b>Partner Game Room</b>\n\nChallenge your partner to a live duel:"
        if is_in_chat
        else "🎮 <b>Mini Games Arcade</b>\n\nSelect a game to play solo:"
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
                "🕹️ <b>Solo Games Arcade</b>\n\nPick a solo game below:",
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
        "🔢 <b>Guess the Number (0–9)</b>\n\n"
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

    # Clean answer - no popup!
    await callback.answer()

    if result == "correct":
        win_text = (
            "🎉 <b>BULLSEYE! YOU WON!</b> 🏆\n\n"
            f"🎯 <b>Secret Number:</b> <b>{target}</b>\n"
            f"⚡ <b>Solved in:</b> <b>{attempts} attempt(s)!</b> 🥇\n\n"
            "<i>Play again or choose another game:</i>"
        )
        win_kb = get_games_menu_keyboard(is_in_chat=False)
        try:
            await callback.message.edit_text(win_text, reply_markup=win_kb)
        except Exception:
            await callback.message.answer(win_text, reply_markup=win_kb)
    elif result == "higher":
        high_text = (
            "🔢 <b>Guess the Number (0–9)</b>\n\n"
            f"❌ <b>{guess_digit}</b> is too low! (Go <b>HIGHER ⬆️</b>)\n"
            f"• Attempts so far: <b>{attempts}</b>\n\n"
            "Try another digit below:"
        )
        high_kb = get_number_guess_keyboard(prefix="cb_solo_guess")
        try:
            await callback.message.edit_text(high_text, reply_markup=high_kb)
        except Exception:
            await callback.message.answer(high_text, reply_markup=high_kb)
    else:  # lower
        low_text = (
            "🔢 <b>Guess the Number (0–9)</b>\n\n"
            f"❌ <b>{guess_digit}</b> is too high! (Go <b>LOWER ⬇️</b>)\n"
            f"• Attempts so far: <b>{attempts}</b>\n\n"
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
        "🧮 <b>Math Speed Puzzle</b>\n\n"
        f"Solve: <b>{puzzle.question}</b>\n\n"
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

    # Clean answer - no popup!
    await callback.answer()

    if is_correct:
        status_text = f"✅ <b>Brilliant!</b> <b>{chosen_ans}</b> is correct! 🌟"
    else:
        status_text = f"❌ <b>Not quite!</b> Correct answer was <b>{answer}</b>."

    next_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Next Puzzle", callback_data="cb_game:solo_math")],
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )
    math_res_text = (
        "🧮 <b>MATH PUZZLE RESULT</b> 🌟\n\n"
        f"{status_text}\n\n"
        "<i>Ready for another round?</i>"
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
        "✊ <b>Rock-Paper-Scissors (vs Bot)</b>\n\n"
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
        res_text = "🎉 <b>YOU WON!</b> 🏆"
    elif outcome == "lose":
        res_text = "🤖 <b>BOT WON!</b>"
    else:
        res_text = "🤝 <b>IT'S A DRAW!</b>"

    again_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Play Again", callback_data="cb_game:solo_rps")],
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )
    result_text = (
        f"✊ <b>ROCK-PAPER-SCISSORS SHOWDOWN!</b> (#{round_id})\n\n"
        f"• <b>Your Move:</b> {u_emoji}\n"
        f"• <b>Bot's Move:</b> {b_emoji}\n\n"
        f"<b>Result:</b> {res_text}"
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
        res = "🎉 <b>YOU ROLLED HIGHER AND WON!</b> 🏆"
    elif outcome == "lose":
        res = "🤖 <b>BOT ROLLED HIGHER!</b>"
    else:
        res = "🤝 <b>EQUAL ROLLS — IT'S A DRAW!</b>"

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
        f"🎲 <b>LUCKY DICE SHOWDOWN!</b> (#{roll_id})\n\n"
        f"• <b>You Rolled:</b> 🎲 <b>{u_roll}</b>\n"
        f"• <b>Bot Rolled:</b> 🎲 <b>{b_roll}</b>\n\n"
        f"<b>Result:</b> {res}"
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
    my_sc, p_sc, ties = duel_games.get_session_score(session["id"], tg_id, partner_id)
    await callback.answer("⚡ Math duel started!")

    duel_text = (
        "⚡ <b>Math Speed Duel</b>\n\n"
        "Solve as fast as you can:\n\n"
        f"👉 <b>{puzzle.question}</b>\n\n"
        f"🏆 <b>Score:</b> You <b>{my_sc}</b> — <b>{p_sc}</b> Partner\n"
        "Tap the correct answer:"
    )
    partner_text = (
        "⚡ <b>Math Speed Duel</b>\n\n"
        "Solve as fast as you can:\n\n"
        f"👉 <b>{puzzle.question}</b>\n\n"
        f"🏆 <b>Score:</b> You <b>{p_sc}</b> — <b>{my_sc}</b> Partner\n"
        "Tap the correct answer:"
    )
    duel_kb = get_math_puzzle_keyboard(puzzle.options, prefix="cb_duel_math")

    try:
        await callback.message.edit_text(duel_text, reply_markup=duel_kb)
    except Exception:
        await callback.message.answer(duel_text, reply_markup=duel_kb)

    try:
        await callback.bot.send_message(chat_id=partner_id, text=partner_text, reply_markup=duel_kb)
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
        await callback.answer("Chat session ended.")
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    status, winner_id, correct_ans, user_att, elapsed, (my_sc, p_sc, ties) = await duel_games.submit_math_answer(
        session["id"], tg_id, chosen_ans
    )

    if status == "winner":
        await callback.answer()
        duel_math_kb = get_duel_rematch_keyboard("math")

        my_win_card = (
            "⚡ <b>MATH SPEED DUEL SHOWDOWN!</b> 🏆\n\n"
            f"🎯 <b>Correct Answer:</b> <b>{correct_ans}</b>\n"
            "🥇 <b>Winner:</b> <b>YOU SOLVED IT FIRST!</b> 🏆\n\n"
            f"📊 <b>Performance Stats:</b>\n"
            f"• <b>Time Taken:</b> <b>{elapsed}s</b>\n"
            f"• <b>Attempts:</b> <b>{user_att}</b>\n\n"
            f"🏆 <b>Total Score:</b> You <b>{my_sc}</b> — <b>{p_sc}</b> Partner (Ties: {ties})\n\n"
            "<i>Tap below to play again:</i>"
        )
        partner_win_card = (
            "⚡ <b>MATH SPEED DUEL SHOWDOWN!</b> 🎯\n\n"
            f"🎯 <b>Correct Answer:</b> <b>{correct_ans}</b>\n"
            "🥇 <b>Winner:</b> <b>PARTNER SOLVED IT FIRST!</b> 🏆\n\n"
            f"📊 <b>Performance Stats:</b>\n"
            f"• <b>Time Taken:</b> <b>{elapsed}s</b>\n"
            f"• <b>Winner Attempts:</b> <b>{user_att}</b>\n\n"
            f"🏆 <b>Total Score:</b> You <b>{p_sc}</b> — <b>{my_sc}</b> Partner (Ties: {ties})\n\n"
            "<i>Tap below to play again:</i>"
        )
        try:
            await callback.message.edit_text(my_win_card, reply_markup=duel_math_kb)
        except Exception:
            await callback.message.answer(my_win_card, reply_markup=duel_math_kb)

        try:
            await callback.bot.send_message(chat_id=partner_id, text=partner_win_card, reply_markup=duel_math_kb)
        except Exception as e:
            logger.warning("Failed to notify math duel partner %s: %s", partner_id, e)

    elif status == "wrong":
        await callback.answer(f"❌ {chosen_ans} is incorrect! Try another option.")
        try:
            await callback.bot.send_message(
                chat_id=partner_id,
                text=f"⚠️ <i>Partner guessed incorrectly ({chosen_ans})! Quick, the math prize is still open!</i>",
            )
        except Exception:
            pass
    elif status == "already_finished":
        await callback.answer(f"Round finished! Answer was {correct_ans}.")
    else:
        await callback.answer("Game expired.")


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
    my_sc, p_sc, ties = duel_games.get_session_score(session["id"], tg_id, partner_id)
    await callback.answer("✊ RPS duel started!")

    rps_duel_text = (
        "✊ <b>Rock-Paper-Scissors Duel</b>\n\n"
        "Choose your secret move below.\n"
        "<i>Moves are revealed once both players pick!</i>\n\n"
        f"🏆 <b>Score:</b> You <b>{my_sc}</b> — <b>{p_sc}</b> Partner\n\n"
        "👇 Tap your move:"
    )
    partner_rps_text = (
        "✊ <b>Rock-Paper-Scissors Duel</b>\n\n"
        "Choose your secret move below.\n"
        "<i>Moves are revealed once both players pick!</i>\n\n"
        f"🏆 <b>Score:</b> You <b>{p_sc}</b> — <b>{my_sc}</b> Partner\n\n"
        "👇 Tap your move:"
    )
    rps_kb = get_rps_keyboard(prefix="cb_duel_rps")

    try:
        await callback.message.edit_text(rps_duel_text, reply_markup=rps_kb)
    except Exception:
        await callback.message.answer(rps_duel_text, reply_markup=rps_kb)

    try:
        await callback.bot.send_message(chat_id=partner_id, text=partner_rps_text, reply_markup=rps_kb)
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
        await callback.answer("Chat session ended.")
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    is_finished, moves, winner_id, (my_sc, p_sc, ties) = await duel_games.submit_rps_move(
        session["id"], tg_id, selected_move
    )

    if not is_finished:
        move_emoji = RPS_EMOJIS.get(selected_move, selected_move)
        await callback.answer(f"Locked in {move_emoji}!")
        try:
            await callback.message.edit_text(
                f"✊ <b>Move Locked:</b> {move_emoji}\n\n"
                "⏳ <i>Waiting for partner to choose...</i>\n\n"
                "<i>Moves will be revealed together!</i>"
            )
        except Exception:
            pass

        try:
            nudge_kb = get_rps_keyboard(prefix="cb_duel_rps")
            await callback.bot.send_message(
                chat_id=partner_id,
                text=(
                    "⚡ <b>Partner has locked in their move!</b>\n\n"
                    "👉 Tap your move below to reveal showdown:"
                ),
                reply_markup=nudge_kb,
            )
        except Exception:
            pass
        return

    # Both players moved: reveal showdown!
    my_move = moves.get(tg_id, "rock")
    partner_move = moves.get(partner_id, "rock")
    my_m_name = RPS_EMOJIS.get(my_move, "❓")
    p_m_name = RPS_EMOJIS.get(partner_move, "❓")

    def get_rps_clash_text(m1: str, m2: str) -> str:
        if m1 == m2:
            return "🤝 Both picked the same move!"
        pair = {m1, m2}
        if pair == {"rock", "scissors"}:
            return "💥 🪨 Rock smashes ✂️ Scissors!"
        if pair == {"paper", "rock"}:
            return "💥 📄 Paper covers 🪨 Rock!"
        if pair == {"scissors", "paper"}:
            return "💥 ✂️ Scissors cut 📄 Paper!"
        return "⚔️ Showdown complete!"

    clash_desc = get_rps_clash_text(my_move, partner_move)

    if winner_id is None:
        outcome_me = "🤝 <b>IT'S A DRAW!</b>"
        outcome_partner = outcome_me
    elif winner_id == tg_id:
        outcome_me = "🏆 <b>YOU WON THIS ROUND!</b> 🥇"
        outcome_partner = "🤖 <b>PARTNER WON THIS ROUND!</b>"
    else:
        outcome_me = "🤖 <b>PARTNER WON THIS ROUND!</b>"
        outcome_partner = "🏆 <b>YOU WON THIS ROUND!</b> 🥇"

    duel_rps_kb = get_duel_rematch_keyboard("rps")

    my_card = (
        "✊ <b>ROCK-PAPER-SCISSORS SHOWDOWN!</b> ⚔️\n\n"
        f"• <b>Your Move:</b> {my_m_name}\n"
        f"• <b>Partner's Move:</b> {p_m_name}\n\n"
        f"<b>Clash:</b> {clash_desc}\n"
        f"<b>Result:</b> {outcome_me}\n\n"
        f"🏆 <b>Total Score:</b> You <b>{my_sc}</b> — <b>{p_sc}</b> Partner (Ties: {ties})\n\n"
        "<i>Tap below for a rematch:</i>"
    )
    partner_card = (
        "✊ <b>ROCK-PAPER-SCISSORS SHOWDOWN!</b> ⚔️\n\n"
        f"• <b>Your Move:</b> {p_m_name}\n"
        f"• <b>Partner's Move:</b> {my_m_name}\n\n"
        f"<b>Clash:</b> {clash_desc}\n"
        f"<b>Result:</b> {outcome_partner}\n\n"
        f"🏆 <b>Total Score:</b> You <b>{p_sc}</b> — <b>{my_sc}</b> Partner (Ties: {ties})\n\n"
        "<i>Tap below for a rematch:</i>"
    )

    await callback.answer()
    try:
        await callback.message.edit_text(my_card, reply_markup=duel_rps_kb)
    except Exception:
        await callback.message.answer(my_card, reply_markup=duel_rps_kb)

    try:
        await callback.bot.send_message(chat_id=partner_id, text=partner_card, reply_markup=duel_rps_kb)
    except Exception as e:
        logger.warning("Failed to send RPS result to %s: %s", partner_id, e)


@router.callback_query(F.data == "cb_game:duel_guess")
async def handle_duel_guess_start(callback: CallbackQuery) -> None:
    """Launches a turn-based Number Guess Duel between both partners, or solo if alone."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    session = await database.get_active_session(tg_id)
    if not session:
        await handle_solo_guess_start(callback)
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    await duel_games.start_guess_duel(session["id"], session["user1_id"], session["user2_id"], tg_id)
    my_sc, p_sc, ties = duel_games.get_session_score(session["id"], tg_id, partner_id)
    await callback.answer()

    starter_text = (
        "🎯 <b>NUMBER GUESS DUEL (0–9)</b>\n\n"
        "A secret digit between <b>0 and 9</b> has been chosen!\n"
        "👑 <b>Win Condition:</b> Guess it with the <b>fewest attempts</b>.\n"
        "⚡ <b>Rules:</b> 1-by-1 turn! If you miss, turn passes to your partner.\n\n"
        "👉 <b>YOUR TURN! Attempt #1:</b> Choose a digit below:\n"
        f"🏆 <b>Score:</b> You <b>{my_sc}</b> — <b>{p_sc}</b> Partner"
    )
    partner_text = (
        "🎯 <b>NUMBER GUESS DUEL (0–9)</b>\n\n"
        "A secret digit between <b>0 and 9</b> has been chosen!\n"
        "👑 <b>Win Condition:</b> Guess it with the <b>fewest attempts</b>.\n"
        "⚡ <b>Rules:</b> 1-by-1 turn! If partner misses, turn passes to you.\n\n"
        "⏳ <b>Partner's Turn:</b> <i>Waiting for partner to make attempt #1...</i>\n"
        f"🏆 <b>Score:</b> You <b>{p_sc}</b> — <b>{my_sc}</b> Partner"
    )
    guess_kb = get_number_guess_keyboard(prefix="cb_duel_guess")
    wait_kb = get_guess_waiting_keyboard()

    try:
        starter_msg = await callback.message.edit_text(starter_text, reply_markup=guess_kb)
    except Exception:
        starter_msg = await callback.message.answer(starter_text, reply_markup=guess_kb)

    if starter_msg:
        await duel_games.register_guess_duel_msg(session["id"], tg_id, starter_msg.message_id)

    try:
        partner_msg = await callback.bot.send_message(chat_id=partner_id, text=partner_text, reply_markup=wait_kb)
        if partner_msg:
            await duel_games.register_guess_duel_msg(session["id"], partner_id, partner_msg.message_id)
    except Exception as e:
        logger.warning("Failed to send guess duel to partner %s: %s", partner_id, e)


@router.callback_query(F.data == "cb_duel_guess_wait")
async def handle_duel_guess_wait(callback: CallbackQuery) -> None:
    """Handles click on waiting button while partner is guessing."""
    await callback.answer("⏳ It's your partner's turn! Please wait for them to guess.")


@router.callback_query(F.data.startswith("cb_duel_guess:"))
async def handle_duel_guess_check(callback: CallbackQuery) -> None:
    """Checks a guess in the turn-based 1-by-1 Number Guess Duel with bold styling."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    guess_digit = int(callback.data.split(":")[1])

    session = await database.get_active_session(tg_id)
    if not session:
        await callback.answer("Chat session ended.")
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    status, target, winner_id, my_att, p_att, elapsed, (my_sc, p_sc, ties), last_guess_info, p_msg_id = (
        await duel_games.submit_guess_duel(session["id"], tg_id, guess_digit)
    )

    if status == "not_your_turn":
        await callback.answer("⏳ It's your partner's turn! Please wait.")
        return

    if status == "already_finished":
        await callback.answer(f"Round already finished! Number was {target}.")
        return

    if status in ("higher", "lower"):
        await callback.answer()

        direction = "HIGHER ⬆️" if status == "higher" else "LOWER ⬇️"
        wait_kb = get_guess_waiting_keyboard()
        my_wait_text = (
            "🎯 <b>NUMBER GUESS DUEL (0–9)</b>\n\n"
            f"❌ <b>Your Guess:</b> <b>{guess_digit}</b> (Secret number is <b>{direction}</b>)\n"
            f"• Your attempts: <b>{my_att}</b> | Partner attempts: <b>{p_att}</b>\n\n"
            "⏳ <b>Partner's Turn:</b> <i>Turn passed to partner! Waiting for their guess...</i>\n"
            f"🏆 <b>Score:</b> You <b>{my_sc}</b> — <b>{p_sc}</b> Partner"
        )
        try:
            await callback.message.edit_text(my_wait_text, reply_markup=wait_kb)
        except Exception:
            pass

        # Partner's turn now! Update partner's card with keypad
        partner_turn_text = (
            "🎯 <b>NUMBER GUESS DUEL (0–9)</b>\n\n"
            f"👀 <b>Partner guessed:</b> <b>{guess_digit}</b> (Secret number is <b>{direction}</b>)\n"
            f"• Partner attempts: <b>{my_att}</b> | Your attempts: <b>{p_att}</b>\n\n"
            f"👉 <b>YOUR TURN! Attempt #{p_att + 1}:</b> Choose a digit below:\n"
            f"🏆 <b>Score:</b> You <b>{p_sc}</b> — <b>{my_sc}</b> Partner"
        )
        guess_kb = get_number_guess_keyboard(prefix="cb_duel_guess")
        if p_msg_id:
            try:
                await callback.bot.edit_message_text(
                    chat_id=partner_id,
                    message_id=p_msg_id,
                    text=partner_turn_text,
                    reply_markup=guess_kb,
                )
            except Exception:
                p_sent = await callback.bot.send_message(
                    chat_id=partner_id, text=partner_turn_text, reply_markup=guess_kb
                )
                await duel_games.register_guess_duel_msg(session["id"], partner_id, p_sent.message_id)
        else:
            p_sent = await callback.bot.send_message(
                chat_id=partner_id, text=partner_turn_text, reply_markup=guess_kb
            )
            await duel_games.register_guess_duel_msg(session["id"], partner_id, p_sent.message_id)

    elif status == "correct":
        await callback.answer()
        duel_guess_kb = get_duel_rematch_keyboard("guess")

        my_win_msg = (
            "🎉 <b>BULLSEYE! YOU WON THE DUEL!</b> 🏆\n\n"
            f"🎯 <b>Secret Number:</b> <b>{target}</b>\n"
            f"🥇 <b>Winner:</b> <b>YOU (Cracked it with {my_att} attempt(s)!)</b>\n\n"
            f"📊 <b>Attempts Breakdown:</b>\n"
            f"• <b>You:</b> <b>{my_att} attempt(s)</b> 🌟\n"
            f"• <b>Partner:</b> <b>{p_att} attempt(s)</b>\n\n"
            f"⏱️ <b>Time:</b> <b>{elapsed}s</b>\n"
            f"🏆 <b>Total Score:</b> You <b>{my_sc}</b> — <b>{p_sc}</b> Partner (Ties: {ties})\n\n"
            "<i>Tap below for a rematch or choose another game:</i>"
        )
        their_win_msg = (
            "🏁 <b>NUMBER GUESS DUEL COMPLETE!</b> 🎯\n\n"
            f"🎯 <b>Secret Number:</b> <b>{target}</b>\n"
            f"🥇 <b>Winner:</b> <b>Partner (Cracked it with {my_att} attempt(s)!)</b> 🏆\n\n"
            f"📊 <b>Attempts Breakdown:</b>\n"
            f"• <b>Partner:</b> <b>{my_att} attempt(s)</b> 🏆\n"
            f"• <b>You:</b> <b>{p_att} attempt(s)</b>\n\n"
            f"⏱️ <b>Time:</b> <b>{elapsed}s</b>\n"
            f"🏆 <b>Total Score:</b> You <b>{p_sc}</b> — <b>{my_sc}</b> Partner (Ties: {ties})\n\n"
            "<i>Tap below for a rematch or choose another game:</i>"
        )
        try:
            await callback.message.edit_text(my_win_msg, reply_markup=duel_guess_kb)
        except Exception:
            await callback.message.answer(my_win_msg, reply_markup=duel_guess_kb)

        if p_msg_id:
            try:
                await callback.bot.edit_message_text(
                    chat_id=partner_id,
                    message_id=p_msg_id,
                    text=their_win_msg,
                    reply_markup=duel_guess_kb,
                )
            except Exception:
                await callback.bot.send_message(chat_id=partner_id, text=their_win_msg, reply_markup=duel_guess_kb)
        else:
            await callback.bot.send_message(chat_id=partner_id, text=their_win_msg, reply_markup=duel_guess_kb)

    else:
        await callback.answer("Game session expired.")


@router.callback_query(F.data == "cb_game:duel_dice")
async def handle_duel_dice(callback: CallbackQuery) -> None:
    """Starter rolls lucky dice and challenges partner to beat it, or solo if alone."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    session = await database.get_active_session(tg_id)
    if not session:
        await handle_solo_dice(callback)
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    starter_roll = await duel_games.start_dice_duel(session["id"], session["user1_id"], session["user2_id"], tg_id)
    my_sc, p_sc, ties = duel_games.get_session_score(session["id"], tg_id, partner_id)

    await callback.answer()

    starter_text = (
        "🎲 <b>LUCKY DICE DUEL</b>\n\n"
        f"• <b>Your Roll:</b> 🎲 <b>{starter_roll}</b>\n"
        "⏳ <i>Waiting for partner to roll challenge dice...</i>\n\n"
        f"🏆 <b>Score:</b> You <b>{my_sc}</b> — <b>{p_sc}</b> Partner"
    )
    partner_challenge_text = (
        "🎲 <b>LUCKY DICE DUEL CHALLENGE!</b>\n\n"
        f"• <b>Partner rolled:</b> 🎲 <b>{starter_roll}</b>\n"
        "⚡ <i>Can you roll higher and win?</i>\n\n"
        f"🏆 <b>Score:</b> You <b>{p_sc}</b> — <b>{my_sc}</b> Partner\n\n"
        "👇 Tap below to roll your dice:"
    )
    challenge_kb = get_dice_challenge_keyboard()

    try:
        await callback.message.edit_text(starter_text)
    except Exception:
        await callback.message.answer(starter_text)

    try:
        await callback.bot.send_message(
            chat_id=partner_id, text=partner_challenge_text, reply_markup=challenge_kb
        )
    except Exception as e:
        logger.warning("Failed to send dice challenge to %s: %s", partner_id, e)


@router.callback_query(F.data == "cb_game:duel_dice_roll")
async def handle_duel_dice_roll(callback: CallbackQuery) -> None:
    """Partner rolls challenge dice to complete the Dice Duel showdown."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    session = await database.get_active_session(tg_id)
    if not session:
        await callback.answer("Chat session ended.")
        return

    partner_id = session["user2_id"] if session["user1_id"] == tg_id else session["user1_id"]
    status, starter_roll, challenger_roll, winner_id, (my_sc, p_sc, ties) = await duel_games.submit_dice_roll(
        session["id"], tg_id
    )

    if status == "same_player":
        await callback.answer("⏳ Waiting for partner to roll challenge dice.")
        return
    elif status in ("no_game", "already_finished"):
        await callback.answer("Duel round already completed.")
        return

    await callback.answer()
    duel_rematch_kb = get_duel_rematch_keyboard("dice")

    if winner_id is None:
        clash_outcome_me = "🤝 <b>IT'S A DRAW!</b> Both rolled the same number!"
        clash_outcome_partner = clash_outcome_me
    elif winner_id == tg_id:
        clash_outcome_me = f"🏆 <b>YOU WON!</b> (🎲 {challenger_roll} beats 🎲 {starter_roll}) 🥇"
        clash_outcome_partner = f"🤖 <b>PARTNER WON!</b> (🎲 {challenger_roll} beats 🎲 {starter_roll})"
    else:
        clash_outcome_me = f"🤖 <b>PARTNER WON!</b> (🎲 {starter_roll} beats 🎲 {challenger_roll})"
        clash_outcome_partner = f"🏆 <b>YOU WON!</b> (🎲 {starter_roll} beats 🎲 {challenger_roll}) 🥇"

    my_card = (
        "🎲 <b>LUCKY DICE DUEL SHOWDOWN!</b> ⚔️\n\n"
        f"• <b>Your Roll:</b> 🎲 <b>{challenger_roll}</b>\n"
        f"• <b>Partner's Roll:</b> 🎲 <b>{starter_roll}</b>\n\n"
        f"<b>Result:</b> {clash_outcome_me}\n\n"
        f"🏆 <b>Total Score:</b> You <b>{my_sc}</b> — <b>{p_sc}</b> Partner (Ties: {ties})\n\n"
        "<i>Tap below to roll again:</i>"
    )
    partner_card = (
        "🎲 <b>LUCKY DICE DUEL SHOWDOWN!</b> ⚔️\n\n"
        f"• <b>Your Roll:</b> 🎲 <b>{starter_roll}</b>\n"
        f"• <b>Partner's Roll:</b> 🎲 <b>{challenger_roll}</b>\n\n"
        f"<b>Result:</b> {clash_outcome_partner}\n\n"
        f"🏆 <b>Total Score:</b> You <b>{p_sc}</b> — <b>{my_sc}</b> Partner (Ties: {ties})\n\n"
        "<i>Tap below to roll again:</i>"
    )

    try:
        await callback.message.edit_text(my_card, reply_markup=duel_rematch_kb)
    except Exception:
        await callback.message.answer(my_card, reply_markup=duel_rematch_kb)

    try:
        await callback.bot.send_message(chat_id=partner_id, text=partner_card, reply_markup=duel_rematch_kb)
    except Exception as e:
        logger.warning("Failed to notify dice duel starter %s: %s", partner_id, e)


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
        f"👤 <b>Gender Preference</b>\n\n"
        f"Current selection: <b>{current_gender}</b>\n\n"
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
        await callback.answer("Invalid selection.")
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
                f"✅ <b>Gender set to {gender_badge}!</b>\n\n"
                "🎂 <b>Now, please select your age range:</b>\n"
                "This helps your partner know who they are chatting with.",
                reply_markup=get_age_keyboard(),
            )
        except Exception as e:
            logger.warning("Failed to edit callback message: %s", e)
    else:
        try:
            await callback.message.edit_text(
                f"✅ <b>Gender set to {gender_badge}!</b>\n\n"
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
        f"🎂 <b>Age Range Selection</b>\n\n"
        f"Current selection: <b>{current_age}</b>\n\n"
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
        await callback.answer("Invalid selection.")
        return

    await database.update_user_age_range(tg_id, selected_age)
    age_badge = format_age_display(selected_age)
    await callback.answer(f"Age range set to {age_badge}!")

    try:
        await callback.message.edit_text(
            f"✅ <b>Age range set to {age_badge}!</b>\n\n"
            "Your anonymous profile is complete.\n\n"
            "👉 Tap <b>🔍 Find Stranger</b> below to start chatting!",
            reply_markup=get_profile_keyboard(),
        )
    except Exception as e:
        logger.warning("Failed to edit callback message: %s", e)


@router.message(Command("language"))
@router.message(Command("lang"))
async def handle_language_command(message: Message) -> None:
    """Allows user to view or update their preferred conversation language."""
    from_user = message.from_user
    if not from_user:
        return

    db_user, is_banned = await get_or_register_user(from_user)
    if is_banned:
        await message.answer("⛔ Your account is suspended.")
        return

    curr_lang = db_user.get("language", "any")
    curr_display = format_language_display(curr_lang)
    await message.answer(
        "🌐 <b>Preferred Chat Language</b>\n\n"
        f"Current: <b>{curr_display}</b>\n\n"
        "Choose your preferred conversation language.\n"
        "<i>(Optional: You'll be prioritized with matching speakers, with automatic fallback so matchmaking never stalls!)</i>",
        reply_markup=get_language_keyboard(curr_lang),
    )


@router.callback_query(F.data == "cb_open_language")
async def handle_open_language_callback(callback: CallbackQuery) -> None:
    """Opens the language selection keyboard from profile or inline buttons."""
    await callback.answer()
    if not callback.from_user or not callback.message:
        return
    user = await database.get_user(callback.from_user.id) or {}
    curr_lang = user.get("language", "any")
    curr_display = format_language_display(curr_lang)
    text = (
        "🌐 <b>Preferred Chat Language</b>\n\n"
        f"Current: <b>{curr_display}</b>\n\n"
        "Choose your preferred conversation language below:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_language_keyboard(curr_lang))
    except Exception:
        await callback.message.answer(text, reply_markup=get_language_keyboard(curr_lang))


@router.callback_query(F.data.startswith("cb_lang:"))
async def handle_set_language_callback(callback: CallbackQuery) -> None:
    """Processes language selection callbacks from inline buttons."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    lang_code = callback.data.split(":")[1]
    if lang_code not in LANGUAGE_NAMES:
        await callback.answer("Invalid language selection.")
        return

    await database.update_user_language(tg_id, lang_code)
    lang_display = format_language_display(lang_code)
    await callback.answer(f"Language set to {lang_display}!")

    try:
        await callback.message.edit_text(
            f"✅ <b>Language set to {lang_display}!</b>\n\n"
            "Matchmaking will prioritize partners who speak your language with seamless fallback.\n\n"
            "👉 Tap <b>🔍 Find Stranger</b> below to start chatting!",
            reply_markup=get_profile_keyboard(),
        )
    except Exception as e:
        logger.warning("Failed to edit callback message: %s", e)


@router.message(Command("spoiler"))
@router.message(Command("blur"))
async def handle_spoiler_command(message: Message) -> None:
    """Toggles media blur / spoiler protection for the user."""
    from_user = message.from_user
    if not from_user:
        return

    db_user, is_banned = await get_or_register_user(from_user)
    if is_banned:
        await message.answer("⛔ Your account is suspended.")
        return

    is_enabled = bool(db_user.get("media_spoiler", 0))
    status_text = "Enabled 👁️" if is_enabled else "Disabled 🚫"
    await message.answer(
        "👁️ <b>Media Blur Protection</b>\n\n"
        f"Current Status: <b>{status_text}</b>\n\n"
        "When enabled, all photos, videos, and animations sent and received are blurred "
        "with Telegram's tap-to-reveal spoiler effect to prevent accidental exposure.",
        reply_markup=get_spoiler_toggle_keyboard(is_enabled),
    )


@router.callback_query(F.data == "cb_open_spoiler")
async def handle_open_spoiler_callback(callback: CallbackQuery) -> None:
    """Opens media blur settings keyboard."""
    await callback.answer()
    if not callback.from_user or not callback.message:
        return
    user = await database.get_user(callback.from_user.id) or {}
    is_enabled = bool(user.get("media_spoiler", 0))
    status_text = "Enabled 👁️" if is_enabled else "Disabled 🚫"
    text = (
        "👁️ <b>Media Blur Protection</b>\n\n"
        f"Current Status: <b>{status_text}</b>\n\n"
        "When enabled, photos, videos, and animations are blurred until tapped to reveal."
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_spoiler_toggle_keyboard(is_enabled))
    except Exception:
        await callback.message.answer(text, reply_markup=get_spoiler_toggle_keyboard(is_enabled))


@router.callback_query(F.data == "cb_toggle_spoiler")
async def handle_toggle_spoiler_callback(callback: CallbackQuery) -> None:
    """Toggles user's media spoiler blur preference."""
    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id
    new_state = await database.toggle_user_media_spoiler(tg_id)
    alert_msg = "Media blur ENABLED 👁️ (Media will be blurred)" if new_state else "Media blur DISABLED"
    await callback.answer(alert_msg)

    status_text = "Enabled 👁️" if new_state else "Disabled 🚫"
    text = (
        "👁️ <b>Media Blur Protection</b>\n\n"
        f"Current Status: <b>{status_text}</b>\n\n"
        f"✅ <i>{alert_msg}</i>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_spoiler_toggle_keyboard(new_state))
    except Exception:
        await callback.message.answer(text, reply_markup=get_spoiler_toggle_keyboard(new_state))


@router.callback_query(F.data == "cb_start_find")
async def handle_start_find_callback(callback: CallbackQuery) -> None:
    """Handles the 'Find a Stranger' button from the welcome message."""
    if not callback.from_user or not callback.message:
        return

    await callback.answer()
    await execute_find_flow(callback.message, callback.from_user)


@router.message(Command("find"))
@router.message(F.text.in_({"🔍 Find Stranger", "🔍 Find a Stranger", "🔍 Start Chatting", "🔍 Find Next"}))
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
            "• Tap <b>⏭️ Next</b> to skip\n"
            "• Tap <b>⏹️ End</b> to leave",
            reply_markup=get_chat_reply_keyboard(),
        )
        return

    gender = db_user.get("gender", "unknown")
    if gender not in ("male", "female", "prefer_not_to_say"):
        await message.answer(
            "⚠️ <b>Gender Selection Required</b>\n\n"
            "Please select your gender preference before searching:",
            reply_markup=get_gender_keyboard(),
        )
        return

    age_range = db_user.get("age_range", "unknown")
    if age_range not in ("below_18", "18-25", "25-35", "40+"):
        await message.answer(
            "🎂 <b>Age Range Required</b>\n\n"
            "Please select your age bracket before searching:",
            reply_markup=get_age_keyboard(),
        )
        return

    # Check if already waiting in queue
    if await match_queue.is_in_queue(tg_id):
        await message.answer(
            "⏳ <b>Already Searching!</b>\n\n"
            "You are currently in line waiting for a match. Please wait a moment or tap Cancel below:",
            reply_markup=get_search_keyboard(),
        )
        return

    # Check premium status
    is_premium = await database.is_premium_active(tg_id)
    user_lang = db_user.get("language", "any")

    # Attempt match or enqueue
    partner_id, matched = await match_queue.find_match_or_enqueue(
        tg_id=tg_id,
        gender=gender,
        is_premium=is_premium,
        age_range=age_range,
        language=user_lang,
    )

    if matched and partner_id:
        partner_db = await database.get_user(partner_id) or {}
        partner_lang = partner_db.get("language", "any")
        notice_for_me = get_match_found_text(
            partner_gender=partner_db.get("gender"),
            partner_age=partner_db.get("age_range"),
            partner_lang=partner_lang,
        )
        notice_for_partner = get_match_found_text(
            partner_gender=gender,
            partner_age=age_range,
            partner_lang=user_lang,
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
            f"🔍 <b>Searching for a partner...</b>{vip_tag}\n\n"
            f"Looking for an opposite-gender stranger (or any waiting stranger).{tip}\n\n"
            "Please wait, or tap below to cancel search:",
            reply_markup=get_search_keyboard(),
        )


async def execute_next_partner_flow(
    event: Message | CallbackQuery,
    from_user: Any,
) -> None:
    """Closes current chat and seamlessly matches/enqueues user with a new stranger."""
    tg_id = from_user.id
    bot = event.bot

    closed_session = await database.close_session_for_user(tg_id)
    if closed_session:
        duel_games.reset_session(closed_session["id"])
        elapsed = get_session_elapsed_seconds(closed_session)
        dur_str = format_chat_duration(elapsed)
        partner_id = (
            closed_session["user2_id"]
            if closed_session["user1_id"] == tg_id
            else closed_session["user1_id"]
        )
        try:
            await bot.send_message(
                chat_id=partner_id,
                text=get_partner_ended_text(dur_str),
                reply_markup=get_partner_disconnected_keyboard(),
            )
        except Exception as e:
            logger.warning("Failed to notify disconnected partner %s: %s", partner_id, e)

    await match_queue.remove_user(tg_id)

    db_user, is_banned = await get_or_register_user(from_user)
    target_msg = event if isinstance(event, Message) else event.message

    if is_banned:
        if target_msg:
            await target_msg.answer("⛔ Your account is suspended.")
        return

    gender = db_user.get("gender", "unknown")
    if gender not in ("male", "female", "prefer_not_to_say"):
        if target_msg:
            await target_msg.answer(
                "⚠️ Please select your gender first using /gender to find a match.",
                reply_markup=get_gender_keyboard(),
            )
        return

    age_range = db_user.get("age_range", "unknown")
    if age_range not in ("below_18", "18-25", "25-35", "40+"):
        if target_msg:
            await target_msg.answer(
                "🎂 Please select your age bracket first using /age to find a match.",
                reply_markup=get_age_keyboard(),
            )
        return

    is_premium = await database.is_premium_active(tg_id)
    user_lang = db_user.get("language", "any")
    new_partner_id, matched = await match_queue.find_match_or_enqueue(
        tg_id=tg_id,
        gender=gender,
        is_premium=is_premium,
        age_range=age_range,
        language=user_lang,
    )

    if matched and new_partner_id:
        partner_db = await database.get_user(new_partner_id) or {}
        partner_lang = partner_db.get("language", "any")
        notice_for_me = get_match_found_text(
            partner_gender=partner_db.get("gender"),
            partner_age=partner_db.get("age_range"),
            partner_lang=partner_lang,
        )
        notice_for_partner = get_match_found_text(
            partner_gender=gender,
            partner_age=age_range,
            partner_lang=user_lang,
        )
        if target_msg:
            await target_msg.answer(notice_for_me, reply_markup=get_chat_reply_keyboard())
        try:
            await bot.send_message(
                chat_id=new_partner_id,
                text=notice_for_partner,
                reply_markup=get_chat_reply_keyboard(),
            )
        except Exception as e:
            logger.error("Failed to notify new matched partner %s: %s", new_partner_id, e)
    else:
        vip_tag = " ⭐ <i>(VIP Priority)</i>" if is_premium else ""
        if target_msg:
            await target_msg.answer(
                f"🔍 <b>Searching for a new stranger...</b>{vip_tag}\n\n"
                "Looking for a match. Please wait a moment...",
                reply_markup=get_search_keyboard(),
            )


async def execute_stop_flow(
    event: Message | CallbackQuery,
    from_user: Any,
) -> None:
    """Closes current chat and presents disconnect motivational card with timing."""
    tg_id = from_user.id
    bot = event.bot

    closed_session = await database.close_session_for_user(tg_id)
    dur_str: Optional[str] = None
    if closed_session:
        duel_games.reset_session(closed_session["id"])
        elapsed = get_session_elapsed_seconds(closed_session)
        dur_str = format_chat_duration(elapsed)
        partner_id = (
            closed_session["user2_id"]
            if closed_session["user1_id"] == tg_id
            else closed_session["user1_id"]
        )
        try:
            await bot.send_message(
                chat_id=partner_id,
                text=get_partner_ended_text(dur_str),
                reply_markup=get_partner_disconnected_keyboard(),
            )
        except Exception as e:
            logger.warning("Failed to notify partner %s on stop: %s", partner_id, e)

    await match_queue.remove_user(tg_id)

    stop_card = get_user_ended_text(dur_str)
    if isinstance(event, Message):
        await event.answer(stop_card, reply_markup=get_partner_disconnected_keyboard())
    elif event.message:
        try:
            await event.message.edit_text(stop_card, reply_markup=get_partner_disconnected_keyboard())
        except Exception:
            await event.message.answer(stop_card, reply_markup=get_partner_disconnected_keyboard())


@router.message(Command("next"))
@router.message(F.text.in_({"⏭️ Next", "⏭️ Next Stranger"}))
async def handle_next_command(message: Message) -> None:
    """
    Handles /next command:
    - If in active chat:
      - If chat duration is < 10 seconds: does NOT confirm, skips to next partner in one click!
      - If chat duration is >= 10 seconds: asks for confirmation with chat timing.
    - If not in chat, seamlessly initiates find flow.
    """
    from_user = message.from_user
    if not from_user:
        return

    tg_id = from_user.id
    db_user, is_banned = await get_or_register_user(from_user)
    if is_banned:
        await message.answer("⛔ Your account is suspended.")
        return

    session = await database.get_active_session(tg_id)
    if not session:
        # Not in active chat; seamlessly find next stranger
        await execute_find_flow(message, from_user)
        return

    elapsed = get_session_elapsed_seconds(session)
    if elapsed >= 10.0:
        dur_str = format_chat_duration(elapsed)
        confirm_text = (
            "⚠️ <b>Disconnect and find next partner?</b>\n\n"
            f"⏱️ <b>Chat Duration:</b> <b>{dur_str}</b>\n\n"
            "Are you sure you want to end this conversation?"
        )
        confirm_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⏭️ Yes, Next Partner", callback_data="cb_chat_confirm:next"),
                    InlineKeyboardButton(text="💬 Keep Chatting", callback_data="cb_chat_confirm:cancel"),
                ]
            ]
        )
        await message.answer(confirm_text, reply_markup=confirm_kb)
        return

    # If elapsed < 10 seconds, don't confirm: go to next partner in one click!
    await execute_next_partner_flow(message, from_user)


@router.message(Command("stop"))
@router.message(F.text.in_({"⏹️ End", "⏹️ End Chat"}))
async def handle_stop_command(message: Message) -> None:
    """
    Handles /stop command:
    - If in active chat:
      - If chat duration is < 10 seconds: does NOT confirm, ends chat in one click!
      - If chat duration is >= 10 seconds: asks for confirmation with chat timing.
    - If in queue: removes user from queue.
    - If neither: informs user they are not in chat.
    """
    from_user = message.from_user
    if not from_user:
        return

    tg_id = from_user.id
    session = await database.get_active_session(tg_id)
    if session:
        elapsed = get_session_elapsed_seconds(session)
        if elapsed >= 10.0:
            dur_str = format_chat_duration(elapsed)
            confirm_text = (
                "⚠️ <b>End current chat?</b>\n\n"
                f"⏱️ <b>Chat Duration:</b> <b>{dur_str}</b>\n\n"
                "Are you sure you want to disconnect from this stranger?"
            )
            confirm_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="⏹️ Yes, End Chat", callback_data="cb_chat_confirm:stop"),
                        InlineKeyboardButton(text="⏭️ Next Partner", callback_data="cb_chat_confirm:next"),
                    ],
                    [
                        InlineKeyboardButton(text="💬 Keep Chatting", callback_data="cb_chat_confirm:cancel"),
                    ],
                ]
            )
            await message.answer(confirm_text, reply_markup=confirm_kb)
            return

        # If elapsed < 10 seconds, don't confirm: end in one click!
        await execute_stop_flow(message, from_user)
        return

    removed_from_queue = await match_queue.remove_user(tg_id)
    if removed_from_queue:
        await message.answer(
            "❌ <b>Search Cancelled</b>\n\n"
            "You have been removed from the matchmaking queue.\n"
            "Tap <b>🔍 Find Stranger</b> whenever you wish to search again!",
            reply_markup=get_idle_reply_keyboard(),
        )
        return

    await message.answer(
        "You are not in an active chat.\nTap <b>🔍 Find Stranger</b> to begin!",
        reply_markup=get_idle_reply_keyboard(),
    )


@router.callback_query(F.data.startswith("cb_chat_confirm:"))
async def handle_chat_confirmation(callback: CallbackQuery) -> None:
    """Handles confirmation decisions (stop, next, cancel) for ending active chats."""
    action = callback.data.split(":")[1]
    await callback.answer()

    if not callback.from_user or not callback.message:
        return

    tg_id = callback.from_user.id

    if action == "cancel":
        session = await database.get_active_session(tg_id)
        if session:
            try:
                await callback.message.edit_text(
                    "💬 <b>Chat continuing!</b> You are still connected with your stranger."
                )
            except Exception:
                pass
        else:
            try:
                await callback.message.edit_text(
                    "👋 Chat was already ended by partner.",
                    reply_markup=get_partner_disconnected_keyboard(),
                )
            except Exception:
                pass
        return

    if action == "stop":
        await execute_stop_flow(callback, callback.from_user)
        return

    if action == "next":
        try:
            await callback.message.edit_text("⏭️ <b>Ending chat and searching for next stranger...</b>")
        except Exception:
            pass
        await execute_next_partner_flow(callback, callback.from_user)
        return


REPORT_REASONS = {
    "nsfw": "Inappropriate / NSFW Content",
    "abuse": "Harassment / Abusive Language",
    "spam": "Spam / Advertising",
    "creepy": "Creepy / Uncomfortable Behavior",
    "other": "Other Policy Violation",
}


@router.message(Command("report"))
@router.message(F.text.in_({"🚨 Report", "🚨 Report User"}))
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
        "🚨 <b>User Reported & Chat Ended</b>\n\n"
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
                "❌ <b>Search Cancelled</b>\n\n"
                "You have been removed from the matchmaking queue.\n"
                "Tap <b>🔍 Find Stranger</b> below whenever you are ready!",
            )
        except Exception as e:
            logger.warning("Failed to edit cancel search message: %s", e)
    else:
        await callback.answer("You are not currently in the queue.")


@router.message(Command("broadcast"))
async def handle_broadcast_command(message: Message) -> None:
    """
    Admin-only broadcast engine.
    Broadcasts text or replied media to all non-banned users in SQLite
    with strict rate limiting (~28 msgs/sec) and detailed delivery metrics.
    """
    from_user = message.from_user
    if not from_user or from_user.id != config.ADMIN_ID:
        await message.answer("⛔ Access denied. This command is restricted to administrators.")
        return

    command_args = message.text.partition(" ")[2].strip() if message.text else ""
    target_reply = message.reply_to_message

    if not command_args and not target_reply:
        await message.answer(
            "📢 <b>Admin Broadcast Usage:</b>\n\n"
            "• <code>/broadcast &lt;announcement text&gt;</code> — Broadcast text message to all users.\n"
            "• Reply to any media or message with <code>/broadcast</code> to broadcast that media to everyone.\n\n"
            "⚡ <i>Built-in safety: Rate-limited at ~28 msgs/sec with auto retry-after handling.</i>"
        )
        return

    recipients = await database.get_broadcast_user_ids()
    total = len(recipients)

    if total == 0:
        await message.answer("⚠️ No registered active users found to broadcast to.")
        return

    status_msg = await message.answer(
        f"📢 <b>Broadcast Starting...</b>\n\n"
        f"Targeting: <b>{total}</b> non-banned users.\n"
        "<i>Delivering messages smoothly...</i>"
    )

    sent_count = 0
    blocked_count = 0
    failed_count = 0
    start_time = time.time()

    for uid in recipients:
        try:
            if target_reply:
                await target_reply.copy_to(chat_id=uid)
            else:
                await message.bot.send_message(
                    chat_id=uid,
                    text=f"📢 <b>Announcement</b>\n\n{command_args}",
                )
            sent_count += 1
        except TelegramAPIError as e:
            err_str = str(e).lower()
            if "blocked" in err_str or "forbidden" in err_str or "deactivated" in err_str or "chat not found" in err_str:
                blocked_count += 1
            elif "retry after" in err_str:
                try:
                    await asyncio.sleep(2.0)
                    if target_reply:
                        await target_reply.copy_to(chat_id=uid)
                    else:
                        await message.bot.send_message(
                            chat_id=uid,
                            text=f"📢 <b>Announcement</b>\n\n{command_args}",
                        )
                    sent_count += 1
                except Exception:
                    failed_count += 1
            else:
                failed_count += 1
        except Exception:
            failed_count += 1

        # Safe rate limiting: 0.035s sleep = max 28 requests/sec
        await asyncio.sleep(0.035)

    elapsed = time.time() - start_time
    rate = sent_count / max(elapsed, 0.1)

    summary_text = (
        "📢 <b>Broadcast Completed!</b>\n\n"
        f"• <b>Total Targeted:</b> {total}\n"
        f"• <b>Delivered:</b> {sent_count} ✅\n"
        f"• <b>Blocked / Left:</b> {blocked_count} 🚫\n"
        f"• <b>Failures:</b> {failed_count} ❌\n"
        f"• <b>Duration:</b> {elapsed:.1f}s\n"
        f"• <b>Speed:</b> {rate:.1f} msg/sec"
    )

    try:
        await status_msg.edit_text(summary_text)
    except Exception:
        await message.answer(summary_text)


@router.message()
async def handle_anonymous_message(message: Message) -> None:
    """
    Core Anonymous Message Forwarding Engine:
    - Dispatches real-time typing / uploading chat action indicator to partner.
    - If user or partner enabled media blur, applies Telegram tap-to-reveal spoiler.
    - Forwards message to partner using copy_to and updates activity timestamp.
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

    # Real-time chat action indicator ("Stranger is typing / uploading...")
    action = "typing"
    if message.photo:
        action = "upload_photo"
    elif message.video or message.video_note or message.animation:
        action = "upload_video"
    elif message.voice or message.audio:
        action = "record_voice"
    elif message.document:
        action = "upload_document"
    elif message.sticker:
        action = "choose_sticker"

    try:
        await message.bot.send_chat_action(chat_id=partner_id, action=action)
    except Exception:
        pass

    # Check spoiler / blur protection preferences
    sender_db = await database.get_user(tg_id) or {}
    partner_db = await database.get_user(partner_id) or {}
    use_spoiler = bool(sender_db.get("media_spoiler", 0)) or bool(partner_db.get("media_spoiler", 0))
    is_spoilerable = bool(message.photo or message.video or message.animation)

    try:
        if use_spoiler and is_spoilerable:
            try:
                await message.copy_to(chat_id=partner_id, has_spoiler=True)
            except Exception:
                await message.copy_to(chat_id=partner_id)
        else:
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
