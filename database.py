import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import aiosqlite
import config

logger = logging.getLogger(__name__)


async def get_db_connection() -> aiosqlite.Connection:
    """Creates and returns an async SQLite database connection."""
    conn = await aiosqlite.connect(config.DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the SQLite database and creates the required tables."""
    path = db_path or config.DB_PATH
    logger.info("Initializing database at: %s", path)

    async with aiosqlite.connect(path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")

        # 1. Users table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                gender TEXT DEFAULT 'unknown',
                is_banned INTEGER DEFAULT 0,
                strikes INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                premium_expiry TEXT,
                account_created_at TEXT
            );
            """
        )

        # 2. Chat sessions table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                started_at TEXT DEFAULT (datetime('now')),
                last_activity_at TEXT DEFAULT (datetime('now'))
            );
            """
        )

        # Ensure last_activity_at column exists if table already existed
        async with db.execute("PRAGMA table_info(chat_sessions);") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
        if "last_activity_at" not in columns:
            await db.execute("ALTER TABLE chat_sessions ADD COLUMN last_activity_at TEXT;")

        # 3. Premium codes table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS premium_codes (
                code TEXT PRIMARY KEY,
                tg_id INTEGER NOT NULL,
                is_used INTEGER DEFAULT 0
            );
            """
        )

        # Indexes for fast querying
        await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_u1 ON chat_sessions(user1_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_u2 ON chat_sessions(user2_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_prem_tg ON premium_codes(tg_id);")

        await db.commit()
    logger.info("Database initialized successfully.")


async def get_user(tg_id: int) -> Optional[dict[str, Any]]:
    """Fetches a user by Telegram ID."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def upsert_user(
    tg_id: int,
    username: Optional[str],
    account_created_at: str,
    gender: str = "unknown",
    is_banned: int = 0,
) -> dict[str, Any]:
    """Inserts a new user or updates username if already present."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO users (tg_id, username, gender, is_banned, strikes, is_premium, premium_expiry, account_created_at)
            VALUES (?, ?, ?, ?, 0, 0, NULL, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                username = excluded.username;
            """,
            (tg_id, username, gender, is_banned, account_created_at),
        )
        await db.commit()

        async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}


async def update_user_gender(tg_id: int, gender: str) -> None:
    """Updates user's gender ('male', 'female', 'unknown')."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET gender = ? WHERE tg_id = ?",
            (gender, tg_id),
        )
        await db.commit()


async def set_user_banned(tg_id: int, is_banned: bool = True) -> None:
    """Bans or unbans a user."""
    banned_int = 1 if is_banned else 0
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = ? WHERE tg_id = ?",
            (banned_int, tg_id),
        )
        await db.commit()


async def add_strike(tg_id: int) -> tuple[int, bool]:
    """
    Increments strikes for a user.
    If strikes >= 3, automatically sets is_banned = 1.
    Returns:
        tuple[int, bool]: (updated_strikes_count, is_now_banned)
    """
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE users SET strikes = strikes + 1 WHERE tg_id = ?",
            (tg_id,),
        )
        async with db.execute("SELECT strikes FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            strikes = row["strikes"] if row else 1

        is_now_banned = strikes >= 3
        if is_now_banned:
            await db.execute(
                "UPDATE users SET is_banned = 1 WHERE tg_id = ?",
                (tg_id,),
            )
        await db.commit()
        return strikes, is_now_banned


async def create_chat_session(user1_id: int, user2_id: int) -> int:
    """Creates a new active chat session between two users."""
    now_str = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(config.DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO chat_sessions (user1_id, user2_id, started_at, last_activity_at)
            VALUES (?, ?, ?, ?)
            """,
            (user1_id, user2_id, now_str, now_str),
        )
        session_id = cursor.lastrowid
        await db.commit()
        return session_id or 0


async def get_active_session(user_id: int) -> Optional[dict[str, Any]]:
    """Returns the current active chat session for a user, or None."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM chat_sessions
            WHERE user1_id = ? OR user2_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def close_session_for_user(user_id: int) -> Optional[dict[str, Any]]:
    """
    Closes and removes any active chat session involving user_id.
    Returns the closed session dictionary, or None.
    """
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM chat_sessions
            WHERE user1_id = ? OR user2_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            session_dict = dict(row)
            cursor = await db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_dict["id"],))
            await db.commit()
            if cursor.rowcount and cursor.rowcount > 0:
                return session_dict
            return None
        return None


