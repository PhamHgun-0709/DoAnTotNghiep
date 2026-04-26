from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_scored_dataset() -> pd.DataFrame:
    scored_dir = workspace_root() / "data" / "processed" / "ad_quality"
    part_files = sorted(scored_dir.glob("part-*.csv"))
    if not part_files:
        raise FileNotFoundError(f"No scored CSV found in {scored_dir}. Run Spark quality job first.")

    frames = [pd.read_csv(path) for path in part_files]
    return pd.concat(frames, ignore_index=True)


def metrics_dict(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 6),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 6),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 6),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 6),
    }


def baseline_rule_predictions(df: pd.DataFrame) -> np.ndarray:
    ctr_ok = df["ctr"].fillna(0.0) >= 0.01
    cvr_ok = df["cvr"].fillna(0.0) >= 0.02
    cpa_ok = (df["cpa"].fillna(np.inf) <= df["cpa"].median(skipna=True)) & (df["approved_conversion"].fillna(0.0) > 0)
    conv_ok = df["approved_conversion"].fillna(0.0) >= 1.0
    score = ctr_ok.astype(int) + cvr_ok.astype(int) + cpa_ok.astype(int) + conv_ok.astype(int)
    return (score >= 3).astype(int).to_numpy()


def main() -> None:
    root = workspace_root()
    output_dir = root / "data" / "curated" / "model_eval"
    model_dir = root / "data" / "curated" / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    df = load_scored_dataset()

    df["campaign_id"] = df["campaign_id"].astype(str)
    df["age"] = df["age"].astype(str)
    df["gender"] = df["gender"].astype(str).str.upper()

    valid_age_mask = df["age"].str.match(r"^\d{2}-\d{2}$", na=False)
    valid_gender_mask = df["gender"].isin(["M", "F"])
    valid_campaign_mask = df["campaign_id"].str.match(r"^\d+$", na=False)

    df = df[valid_age_mask & valid_gender_mask & valid_campaign_mask].copy()

    df["conversion_success"] = (df["approved_conversion"].fillna(0.0) >= 1.0).astype(int)

    feature_cols_num = [
        "impressions",
        "clicks",
        "spent",
        "ctr",
        "cpc",
    ]
    feature_cols_cat = ["campaign_id", "age", "gender"]

    X = df[feature_cols_num + feature_cols_cat].copy()
    y = df["conversion_success"].to_numpy()

    row_indices = np.arange(len(df))
    train_idx, test_idx, y_train, y_test = train_test_split(
        row_indices,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, feature_cols_num),
            ("cat", categorical_transformer, feature_cols_cat),
        ]
    )

    model = LogisticRegression(max_iter=2000, class_weight="balanced")

    clf = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    model_metrics = metrics_dict(y_test, y_pred, y_prob)

    baseline_test_df = df.iloc[test_idx]
    baseline_pred = baseline_rule_predictions(baseline_test_df)
    baseline_prob = baseline_pred.astype(float)
    baseline_metrics = metrics_dict(y_test, baseline_pred, baseline_prob)

    metrics_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": "conversion_success (approved_conversion >= 1)",
        "dataset": {
            "total_rows": int(len(df)),
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
            "positive_rate": round(float(y.mean()), 6),
        },
        "rule_baseline": baseline_metrics,
        "logistic_regression": model_metrics,
        "delta": {
            key: round(model_metrics[key] - baseline_metrics[key], 6)
            for key in ["accuracy", "precision", "recall", "f1", "roc_auc"]
        },
    }

    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    model_path = model_dir / "conversion_model.joblib"
    joblib.dump(clf, model_path)

    feature_names = clf.named_steps["preprocessor"].get_feature_names_out()
    coefficients = clf.named_steps["model"].coef_[0]
    feature_df = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefficients,
            "abs_coefficient": np.abs(coefficients),
        }
    ).sort_values("abs_coefficient", ascending=False)

    feature_df.head(30).to_csv(output_dir / "top_features.csv", index=False)

    print(f"Metrics saved: {metrics_path}")
    print(f"Model saved: {model_path}")


if __name__ == "__main__":
    main()
