"""Tests for qayta.places."""

import httpx
import pytest
from hypothesis import given
from hypothesis import strategies as st

from qayta import places, storage
from qayta.places import build_overpass_query, fetch_nearby, haversine, sort_by_distance

_lat = st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)
_lon = st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)
_points = st.lists(
    st.fixed_dictionaries({"lat": _lat, "lon": _lon, "name": st.text(max_size=10)}),
    max_size=30,
)


# Feature: mini-app, Property 1: Distance sort is non-decreasing
@given(points=_points, origin_lat=_lat, origin_lon=_lon)
def test_sort_by_distance_non_decreasing(points, origin_lat, origin_lon):
    """**Validates: Requirements 9.1**"""
    result = sort_by_distance(points, origin_lat, origin_lon)
    assert len(result) == len(points)
    distances = [p["distance_m"] for p in result]
    assert all(a <= b for a, b in zip(distances, distances[1:], strict=False))


# ---------------------------------------------------------------------------
# Unit tests (Requirements 9.1-9.6); httpx is mocked, no network.
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    """Fresh in-memory database per test."""
    storage._conn = None
    storage.init_db(":memory:")
    yield
    if storage._conn is not None:
        storage._conn.close()
    storage._conn = None


class _FakeResponse:
    def __init__(self, data: dict | None = None, error: Exception | None = None) -> None:
        self._data = data or {}
        self._error = error

    def raise_for_status(self) -> None:
        if self._error:
            raise self._error

    def json(self) -> dict:
        return self._data


def _patch_client(monkeypatch, responses: list[_FakeResponse]) -> list[str]:
    """Replace httpx.AsyncClient; return the list of URLs that were posted to."""
    calls: list[str] = []

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *exc) -> None:
            return None

        async def post(self, url: str, data: dict | None = None) -> _FakeResponse:
            calls.append(url)
            return responses[min(len(calls) - 1, len(responses) - 1)]

    monkeypatch.setattr(places.httpx, "AsyncClient", FakeClient)
    return calls


def test_haversine_identity_at_origin():
    assert haversine(0, 0, 0, 0) == 0


def test_haversine_one_degree_is_about_111_km():
    assert haversine(0, 0, 1, 0) == pytest.approx(111_195, rel=0.01)
    assert haversine(0, 0, 0, 1) == pytest.approx(111_195, rel=0.01)


def test_build_overpass_query_contains_osm_tag():
    query = build_overpass_query(41.3, 69.2, 5000, "recycling:glass")
    assert "recycling:glass" in query
    assert "(around:5000,41.3,69.2)" in query


async def test_fetch_nearby_cache_miss_fetches_and_stores(db, monkeypatch):
    elements = [
        {"lat": 41.31, "lon": 69.24, "tags": {"name": "A", "recycling:glass": "yes"}},
        {"lat": 41.30, "lon": 69.24, "tags": {"name": "B"}},
    ]
    calls = _patch_client(monkeypatch, [_FakeResponse({"elements": elements})])

    result = await fetch_nearby(41.3, 69.24, "GLASS")

    assert len(calls) == 1
    assert [p["name"] for p in result] == ["A", "B"]  # known material first
    assert storage._require_conn().execute("SELECT COUNT(*) FROM overpass_cache").fetchone()[0] == 1


async def test_fetch_nearby_cache_hit_skips_network(db, monkeypatch):
    elements = [{"lat": 41.31, "lon": 69.24, "tags": {"name": "A"}}]
    calls = _patch_client(monkeypatch, [_FakeResponse({"elements": elements})])

    first = await fetch_nearby(41.3001, 69.2401, "GLASS")
    second = await fetch_nearby(41.3002, 69.2402, "GLASS")  # same rounded key

    assert len(calls) == 1
    assert second == first


async def test_fetch_nearby_all_endpoints_fail_returns_empty(db, monkeypatch):
    err = httpx.ConnectError("boom")
    calls = _patch_client(monkeypatch, [_FakeResponse(error=err)])

    assert await fetch_nearby(41.3, 69.24, "GLASS") == []
    assert len(calls) == len(places.OVERPASS_ENDPOINTS)

