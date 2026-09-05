import urllib.parse
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_idle_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent mobile bottom keyboard when user is idle (not in chat)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Find Stranger")],
            [KeyboardButton(text="🎮 Mini Games"), KeyboardButton(text="🎲 Icebreakers")],
            [KeyboardButton(text="👤 Profile"), KeyboardButton(text="🚀 Invite Friends")],
            [KeyboardButton(text="❓ Help")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_chat_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent mobile bottom keyboard when user is actively in a chat."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭️ Next Stranger"), KeyboardButton(text="⏹️ End Chat")],
            [KeyboardButton(text="🎲 Send Icebreaker"), KeyboardButton(text="🎮 Play Game")],
            [KeyboardButton(text="🚨 Report User")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard for gender selection."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👨 Male", callback_data="cb_gender:male"),
                InlineKeyboardButton(text="👩 Female", callback_data="cb_gender:female"),
            ],
            [
                InlineKeyboardButton(
                    text="🎭 Prefer not to say", callback_data="cb_gender:prefer_not_to_say"
                ),
            ],
        ]
    )


def get_age_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard for age range selection."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🐣 Below 18", callback_data="cb_age:below_18"),
                InlineKeyboardButton(text="✨ 18–25", callback_data="cb_age:18-25"),
            ],
            [
                InlineKeyboardButton(text="💼 25–35", callback_data="cb_age:25-35"),
                InlineKeyboardButton(text="🌟 40+", callback_data="cb_age:40+"),
            ],
        ]
    )


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard for updating profile attributes."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Change Gender", callback_data="cb_open_gender"),
                InlineKeyboardButton(text="🎂 Change Age", callback_data="cb_open_age"),
            ],
            [
                InlineKeyboardButton(text="🔍 Find Next Stranger", callback_data="cb_start_find"),
            ],
        ]
    )


def get_partner_disconnected_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard when partner disconnects: Find Next or Change Profile."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Find Next Stranger", callback_data="cb_start_find"),
                InlineKeyboardButton(text="👤 Change Profile", callback_data="cb_open_profile"),
            ]
        ]
    )


def get_search_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard with a Cancel Search button while in queue."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Cancel Search", callback_data="cb_cancel_search")
            ]
        ]
    )


def get_report_reasons_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard with selectable report reason options."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔞 Inappropriate / NSFW", callback_data="cb_report:nsfw"),
            ],
            [
                InlineKeyboardButton(text="🤬 Harassment / Abuse", callback_data="cb_report:abuse"),
            ],
            [
                InlineKeyboardButton(text="📢 Spam / Advertising", callback_data="cb_report:spam"),
            ],
            [
                InlineKeyboardButton(text="👤 Creepy / Uncomfortable", callback_data="cb_report:creepy"),
            ],
            [
                InlineKeyboardButton(text="❌ Other Policy Violation", callback_data="cb_report:other"),
            ],
            [
                InlineKeyboardButton(text="🔙 Cancel", callback_data="cb_report:cancel"),
            ],
        ]
    )


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard for the upgraded welcome greeting."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Find a Stranger", callback_data="cb_start_find"),
                InlineKeyboardButton(text="❓ Help", callback_data="cb_help"),
            ],
            [
                InlineKeyboardButton(text="👤 Set Gender", callback_data="cb_open_gender"),
                InlineKeyboardButton(text="🎂 Set Age", callback_data="cb_open_age"),
            ],
            [
                InlineKeyboardButton(text="🎲 Random Icebreaker", callback_data="cb_get_icebreaker"),
            ],
        ]
    )


def get_invite_keyboard(bot_username: str = "StrangersChattingBot") -> InlineKeyboardMarkup:
    """Returns inline keyboard with a one-tap Telegram share button."""
    share_url = f"https://t.me/{bot_username}"
    share_text = "⚡ Chat with strangers worldwide anonymously! Safe, fast, and 100% free. Join here:"
    encoded_url = urllib.parse.quote(share_url, safe="")
    encoded_text = urllib.parse.quote(share_text, safe="")
    telegram_share_link = f"https://t.me/share/url?url={encoded_url}&text={encoded_text}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 Share with Friends", url=telegram_share_link),
            ]
        ]
    )


def get_games_menu_keyboard(is_in_chat: bool = False) -> InlineKeyboardMarkup:
    """Returns inline keyboard for selecting games based on whether user is in active chat."""
    if is_in_chat:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⚡ Math Speed Duel", callback_data="cb_game:duel_math"),
                    InlineKeyboardButton(text="✊ RPS Duel", callback_data="cb_game:duel_rps"),
                ],
                [
                    InlineKeyboardButton(text="🔢 Number Guess Race", callback_data="cb_game:duel_guess"),
                    InlineKeyboardButton(text="🎲 Dice Roll Duel", callback_data="cb_game:duel_dice"),
                ],
                [
                    InlineKeyboardButton(text="🎲 3D Animated Dice", callback_data="cb_game:animated_dice"),
                    InlineKeyboardButton(text="🕹️ Solo Games Menu", callback_data="cb_game:solo_menu"),
                ],
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔢 Guess Number (0–9)", callback_data="cb_game:solo_guess"),
                InlineKeyboardButton(text="🧮 Math Puzzle", callback_data="cb_game:solo_math"),
            ],
            [
                InlineKeyboardButton(text="✊ Rock-Paper-Scissors", callback_data="cb_game:solo_rps"),
                InlineKeyboardButton(text="🎲 Lucky Dice Roll", callback_data="cb_game:solo_dice"),
            ],
            [
                InlineKeyboardButton(text="🎲 3D Animated Dice", callback_data="cb_game:animated_dice"),
            ],
        ]
    )


def get_number_guess_keyboard(prefix: str = "cb_solo_guess") -> InlineKeyboardMarkup:
    """Returns 0-9 number keypad for guessing games."""
    row1 = [InlineKeyboardButton(text=str(i), callback_data=f"{prefix}:{i}") for i in range(0, 5)]
    row2 = [InlineKeyboardButton(text=str(i), callback_data=f"{prefix}:{i}") for i in range(5, 10)]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row1,
            row2,
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )


def get_math_puzzle_keyboard(options: list[int], prefix: str = "cb_solo_math") -> InlineKeyboardMarkup:
    """Returns 4 multiple-choice buttons in a 2x2 grid for math problems."""
    buttons = [InlineKeyboardButton(text=str(opt), callback_data=f"{prefix}:{opt}") for opt in options]
    rows = [buttons[:2], buttons[2:]]
    rows.append([InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_rps_keyboard(prefix: str = "cb_solo_rps") -> InlineKeyboardMarkup:
    """Returns Rock, Paper, Scissors buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🪨 Rock", callback_data=f"{prefix}:rock"),
                InlineKeyboardButton(text="📄 Paper", callback_data=f"{prefix}:paper"),
                InlineKeyboardButton(text="✂️ Scissors", callback_data=f"{prefix}:scissors"),
            ],
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )
