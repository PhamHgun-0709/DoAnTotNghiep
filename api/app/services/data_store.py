from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.dataset_manager import (
    append_dataset_history as _append_dataset_history,
    load_active_dataset as _load_active_dataset,
    load_dataset_history as _load_dataset_history,
    save_active_dataset as _save_active_dataset,
    deactivate_active_dataset as _deactivate_active_dataset,
    activate_dataset_by_id as _activate_dataset_by_id,
)
from app.services.upload_log_service import read_upload_logs_page


NUMERIC_FIELDS = {
    "impressions",
    "clicks",
    "conversions",
    "spend",
    "revenue",
    "ctr",
    "cpc",
    "cpm",
    "cvr",
    "cpa",
    "quality_score",
}

RECOMMENDATION_NUMERIC_FIELDS = {
    "ads_count",
    "total_spent",
    "total_conversions",
    "avg_ctr",
    "avg_cvr",
    "avg_cpa",
    "good_ratio",
    "conversion_per_spend",
    "recommendation_score",
    "recommended_weight",
}

RECOMMENDATION_STRING_FIELDS = {
    "segment_id",
    "campaign_id",
    "age_group",
    "suggested_action",
}

STRING_FIELDS = {
    "ad_id",
    "campaign_id",
    "date",
    "platform",
    "age_group",
    "quality_label",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _active_dataset_metadata_file() -> Path:
    return _project_root() / "data" / "metadata" / "current_dataset.json"


def _dataset_history_file() -> Path:
    return _project_root() / "data" / "metadata" / "dataset_history.json"


def _latest_spark_output_file() -> Path:
    output_dir = _project_root() / "data" / "processed" / "ad_quality"
    part_files = sorted(output_dir.glob("part-*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not part_files:
        raise FileNotFoundError(
            f"No Spark output found in {output_dir}. Run spark/jobs/ad_quality_job.py first."
        )
    return part_files[0]


def _latest_recommendation_output_file() -> Path:
    output_dir = _project_root() / "data" / "curated" / "budget_recommendations"
    part_files = sorted(output_dir.glob("part-*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not part_files:
        raise FileNotFoundError(
            f"No recommendation output found in {output_dir}. Run spark/jobs/budget_recommendation_job.py first."
        )
    return part_files[0]


def _to_float(value: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _require_uploaded_data() -> bool:
    return os.getenv("REQUIRE_UPLOAD_DATA", "false").strip().lower() in {"1", "true", "yes", "on"}


def _has_uploaded_data() -> bool:
    try:
        page = read_upload_logs_page(page=1, page_size=1)
        return int(page.get("total", 0)) > 0
    except Exception:
        return False


def _normalize_row(row: dict[str, str]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for key in STRING_FIELDS:
        normalized[key] = row.get(key, "")

    for key in NUMERIC_FIELDS:
        normalized[key] = _to_float(row.get(key, ""))

    if normalized["quality_score"] is not None:
        normalized["quality_score"] = int(normalized["quality_score"])

    return normalized


def _normalize_generic_row(
    row: dict[str, str], string_fields: set[str], numeric_fields: set[str], int_fields: set[str] | None = None
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    int_fields = int_fields or set()

    for key in string_fields:
        normalized[key] = row.get(key, "")

    for key in numeric_fields:
        normalized[key] = _to_float(row.get(key, ""))
        if key in int_fields and normalized[key] is not None:
            normalized[key] = int(normalized[key])

    return normalized


@lru_cache(maxsize=1)
def load_scored_ads() -> list[dict[str, Any]]:
    if _require_uploaded_data() and not _has_uploaded_data():
        return []

    data_file = _latest_spark_output_file()
    records: list[dict[str, Any]] = []

    with data_file.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            records.append(_normalize_row(row))

    return records


def reload_scored_ads() -> list[dict[str, Any]]:
    load_scored_ads.cache_clear()
    return load_scored_ads()


@lru_cache(maxsize=1)
def load_budget_recommendations() -> list[dict[str, Any]]:
    if _require_uploaded_data() and not _has_uploaded_data():
        return []

    data_file = _latest_recommendation_output_file()
    records: list[dict[str, Any]] = []

    with data_file.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            records.append(
                _normalize_generic_row(
                    row,
                    string_fields=RECOMMENDATION_STRING_FIELDS,
                    numeric_fields=RECOMMENDATION_NUMERIC_FIELDS,
                    int_fields={"ads_count"},
                )
            )

    return records


def reload_budget_recommendations() -> list[dict[str, Any]]:
    load_budget_recommendations.cache_clear()
    return load_budget_recommendations()


def read_active_dataset_metadata() -> dict[str, Any] | None:
    return _load_active_dataset()


def write_active_dataset_metadata(
    *,
    file_name: str,
    file_path: str,
    uploaded_by: str,
    uploaded_role: str,
    scored_rows: int,
    segment_rows: int,
) -> dict[str, Any]:
    return _save_active_dataset(
        file_name=file_name,
        file_path=file_path,
        uploaded_by=uploaded_by,
        uploaded_role=uploaded_role,
        scored_rows=scored_rows,
        segment_rows=segment_rows,
    )


def read_dataset_history(limit: int = 10) -> list[dict[str, Any]]:
    return _load_dataset_history(limit=limit)


def append_dataset_history(entry: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    return _append_dataset_history(entry, limit=limit)


def deactivate_active_dataset() -> dict[str, Any] | None:
    return _deactivate_active_dataset()


def activate_dataset_by_id(dataset_id: int) -> dict[str, Any] | None:
    return _activate_dataset_by_id(int(dataset_id))
