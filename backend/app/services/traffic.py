from __future__ import annotations

import asyncio
from collections import Counter
from hashlib import sha256
from math import ceil

import httpx

from app.core.config import get_settings
from app.services.cache import cache
from app.services.geo import bounding_box, geocode_city, geocode_india_location
from app.services.weather import current_weather


TOMTOM_INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"
TOMTOM_FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
TOMTOM_ROUTE_URL = "https://api.tomtom.com/routing/1/calculateRoute/{locations}/json"
OSRM_ROUTE_URL = "https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"

TRAFFIC_COLORS = {
    "normal": [37, 99, 235, 180],
    "moderate": [245, 158, 11, 230],
    "heavy": [220, 38, 38, 240],
}


def _fallback_score(weather: dict) -> int:
    precipitation = float(weather.get("precipitation_mm") or 0)
    wind = float(weather.get("wind_speed_kmh") or 0)
    humidity = float(weather.get("humidity_percent") or 0)
    score = 42 + min(22, precipitation * 9) + min(16, wind / 3) + (8 if humidity > 85 else 0)
    return int(min(95, max(15, score)))


async def traffic_route(start: str, end: str) -> dict:
    start_location, end_location = await asyncio.gather(
        geocode_india_location(start),
        geocode_india_location(end),
    )
    settings = get_settings()
    key = (
        "traffic-route:"
        f"{start_location['latitude']}:{start_location['longitude']}:"
        f"{end_location['latitude']}:{end_location['longitude']}:{bool(settings.tomtom_api_key)}"
    )
    cached = cache.get(key)
    if cached:
        return cached

    mode = "Current Route"
    source = "OSRM route geometry with demo traffic coloring"
    route_points: list[dict] = []
    summary: dict = {}
    flow_samples: list[dict] = []

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        if settings.tomtom_api_key:
            try:
                route_points, summary = await _tomtom_route(client, start_location, end_location, settings.tomtom_api_key)
                flow_samples = await _traffic_flow_samples(client, route_points, settings.tomtom_api_key)
                mode = "live"
                source = "TomTom Routing API + TomTom Traffic Flow samples"
            except httpx.HTTPError:
                route_points = []

        if not route_points:
            route_points, summary = await _osrm_route(client, start_location, end_location)

    display_points = _downsample_points(route_points, max_points=320)
    if flow_samples:
        route_segments = _segments_from_flow(display_points, flow_samples)
    else:
        route_segments = _demo_route_segments(display_points, start_location["name"], end_location["name"])

    counts = Counter(segment["status"] for segment in route_segments)
    congestion_score = _route_congestion_score(counts, max(len(route_segments), 1))
    summary.setdefault("traffic_delay_seconds", 0)
    result = {
        "mode": mode,
        "source": source,
        "start": start_location,
        "end": end_location,
        "route_points": display_points,
        "route_segments": route_segments,
        "summary": {
            "distance_km": round(float(summary.get("distance_meters", 0)) / 1000, 1),
            "travel_time_min": round(float(summary.get("travel_time_seconds", 0)) / 60, 1),
            "traffic_delay_min": round(float(summary.get("traffic_delay_seconds", 0)) / 60, 1),
            "normal_segments": counts.get("normal", 0),
            "moderate_segments": counts.get("moderate", 0),
            "heavy_segments": counts.get("heavy", 0),
            "congestion_score": congestion_score,
        },
        "recommendation": _route_recommendation(counts.get("heavy", 0), counts.get("moderate", 0), congestion_score),
    }
    return cache.set(key, result, ttl_seconds=60 if settings.tomtom_api_key else 60 * 10)


