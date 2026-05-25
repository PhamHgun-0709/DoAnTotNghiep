from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReportsResponse(BaseModel):
    summary: dict[str, Any] = Field(default_factory=dict)
    quality_distribution: dict[str, Any] = Field(default_factory=dict)
    recommendation_count: int = 0
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    recommendation_plan: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"
