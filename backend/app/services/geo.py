from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.cache import cache
from app.services.india_locations import find_india_location


OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


async def geocode_city(city: str) -> dict:
    key = f"geocode:{city.lower().strip()}"
    cached = cache.get(key)
    if cached:
        return cached

    settings = get_settings()
    params = {"name": city, "count": 1, "language": "en", "format": "json"}
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(OPEN_METEO_GEOCODE_URL, params=params)
        response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        raise ValueError(f"Could not geocode city: {city}")

    result = results[0]
    location = {
        "name": result.get("name", city),
        "country": result.get("country", ""),
        "admin1": result.get("admin1", ""),
        "latitude": float(result["latitude"]),
        "longitude": float(result["longitude"]),
        "timezone": result.get("timezone", "auto"),
    }
    return cache.set(key, location, ttl_seconds=60 * 60 * 24)


def bounding_box(latitude: float, longitude: float, radius_degrees: float = 0.08) -> str:
    min_lon = longitude - radius_degrees
    min_lat = latitude - radius_degrees
    max_lon = longitude + radius_degrees
    max_lat = latitude + radius_degrees
    return f"{min_lon:.6f},{min_lat:.6f},{max_lon:.6f},{max_lat:.6f}"


async def geocode_india_location(query: str) -> dict:
    builtin = find_india_location(query)
    if builtin:
        return {
            "name": builtin["name"],
            "country": "India",
            "admin1": builtin["state"],
            "latitude": float(builtin["latitude"]),
            "longitude": float(builtin["longitude"]),
            "timezone": "Asia/Kolkata",
            "source": "Built-in India location catalog",
        }

    key = f"india-geocode:{query.lower().strip()}"
    cached = cache.get(key)
    if cached:
        return cached

    settings = get_settings()
    params = {
        "q": f"{query}, India",
        "format": "json",
        "limit": 1,
        "countrycodes": "in",
        "addressdetails": 1,
    }
    headers = {"User-Agent": "SmartCitiesHackathon/1.0"}
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(NOMINATIM_SEARCH_URL, params=params, headers=headers)
        response.raise_for_status()
    results = response.json()
    if not results:
        raise ValueError(f"Could not find an Indian location for: {query}")

    result = results[0]
    address = result.get("address", {})
    location = {
        "name": result.get("name") or query,
        "display_name": result.get("display_name", query),
        "country": "India",
        "admin1": address.get("state") or address.get("region") or "",
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
        "timezone": "Asia/Kolkata",
        "source": "OpenStreetMap Nominatim",
    }
    return cache.set(key, location, ttl_seconds=60 * 60 * 24)