async def traffic_snapshot(city: str) -> dict:
    location = await geocode_city(city)
    weather = await current_weather(city)
    settings = get_settings()
    key = f"traffic:{city.lower().strip()}:{bool(settings.tomtom_api_key)}"
    cached = cache.get(key)
    if cached:
        return cached

    if not settings.tomtom_api_key:
        score = _fallback_score(weather)
        snapshot = {
            "source": "Fallback model using live weather context",
            "mode": "fallback",
            "location": location,
            "congestion_score": score,
            "current_speed_kmh": None,
            "free_flow_speed_kmh": None,
            "delay_seconds": None,
            "road_closure": False,
            "incidents": [],
            "incident_count": 0,
            "top_incident_types": [],
            "recommendation": _recommendation(score, 0),
        }
        return cache.set(key, snapshot, ttl_seconds=60 * 5)

    incidents: list[dict] = []
    flow_data: dict = {}
    bbox = bounding_box(location["latitude"], location["longitude"], radius_degrees=0.09)
    fields = (
        "{incidents{type,geometry{type,coordinates},properties{"
        "id,iconCategory,magnitudeOfDelay,events{description,code,iconCategory},"
        "startTime,endTime,from,to,length,delay,roadNumbers,timeValidity,"
        "probabilityOfOccurrence,numberOfReports,lastReportTime}}}"
    )
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        try:
            incident_response = await client.get(
                TOMTOM_INCIDENTS_URL,
                params={
                    "key": settings.tomtom_api_key,
                    "bbox": bbox,
                    "fields": fields,
                    "language": "en-US",
                    "timeValidityFilter": "present",
                },
                headers=headers,
            )
            incident_response.raise_for_status()
            incidents = _normalize_incidents(incident_response.json().get("incidents", []))
        except httpx.HTTPError:
            incidents = []

        try:
            flow_response = await client.get(
                TOMTOM_FLOW_URL,
                params={
                    "key": settings.tomtom_api_key,
                    "point": f"{location['latitude']},{location['longitude']}",
                    "unit": "KMPH",
                },
                headers=headers,
            )
            flow_response.raise_for_status()
            flow_data = flow_response.json().get("flowSegmentData", {})
        except httpx.HTTPError:
            flow_data = {}

    current_speed = flow_data.get("currentSpeed")
    free_flow_speed = flow_data.get("freeFlowSpeed")
    if current_speed and free_flow_speed:
        congestion_score = int(max(0, min(100, 100 - (float(current_speed) / float(free_flow_speed) * 100))))
    else:
        congestion_score = _fallback_score(weather)

    incident_types = Counter(item.get("category", "Other") for item in incidents)
    snapshot = {
        "source": "TomTom Traffic API",
        "mode": "live",
        "location": location,
        "congestion_score": congestion_score,
        "current_speed_kmh": current_speed,
        "free_flow_speed_kmh": free_flow_speed,
        "delay_seconds": flow_data.get("currentTravelTime", 0) - flow_data.get("freeFlowTravelTime", 0)
        if flow_data.get("currentTravelTime") and flow_data.get("freeFlowTravelTime")
        else None,
        "road_closure": bool(flow_data.get("roadClosure", False)),
        "incidents": incidents,
        "incident_count": len(incidents),
        "top_incident_types": [{"type": item, "count": count} for item, count in incident_types.most_common(5)],
        "recommendation": _recommendation(congestion_score, len(incidents)),
    }
    return cache.set(key, snapshot, ttl_seconds=60)


def _normalize_incidents(features: list[dict]) -> list[dict]:
    normalized = []
    for feature in features[:80]:
        properties = feature.get("properties") or {}
        event = (properties.get("events") or [{}])[0]
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates")
        latitude = None
        longitude = None
        if geometry.get("type") == "Point" and isinstance(coordinates, list) and len(coordinates) >= 2:
            longitude, latitude = coordinates[:2]
        elif geometry.get("type") == "LineString" and coordinates:
            first = coordinates[0]
            if isinstance(first, list) and len(first) >= 2:
                longitude, latitude = first[:2]

        normalized.append(
            {
                "id": properties.get("id"),
                "category": event.get("description") or f"Category {properties.get('iconCategory', 'Unknown')}",
                "delay_seconds": properties.get("delay"),
                "magnitude": properties.get("magnitudeOfDelay"),
                "from": properties.get("from"),
                "to": properties.get("to"),
                "road_numbers": properties.get("roadNumbers") or [],
                "latitude": latitude,
                "longitude": longitude,
                "last_report_time": properties.get("lastReportTime"),
            }
        )
    return normalized


