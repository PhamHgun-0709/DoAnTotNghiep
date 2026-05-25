from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DatasetMetadata(BaseModel):
    active_dataset: str
    file_name: str
    file_path: str
    uploaded_by: str
    uploaded_role: str
    scored_rows: int
    segment_rows: int
    updated_at: str

    class Config:
        extra = "allow"


class UploadResponse(BaseModel):
    message: str
    file_path: str
    active_dataset: DatasetMetadata
    dataset_history: list[DatasetMetadata] = Field(default_factory=list)

    class Config:
        extra = "allow"


class DashboardResponse(BaseModel):
    summary: dict[str, Any] = Field(default_factory=dict)
    total_records: int
    has_data: bool
    active_dataset: DatasetMetadata | None = None
    dataset_history: list[DatasetMetadata] = Field(default_factory=list)

    class Config:
        extra = "allow"
