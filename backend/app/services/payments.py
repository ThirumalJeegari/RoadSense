from __future__ import annotations

import httpx

from app.core.config import get_settings


RAZORPAY_SUBSCRIPTIONS_URL = "https://api.razorpay.com/v1/subscriptions"

PRIME_FEATURES = [
    "Live traffic route intelligence",
    "Expanded smart parking points",
    "Road damage map survey data",
    "Operations-ready city dashboard",
]


def prime_plan_status() -> dict:
    settings = get_settings()
    configured = bool(
        settings.razorpay_key_id
        and settings.razorpay_key_secret
        and settings.razorpay_prime_plan_id
    )
    return {
        "plan": "RoadSense Prime",
        "provider": "Razorpay",
        "configured": configured,
        "plan_id_set": bool(settings.razorpay_prime_plan_id),
        "total_count": settings.razorpay_prime_total_count,
        "features": PRIME_FEATURES,
    }


async def create_prime_subscription(customer: dict | None = None) -> dict:
    settings = get_settings()
    status = prime_plan_status()
    customer = customer or {}

    if not status["configured"]:
        return {
            **status,
            "mode": "demo",
            "payment_status": "not_configured",
            "message": "Add Razorpay key id, key secret, and Prime plan id to create a live subscription link.",
        }

    payload = {
        "plan_id": settings.razorpay_prime_plan_id,
        "total_count": settings.razorpay_prime_total_count,
        "quantity": 1,
        "customer_notify": True,
        "notes": {
            "product": "RoadSense Prime",
            "customer_name": str(customer.get("name", ""))[:120],
            "customer_email": str(customer.get("email", ""))[:120],
        },
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(
            RAZORPAY_SUBSCRIPTIONS_URL,
            json=payload,
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise RuntimeError(f"Razorpay subscription error: {detail}") from exc

    subscription = response.json()
    return {
        **status,
        "mode": "live",
        "payment_status": subscription.get("status"),
        "subscription_id": subscription.get("id"),
        "short_url": subscription.get("short_url"),
    }


async def fetch_prime_subscription(subscription_id: str) -> dict:
    settings = get_settings()
    status = prime_plan_status()
    subscription_id = str(subscription_id or "").strip()

    if not subscription_id:
        raise ValueError("No Razorpay subscription id found for this account.")

    if not status["configured"]:
        return {
            **status,
            "mode": "demo",
            "payment_status": "not_configured",
            "subscription_id": subscription_id,
            "message": "Add Razorpay key id, key secret, and Prime plan id to verify live payments.",
        }

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(
            f"{RAZORPAY_SUBSCRIPTIONS_URL}/{subscription_id}",
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise RuntimeError(f"Razorpay subscription status error: {detail}") from exc

    subscription = response.json()
    return {
        **status,
        "mode": "live",
        "payment_status": subscription.get("status"),
        "subscription_id": subscription.get("id") or subscription_id,
        "short_url": subscription.get("short_url"),
        "current_start": subscription.get("current_start"),
        "current_end": subscription.get("current_end"),
        "paid_count": subscription.get("paid_count"),
        "remaining_count": subscription.get("remaining_count"),
    }
