from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str


class DashboardQuery(BaseModel):
    city: str = Field(default="Bengaluru", min_length=2)
    parking_provider: str = "india"
    parking_city: str = Field(default="Bengaluru", min_length=2)
    parking_limit: int = Field(default=180, ge=25, le=2000)
