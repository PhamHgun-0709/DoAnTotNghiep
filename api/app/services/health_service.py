from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _iso_utc_from_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _asset_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "path": str(path),
            "last_modified_utc": None,
            "age_minutes": None,
        }

    modified_ts = path.stat().st_mtime
    now_ts = datetime.now(tz=timezone.utc).timestamp()
    age_minutes = round((now_ts - modified_ts) / 60.0, 2)

    return {
        "exists": True,
        "path": str(path),
        "last_modified_utc": _iso_utc_from_timestamp(modified_ts),
        "age_minutes": age_minutes,
    }


def _latest_part_csv(directory: Path) -> Path:
    part_files = sorted(directory.glob("part-*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not part_files:
        return directory / "part-*.csv"
    return part_files[0]


def build_data_health_snapshot() -> dict[str, Any]:
    root = _project_root()

    assets = {
        "scored_ads_csv": _asset_status(_latest_part_csv(root / "data" / "processed" / "ad_quality")),
        "budget_recommendations_csv": _asset_status(
            _latest_part_csv(root / "data" / "curated" / "budget_recommendations")
        ),
        "model_metrics_json": _asset_status(root / "data" / "curated" / "model_eval" / "metrics.json"),
        "top_features_csv": _asset_status(root / "data" / "curated" / "model_eval" / "top_features.csv"),
        "conversion_model_joblib": _asset_status(root / "data" / "curated" / "models" / "conversion_model.joblib"),
    }

    all_required_assets_ready = all(item["exists"] for item in assets.values())

    return {
        "all_required_assets_ready": all_required_assets_ready,
        "data_assets": assets,
    }
