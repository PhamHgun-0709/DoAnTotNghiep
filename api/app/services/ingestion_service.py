from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CANONICAL_COLUMNS = {
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
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _safe_divide(num: pd.Series, den: pd.Series) -> pd.Series:
    den = den.replace(0, np.nan)
    return (num / den).fillna(0.0)


def _write_single_csv(df: pd.DataFrame, output_dir: Path, file_name: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    # Preserve previous outputs (do not delete old parts).
    # Write with a timestamped filename so history is kept for auditing.
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target_name = f"part-{ts}.csv"
    df.to_csv(output_dir / target_name, index=False)


def save_uploaded_file(temp_file: Any, file_name: str) -> Path:
    raw_dir = _project_root() / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    saved_path = raw_dir / f"uploaded_{file_name}"
    with saved_path.open("wb") as out_file:
        shutil.copyfileobj(temp_file, out_file)
    return saved_path


def build_analysis_from_csv(csv_path: Path) -> dict[str, int]:
    df = pd.read_csv(csv_path)
    cols = set(df.columns)
    if not CANONICAL_COLUMNS.issubset(cols):
        expected = sorted(CANONICAL_COLUMNS)
        raise ValueError(
            "Uploaded CSV missing required columns. "
            f"Need: {expected}. Got: {sorted(cols)}"
        )

    df = df.copy()
    for col in ["impressions", "clicks", "conversions", "spend", "revenue"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "ad_id" not in df.columns:
        df["ad_id"] = np.arange(1, len(df) + 1)

    df["campaign_id"] = df["campaign_id"].astype(str)
    df["age_group"] = df["age_group"].astype(str)

    df["ctr"] = _safe_divide(df["clicks"], df["impressions"])
    df["cpc"] = _safe_divide(df["spend"], df["clicks"])
    df["cvr"] = _safe_divide(df["conversions"], df["clicks"])
    df["cpa"] = np.where(df["conversions"] > 0, df["spend"] / df["conversions"], np.nan)
    df["cpm"] = np.where(df["impressions"] > 0, (df["spend"] / df["impressions"]) * 1000, 0.0)

    cpa_median = float(df["cpa"].dropna().median()) if not df["cpa"].dropna().empty else 0.0
    df["rule_ctr"] = (df["ctr"] >= 0.01).astype(int)
    df["rule_cvr"] = (df["cvr"] >= 0.02).astype(int)
    df["rule_cpa"] = ((df["conversions"] > 0) & (df["cpa"] <= cpa_median)).astype(int)
    df["rule_conv"] = (df["conversions"] >= 1.0).astype(int)
    df["quality_score"] = df[["rule_ctr", "rule_cvr", "rule_cpa", "rule_conv"]].sum(axis=1)
    df["quality_label"] = np.where(df["quality_score"] >= 3, "good", np.where(df["quality_score"] == 2, "average", "bad"))

    scored_cols = [
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
    ]
    scored_df = df[scored_cols].copy()
    _write_single_csv(scored_df, _project_root() / "data" / "processed" / "ad_quality", "part-uploaded.csv")

    seg_df = scored_df[(scored_df["campaign_id"].str.len() > 0) & (scored_df["age_group"].str.len() > 0)].copy()
    if seg_df.empty:
        rec_df = pd.DataFrame(
            columns=[
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
            ]
        )
    else:
        grouped = (
            seg_df.groupby(["campaign_id", "age_group"], as_index=False)
            .agg(
                ads_count=("ad_id", "count"),
                total_spent=("spend", "sum"),
                total_conversions=("conversions", "sum"),
                avg_ctr=("ctr", "mean"),
                avg_cvr=("cvr", "mean"),
                avg_cpa=("cpa", "mean"),
                good_ratio=("quality_label", lambda s: (s == "good").mean()),
            )
        )

        grouped["conversion_per_spend"] = np.where(
            grouped["total_spent"] > 0,
            grouped["total_conversions"] / grouped["total_spent"],
            0.0,
        )
        grouped["cpa_inverse"] = np.where(grouped["avg_cpa"] > 0, 1.0 / grouped["avg_cpa"], 0.0)

        def norm(series: pd.Series) -> pd.Series:
            min_v = series.min()
            max_v = series.max()
            if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v:
                return pd.Series([0.5] * len(series), index=series.index)
            return (series - min_v) / (max_v - min_v)

        grouped["norm_ctr"] = norm(grouped["avg_ctr"])
        grouped["norm_cvr"] = norm(grouped["avg_cvr"])
        grouped["norm_conversion_per_spend"] = norm(grouped["conversion_per_spend"])
        grouped["norm_good_ratio"] = norm(grouped["good_ratio"])
        grouped["norm_cpa_inverse"] = norm(grouped["cpa_inverse"])

        grouped["recommendation_score"] = (
            grouped["norm_ctr"] * 0.2
            + grouped["norm_cvr"] * 0.3
            + grouped["norm_conversion_per_spend"] * 0.25
            + grouped["norm_good_ratio"] * 0.15
            + grouped["norm_cpa_inverse"] * 0.1
        )
        grouped["suggested_action"] = np.where(
            grouped["recommendation_score"] >= 0.7,
            "increase_budget",
            np.where(grouped["recommendation_score"] >= 0.45, "keep_and_test", "reduce_budget"),
        )

        total_score = grouped["recommendation_score"].sum()
        grouped["recommended_weight"] = np.where(total_score > 0, grouped["recommendation_score"] / total_score, 0.0)
        grouped["segment_id"] = grouped["campaign_id"] + "|" + grouped["age_group"]

        rec_df = grouped[
            [
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
            ]
        ].sort_values("recommendation_score", ascending=False)

    _write_single_csv(rec_df, _project_root() / "data" / "curated" / "budget_recommendations", "part-uploaded.csv")
    return {"scored_rows": int(len(scored_df)), "segment_rows": int(len(rec_df))}