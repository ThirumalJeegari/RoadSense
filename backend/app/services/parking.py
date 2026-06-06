from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import re

import httpx

from app.core.config import get_settings
from app.services.cache import cache
from app.services.geo import geocode_india_location


LA_OCCUPANCY_URL = "https://data.lacity.org/resource/e7h6-4a3e.json"
LA_INVENTORY_URL = "https://data.lacity.org/resource/s49e-q6j2.json"
ARLINGTON_URL = "https://api.exactpark.com/api/v2/arlington/status/zones"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
]


async def parking_snapshot(provider: str = "india", limit: int = 180, city: str = "Bengaluru") -> dict:
    provider_key = provider.lower().strip()
    if provider_key in {"india", "in", "osm", "openstreetmap"}:
        return await _india_parking(city=city, limit=limit)
    if provider_key in {"la", "los-angeles", "los angeles"}:
        return await _la_parking(limit)
    if provider_key in {"arlington", "arl"}:
        return await _arlington_parking(limit)
    raise ValueError("Unsupported parking provider. Use 'india', 'la', or 'arlington'.")


async def _india_parking(city: str, limit: int) -> dict:
    limit = max(25, min(limit, 300))
    location = await geocode_india_location(city)
    key = f"parking:india:{location['latitude']}:{location['longitude']}:{limit}"
    cached = cache.get(key)
    if cached:
        return cached

    settings = get_settings()
    query = _overpass_query(location["latitude"], location["longitude"], limit)
    elements: list[dict] = []
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        for url in OVERPASS_URLS:
            try:
                response = await client.post(
                    url,
                    data={"data": query},
                    headers={"Accept": "application/json", "User-Agent": "SmartCitiesHackathon/1.0"},
                )
                response.raise_for_status()
                elements = response.json().get("elements", [])
                if elements:
                    break
            except httpx.HTTPError:
                continue

    facilities = _india_facilities_from_osm(elements, location, limit)
    source_url = "https://www.openstreetmap.org"
    provider = f"India Parking - {location['name']}"
    source_note = "OpenStreetMap parking locations with estimated live slot availability"
    used_fallback = False
    if not facilities:
        facilities = _fallback_india_facilities(location, limit)
        source_note = "Generated India demo parking points because the public Overpass API was unavailable"
        used_fallback = True

    snapshot = _summarize(facilities, provider=provider, source_url=source_url)
    snapshot.update(
        {
            "city": location["name"],
            "location": location,
            "source_note": source_note,
            "total_facilities": len(facilities),
        }
    )
    return cache.set(key, snapshot, ttl_seconds=45 if used_fallback else 60 * 10)


async def _la_parking(limit: int) -> dict:
    limit = max(50, min(limit, 1000))
    key = f"parking:la:{limit}"
    cached = cache.get(key)
    if cached:
        return cached

    settings = get_settings()
    headers = _socrata_headers()
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        occupancy_response = await client.get(
            LA_OCCUPANCY_URL,
            params={
                "$select": "spaceid,eventtime,occupancystate",
                "$order": "eventtime DESC",
                "$limit": str(limit),
            },
            headers=headers,
        )
        occupancy_response.raise_for_status()
        occupancy_items = occupancy_response.json()

        ids = [item.get("spaceid") for item in occupancy_items if item.get("spaceid")]
        inventory: dict[str, dict] = {}
        for chunk in _chunks(ids, 80):
            quoted_ids = ",".join(_soql_string(space_id) for space_id in chunk)
            inventory_response = await client.get(
                LA_INVENTORY_URL,
                params={
                    "$select": "spaceid,blockface,metertype,ratetype,raterange,timelimit,latlng",
                    "$where": f"spaceid in({quoted_ids})",
                    "$limit": str(len(chunk)),
                },
                headers=headers,
            )
            inventory_response.raise_for_status()
            inventory.update({item.get("spaceid"): item for item in inventory_response.json()})

    stalls = []
    for occupancy in occupancy_items:
        item = inventory.get(occupancy.get("spaceid"), {})
        latlng = item.get("latlng") or {}
        if not latlng.get("latitude") or not latlng.get("longitude"):
            continue
        state = (occupancy.get("occupancystate") or "UNKNOWN").lower()
        stalls.append(
            {
                "id": occupancy.get("spaceid"),
                "name": occupancy.get("spaceid"),
                "block": item.get("blockface", "Los Angeles"),
                "status": _normalize_status(state),
                "latitude": float(latlng["latitude"]),
                "longitude": float(latlng["longitude"]),
                "timestamp": occupancy.get("eventtime"),
                "rate": item.get("raterange"),
                "time_limit": item.get("timelimit"),
                "source": "LADOT Parking Meter Occupancy",
            }
        )

    snapshot = _summarize(stalls, provider="Los Angeles LADOT", source_url=LA_OCCUPANCY_URL)
    return cache.set(key, snapshot, ttl_seconds=60)


