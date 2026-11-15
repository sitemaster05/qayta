"""Tests for qayta.reports."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qayta import impact, reports, storage

TOKEN = "123456:test-token"


@pytest.fixture(autouse=True)
def db():
    """Fresh in-memory database and fixed token per test."""
    storage._conn = None
    storage.init_db(":memory:")
    with patch.object(impact, "get_settings", return_value=SimpleNamespace(telegram_bot_token=TOKEN)):
        yield
    if storage._conn is not None:
        storage._conn.close()
    storage._conn = None


def test_add_report_creates_pending_row() -> None:
    """**Validates: Requirements 11.1**"""
    rid = reports.add_report("price", {"material": "PET_1", "price_som_per_kg": 1200}, 42)
    pending = reports.get_pending_reports()
    assert [r["id"] for r in pending] == [rid]
    assert pending[0]["status"] == "pending"
    assert pending[0]["type"] == "price"
    assert pending[0]["payload"]["price_som_per_kg"] == 1200
    assert pending[0]["reviewed_at"] is None


def test_add_report_stores_hash_not_raw_id() -> None:
    """**Validates: Requirements 11.2**"""
    reports.add_report("point", {"name": "X"}, 987654321)
    stored = storage._require_conn().execute("SELECT user_id_hash FROM reports").fetchone()[0]
    assert stored == impact.hash_user_id(987654321)
    assert "987654321" not in stored


def test_approve_sets_status_and_credits_reporter() -> None:
    """**Validates: Requirements 12.1, 12.2**"""
    rid = reports.add_report("point", {"name": "X"}, 7)
    row = reports.approve_report(rid)
    assert row["status"] == "approved"
    assert row["reviewed_at"] is not None
    assert reports.get_pending_reports() == []
    assert impact.get_stats(impact.hash_user_id(7))["approved_reports"] == 1


def test_approve_twice_does_not_double_credit() -> None:
    rid = reports.add_report("point", {"name": "X"}, 7)
    reports.approve_report(rid)
    reports.approve_report(rid)
    assert impact.get_stats(impact.hash_user_id(7))["approved_reports"] == 1


def test_reject_sets_status_without_points() -> None:
    """**Validates: Requirements 12.3**"""
    rid = reports.add_report("point", {"name": "X"}, 7)
    reports.reject_report(rid)
    row = storage._require_conn().execute(
        "SELECT status, reviewed_at FROM reports WHERE id = ?", (rid,)
    ).fetchone()
    assert row[0] == "rejected"
    assert row[1] is not None
    assert impact.get_stats(impact.hash_user_id(7))["approved_reports"] == 0


def test_approve_unknown_report_raises() -> None:
    with pytest.raises(KeyError):
        reports.approve_report(999)


def test_user_id_hash_differs_from_plain_id() -> None:
    """**Validates: Requirements 6.4**"""
    reports.add_report("point", {"name": "X"}, 42)
    stored = storage._require_conn().execute("SELECT user_id_hash FROM reports").fetchone()[0]
    assert stored != str(42)


def test_pending_reports_oldest_first_and_reviewed_ones_leave_queue() -> None:
    """**Validates: Requirements 7.3, 7.4**"""
    first = reports.add_report("point", {"name": "A"}, 1)
    second = reports.add_report("price", {"material": "PET_1"}, 2)
    third = reports.add_report("point", {"name": "C"}, 3)
    assert [r["id"] for r in reports.get_pending_reports()] == [first, second, third]
    reports.reject_report(second)
    assert [r["id"] for r in reports.get_pending_reports()] == [first, third]


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(user_id=st.integers())
def test_property_report_user_id_always_stored_hashed(user_id: int) -> None:
    """**Property 5: Report user_id is always stored hashed**

    **Validates: Requirements 6.4**
    """
    rid = reports.add_report("point", {"name": "X"}, user_id)
    stored = storage._require_conn().execute(
        "SELECT user_id_hash FROM reports WHERE id = ?", (rid,)
    ).fetchone()[0]
    assert stored == impact.hash_user_id(user_id)
    assert stored != str(user_id)
