from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import Body, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.schemas import HealthResponse
from app.services.auth import (
    activate_prime_user,
    login_user,
    request_password_reset,
    reset_password_user,
    signup_user,
    update_profile_user,
    update_prime_subscription_user,
    user_from_authorization,
)
from app.services.database import init_db
from app.services.geo import search_india_locations
from app.services.india_locations import list_india_locations
from app.services.parking import parking_snapshot
from app.services.payments import create_prime_subscription, fetch_prime_subscription, prime_plan_status
from app.services.road_damage import analyze_road_image
from app.services.traffic import traffic_route, traffic_snapshot
from app.services.weather import current_weather


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="RoadSense API for traffic management, parking intelligence, and road damage detection.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    init_db()


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs", "health": f"{settings.api_prefix}/health"}


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=settings.app_name)


@app.post(f"{settings.api_prefix}/auth/login")
async def login(payload: Optional[dict] = Body(default=None)) -> dict:
    try:
        return login_user(payload or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(f"{settings.api_prefix}/auth/signup")
async def signup(payload: Optional[dict] = Body(default=None)) -> dict:
    try:
        return signup_user(payload or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(f"{settings.api_prefix}/auth/forgot-password")
async def forgot_password(payload: Optional[dict] = Body(default=None)) -> dict:
    try:
        return request_password_reset(payload or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not send reset email: {exc}") from exc


@app.post(f"{settings.api_prefix}/auth/reset-password")
async def reset_password(payload: Optional[dict] = Body(default=None)) -> dict:
    try:
        return reset_password_user(payload or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/auth/me")
async def me(authorization: Optional[str] = Header(default=None)) -> dict:
    try:
        return {"user": user_from_authorization(authorization)}
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.put(f"{settings.api_prefix}/auth/profile")
async def update_profile(
    payload: Optional[dict] = Body(default=None),
    authorization: Optional[str] = Header(default=None),
) -> dict:
    try:
        return update_profile_user(authorization, payload or {})
    except ValueError as exc:
        message = str(exc)
        status_code = 401 if "token" in message.lower() or "login" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@app.post(f"{settings.api_prefix}/auth/logout")
async def logout() -> dict:
    return {"status": "logged_out"}


@app.get(f"{settings.api_prefix}/subscriptions/prime")
async def prime_subscription_status() -> dict:
    return prime_plan_status()


@app.post(f"{settings.api_prefix}/subscriptions/prime")
async def prime_subscription(
    payload: Optional[dict] = Body(default=None),
    authorization: Optional[str] = Header(default=None),
) -> dict:
    try:
        customer = payload or {}
        if authorization:
            user = user_from_authorization(authorization)
            customer = {
                **customer,
                "name": customer.get("name") or user.get("name"),
                "email": customer.get("email") or user.get("email"),
                "account_email": user.get("email"),
            }
        result = await create_prime_subscription(customer)
        if authorization and result.get("subscription_id"):
            auth_result = update_prime_subscription_user(authorization, result)
            return {**result, **auth_result}
        return result
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post(f"{settings.api_prefix}/subscriptions/prime/sync")
async def sync_prime_subscription(
    payload: Optional[dict] = Body(default=None),
    authorization: Optional[str] = Header(default=None),
) -> dict:
    try:
        user = user_from_authorization(authorization)
        body = payload or {}
        subscription_id = str(
            body.get("subscription_id") or user.get("subscription_id") or "",
        ).strip()
        if not subscription_id:
            raise ValueError("No Razorpay subscription found for this account. Create the Prime checkout link first.")

        result = await fetch_prime_subscription(subscription_id)
        auth_result = update_prime_subscription_user(authorization, result)
        return {**result, **auth_result}
    except ValueError as exc:
        message = str(exc)
        status_code = 401 if "token" in message.lower() or "login" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post(f"{settings.api_prefix}/subscriptions/prime/activate-demo")
async def activate_prime_demo(authorization: Optional[str] = Header(default=None)) -> dict:
    try:
        return activate_prime_user(
            authorization,
            {
                "mode": "demo",
                "subscription_id": "demo_prime_subscription",
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


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


@app.get(f"{settings.api_prefix}/location-search")
async def location_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(8, ge=1, le=12),
) -> dict:
    try:
        return {"locations": await search_india_locations(q, limit=limit)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


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