async def _arlington_parking(limit: int) -> dict:
    limit = max(50, min(limit, 2000))
    key = f"parking:arlington:{limit}"
    cached = cache.get(key)
    if cached:
        return cached

    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(ARLINGTON_URL)
        response.raise_for_status()
    payload = response.json()
    stalls = []
    for item in payload.get("data", [])[:limit]:
        location = item.get("location") or {}
        if location.get("lat") is None or location.get("long") is None:
            continue
        stalls.append(
            {
                "id": item.get("stallID"),
                "name": item.get("stallName"),
                "block": item.get("blockfaceID"),
                "status": _normalize_status(item.get("status", "unknown")),
                "latitude": float(location["lat"]),
                "longitude": float(location["long"]),
                "timestamp": item.get("payloadTimestamp"),
                "rate": None,
                "time_limit": None,
                "source": "Arlington ExactPark",
            }
        )

    snapshot = _summarize(stalls, provider="Arlington ExactPark", source_url=ARLINGTON_URL)
    return cache.set(key, snapshot, ttl_seconds=60)


def _overpass_query(latitude: float, longitude: float, limit: int) -> str:
    radius_meters = 12000
    return (
        f"[out:json][timeout:12];"
        f"node[\"amenity\"=\"parking\"](around:{radius_meters},{latitude},{longitude});"
        f"out body {limit};"
    )


def _india_facilities_from_osm(elements: list[dict], location: dict, limit: int) -> list[dict]:
    facilities = []
    for element in elements[:limit]:
        tags = element.get("tags") or {}
        latitude = element.get("lat") or (element.get("center") or {}).get("lat")
        longitude = element.get("lon") or (element.get("center") or {}).get("lon")
        if latitude is None or longitude is None:
            continue

        parking_type = tags.get("parking", "parking")
        capacity = _capacity_from_tags(tags, parking_type, element["id"])
        available_slots = _estimated_available_slots(element["id"], capacity, parking_type)
        occupied_slots = max(capacity - available_slots, 0)
        availability_percent = round((available_slots / capacity) * 100, 1) if capacity else 0
        status = "vacant" if available_slots > 0 else "occupied"
        name = tags.get("name") or _parking_name(location["name"], parking_type, len(facilities) + 1)
        block = tags.get("addr:street") or tags.get("operator") or tags.get("access") or location["name"]

        facilities.append(
            {
                "id": f"{element.get('type', 'osm')}/{element['id']}",
                "name": name,
                "block": block,
                "status": status,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "rate": "Paid" if tags.get("fee") == "yes" else "Free/Unknown",
                "time_limit": tags.get("maxstay"),
                "parking_type": parking_type.replace("_", " ").title(),
                "capacity": capacity,
                "available_slots": available_slots,
                "occupied_slots": occupied_slots,
                "availability_percent": availability_percent,
                "fee": tags.get("fee", "unknown"),
                "access": tags.get("access", "public/unknown"),
                "source": "OpenStreetMap Overpass",
            }
        )
    return facilities


def _fallback_india_facilities(location: dict, limit: int) -> list[dict]:
    names = [
        "Metro Station Parking",
        "Bus Stand Parking",
        "Market Parking",
        "Mall Parking",
        "Railway Station Parking",
        "Public Parking Zone",
        "Multi Level Car Park",
        "Hospital Visitor Parking",
        "Commercial Street Parking",
        "Civic Centre Parking",
    ]
    facilities = []
    count = max(40, min(limit, 120))
    for index in range(count):
        ring = 0.018 + (index % 9) * 0.006
        direction = ((index * 47) % 360) / 57.2958
        latitude = location["latitude"] + ring * _sin(direction)
        longitude = location["longitude"] + ring * _cos(direction)
        parking_type = "multi-storey" if index % 5 == 0 else "surface"
        capacity = 40 + (_stable_number(f"{location['name']}:{index}", 180))
        available_slots = _estimated_available_slots(index, capacity, parking_type)
        facilities.append(
            {
                "id": f"demo/{location['name']}/{index}",
                "name": f"{location['name']} {names[index % len(names)]}",
                "block": location["name"],
                "status": "vacant" if available_slots > 0 else "occupied",
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "rate": "Unknown",
                "time_limit": None,
                "parking_type": parking_type.replace("_", " ").title(),
                "capacity": capacity,
                "available_slots": available_slots,
                "occupied_slots": capacity - available_slots,
                "availability_percent": round((available_slots / capacity) * 100, 1),
                "fee": "unknown",
                "access": "public/unknown",
                "source": "Generated India demo parking points",
            }
        )
    return facilities


