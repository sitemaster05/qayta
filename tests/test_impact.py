"""Tests for qayta.impact."""

import hashlib
import hmac
import re
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from qayta import impact, storage


# Feature: mini-app, Property 2: Points maths identity
@given(
    st.integers(min_value=0, max_value=10**9),
    st.integers(min_value=0, max_value=10**9),
)
def test_total_points_identity(items: int, reports: int) -> None:
    """**Validates: Requirements 10.1**"""
    assert impact.total_points(items, reports) == items + 5 * reports


# Feature: mini-app, Property 3: Level is always a valid string
@given(st.integers(min_value=0, max_value=10**9), st.integers(min_value=0, max_value=10**9))
def test_get_level_valid_and_monotonic(a: int, b: int) -> None:
    """**Validates: Requirements 10.2**"""
    keys = [key for _, key in impact.LEVELS]
    lo, hi = sorted((a, b))
    assert impact.get_level(lo) in keys
    assert impact.get_level(hi) in keys
    assert keys.index(impact.get_level(lo)) <= keys.index(impact.get_level(hi))


# Feature: mini-app, Property 5: Report user_id is always stored hashed (hash_user_id variant)
@given(st.integers(), st.integers())
def test_hash_user_id_properties(a: int, b: int) -> None:
    """**Validates: Requirements 10.3, 10.4**"""
    token = "123456:test-token"
    with patch.object(impact, "get_settings", return_value=SimpleNamespace(telegram_bot_token=token)):
        h = impact.hash_user_id(a)
        assert h == impact.hash_user_id(a)
        assert re.fullmatch(r"[0-9a-f]{64}", h)
        assert h != str(a)
        assert h == hmac.new(token.encode(), str(a).encode(), hashlib.sha256).hexdigest()
        if a != b:
            assert h != impact.hash_user_id(b)



@pytest.fixture
def db():
    """Fresh in-memory database per test."""
    storage._conn = None
    storage.init_db(":memory:")
    yield
    if storage._conn is not None:
        storage._conn.close()
    storage._conn = None


def test_increment_items_creates_and_accumulates(db) -> None:
    """**Validates: Requirements 10.1, 10.3**"""
    impact.increment_items("aaaa", 3)
    impact.increment_items("aaaa", 2)
    stats = impact.get_stats("aaaa")
    assert stats["items_sorted"] == 5
    assert stats["counted_items"] == 5
    assert stats["points"] == 5


def test_increment_items_ignores_non_positive(db) -> None:
    """**Validates: Requirements 10.1**"""
    impact.increment_items("aaaa", 0)
    impact.increment_items("aaaa", -2)
    assert impact.get_stats("aaaa")["items_sorted"] == 0


def test_daily_cap_and_day_rollover(db, monkeypatch) -> None:
    """**Validates: Requirements 10.1**"""
    monkeypatch.setattr(impact, "_today", lambda: "2030-01-01")
    impact.increment_items("aaaa", 15)
    impact.increment_items("aaaa", 15)
    stats = impact.get_stats("aaaa")
    assert stats["items_sorted"] == 30
    assert stats["counted_items"] == 20
    impact.increment_items("aaaa", 5)
    assert impact.get_stats("aaaa")["counted_items"] == 20

    monkeypatch.setattr(impact, "_today", lambda: "2030-01-02")
    impact.increment_items("aaaa", 25)
    stats = impact.get_stats("aaaa")
    assert stats["items_sorted"] == 60
    assert stats["counted_items"] == 40


def test_increment_reports_upsert(db) -> None:
    """**Validates: Requirements 10.1, 10.2**"""
    impact.increment_reports("bbbb")
    impact.increment_reports("bbbb", 2)
    impact.increment_reports("bbbb", 0)
    stats = impact.get_stats("bbbb")
    assert stats["approved_reports"] == 3
    assert stats["points"] == 15
    assert stats["level"] == "level.recycler"


def test_get_stats_unknown_user(db) -> None:
    """**Validates: Requirements 10.4**"""
    assert impact.get_stats("nobody") == {
        "items_sorted": 0,
        "approved_reports": 0,
        "counted_items": 0,
        "points": 0,
        "level": "level.beginner",
    }


def test_leaderboard_order_alias_limit(db) -> None:
    """**Validates: Requirements 10.5**"""
    low, mid, top = "abcd" + "0" * 60, "ef01" + "0" * 60, "9999" + "0" * 60
    impact.increment_items(low, 1)
    impact.increment_items(mid, 4)
    impact.increment_reports(top, 2)
    board = impact.get_leaderboard()
    assert [e["points"] for e in board] == [10, 4, 1]
    assert board[0]["alias"] == "Recycler #9999"
    assert board[1]["alias"] == "Recycler #EF01"
    for entry in board:
        assert set(entry) == {"alias", "points", "level"}
        assert low not in str(entry) and mid not in str(entry) and top not in str(entry)
    assert len(impact.get_leaderboard(limit=2)) == 2


def test_get_rank_matches_leaderboard_order(db) -> None:
    """**Validates: Requirements 10.5**"""
    low, top = "abcd" + "0" * 60, "9999" + "0" * 60
    impact.increment_items(low, 2)
    impact.increment_items(top, 9)
    assert impact.get_rank(top) == 1
    assert impact.get_rank(low) == 2
    assert impact.get_rank("nobody") is None
