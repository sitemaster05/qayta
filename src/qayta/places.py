"""Nearby collection points: Overpass queries, distance sort and a 24 h SQLite cache.

Points without ``recycling:*`` tags are kept (most Uzbek points have none). They are
marked ``materials_known: False`` and listed after the points known to accept the material.
"""

import json
import logging
import math
from datetime import UTC, datetime, timedelta

import httpx

from qayta import storage
from qayta.materials import CATALOGUE

logger = logging.getLogger(__name__)

OVERPASS_ENDPOINTS: tuple[str, ...] = (
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)
USER_AGENT = "Qayta-bot/1.0 (+https://github.com/qayta)"
REQUEST_TIMEOUT_S = 25.0
CACHE_TTL = timedelta(hours=24)
_EARTH_RADIUS_M = 6_371_000.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in metres between two coordinates."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def sort_by_distance(points: list[dict], origin_lat: float, origin_lon: float) -> list[dict]:
    """Return new dicts with ``distance_m`` added, sorted ascending by distance."""
    with_distance = [
        {**p, "distance_m": haversine(origin_lat, origin_lon, p["lat"], p["lon"])} for p in points
    ]
    return sorted(with_distance, key=lambda p: p["distance_m"])


def build_overpass_query(lat: float, lon: float, radius_m: int, osm_tag: str) -> str:
    """Build an Overpass QL query for recycling points and scrap yards around a location.

    All ``amenity=recycling`` and ``shop=scrap`` features are requested, including ones
    without *osm_tag*; ``fetch_nearby`` decides afterwards which ones are known to accept
    the material. ``shop=second_hand`` is never queried.
    """
    around = f"(around:{radius_m},{lat},{lon})"
    return (
        "[out:json][timeout:25];\n"
        f"// material tag: {osm_tag}\n"
        "(\n"
        f'  nwr["amenity"="recycling"]{around};\n'
        f'  nwr["shop"="scrap"]{around};\n'
        ");\n"
        "out center;"
    )


def _parse_elements(elements: list[dict], osm_tag: str) -> list[dict]:
    """Convert Overpass elements into point dicts (without distance)."""
    points: list[dict] = []
    for el in elements:
        center = el.get("center") or {}
        lat = el.get("lat", center.get("lat"))
        lon = el.get("lon", center.get("lon"))
        if lat is None or lon is None:
            continue
        tags = el.get("tags") or {}
        value = tags.get(osm_tag)
        if value == "no":
            continue  # explicitly does not accept this material
        points.append(
            {
                "lat": float(lat),
                "lon": float(lon),
                "name": tags.get("name") or tags.get("operator") or "",
                "phone": tags.get("phone") or tags.get("contact:phone") or "",
                "hours": tags.get("opening_hours", ""),
                "materials_known": value == "yes",
            }
        )
    return points


def _read_cache(key: str) -> list[dict] | None:
    conn = storage._require_conn()
    row = conn.execute(
        "SELECT payload, fetched_at FROM overpass_cache WHERE cache_key = ?", (key,)
    ).fetchone()
    if row is None:
        return None
    try:
        fetched_at = datetime.fromisoformat(row[1])
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - fetched_at > CACHE_TTL:
            return None
        return json.loads(row[0])
    except (ValueError, TypeError):
        return None


def _write_cache(key: str, points: list[dict]) -> None:
    conn = storage._require_conn()
    conn.execute(
        "INSERT OR REPLACE INTO overpass_cache (cache_key, payload, fetched_at) VALUES (?, ?, ?)",
        (key, json.dumps(points, ensure_ascii=False), datetime.now(UTC).isoformat()),
    )
    conn.commit()


async def fetch_nearby(
    lat: float, lon: float, material_key: str, radius_m: int = 5000
) -> list[dict]:
    """Return collection points near (lat, lon) for *material_key*, nearest known first.

    Each dict has ``lat``, ``lon``, ``name``, ``phone``, ``hours``, ``distance_m`` and
    ``materials_known``. Points known to accept the material come first (by distance),
    then points with unknown materials (by distance). Returns ``[]`` if every Overpass
    endpoint fails.
    """
    key = f"{lat:.3f},{lon:.3f},{material_key}"
    cached = _read_cache(key)
    if cached is not None:
        return cached

    osm_tag = CATALOGUE[material_key].osm_tag
    query = build_overpass_query(lat, lon, radius_m, osm_tag)
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S, headers=headers) as client:
        for url in OVERPASS_ENDPOINTS:
            try:
                response = await client.post(url, data={"data": query})
                response.raise_for_status()
                elements = response.json().get("elements", [])
            except (httpx.HTTPError, ValueError, AttributeError) as exc:
                logger.warning("Overpass request to %s failed: %s", url, exc)
                continue

            points = sort_by_distance(_parse_elements(elements, osm_tag), lat, lon)
            points.sort(key=lambda p: not p["materials_known"])  # stable: keeps distance order
            _write_cache(key, points)
            return points

    logger.warning("All Overpass endpoints failed for %s", key)
    return []
