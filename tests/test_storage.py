"""Tests for storage.py — SQLite language-preference helpers."""

import pytest

import qayta.storage as storage


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset the module-level connection before every test so each test is isolated."""
    storage._conn = None
    yield
    if storage._conn is not None:
        storage._conn.close()
        storage._conn = None


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_get_lang_returns_uz_for_unknown_user(in_memory_db: str) -> None:
    """get_lang defaults to 'uz' when no row exists for the user."""
    storage.init_db(in_memory_db)
    assert storage.get_lang(99999) == "uz"


def test_set_lang_then_get_lang_round_trips(in_memory_db: str) -> None:
    """set_lang followed by get_lang returns the stored value."""
    storage.init_db(in_memory_db)
    storage.set_lang(42, "ru")
    assert storage.get_lang(42) == "ru"


def test_set_lang_overwrites_existing(in_memory_db: str) -> None:
    """A second set_lang call for the same user replaces the previous language."""
    storage.init_db(in_memory_db)
    storage.set_lang(1, "en")
    storage.set_lang(1, "uz")
    assert storage.get_lang(1) == "uz"


def test_multiple_users_are_independent(in_memory_db: str) -> None:
    """Language preferences for different users don't interfere."""
    storage.init_db(in_memory_db)
    storage.set_lang(1, "en")
    storage.set_lang(2, "ru")
    assert storage.get_lang(1) == "en"
    assert storage.get_lang(2) == "ru"


def test_init_db_is_idempotent(in_memory_db: str) -> None:
    """Calling init_db twice does not raise and reuses the same connection."""
    storage.init_db(in_memory_db)
    first_conn = storage._conn
    storage.init_db(in_memory_db)
    assert storage._conn is first_conn


def test_get_lang_raises_before_init() -> None:
    """get_lang raises RuntimeError when init_db has not been called."""
    with pytest.raises(RuntimeError, match="init_db"):
        storage.get_lang(1)


def test_set_lang_raises_before_init() -> None:
    """set_lang raises RuntimeError when init_db has not been called."""
    with pytest.raises(RuntimeError, match="init_db"):
        storage.set_lang(1, "uz")


def test_init_db_creates_parent_directory(tmp_path: "pytest.TempPathFactory") -> None:
    """init_db creates missing parent directories for the db file."""
    db_file = tmp_path / "nested" / "dir" / "qayta.db"
    storage.init_db(str(db_file))
    assert db_file.exists()


# ---------------------------------------------------------------------------
# Schema tests for the mini-app tables
# ---------------------------------------------------------------------------


def _columns(table: str) -> list[str]:
    conn = storage._require_conn()
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def test_init_db_creates_new_tables(in_memory_db: str) -> None:
    """init_db creates reports, impact and overpass_cache in an in-memory DB."""
    storage.init_db(in_memory_db)
    conn = storage._require_conn()
    names = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"reports", "impact", "overpass_cache"} <= names


def test_reports_columns(in_memory_db: str) -> None:
    storage.init_db(in_memory_db)
    assert _columns("reports") == [
        "id", "type", "payload", "user_id_hash", "status", "created_at", "reviewed_at",
    ]


def test_impact_columns_include_daily_cap_fields(in_memory_db: str) -> None:
    storage.init_db(in_memory_db)
    cols = _columns("impact")
    assert {"user_id_hash", "items_sorted", "approved_reports"} <= set(cols)
    assert {"counted_items", "items_day", "items_today"} <= set(cols)


def test_overpass_cache_columns(in_memory_db: str) -> None:
    storage.init_db(in_memory_db)
    assert _columns("overpass_cache") == ["cache_key", "payload", "fetched_at"]


def test_reports_status_defaults_to_pending(in_memory_db: str) -> None:
    storage.init_db(in_memory_db)
    conn = storage._require_conn()
    conn.execute(
        "INSERT INTO reports (type, payload, user_id_hash, created_at) VALUES (?, ?, ?, ?)",
        ("point", "{}", "abc", "2024-01-01T00:00:00Z"),
    )
    row = conn.execute("SELECT status, reviewed_at FROM reports").fetchone()
    assert row == ("pending", None)


def test_impact_counters_default_to_zero(in_memory_db: str) -> None:
    storage.init_db(in_memory_db)
    conn = storage._require_conn()
    conn.execute("INSERT INTO impact (user_id_hash) VALUES ('abc')")
    row = conn.execute(
        "SELECT items_sorted, approved_reports, counted_items, items_day, items_today FROM impact"
    ).fetchone()
    assert row == (0, 0, 0, None, 0)
