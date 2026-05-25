from __future__ import annotations

import sys
from typing import Any

import requests


BASE_URL = "http://127.0.0.1:8000"


def must_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(f"{BASE_URL}{path}", params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def assert_has_keys(obj: dict[str, Any], keys: list[str], name: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise AssertionError(f"{name} missing keys: {missing}")


def main() -> None:
    health = must_get("/health")
    assert health.get("status") == "ok", "health endpoint failed"
    assert_has_keys(
        health,
        ["status", "postgres_ready", "all_required_assets_ready", "data_assets"],
        "health",
    )

    summary = must_get("/api/summary")
    assert_has_keys(summary, ["total_ads", "avg_ctr", "quality_distribution"], "summary")

    quality_chart = must_get("/api/charts/quality-distribution")
    assert_has_keys(quality_chart, ["labels", "values"], "quality chart")

    campaign_chart = must_get("/api/charts/campaign-kpi", {"group_by": "campaign_id"})
    assert_has_keys(campaign_chart, ["labels", "ctr", "cvr", "spend"], "campaign chart")

    recommendations = must_get("/api/recommendations/segments", {"limit": 5})
    assert_has_keys(recommendations, ["total", "items"], "recommendations")

    budget_plan = must_get(
        "/api/recommendations/budget-plan",
        {"total_budget": 20000, "top_n": 6},
    )
    assert_has_keys(
        budget_plan,
        ["total_budget", "segments_used", "expected_total_conversions", "allocations"],
        "budget plan",
    )

    options = must_get("/api/filters/options")
    assert_has_keys(options, ["campaign_ids", "age_groups", "quality_labels"], "filter options")

    print("API smoke test passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"API smoke test failed: {exc}")
        sys.exit(1)