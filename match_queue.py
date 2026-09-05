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


class MatchQueueManager:
    """
    Thread-safe & asyncio-safe virtual queue for Stranger Chat.
    Handles opposite-gender matching with priority for premium users.
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
    ) -> tuple[Optional[int], bool]:
        """
        Attempts to match the user with an opposite-gender user waiting in the queue.
        If a match is found:
          - The matched user is removed from the queue.
          - An active chat session is persisted in SQLite.
          - Returns (partner_tg_id, True).
        If no match is found:
          - The user is enqueued.
          - Returns (None, False).
        """
        target_gender = "female" if gender.lower() == "male" else "male"

        async with self._lock:
            # Check if user is already waiting
            if tg_id in self._queue:
                logger.info("User %s is already in queue.", tg_id)
                return None, False

            # Find opposite-gender candidates
            candidates: list[QueueUser] = [
                u
                for u in self._queue.values()
                if u.gender.lower() == target_gender and u.tg_id != tg_id
            ]

            if candidates:
                # Priority: Premium first (False > True inverted, so not is_premium -> 0 for True, 1 for False),
                # followed by oldest wait time (joined_at ascending)
                candidates.sort(key=lambda u: (not u.is_premium, u.joined_at))
                matched_user = candidates[0]

                # Remove matched user from queue
                del self._queue[matched_user.tg_id]

                # Create persistent session in SQLite
                await database.create_chat_session(tg_id, matched_user.tg_id)
                logger.info(
                    "Matched user %s (%s, prem=%s) with %s (%s, prem=%s). Session created.",
                    tg_id,
                    gender,
                    is_premium,
                    matched_user.tg_id,
                    matched_user.gender,
                    matched_user.is_premium,
                )
                return matched_user.tg_id, True

            # No match available yet; add to queue
            self._queue[tg_id] = QueueUser(
                tg_id=tg_id,
                gender=gender.lower(),
                is_premium=is_premium,
                joined_at=time.time(),
            )
            logger.info(
                "Enqueued user %s (%s, prem=%s). Queue size: %d",
                tg_id,
                gender,
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
            premiums = sum(1 for u in self._queue.values() if u.is_premium)
            return {
                "total": total,
                "males": males,
                "females": females,
                "premiums": premiums,
            }

    async def clear(self) -> None:
        """Clears all users from the queue (for testing/maintenance)."""
        async with self._lock:
            self._queue.clear()


# Global queue manager singleton instance
match_queue = MatchQueueManager()
