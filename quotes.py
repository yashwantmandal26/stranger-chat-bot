from datetime import datetime, timezone
import random
from typing import Any, Optional

MOTIVATIONAL_QUOTES: list[str] = [
    "“Every new beginning comes from some other beginning’s end.” — Seneca",
    "“Not every connection is meant to last forever; some are just meant to remind us that we can connect.”",
    "“Don’t be sad because it’s over, smile because it happened.” — Dr. Seuss",
    "“Sometimes people enter our lives just to teach us how to appreciate the next one.”",
    "“The magic of life is that any stranger could become your next great friend.”",
    "“Every person you meet knows something you don’t. Onto the next adventure!”",
    "“What is meant for you will never pass you by. Keep an open heart and a positive mind.”",
    "“Every exit is an entrance somewhere else.” — Tom Stoppard",
    "“A journey of a thousand miles begins with a single conversation.”",
    "“Close the door to the past, take a deep breath, and step into the next conversation.”",
    "“A stranger is simply a friend you haven’t had the pleasure to talk with yet.” — W.B. Yeats",
    "“Your vibe attracts your tribe. Stay curious, stay positive!”",
    "“Keep your head high and your vibe positive. Your next great conversation is one tap away!”",
    "“The best chapter of your story is still being written. Turn the page!”",
    "“Never regret a conversation spoken with kindness. Every interaction helps you grow.”",
    "“Opportunities to connect are everywhere. Keep shining bright!”",
    "“Stars can’t shine without a little darkness. Onward to new horizons!”",
    "“The world is filled with interesting minds waiting to cross paths with yours.”",
    "“It takes only one meaningful conversation to turn a whole day around.”",
    "“When one door closes, a world of new connections opens up.” — Alexander Graham Bell",
    "“Radiate positive energy, and the right people will naturally find their way to you.”",
    "“Life is short, but the world is wide. Go discover someone new today!”",
    "“Be fearless in the pursuit of genuine human connections.”",
    "“Every hello starts a story. What will your next story be?”",
    "“Trust the timing of your life. The best conversations are yet to come!”",
    "“One conversation can change everything. Keep connecting!”",
    "“Kind words can be short and easy to speak, but their echoes are truly endless.” — Mother Teresa",
    "“There are no strangers here; only friends you haven't met yet.”",
    "“Every ending is a chance to reset, refocus, and recharge.”",
    "“The universe has a way of leading you exactly where you need to be. Onto the next!”",
]


def get_random_motivational_quote() -> str:
    """Returns a random motivational quote."""
    return random.choice(MOTIVATIONAL_QUOTES)


def format_chat_duration(seconds: float) -> str:
    """Formats duration in seconds to a human-readable string (e.g. '8 seconds', '2m 14s', '1h 5m')."""
    total_secs = max(0, int(round(seconds)))
    if total_secs < 60:
        return f"{total_secs} second{'s' if total_secs != 1 else ''}"
    minutes = total_secs // 60
    rem_secs = total_secs % 60
    if minutes < 60:
        if rem_secs > 0:
            return f"{minutes}m {rem_secs}s"
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    rem_mins = minutes % 60
    if rem_mins > 0:
        return f"{hours}h {rem_mins}m"
    return f"{hours} hour{'s' if hours != 1 else ''}"


def get_session_elapsed_seconds(session: dict[str, Any]) -> float:
    """Calculates elapsed seconds since session started."""
    started_at_str = session.get("started_at")
    if not started_at_str:
        return 0.0
    try:
        dt = datetime.fromisoformat(started_at_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return 0.0


def get_partner_ended_text(duration: Optional[str] = None) -> str:
    """Generates the clean card when a chat partner disconnects."""
    quote = get_random_motivational_quote()
    dur_line = f"⏱️ <b>Chat Duration:</b> <b>{duration}</b>\n\n" if duration else ""
    return (
        "👋 <b>Stranger has disconnected.</b>\n\n"
        f"{dur_line}"
        "✨ <b>Thought of the Moment:</b>\n"
        f"<i>{quote}</i>\n\n"
        "Ready to meet someone new?"
    )


def get_user_ended_text(duration: Optional[str] = None) -> str:
    """Generates the clean card when a user ends their own chat."""
    quote = get_random_motivational_quote()
    dur_line = f"⏱️ <b>Chat Duration:</b> <b>{duration}</b>\n\n" if duration else ""
    return (
        "⏹️ <b>Chat ended.</b>\n\n"
        f"{dur_line}"
        "✨ <b>Thought of the Moment:</b>\n"
        f"<i>{quote}</i>\n\n"
        "Where would you like to go next?"
    )
