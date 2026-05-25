from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_AD_QUALITY_COLUMNS = {
    "ad_id",
    "campaign_id",
    "date",
    "platform",
    "age_group",
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
    "quality_label",
}

REQUIRED_RECOMMENDATION_COLUMNS = {
    "segment_id",
    "campaign_id",
    "age_group",
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
    "suggested_action",
}


def load_latest_csv(directory: Path) -> pd.DataFrame:
    parts = sorted(directory.glob("part-*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not parts:
        raise FileNotFoundError(f"No part csv in {directory}")
    return pd.read_csv(parts[0])


def main() -> None:
    ad_quality_dir = ROOT / "data" / "processed" / "ad_quality"
    recommendation_dir = ROOT / "data" / "curated" / "budget_recommendations"

    ad_df = load_latest_csv(ad_quality_dir)
    rec_df = load_latest_csv(recommendation_dir)

    missing_ad_cols = REQUIRED_AD_QUALITY_COLUMNS - set(ad_df.columns)
    missing_rec_cols = REQUIRED_RECOMMENDATION_COLUMNS - set(rec_df.columns)

    if missing_ad_cols:
        raise AssertionError(f"ad_quality missing columns: {sorted(missing_ad_cols)}")
    if missing_rec_cols:
        raise AssertionError(f"recommendation missing columns: {sorted(missing_rec_cols)}")

    if ad_df.empty:
        raise AssertionError("ad_quality output is empty")
    if rec_df.empty:
        raise AssertionError("budget_recommendations output is empty")

    if not ad_df["quality_label"].isin(["good", "average", "bad"]).all():
        raise AssertionError("quality_label contains invalid values")

    if not rec_df["suggested_action"].isin(["increase_budget", "keep_and_test", "reduce_budget"]).all():
        raise AssertionError("suggested_action contains invalid values")

    if (rec_df["recommended_weight"].fillna(0) < 0).any():
        raise AssertionError("recommended_weight contains negative values")

    print("Spark output smoke test passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Spark output smoke test failed: {exc}")
        sys.exit(1)
