from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.cache import cache
from app.services.geo import geocode_city


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


WEATHER_CODES = {
    0: "Clear",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Light showers",
    81: "Showers",
    82: "Heavy showers",
    95: "Thunderstorm",
}


async def current_weather(city: str) -> dict:
    location = await geocode_city(city)
    key = f"weather:{location['latitude']}:{location['longitude']}"
    cached = cache.get(key)
    if cached:
        return cached

    settings = get_settings()
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "hourly": "precipitation_probability,temperature_2m",
        "forecast_days": 1,
        "timezone": location.get("timezone", "auto"),
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(OPEN_METEO_FORECAST_URL, params=params)
        response.raise_for_status()
    payload = response.json()
    current = payload.get("current", {})
    code = int(current.get("weather_code", 0))

    weather = {
        "location": location,
        "observed_at": current.get("time"),
        "temperature_c": current.get("temperature_2m"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "precipitation_mm": current.get("precipitation", 0),
        "wind_speed_kmh": current.get("wind_speed_10m", 0),
        "condition": WEATHER_CODES.get(code, "Unknown"),
        "weather_code": code,
        "hourly": payload.get("hourly", {}),
        "source": "Open-Meteo",
    }
    return cache.set(key, weather, ttl_seconds=60 * 10)
