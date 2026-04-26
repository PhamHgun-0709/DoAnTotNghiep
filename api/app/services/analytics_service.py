from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _safe_number(value: float | None) -> float:
    return value if value is not None else 0.0


def _is_valid_age_band(value: str) -> bool:
    parts = value.split("-")
    return len(parts) == 2 and all(part.isdigit() for part in parts)


def _is_valid_gender(value: str) -> bool:
    return value.upper() in {"M", "F"}


def filter_ads(
    records: list[dict[str, Any]],
    campaign_id: str | None = None,
    age: str | None = None,
    gender: str | None = None,
    quality_label: str | None = None,
    min_ctr: float | None = None,
    max_cpa: float | None = None,
) -> list[dict[str, Any]]:
    filtered = records

    if campaign_id:
        filtered = [r for r in filtered if str(r["campaign_id"]) == campaign_id]
    if age:
        filtered = [r for r in filtered if r["age"] == age]
    if gender:
        filtered = [r for r in filtered if str(r["gender"]).lower() == gender.lower()]
    if quality_label:
        filtered = [r for r in filtered if str(r["quality_label"]).lower() == quality_label.lower()]
    if min_ctr is not None:
        filtered = [r for r in filtered if _safe_number(r["ctr"]) >= min_ctr]
    if max_cpa is not None:
        filtered = [r for r in filtered if r["cpa"] is not None and _safe_number(r["cpa"]) <= max_cpa]

    return filtered


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(records)
    if count == 0:
        return {
            "total_ads": 0,
            "total_spent": 0.0,
            "total_approved_conversion": 0.0,
            "avg_ctr": 0.0,
            "avg_cvr": 0.0,
            "avg_cpc": 0.0,
            "avg_cpa": 0.0,
            "quality_distribution": {"good": 0, "average": 0, "bad": 0},
        }

    spent_sum = sum(_safe_number(r["spent"]) for r in records)
    approved_conversion_sum = sum(_safe_number(r["approved_conversion"]) for r in records)
    ctr_avg = sum(_safe_number(r["ctr"]) for r in records) / count
    cvr_avg = sum(_safe_number(r["cvr"]) for r in records) / count
    cpc_avg = sum(_safe_number(r["cpc"]) for r in records) / count

    cpa_values = [_safe_number(r["cpa"]) for r in records if r["cpa"] is not None]
    cpa_avg = sum(cpa_values) / len(cpa_values) if cpa_values else 0.0

    quality_counter = Counter(str(r["quality_label"]).lower() for r in records)

    return {
        "total_ads": count,
        "total_spent": round(spent_sum, 4),
        "total_approved_conversion": round(approved_conversion_sum, 4),
        "avg_ctr": round(ctr_avg, 6),
        "avg_cvr": round(cvr_avg, 6),
        "avg_cpc": round(cpc_avg, 6),
        "avg_cpa": round(cpa_avg, 6),
        "quality_distribution": {
            "good": quality_counter.get("good", 0),
            "average": quality_counter.get("average", 0),
            "bad": quality_counter.get("bad", 0),
        },
    }


def chart_quality_distribution(records: list[dict[str, Any]]) -> dict[str, Any]:
    counter = Counter(str(r["quality_label"]).lower() for r in records)
    labels = ["good", "average", "bad"]
    values = [counter.get(label, 0) for label in labels]
    return {"labels": labels, "values": values}


def chart_campaign_kpi(records: list[dict[str, Any]], group_by: str = "campaign_id", top_n: int | None = 12) -> dict[str, Any]:
    ctr_map: dict[str, list[float]] = defaultdict(list)
    cvr_map: dict[str, list[float]] = defaultdict(list)
    spent_map: dict[str, float] = defaultdict(float)

    for record in records:
        key = str(record.get(group_by, ""))
        ctr_map[key].append(_safe_number(record["ctr"]))
        cvr_map[key].append(_safe_number(record["cvr"]))
        spent_map[key] += _safe_number(record["spent"])

    grouped_rows = []
    for key in ctr_map.keys():
        grouped_rows.append(
            {
                "label": key,
                "ctr": round(sum(ctr_map[key]) / len(ctr_map[key]), 6),
                "cvr": round(sum(cvr_map[key]) / len(cvr_map[key]), 6),
                "spent": round(spent_map[key], 2),
            }
        )

    grouped_rows.sort(key=lambda item: item["spent"], reverse=True)
    if top_n is not None:
        grouped_rows = grouped_rows[:top_n]

    return {
        "labels": [row["label"] for row in grouped_rows],
        "ctr": [row["ctr"] for row in grouped_rows],
        "cvr": [row["cvr"] for row in grouped_rows],
        "spent": [row["spent"] for row in grouped_rows],
    }


def chart_kpi_by_age(records: list[dict[str, Any]]) -> dict[str, Any]:
    valid_records = [r for r in records if _is_valid_age_band(str(r.get("age", "")))]
    return chart_campaign_kpi(valid_records, group_by="age", top_n=None)


def chart_kpi_by_gender(records: list[dict[str, Any]]) -> dict[str, Any]:
    valid_records = [r for r in records if _is_valid_gender(str(r.get("gender", "")))]
    return chart_campaign_kpi(valid_records, group_by="gender", top_n=None)
