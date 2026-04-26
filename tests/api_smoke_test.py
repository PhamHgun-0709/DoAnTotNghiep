from __future__ import annotations

import sys
from typing import Any

import requests


BASE_URL = "http://127.0.0.1:8000"


def must_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(f"{BASE_URL}{path}", params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def must_get_auth(path: str, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def must_post_auth(path: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{BASE_URL}{path}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def must_patch_auth(path: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.patch(
        f"{BASE_URL}{path}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def must_delete_auth(path: str, token: str) -> dict[str, Any]:
    response = requests.delete(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def login_demo(username: str, password: str) -> str:
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": username, "password": password},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise AssertionError("Login response missing access_token")
    return str(token)


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

    assets = health.get("data_assets", {})
    assert isinstance(assets, dict), "health.data_assets must be an object"
    for asset_key in [
        "scored_ads_csv",
        "budget_recommendations_csv",
        "model_metrics_json",
        "top_features_csv",
        "conversion_model_joblib",
    ]:
        if asset_key not in assets:
            raise AssertionError(f"health.data_assets missing key: {asset_key}")

    summary = must_get("/api/summary")
    assert_has_keys(summary, ["total_ads", "avg_ctr", "quality_distribution"], "summary")

    quality_chart = must_get("/api/charts/quality-distribution")
    assert_has_keys(quality_chart, ["labels", "values"], "quality chart")

    campaign_chart = must_get("/api/charts/campaign-kpi", {"group_by": "campaign_id"})
    assert_has_keys(campaign_chart, ["labels", "ctr", "cvr", "spent"], "campaign chart")

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
    assert_has_keys(options, ["campaign_ids", "ages", "genders", "quality_labels"], "filter options")

    token = login_demo("analyst", "analyst123")
    admin_token = login_demo("admin", "admin123")

    experiment_metrics = must_get_auth("/api/experiments/metrics", token=token)
    assert_has_keys(experiment_metrics, ["dataset", "rule_baseline", "logistic_regression", "delta"], "experiment metrics")

    model_evidence = must_get_auth("/api/experiments/model-evidence", token=token)
    assert_has_keys(
        model_evidence,
        ["assumptions", "confusion_matrices", "threshold_tradeoff", "recommended_threshold_by_f1"],
        "model evidence",
    )

    top_features = must_get_auth("/api/experiments/top-features", token=token, params={"limit": 5})
    assert_has_keys(top_features, ["total", "items"], "top features")

    users = must_get_auth("/api/auth/users", token=admin_token)
    assert_has_keys(users, ["total", "items"], "auth users")

    temp_username = "temp_smoke_user"
    must_post_auth(
        "/api/auth/users",
        token=admin_token,
        payload={
            "username": temp_username,
            "password": "temp1234",
            "role": "guest",
            "full_name": "Temp Smoke",
        },
    )
    must_patch_auth(
        f"/api/auth/users/{temp_username}",
        token=admin_token,
        payload={"role": "analyst", "full_name": "Temp Smoke Updated"},
    )
    must_delete_auth(f"/api/auth/users/{temp_username}", token=admin_token)

    print("API smoke test passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"API smoke test failed: {exc}")
        sys.exit(1)
