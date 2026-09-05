import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import database

logger = logging.getLogger(__name__)


@dataclass
class QueueUser:
    tg_id: int
    gender: str
    is_premium: bool
    joined_at: float
    age_range: str = "unknown"


class MatchQueueManager:
    """
    Thread-safe & asyncio-safe virtual queue for Stranger Chat.
    Handles opposite-gender matching with fallback to any gender,
    with priority for premium users and wait time.
    """

    def __init__(self) -> None:
        self._queue: dict[int, QueueUser] = {}
        self._lock = asyncio.Lock()

    async def is_in_queue(self, tg_id: int) -> bool:
        """Returns True if user is currently waiting in queue."""
        async with self._lock:
            return tg_id in self._queue

    async def remove_user(self, tg_id: int) -> bool:
        """
        Removes a user from the queue if present.
        Returns True if user was removed, False if not in queue.
        """
        async with self._lock:
            if tg_id in self._queue:
                del self._queue[tg_id]
                logger.info("Removed user %s from matchmaking queue.", tg_id)
                return True
            return False

    async def find_match_or_enqueue(
        self,
        tg_id: int,
        gender: str,
        is_premium: bool,
        age_range: str = "unknown",
    ) -> tuple[Optional[int], bool]:
        """
        Attempts to match the user with a partner waiting in the queue.
        1. If user specified 'male' or 'female', tries opposite-gender candidates first.
        2. If no opposite-gender candidates are found (or user is 'prefer_not_to_say'),
           falls back to matching with ANY available user in the queue.
        3. If no users are waiting in the queue, enqueues this user.
        """
        gender_norm = gender.lower().strip()
        target_gender = (
            "female"
            if gender_norm == "male"
            else ("male" if gender_norm == "female" else None)
        )

        async with self._lock:
            # Check if user is already waiting
            if tg_id in self._queue:
                logger.info("User %s is already in queue.", tg_id)
                return None, False

            candidates: list[QueueUser] = []

            # 1. Try finding opposite-gender candidates first
            if target_gender:
                candidates = [
                    u
                    for u in self._queue.values()
                    if u.gender.lower() == target_gender and u.tg_id != tg_id
                ]

            # 2. Fallback: If opposite gender is not found, match with ANY available user
            if not candidates:
                candidates = [
                    u
                    for u in self._queue.values()
                    if u.tg_id != tg_id
                ]

            if candidates:
                # Priority: Premium first, same age range preference, oldest wait time
                candidates.sort(
                    key=lambda u: (
                        not u.is_premium,
                        (u.age_range != age_range)
                        if (age_range != "unknown" and u.age_range != "unknown")
                        else False,
                        u.joined_at,
                    )
                )
                matched_user = candidates[0]

                # Remove matched user from queue
                del self._queue[matched_user.tg_id]

                # Create persistent session in SQLite
                await database.create_chat_session(tg_id, matched_user.tg_id)
                logger.info(
                    "Matched user %s (%s, age=%s, prem=%s) with %s (%s, age=%s, prem=%s). Session created.",
                    tg_id,
                    gender_norm,
                    age_range,
                    is_premium,
                    matched_user.tg_id,
                    matched_user.gender,
                    matched_user.age_range,
                    matched_user.is_premium,
                )
                return matched_user.tg_id, True

            # No match available yet; add to queue
            self._queue[tg_id] = QueueUser(
                tg_id=tg_id,
                gender=gender_norm,
                is_premium=is_premium,
                joined_at=time.time(),
                age_range=age_range,
            )
            logger.info(
                "Enqueued user %s (%s, age=%s, prem=%s). Queue size: %d",
                tg_id,
                gender_norm,
                age_range,
                is_premium,
                len(self._queue),
            )
            return None, False

    async def get_stats(self) -> dict[str, int]:
        """Returns snapshot statistics about the current queue."""
        async with self._lock:
            total = len(self._queue)
            males = sum(1 for u in self._queue.values() if u.gender == "male")
            females = sum(1 for u in self._queue.values() if u.gender == "female")
            prefer_not_to_say = sum(
                1 for u in self._queue.values() if u.gender == "prefer_not_to_say"
            )
            premiums = sum(1 for u in self._queue.values() if u.is_premium)
            return {
                "total": total,
                "males": males,
                "females": females,
                "prefer_not_to_say": prefer_not_to_say,
                "premiums": premiums,
            }

    async def clear(self) -> None:
        """Clears all users from the queue (for testing/maintenance)."""
        async with self._lock:
            self._queue.clear()


# Global queue manager singleton instance
match_queue = MatchQueueManager()
