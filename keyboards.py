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
            [KeyboardButton(text="🎮 Games"), KeyboardButton(text="🎲 Icebreaker")],
            [KeyboardButton(text="👤 Profile"), KeyboardButton(text="❓ Help")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_chat_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent mobile bottom keyboard when user is actively in a chat."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭️ Next"), KeyboardButton(text="⏹️ End")],
            [
                KeyboardButton(text="🎲 Icebreaker"),
                KeyboardButton(text="🎮 Game"),
                KeyboardButton(text="🚨 Report"),
            ],
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
                InlineKeyboardButton(text="👤 Gender", callback_data="cb_open_gender"),
                InlineKeyboardButton(text="🎂 Age", callback_data="cb_open_age"),
            ],
            [
                InlineKeyboardButton(text="🌐 Language", callback_data="cb_open_language"),
                InlineKeyboardButton(text="👁️ Media Blur", callback_data="cb_open_spoiler"),
            ],
            [
                InlineKeyboardButton(text="🔍 Find Stranger", callback_data="cb_start_find"),
            ],
        ]
    )


def get_language_keyboard(current_lang: str = "any") -> InlineKeyboardMarkup:
    """Returns inline keyboard for preferred conversation language selection."""
    curr = (current_lang or "any").lower().strip()
    languages = [
        ("any", "🌐 Any (Global)"),
        ("en", "🇺🇸 English"),
        ("hi", "🇮🇳 Hindi"),
        ("hinglish", "🇮🇳 Hinglish"),
        ("es", "🇪🇸 Spanish"),
        ("ru", "🇷🇺 Russian"),
        ("ar", "🇸🇦 Arabic"),
    ]
    rows = []
    any_label = f"✓ {languages[0][1]}" if curr == "any" else languages[0][1]
    rows.append([InlineKeyboardButton(text=any_label, callback_data="cb_lang:any")])

    lang_buttons = []
    for code, label in languages[1:]:
        text = f"✓ {label}" if curr == code else label
        lang_buttons.append(InlineKeyboardButton(text=text, callback_data=f"cb_lang:{code}"))

    for i in range(0, len(lang_buttons), 2):
        rows.append(lang_buttons[i : i + 2])

    rows.append([InlineKeyboardButton(text="🔙 Back to Profile", callback_data="cb_open_profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_spoiler_toggle_keyboard(is_enabled: bool) -> InlineKeyboardMarkup:
    """Returns inline keyboard to toggle media spoiler / blur protection."""
    status_text = (
        "👁️ Media Blur: ON ✅ (Tap to Disable)"
        if is_enabled
        else "👁️ Media Blur: OFF ❌ (Tap to Enable)"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=status_text, callback_data="cb_toggle_spoiler"),
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Profile", callback_data="cb_open_profile"),
            ],
        ]
    )


def get_partner_disconnected_keyboard() -> InlineKeyboardMarkup:
    """Returns clean inline keyboard when partner disconnects: Find Next or Profile."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Find Next", callback_data="cb_start_find"),
                InlineKeyboardButton(text="👤 Profile", callback_data="cb_open_profile"),
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
    """Returns minimal inline keyboard for welcome greeting."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Start Chatting", callback_data="cb_start_find"),
            ],
            [
                InlineKeyboardButton(text="👤 Set Gender", callback_data="cb_open_gender"),
                InlineKeyboardButton(text="🎂 Set Age", callback_data="cb_open_age"),
            ],
            [
                InlineKeyboardButton(text="🎮 Games", callback_data="cb_game:menu"),
                InlineKeyboardButton(text="❓ Help", callback_data="cb_help"),
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
    """Returns clean inline keyboard for selecting games."""
    if is_in_chat:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⚡ Math Duel", callback_data="cb_game:duel_math"),
                    InlineKeyboardButton(text="✊ RPS Duel", callback_data="cb_game:duel_rps"),
                ],
                [
                    InlineKeyboardButton(text="🔢 Number Guess", callback_data="cb_game:duel_guess"),
                    InlineKeyboardButton(text="🎲 Dice Duel", callback_data="cb_game:duel_dice"),
                ],
                [
                    InlineKeyboardButton(text="🕹️ Solo Games", callback_data="cb_game:solo_menu"),
                ],
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔢 Number Guess", callback_data="cb_game:solo_guess"),
                InlineKeyboardButton(text="🧮 Math Puzzle", callback_data="cb_game:solo_math"),
            ],
            [
                InlineKeyboardButton(text="✊ Rock-Paper-Scissors", callback_data="cb_game:solo_rps"),
                InlineKeyboardButton(text="🎲 Lucky Dice", callback_data="cb_game:solo_dice"),
            ],
            [
                InlineKeyboardButton(text="🎲 3D Physics Dice", callback_data="cb_game:animated_dice"),
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


def get_guess_waiting_keyboard() -> InlineKeyboardMarkup:
    """Returns waiting keyboard when it is partner's turn in number guess duel."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏳ Partner's Turn (Please Wait...)", callback_data="cb_duel_guess_wait")],
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


def get_dice_challenge_keyboard() -> InlineKeyboardMarkup:
    """Returns button for challenging partner to roll their dice."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎲 Roll Challenge Dice!", callback_data="cb_game:duel_dice_roll"),
            ],
            [
                InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu"),
            ],
        ]
    )


def get_duel_rematch_keyboard(game_key: str) -> InlineKeyboardMarkup:
    """Returns rematch and menu buttons for completed partner duels."""
    labels = {
        "math": ("⚡ New Math Duel", "cb_game:duel_math"),
        "rps": ("✊ Play RPS Again", "cb_game:duel_rps"),
        "guess": ("🔢 New Number Race", "cb_game:duel_guess"),
        "dice": ("🎲 Roll Dice Again", "cb_game:duel_dice"),
    }
    btn_text, cb = labels.get(game_key, ("🔄 Play Again", "cb_game:menu"))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data=cb)],
            [InlineKeyboardButton(text="🎮 Games Menu", callback_data="cb_game:menu")],
        ]
    )
