import bisect
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the checkpoints dataset
DATA_PATH = Path(__file__).resolve().parent / "data" / "id_checkpoints.json"

# Minimal fallback milestone points in case external dataset file is absent
_FALLBACK_CHECKPOINTS = [
    (0, "2013-08-14"),
    (63263518, "2014-10-27"),
    (124872445, "2015-08-17"),
    (222021233, "2016-06-08"),
    (369669043, "2017-03-31"),
    (5288930461, "2022-01-27"),
    (5694365966, "2022-08-28"),
    (5983753471, "2022-12-23"),
    (6135597783, "2023-05-24"),
    (6749492866, "2023-11-22"),
    (6903333095, "2024-01-31"),
    (7085776398, "2024-05-10"),
    (7458668365, "2024-08-02"),
    (7664959631, "2024-12-19"),
    (7834356221, "2025-09-01"),
    (8559682245, "2025-11-11"),
]


def _load_checkpoints() -> list[tuple[int, float]]:
    """Loads and returns sorted (user_id, timestamp_seconds) checkpoints."""
    points: list[tuple[int, float]] = []
    if DATA_PATH.exists():
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            for item in raw_data:
                uid = int(item["id"])
                dt = datetime.fromisoformat(item["date"]).replace(tzinfo=timezone.utc)
                points.append((uid, dt.timestamp()))
        except Exception as e:
            logger.warning("Failed to load checkpoints from %s: %s. Using fallback.", DATA_PATH, e)

    if not points:
        for uid, date_str in _FALLBACK_CHECKPOINTS:
            dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            points.append((uid, dt.timestamp()))

    points.sort(key=lambda x: x[0])
    return points


_CHECKPOINTS: list[tuple[int, float]] = _load_checkpoints()
_CHECKPOINT_IDS: list[int] = [p[0] for p in _CHECKPOINTS]


def estimate_account_creation_date(tg_id: int) -> datetime:
    """
    Estimates Telegram account creation date by interpolating
    the numeric user ID against milestone checkpoints.
    """
    if not _CHECKPOINTS:
        return datetime.now(timezone.utc)

    # If ID is older than our earliest milestone
    if tg_id <= _CHECKPOINTS[0][0]:
        return datetime.fromtimestamp(_CHECKPOINTS[0][1], tz=timezone.utc)

    # If ID is newer than our latest milestone, extrapolate using the last segment rate
    if tg_id >= _CHECKPOINTS[-1][0]:
        p_prev = _CHECKPOINTS[-2]
        p_last = _CHECKPOINTS[-1]
        id_delta = p_last[0] - p_prev[0]
        ts_delta = p_last[1] - p_prev[1]
        rate = ts_delta / id_delta if id_delta > 0 else 0
        est_ts = p_last[1] + (tg_id - p_last[0]) * rate
        now_ts = datetime.now(timezone.utc).timestamp()
        if est_ts > now_ts:
            est_ts = now_ts
        return datetime.fromtimestamp(est_ts, tz=timezone.utc)

    # Find the interval containing tg_id using binary search
    idx = bisect.bisect_right(_CHECKPOINT_IDS, tg_id)
    id_low, ts_low = _CHECKPOINTS[idx - 1]
    id_high, ts_high = _CHECKPOINTS[idx]

    ratio = (tg_id - id_low) / (id_high - id_low)
    est_ts = ts_low + ratio * (ts_high - ts_low)
    return datetime.fromtimestamp(est_ts, tz=timezone.utc)


def check_account_age(tg_id: int, min_days: int = 30) -> tuple[bool, int, datetime]:
    """
    Checks if a Telegram account is at least `min_days` old.
    Returns:
        tuple[bool, int, datetime]:
        (is_allowed, age_in_days, estimated_creation_date)
    """
    now = datetime.now(timezone.utc)
    est_date = estimate_account_creation_date(tg_id)
    age_days = (now - est_date).days

    is_allowed = age_days >= min_days
    return is_allowed, age_days, est_date
