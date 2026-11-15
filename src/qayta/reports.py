"""Community reports (new points and prices) awaiting admin review.

The raw Telegram user id is never stored: only ``impact.hash_user_id(user_id)``.
"""

import json
import logging
import sqlite3
from datetime import UTC, datetime

from qayta import impact, storage

logger = logging.getLogger(__name__)

_COLUMNS = "id, type, payload, user_id_hash, status, created_at, reviewed_at"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_dict(row: tuple) -> dict:
    """Convert a DB row to a dict; ``payload`` is decoded from JSON."""
    report = dict(zip(_COLUMNS.split(", "), row, strict=True))
    report["payload"] = json.loads(report["payload"])
    return report


def _fetch(conn: sqlite3.Connection, report_id: int) -> dict:
    row = conn.execute(f"SELECT {_COLUMNS} FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row is None:
        raise KeyError(f"report {report_id} not found")
    return _to_dict(row)


def add_report(type_: str, payload: dict, user_id: int) -> int:
    """Insert a pending report and return its id. Stores only the hashed user id."""
    conn = storage._require_conn()
    cur = conn.execute(
        "INSERT INTO reports (type, payload, user_id_hash, status, created_at) "
        "VALUES (?, ?, ?, 'pending', ?)",
        (type_, json.dumps(payload, ensure_ascii=False), impact.hash_user_id(user_id), _now()),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_pending_reports() -> list[dict]:
    """Return all pending reports, oldest first."""
    conn = storage._require_conn()
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM reports WHERE status = 'pending' ORDER BY created_at ASC, id ASC"
    ).fetchall()
    return [_to_dict(r) for r in rows]


def approve_report(report_id: int) -> dict:
    """Mark a pending report approved and credit the reporter. Returns the updated row.

    A report that is not pending is returned unchanged and earns no extra points.
    Raises ``KeyError`` if the id is unknown.
    """
    conn = storage._require_conn()
    report = _fetch(conn, report_id)
    if report["status"] != "pending":
        return report
    conn.execute(
        "UPDATE reports SET status = 'approved', reviewed_at = ? WHERE id = ?",
        (_now(), report_id),
    )
    conn.commit()
    impact.increment_reports(report["user_id_hash"])
    return _fetch(conn, report_id)


def reject_report(report_id: int) -> None:
    """Mark a pending report rejected and set ``reviewed_at``; no points are awarded."""
    conn = storage._require_conn()
    conn.execute(
        "UPDATE reports SET status = 'rejected', reviewed_at = ? WHERE id = ? AND status = 'pending'",
        (_now(), report_id),
    )
    conn.commit()
