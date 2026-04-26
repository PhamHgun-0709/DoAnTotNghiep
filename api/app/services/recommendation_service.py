from __future__ import annotations

from typing import Any


def filter_segments(
    records: list[dict[str, Any]],
    campaign_id: str | None = None,
    age: str | None = None,
    gender: str | None = None,
    suggested_action: str | None = None,
) -> list[dict[str, Any]]:
    filtered = records

    if campaign_id:
        filtered = [r for r in filtered if str(r.get("campaign_id", "")) == campaign_id]
    if age:
        filtered = [r for r in filtered if str(r.get("age", "")) == age]
    if gender:
        filtered = [r for r in filtered if str(r.get("gender", "")).lower() == gender.lower()]
    if suggested_action:
        filtered = [r for r in filtered if str(r.get("suggested_action", "")).lower() == suggested_action.lower()]

    return filtered


def budget_plan(records: list[dict[str, Any]], total_budget: float, top_n: int = 10) -> dict[str, Any]:
    ranked = sorted(records, key=lambda r: float(r.get("recommendation_score") or 0), reverse=True)
    picked = ranked[:top_n]

    weight_sum = sum(float(r.get("recommended_weight") or 0) for r in picked)

    allocations = []
    for row in picked:
        weight = float(row.get("recommended_weight") or 0)
        score = float(row.get("recommendation_score") or 0)
        avg_cpa = row.get("avg_cpa")

        normalized_weight = (weight / weight_sum) if weight_sum > 0 else (1.0 / max(len(picked), 1))
        allocated_budget = total_budget * normalized_weight

        expected_conversions = None
        if avg_cpa is not None and float(avg_cpa) > 0:
            expected_conversions = round(allocated_budget / float(avg_cpa), 4)

        allocations.append(
            {
                "segment_id": row.get("segment_id"),
                "campaign_id": row.get("campaign_id"),
                "age": row.get("age"),
                "gender": row.get("gender"),
                "suggested_action": row.get("suggested_action"),
                "recommendation_score": round(score, 6),
                "weight": round(normalized_weight, 6),
                "allocated_budget": round(allocated_budget, 2),
                "expected_conversions": expected_conversions,
            }
        )

    expected_total = sum(float(a["expected_conversions"] or 0) for a in allocations)

    return {
        "total_budget": round(total_budget, 2),
        "segments_used": len(allocations),
        "expected_total_conversions": round(expected_total, 4),
        "allocations": allocations,
    }


def explain_segment(row: dict[str, Any]) -> str:
    score = float(row.get("recommendation_score") or 0.0)
    avg_cpa = float(row.get("avg_cpa") or 0.0)
    avg_cvr = float(row.get("avg_cvr") or 0.0)
    good_ratio = float(row.get("good_ratio") or 0.0)
    action = str(row.get("suggested_action") or "keep_and_test")

    reasons: list[str] = []

    if avg_cpa > 0:
        reasons.append(f"avg_cpa={avg_cpa:.2f}")
    reasons.append(f"avg_cvr={avg_cvr:.4f}")
    reasons.append(f"good_ratio={good_ratio:.2f}")
    reasons.append(f"score={score:.4f}")

    if action == "increase_budget":
        decision_text = "Tang ngan sach do hieu qua tong hop cao"
    elif action == "reduce_budget":
        decision_text = "Giam ngan sach do hieu qua tong hop thap"
    else:
        decision_text = "Giu ngan sach va tiep tuc A/B test"

    return f"{decision_text}; " + ", ".join(reasons)


def add_explanations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        copy["explanation"] = explain_segment(copy)
        enriched.append(copy)
    return enriched
