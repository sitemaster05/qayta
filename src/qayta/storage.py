"""SQLite helper for per-user language preferences.

The module keeps a single module-level connection (`_conn`) that is created by
`init_db()`.  All public helpers raise `RuntimeError` when called before `init_db()`.
The connection is not thread-safe, but `python-telegram-bot`'s async polling runs in a
single OS thread, so a plain `sqlite3.connect` is fine here.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_conn: sqlite3.Connection | None = None

_CREATE_USER_LANGUAGE = """
CREATE TABLE IF NOT EXISTS user_language (
    user_id   INTEGER PRIMARY KEY,
    lang      TEXT    NOT NULL DEFAULT 'uz'
);
"""

# Community reports from the Mini App. user_id_hash is HMAC-SHA256 (see impact.hash_user_id).
_CREATE_REPORTS = """
CREATE TABLE IF NOT EXISTS reports (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    type          TEXT    NOT NULL,
    payload       TEXT    NOT NULL,
    user_id_hash  TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'pending',
    created_at    TEXT    NOT NULL,
    reviewed_at   TEXT
);
"""

# Per-user counters. items_day / items_today back the 20 items per day points cap.
_CREATE_IMPACT = """
CREATE TABLE IF NOT EXISTS impact (
    user_id_hash      TEXT    PRIMARY KEY,
    items_sorted      INTEGER NOT NULL DEFAULT 0,
    approved_reports  INTEGER NOT NULL DEFAULT 0,
    counted_items     INTEGER NOT NULL DEFAULT 0,
    items_day         TEXT,
    items_today       INTEGER NOT NULL DEFAULT 0
);
"""

_CREATE_OVERPASS_CACHE = """
CREATE TABLE IF NOT EXISTS overpass_cache (
    cache_key   TEXT PRIMARY KEY,
    payload     TEXT NOT NULL,
    fetched_at  TEXT NOT NULL
);
"""


def init_db(db_path: str = "data/qayta.db") -> None:
    """Open (or create) the SQLite database at *db_path* and run schema migrations.

    Creates the parent directory when it does not exist yet.
    Subsequent calls are no-ops (the module-level connection is reused).
    """
    global _conn  # noqa: PLW0603

    if _conn is not None:
        return  # already initialised

    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _conn = sqlite3.connect(db_path, check_same_thread=False)
    _conn.execute("PRAGMA journal_mode=WAL;")
    _conn.execute(_CREATE_USER_LANGUAGE)
    _conn.execute(_CREATE_REPORTS)
    _conn.execute(_CREATE_IMPACT)
    _conn.execute(_CREATE_OVERPASS_CACHE)
    _conn.commit()
    logger.debug("Database initialised at %s", db_path)


def _require_conn() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("storage.init_db() has not been called yet")
    return _conn


def get_lang(user_id: int) -> str:
    """Return the stored language code for *user_id*, defaulting to ``"uz"``."""
    conn = _require_conn()
    row = conn.execute(
        "SELECT lang FROM user_language WHERE user_id = ?", (user_id,)
    ).fetchone()
    return row[0] if row else "uz"


def set_lang(user_id: int, lang: str) -> None:
    """Upsert the language preference for *user_id*."""
    conn = _require_conn()
    conn.execute(
        "INSERT OR REPLACE INTO user_language (user_id, lang) VALUES (?, ?)",
        (user_id, lang),
    )
    conn.commit()
    logger.debug("Language for user %d set to %s", user_id, lang)