def _capacity_from_tags(tags: dict, parking_type: str, fallback_id: int) -> int:
    tagged_capacity = _first_int(tags.get("capacity") or tags.get("capacity:car") or "")
    if tagged_capacity:
        return max(1, min(tagged_capacity, 2000))

    base_ranges = {
        "multi-storey": (120, 520),
        "underground": (90, 320),
        "surface": (24, 160),
        "street_side": (8, 48),
        "lane": (8, 42),
        "rooftop": (35, 140),
    }
    low, high = base_ranges.get(parking_type, (20, 130))
    return low + _stable_number(str(fallback_id), high - low)


def _estimated_available_slots(identifier: int | str, capacity: int, parking_type: str) -> int:
    hour = datetime.now().hour
    seed = _stable_number(f"{identifier}:{hour}:{parking_type}", 100)
    busy_pressure = 18 if 8 <= hour <= 11 or 17 <= hour <= 21 else 0
    demand = min(98, seed + busy_pressure)
    if demand > 88:
        return 0
    availability_ratio = max(0.04, (100 - demand) / 100)
    return int(round(capacity * availability_ratio))


def _parking_name(city: str, parking_type: str, number: int) -> str:
    readable_type = parking_type.replace("_", " ").title()
    return f"{city} {readable_type} Parking {number}"


def _first_int(value: str) -> int | None:
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def _stable_number(value: str, modulo: int) -> int:
    return int(sha256(value.encode("utf-8")).hexdigest()[:8], 16) % max(modulo, 1)


def _sin(value: float) -> float:
    # Small local approximation is enough for placing fallback map points.
    from math import sin

    return sin(value)


def _cos(value: float) -> float:
    from math import cos

    return cos(value)


def _socrata_headers() -> dict[str, str]:
    settings = get_settings()
    headers = {"Accept": "application/json"}
    if settings.soda_app_token:
        headers["X-App-Token"] = settings.soda_app_token
    return headers


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _soql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _normalize_status(status: str) -> str:
    value = status.lower()
    if value in {"vacant", "available", "open"}:
        return "vacant"
    if value in {"occupied", "unavailable", "closed"}:
        return "occupied"
    return "unknown"


def _summarize(stalls: list[dict], provider: str, source_url: str) -> dict:
    counts = Counter(stall["status"] for stall in stalls)
    has_slot_data = any("capacity" in stall for stall in stalls)
    if has_slot_data:
        total = sum(int(stall.get("capacity") or 0) for stall in stalls)
        vacant = sum(int(stall.get("available_slots") or 0) for stall in stalls)
        occupied = sum(int(stall.get("occupied_slots") or 0) for stall in stalls)
    else:
        total = len(stalls)
        vacant = counts.get("vacant", 0)
        occupied = counts.get("occupied", 0)
    occupancy_rate = round((occupied / total) * 100, 1) if total else 0
    availability_rate = round((vacant / total) * 100, 1) if total else 0
    return {
        "provider": provider,
        "source_url": source_url,
        "total_facilities": len(stalls),
        "total_spaces": total,
        "vacant_spaces": vacant,
        "occupied_spaces": occupied,
        "unknown_spaces": counts.get("unknown", 0),
        "occupancy_rate": occupancy_rate,
        "availability_rate": availability_rate,
        "stalls": stalls,
        "recommendation": _parking_recommendation(availability_rate),
    }


def _parking_recommendation(availability_rate: float) -> str:
    if availability_rate < 12:
        return "High demand detected. Raise driver guidance priority and route vehicles to overflow zones."
    if availability_rate < 28:
        return "Parking is tightening. Highlight streets with available stalls and watch turnover."
    return "Availability is healthy. Maintain standard guidance."
