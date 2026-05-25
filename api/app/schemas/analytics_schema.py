from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SummaryResponse(BaseModel):
    total_ads: int
    total_spent: float
    total_impressions: float
    total_conversions: float
    avg_ctr: float
    avg_cvr: float
    avg_cpc: float
    avg_cpm: float
    avg_cpa: float
    quality_distribution: dict[str, int] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class AnalyticsResponse(BaseModel):
    count: int
    metrics: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class AnalyticsOverviewResponse(BaseModel):
    count: int
    total_spent: float
    total_impressions: int
    total_conversions: float
    total_revenue: float
    metrics: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class HighROICampaignsResponse(BaseModel):
    total: int
    campaigns: list[dict[str, Any]] = Field(default_factory=list)

    class Config:
        extra = "allow"


class RetrainResponse(BaseModel):
    classifier: dict[str, Any] = Field(default_factory=dict)
    predictor: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"
