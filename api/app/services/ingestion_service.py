from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "ad_id",
    "reporting_start",
    "reporting_end",
    "campaign_id",
    "fb_campaign_id",
    "age",
    "gender",
    "impressions",
    "clicks",
    "spent",
    "approved_conversion",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _safe_divide(num: pd.Series, den: pd.Series) -> pd.Series:
    den = den.replace(0, np.nan)
    return (num / den).fillna(0.0)


def _write_single_csv(df: pd.DataFrame, output_dir: Path, file_name: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("part-*.csv"):
        old.unlink(missing_ok=True)
    df.to_csv(output_dir / file_name, index=False)


def save_uploaded_file(temp_file: Any, file_name: str) -> Path:
    raw_dir = _project_root() / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    saved_path = raw_dir / f"uploaded_{file_name}"
    with saved_path.open("wb") as out_file:
        shutil.copyfileobj(temp_file, out_file)

    return saved_path


def build_analysis_from_csv(csv_path: Path) -> dict[str, int]:
    df = pd.read_csv(csv_path)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Uploaded CSV missing required columns: {sorted(missing)}")

    for col in ["impressions", "clicks", "spent", "approved_conversion"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["ctr"] = _safe_divide(df["clicks"], df["impressions"])
    df["cpc"] = _safe_divide(df["spent"], df["clicks"])
    df["cvr"] = _safe_divide(df["approved_conversion"], df["clicks"])
    df["cpa"] = np.where(df["approved_conversion"] > 0, df["spent"] / df["approved_conversion"], np.nan)

    cpa_median = float(df["cpa"].dropna().median()) if not df["cpa"].dropna().empty else 0.0

    df["rule_ctr"] = (df["ctr"] >= 0.01).astype(int)
    df["rule_cvr"] = (df["cvr"] >= 0.02).astype(int)
    df["rule_cpa"] = ((df["approved_conversion"] > 0) & (df["cpa"] <= cpa_median)).astype(int)
    df["rule_conv"] = (df["approved_conversion"] >= 1.0).astype(int)
    df["quality_score"] = df[["rule_ctr", "rule_cvr", "rule_cpa", "rule_conv"]].sum(axis=1)
    df["quality_label"] = np.where(df["quality_score"] >= 3, "good", np.where(df["quality_score"] == 2, "average", "bad"))

    scored_cols = [
        "ad_id",
        "campaign_id",
        "fb_campaign_id",
        "reporting_start",
        "reporting_end",
        "age",
        "gender",
        "impressions",
        "clicks",
        "spent",
        "approved_conversion",
        "ctr",
        "cpc",
        "cvr",
        "cpa",
        "quality_score",
        "quality_label",
    ]
    scored_df = df[scored_cols].copy()

    processed_dir = _project_root() / "data" / "processed" / "ad_quality"
    _write_single_csv(scored_df, processed_dir, "part-uploaded.csv")

    seg_df = scored_df.copy()
    seg_df["campaign_id"] = seg_df["campaign_id"].astype(str)
    seg_df["age"] = seg_df["age"].astype(str)
    seg_df["gender"] = seg_df["gender"].astype(str).str.upper()

    seg_df = seg_df[
        seg_df["age"].str.match(r"^\d{2}-\d{2}$", na=False)
        & seg_df["gender"].isin(["M", "F"])
        & seg_df["campaign_id"].str.match(r"^\d+$", na=False)
    ].copy()

    if seg_df.empty:
        rec_df = pd.DataFrame(
            columns=[
                "segment_id",
                "campaign_id",
                "age",
                "gender",
                "ads_count",
                "total_spent",
                "total_approved_conversion",
                "avg_ctr",
                "avg_cvr",
                "avg_cpa",
                "good_ratio",
                "conversion_per_spent",
                "recommendation_score",
                "recommended_weight",
                "suggested_action",
            ]
        )
    else:
        grouped = (
            seg_df.groupby(["campaign_id", "age", "gender"], as_index=False)
            .agg(
                ads_count=("ad_id", "count"),
                total_spent=("spent", "sum"),
                total_approved_conversion=("approved_conversion", "sum"),
                avg_ctr=("ctr", "mean"),
                avg_cvr=("cvr", "mean"),
                avg_cpa=("cpa", "mean"),
                good_ratio=("quality_label", lambda s: (s == "good").mean()),
            )
        )

        grouped["conversion_per_spent"] = np.where(
            grouped["total_spent"] > 0,
            grouped["total_approved_conversion"] / grouped["total_spent"],
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
        grouped["norm_conversion_per_spent"] = norm(grouped["conversion_per_spent"])
        grouped["norm_good_ratio"] = norm(grouped["good_ratio"])
        grouped["norm_cpa_inverse"] = norm(grouped["cpa_inverse"])

        grouped["recommendation_score"] = (
            grouped["norm_ctr"] * 0.2
            + grouped["norm_cvr"] * 0.3
            + grouped["norm_conversion_per_spent"] * 0.25
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
        grouped["segment_id"] = grouped["campaign_id"] + "|" + grouped["age"] + "|" + grouped["gender"]

        rec_df = grouped[
            [
                "segment_id",
                "campaign_id",
                "age",
                "gender",
                "ads_count",
                "total_spent",
                "total_approved_conversion",
                "avg_ctr",
                "avg_cvr",
                "avg_cpa",
                "good_ratio",
                "conversion_per_spent",
                "recommendation_score",
                "recommended_weight",
                "suggested_action",
            ]
        ].sort_values("recommendation_score", ascending=False)

    curated_dir = _project_root() / "data" / "curated" / "budget_recommendations"
    _write_single_csv(rec_df, curated_dir, "part-uploaded.csv")

    return {"scored_rows": int(len(scored_df)), "segment_rows": int(len(rec_df))}
