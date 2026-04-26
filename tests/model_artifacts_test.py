from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    metrics_path = ROOT / "data" / "curated" / "model_eval" / "metrics.json"
    model_path = ROOT / "data" / "curated" / "models" / "conversion_model.joblib"
    features_path = ROOT / "data" / "curated" / "model_eval" / "top_features.csv"

    if not metrics_path.exists():
        raise FileNotFoundError(f"Missing metrics file: {metrics_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Missing model artifact: {model_path}")
    if not features_path.exists():
        raise FileNotFoundError(f"Missing feature file: {features_path}")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    for section in ["rule_baseline", "logistic_regression", "delta"]:
        if section not in metrics:
            raise AssertionError(f"metrics.json missing section: {section}")

    for metric_name in ["accuracy", "precision", "recall", "f1", "roc_auc"]:
        if metric_name not in metrics["rule_baseline"]:
            raise AssertionError(f"rule_baseline missing metric: {metric_name}")
        if metric_name not in metrics["logistic_regression"]:
            raise AssertionError(f"logistic_regression missing metric: {metric_name}")

        rule_value = float(metrics["rule_baseline"][metric_name])
        model_value = float(metrics["logistic_regression"][metric_name])

        if not (0.0 <= rule_value <= 1.0):
            raise AssertionError(f"rule metric out of range [0,1]: {metric_name}={rule_value}")
        if not (0.0 <= model_value <= 1.0):
            raise AssertionError(f"model metric out of range [0,1]: {metric_name}={model_value}")

    features_df = pd.read_csv(features_path)
    required_columns = {"feature", "coefficient", "abs_coefficient"}
    missing_columns = required_columns - set(features_df.columns)
    if missing_columns:
        raise AssertionError(f"top_features.csv missing columns: {sorted(missing_columns)}")

    if features_df.empty:
        raise AssertionError("top_features.csv is empty")

    print("Model artifact test passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Model artifact test failed: {exc}")
        sys.exit(1)
