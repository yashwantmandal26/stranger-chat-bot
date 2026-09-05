import urllib.parse
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard for gender selection."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👨 Male", callback_data="cb_gender:male"),
                InlineKeyboardButton(text="👩 Female", callback_data="cb_gender:female"),
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


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """Returns inline keyboard for the upgraded welcome greeting."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Find a Stranger", callback_data="cb_start_find"),
                InlineKeyboardButton(text="❓ Help", callback_data="cb_help"),
            ]
        ]
    )


def get_invite_keyboard(bot_username: str = "StrangersChattingBot") -> InlineKeyboardMarkup:
    """Returns inline keyboard with a one-tap Telegram share button."""
    share_url = f"https://t.me/{bot_username}"
    share_text = "I'm chatting with new people worldwide on this free anonymous bot! Join here:"
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
