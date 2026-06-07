from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "RoadSense Operations Hub API"
    api_prefix: str = "/api"
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    tomtom_api_key: str = os.getenv("TOMTOM_API_KEY", "")
    soda_app_token: str = os.getenv("SODA_APP_TOKEN", "")
    razorpay_key_id: str = os.getenv("RAZORPAY_KEY_ID", "")
    razorpay_key_secret: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    razorpay_prime_plan_id: str = os.getenv("RAZORPAY_PRIME_PLAN_ID", "")
    razorpay_prime_total_count: int = int(os.getenv("RAZORPAY_PRIME_TOTAL_COUNT", "12"))
    auth_token_secret: str = os.getenv("AUTH_TOKEN_SECRET", "roadsense-dev-secret-change-me")
    auth_token_ttl_seconds: int = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "86400"))
    password_hash_secret: str = os.getenv("PASSWORD_HASH_SECRET", "roadsense-password-hash-secret-change-me")
    password_reset_code_ttl_seconds: int = int(os.getenv("PASSWORD_RESET_CODE_TTL_SECONDS", "900"))
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./roadsense.db")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "BACKEND_CORS_ORIGINS",
            "http://localhost:8501,http://127.0.0.1:8501",
        ).split(",")
        if origin.strip()
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
