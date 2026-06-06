from __future__ import annotations

import asyncio

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.schemas import HealthResponse
from app.services.india_locations import list_india_locations
from app.services.parking import parking_snapshot
from app.services.road_damage import analyze_road_image
from app.services.traffic import traffic_route, traffic_snapshot
from app.services.weather import current_weather


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Smart Cities API for traffic management, parking intelligence, and road damage detection.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs", "health": f"{settings.api_prefix}/health"}


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=settings.app_name)


@app.get(f"{settings.api_prefix}/weather")
async def weather(city: str = Query("Bengaluru", min_length=2)) -> dict:
    try:
        return await current_weather(city)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/traffic")
async def traffic(city: str = Query("Bengaluru", min_length=2)) -> dict:
    try:
        return await traffic_snapshot(city)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/india-locations")
async def india_locations() -> dict:
    return {"locations": list_india_locations()}


@app.get(f"{settings.api_prefix}/traffic-route")
async def route_traffic(
    start: str = Query("Chennai", min_length=2),
    end: str = Query("Bengaluru", min_length=2),
) -> dict:
    if start.strip().lower() == end.strip().lower():
        raise HTTPException(status_code=400, detail="Start and end locations must be different.")
    try:
        return await traffic_route(start=start, end=end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/parking")
async def parking(
    provider: str = Query("india", pattern="^(india|in|osm|openstreetmap|la|los-angeles|los angeles|arlington|arl)$"),
    city: str = Query("Bengaluru", min_length=2),
    limit: int = Query(180, ge=25, le=2000),
) -> dict:
    try:
        return await parking_snapshot(provider=provider, limit=limit, city=city)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/dashboard")
async def dashboard(
    city: str = Query("Bengaluru", min_length=2),
    parking_provider: str = Query("india"),
    parking_city: str = Query("Bengaluru", min_length=2),
    parking_limit: int = Query(180, ge=25, le=2000),
) -> dict:
    try:
        weather_data, traffic_data, parking_data = await asyncio.gather(
            current_weather(city),
            traffic_snapshot(city),
            parking_snapshot(provider=parking_provider, limit=parking_limit, city=parking_city),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "city": city,
        "weather": weather_data,
        "traffic": traffic_data,
        "parking": parking_data,
    }


@app.post(f"{settings.api_prefix}/road-damage/analyze")
async def road_damage(file: UploadFile = File(...)) -> dict:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload an image file.")
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        return analyze_road_image(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not analyze image: {exc}") from exc