def _recommendation(congestion_score: int, incident_count: int) -> str:
    if congestion_score >= 75 or incident_count >= 8:
        return "Activate incident response, suggest alternate corridors, and prioritize signal timing on parallel routes."
    if congestion_score >= 50 or incident_count >= 3:
        return "Monitor corridors closely and publish driver guidance for expected delays."
    return "Traffic is operating within normal range. Keep monitoring live feeds."


async def _tomtom_route(
    client: httpx.AsyncClient,
    start_location: dict,
    end_location: dict,
    api_key: str,
) -> tuple[list[dict], dict]:
    locations = (
        f"{start_location['latitude']},{start_location['longitude']}:"
        f"{end_location['latitude']},{end_location['longitude']}"
    )
    response = await client.get(
        TOMTOM_ROUTE_URL.format(locations=locations),
        params={
            "key": api_key,
            "traffic": "true",
            "travelMode": "car",
            "routeRepresentation": "polyline",
            "computeTravelTimeFor": "all",
            "sectionType": "traffic",
        },
    )
    response.raise_for_status()
    payload = response.json()
    route = payload["routes"][0]
    points = []
    for leg in route.get("legs", []):
        for point in leg.get("points", []):
            points.append({"latitude": float(point["latitude"]), "longitude": float(point["longitude"])})
    summary = route.get("summary", {})
    return points, {
        "distance_meters": summary.get("lengthInMeters", 0),
        "travel_time_seconds": summary.get("travelTimeInSeconds", 0),
        "traffic_delay_seconds": summary.get("trafficDelayInSeconds", 0),
    }


async def _osrm_route(
    client: httpx.AsyncClient,
    start_location: dict,
    end_location: dict,
) -> tuple[list[dict], dict]:
    response = await client.get(
        OSRM_ROUTE_URL.format(
            start_lon=start_location["longitude"],
            start_lat=start_location["latitude"],
            end_lon=end_location["longitude"],
            end_lat=end_location["latitude"],
        ),
        params={"overview": "full", "geometries": "geojson", "steps": "false"},
    )
    response.raise_for_status()
    payload = response.json()
    route = payload["routes"][0]
    coordinates = route.get("geometry", {}).get("coordinates", [])
    points = [{"latitude": float(lat), "longitude": float(lon)} for lon, lat in coordinates]
    return points, {
        "distance_meters": route.get("distance", 0),
        "travel_time_seconds": route.get("duration", 0),
        "traffic_delay_seconds": 0,
    }


async def _traffic_flow_samples(client: httpx.AsyncClient, route_points: list[dict], api_key: str) -> list[dict]:
    indexes = _even_indexes(len(route_points), max_samples=18)
    tasks = [_traffic_flow_sample(client, route_points[index], index, api_key) for index in indexes]
    samples = await asyncio.gather(*tasks, return_exceptions=True)
    return [sample for sample in samples if isinstance(sample, dict)]


async def _traffic_flow_sample(
    client: httpx.AsyncClient,
    point: dict,
    source_index: int,
    api_key: str,
) -> dict:
    response = await client.get(
        TOMTOM_FLOW_URL,
        params={
            "key": api_key,
            "point": f"{point['latitude']},{point['longitude']}",
            "unit": "KMPH",
        },
    )
    response.raise_for_status()
    flow = response.json().get("flowSegmentData", {})
    current_speed = flow.get("currentSpeed")
    free_flow_speed = flow.get("freeFlowSpeed")
    if not current_speed or not free_flow_speed:
        status = "normal"
        ratio = None
    else:
        ratio = max(0.0, min(1.2, float(current_speed) / max(float(free_flow_speed), 1.0)))
        status = _status_from_speed_ratio(ratio)
    return {
        "source_index": source_index,
        "status": status,
        "ratio": ratio,
        "current_speed_kmh": current_speed,
        "free_flow_speed_kmh": free_flow_speed,
    }


