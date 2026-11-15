"""Per-user impact counters, points, levels and leaderboard.

Points = counted_items + 5 * approved_reports, where at most DAILY_ITEM_CAP sorted
items per user per UTC day are added to counted_items (fair-points rule).
Level names are locale keys; translate them with the i18n layer.
"""

import hashlib
import hmac
import logging
from datetime import UTC, datetime

from qayta import storage
from qayta.config import get_settings

logger = logging.getLogger(__name__)

DAILY_ITEM_CAP = 20
REPORT_POINTS = 5

# (threshold, locale key) in ascending order of threshold.
LEVELS: list[tuple[int, str]] = [
    (0, "level.beginner"),
    (10, "level.recycler"),
    (50, "level.champion"),
    (100, "level.legend"),
]


def hash_user_id(user_id: int) -> str:
    """Return HMAC-SHA256 hex of *user_id* keyed with the bot token.

    Stable pseudonym, not anonymisation: anyone holding the bot token can recompute it.
    """
    key = get_settings().telegram_bot_token.encode()
    return hmac.new(key, str(user_id).encode(), hashlib.sha256).hexdigest()


def total_points(counted_items: int, approved_reports: int) -> int:
    """Pure points formula: counted items plus 5 per approved report."""
    return counted_items + REPORT_POINTS * approved_reports


def get_level(points: int) -> str:
    """Return the locale key of the highest level whose threshold is <= *points*."""
    for threshold, key in reversed(LEVELS):
        if points >= threshold:
            return key
    return LEVELS[0][1]


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def increment_items(user_id_hash: str, n: int = 1) -> None:
    """Add *n* sorted items; only up to 20 per day count towards points."""
    if n <= 0:
        return
    conn = storage._require_conn()
    today = _today()
    row = conn.execute(
        "SELECT items_day, items_today FROM impact WHERE user_id_hash = ?",
        (user_id_hash,),
    ).fetchone()
    items_today = row[1] if row and row[0] == today else 0
    counted = max(0, min(n, DAILY_ITEM_CAP - items_today))
    conn.execute(
        """
        INSERT INTO impact (user_id_hash, items_sorted, counted_items, items_day, items_today)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id_hash) DO UPDATE SET
            items_sorted  = items_sorted + excluded.items_sorted,
            counted_items = counted_items + excluded.counted_items,
            items_day     = excluded.items_day,
            items_today   = ?
        """,
        (user_id_hash, n, counted, today, items_today + counted, items_today + counted),
    )
    conn.commit()


def increment_reports(user_id_hash: str, n: int = 1) -> None:
    """Add *n* approved community reports."""
    if n <= 0:
        return
    conn = storage._require_conn()
    conn.execute(
        """
        INSERT INTO impact (user_id_hash, approved_reports) VALUES (?, ?)
        ON CONFLICT(user_id_hash) DO UPDATE SET
            approved_reports = approved_reports + excluded.approved_reports
        """,
        (user_id_hash, n),
    )
    conn.commit()


def get_stats(user_id_hash: str) -> dict:
    """Return counters, points and level key for a user (zeros if unknown)."""
    conn = storage._require_conn()
    row = conn.execute(
        "SELECT items_sorted, approved_reports, counted_items FROM impact "
        "WHERE user_id_hash = ?",
        (user_id_hash,),
    ).fetchone()
    items, reports, counted = row if row else (0, 0, 0)
    points = total_points(counted, reports)
    return {
        "items_sorted": items,
        "approved_reports": reports,
        "counted_items": counted,
        "points": points,
        "level": get_level(points),
    }


def _alias(user_id_hash: str) -> str:
    return f"Recycler #{user_id_hash[:4].upper()}"


def get_rank(user_id_hash: str) -> int | None:
    """Return the 1-based leaderboard position of a user, or ``None`` if they have no row."""
    conn = storage._require_conn()
    row = conn.execute(
        "SELECT counted_items + ? * approved_reports FROM impact WHERE user_id_hash = ?",
        (REPORT_POINTS, user_id_hash),
    ).fetchone()
    if row is None:
        return None
    pts = row[0]
    (ahead,) = conn.execute(
        """
        SELECT COUNT(*) FROM impact
        WHERE counted_items + ? * approved_reports > ?
           OR (counted_items + ? * approved_reports = ? AND user_id_hash < ?)
        """,
        (REPORT_POINTS, pts, REPORT_POINTS, pts, user_id_hash),
    ).fetchone()
    return ahead + 1


def get_leaderboard(limit: int = 10) -> list[dict]:
    """Return the top users as ``{"alias", "points", "level"}``; never the hash."""
    conn = storage._require_conn()
    rows = conn.execute(
        """
        SELECT user_id_hash, counted_items + ? * approved_reports AS pts
        FROM impact
        ORDER BY pts DESC, user_id_hash ASC
        LIMIT ?
        """,
        (REPORT_POINTS, limit),
    ).fetchall()
    return [
        {"alias": _alias(h), "points": pts, "level": get_level(pts)} for h, pts in rows
    ]