async def save_premium_code(code: str, tg_id: int) -> None:
    """Stores a generated 4-digit premium code for a user."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO premium_codes (code, tg_id, is_used)
            VALUES (?, ?, 0)
            ON CONFLICT(code) DO UPDATE SET
                tg_id = excluded.tg_id,
                is_used = 0;
            """,
            (code, tg_id),
        )
        await db.commit()


async def activate_premium_code(code: str, days: int = 30) -> Optional[int]:
    """
    Validates and activates a premium code.
    Sets is_premium = 1 and premium_expiry to now + days.
    Returns the user's tg_id if successful, or None if code is invalid/used.
    """
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM premium_codes WHERE code = ? AND is_used = 0",
            (code,),
        ) as cursor:
            code_row = await cursor.fetchone()

        if not code_row:
            return None

        tg_id = code_row["tg_id"]
        expiry_dt = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

        # Mark code as used
        await db.execute(
            "UPDATE premium_codes SET is_used = 1 WHERE code = ?",
            (code,),
        )
        # Update user premium status
        await db.execute(
            """
            UPDATE users
            SET is_premium = 1, premium_expiry = ?
            WHERE tg_id = ?
            """,
            (expiry_dt, tg_id),
        )
        await db.commit()
        return tg_id


async def is_premium_active(tg_id: int) -> bool:
    """Checks whether the user currently has an active premium subscription."""
    user = await get_user(tg_id)
    if not user or not user.get("is_premium"):
        return False
    expiry_str = user.get("premium_expiry")
    if not expiry_str:
        return True
    try:
        expiry_dt = datetime.fromisoformat(expiry_str)
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        return expiry_dt > datetime.now(timezone.utc)
    except Exception:
        return False


async def get_partner_id(user_id: int) -> Optional[int]:
    """Returns the partner user ID in the active chat session, or None."""
    session = await get_active_session(user_id)
    if not session:
        return None
    if session["user1_id"] == user_id:
        return session["user2_id"]
    return session["user1_id"]


async def update_session_activity(user_id: int) -> None:
    """Updates the last_activity_at timestamp for the active chat session."""
    now_str = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            """
            UPDATE chat_sessions
            SET last_activity_at = ?
            WHERE user1_id = ? OR user2_id = ?
            """,
            (now_str, user_id, user_id),
        )
        await db.commit()


async def get_and_close_inactive_sessions(timeout_minutes: int = 10) -> list[dict[str, Any]]:
    """
    Finds and closes all chat sessions where last_activity_at (or started_at)
    is older than timeout_minutes.
    Returns a list of closed session dictionaries.
    """
    threshold = (datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)).isoformat()
    closed_sessions: list[dict[str, Any]] = []

    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM chat_sessions
            WHERE COALESCE(last_activity_at, started_at) < ?
            """,
            (threshold,),
        ) as cursor:
            rows = await cursor.fetchall()

        for row in rows:
            sess_dict = dict(row)
            cursor = await db.execute("DELETE FROM chat_sessions WHERE id = ?", (sess_dict["id"],))
            if cursor.rowcount and cursor.rowcount > 0:
                closed_sessions.append(sess_dict)

        await db.commit()

    return closed_sessions


async def get_stats() -> dict[str, int]:
    """Returns database statistics for admin reporting."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users;") as cursor:
            row = await cursor.fetchone()
            total_users = row[0] if row else 0

        async with db.execute("SELECT COUNT(*) FROM users WHERE gender = 'male';") as cursor:
            row = await cursor.fetchone()
            male_users = row[0] if row else 0

        async with db.execute("SELECT COUNT(*) FROM users WHERE gender = 'female';") as cursor:
            row = await cursor.fetchone()
            female_users = row[0] if row else 0

        async with db.execute("SELECT COUNT(*) FROM chat_sessions;") as cursor:
            row = await cursor.fetchone()
            active_chats = row[0] if row else 0

    return {
        "total_users": total_users,
        "male_users": male_users,
        "female_users": female_users,
        "active_chats": active_chats,
    }