def _status_from_speed_ratio(ratio: float) -> str:
    if ratio <= 0.45:
        return "heavy"
    if ratio <= 0.75:
        return "moderate"
    return "normal"


def _downsample_points(route_points: list[dict], max_points: int) -> list[dict]:
    if len(route_points) <= max_points:
        return [
            {"latitude": point["latitude"], "longitude": point["longitude"], "source_index": index}
            for index, point in enumerate(route_points)
        ]
    step = ceil(len(route_points) / max_points)
    sampled = [
        {"latitude": point["latitude"], "longitude": point["longitude"], "source_index": index}
        for index, point in enumerate(route_points)
        if index % step == 0
    ]
    last = route_points[-1]
    if sampled[-1]["source_index"] != len(route_points) - 1:
        sampled.append({"latitude": last["latitude"], "longitude": last["longitude"], "source_index": len(route_points) - 1})
    return sampled


def _even_indexes(length: int, max_samples: int) -> list[int]:
    if length <= 0:
        return []
    if length <= max_samples:
        return list(range(length))
    return sorted({round(index * (length - 1) / (max_samples - 1)) for index in range(max_samples)})


def _segments_from_flow(display_points: list[dict], flow_samples: list[dict]) -> list[dict]:
    return [
        _route_segment(display_points[index], display_points[index + 1], _nearest_flow_status(display_points[index], flow_samples))
        for index in range(len(display_points) - 1)
    ]


def _nearest_flow_status(point: dict, flow_samples: list[dict]) -> dict:
    return min(flow_samples, key=lambda sample: abs(sample["source_index"] - point["source_index"]))


def _demo_route_segments(display_points: list[dict], start_name: str, end_name: str) -> list[dict]:
    seed = int(sha256(f"{start_name}:{end_name}".encode("utf-8")).hexdigest()[:8], 16)
    total = max(len(display_points) - 1, 1)
    segments = []
    for index in range(len(display_points) - 1):
        progress = index / total
        city_pressure = 24 if progress < 0.16 or progress > 0.84 else 0
        pattern = ((index * 37) + seed) % 100
        score = pattern + city_pressure
        if score >= 105:
            status = "heavy"
        elif score >= 82:
            status = "moderate"
        else:
            status = "normal"
        segments.append(_route_segment(display_points[index], display_points[index + 1], {"status": status}))
    return segments


def _route_segment(start: dict, end: dict, traffic: dict) -> dict:
    status = traffic.get("status", "normal")
    current_speed = traffic.get("current_speed_kmh")
    free_flow_speed = traffic.get("free_flow_speed_kmh")
    speed_note = ""
    if current_speed and free_flow_speed:
        speed_note = f"{current_speed} km/h now, {free_flow_speed} km/h free flow"
    label = {"normal": "Normal traffic", "moderate": "Moderate traffic", "heavy": "Heavy traffic"}[status]
    return {
        "path": [[start["longitude"], start["latitude"]], [end["longitude"], end["latitude"]]],
        "from_latitude": start["latitude"],
        "from_longitude": start["longitude"],
        "to_latitude": end["latitude"],
        "to_longitude": end["longitude"],
        "status": status,
        "status_label": label,
        "color": TRAFFIC_COLORS[status],
        "current_speed_kmh": current_speed,
        "free_flow_speed_kmh": free_flow_speed,
        "tooltip": f"{label} {speed_note}".strip(),
    }


def _route_congestion_score(counts: Counter, total_segments: int) -> int:
    weighted = counts.get("moderate", 0) * 45 + counts.get("heavy", 0) * 100
    return int(round(weighted / total_segments))


def _route_recommendation(heavy_segments: int, moderate_segments: int, congestion_score: int) -> str:
    if heavy_segments:
        return "Heavy traffic is present on the route. Prioritize diversions around red sections and update driver guidance."
    if moderate_segments or congestion_score >= 35:
        return "Moderate traffic is present. Watch the yellow sections and keep alternate routes ready."
    return "The selected route is mostly clear. Continue live monitoring."
