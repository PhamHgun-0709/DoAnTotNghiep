from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import csv


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _metrics_path() -> Path:
    return _project_root() / "data" / "curated" / "model_eval" / "metrics.json"


def _features_path() -> Path:
    return _project_root() / "data" / "curated" / "model_eval" / "top_features.csv"


def load_experiment_metrics() -> dict[str, Any]:
    path = _metrics_path()
    if not path.exists():
        raise FileNotFoundError(f"Metrics file not found: {path}. Run model training first.")

    return json.loads(path.read_text(encoding="utf-8"))


def load_top_features(limit: int = 20) -> list[dict[str, Any]]:
    path = _features_path()
    if not path.exists():
        raise FileNotFoundError(f"Feature file not found: {path}. Run model training first.")

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            rows.append(
                {
                    "feature": row.get("feature", ""),
                    "coefficient": round(float(row.get("coefficient", 0.0)), 6),
                    "abs_coefficient": round(float(row.get("abs_coefficient", 0.0)), 6),
                }
            )

    return rows[:limit]


def experiment_decision(metrics: dict[str, Any], objective: str = "balanced") -> dict[str, Any]:
    rule = metrics.get("rule_baseline", {})
    model = metrics.get("logistic_regression", {})

    metric_names = ["accuracy", "precision", "recall", "f1", "roc_auc"]
    deltas = {
        name: round(float(model.get(name, 0.0)) - float(rule.get(name, 0.0)), 6)
        for name in metric_names
    }

    objective = objective.lower().strip()
    if objective not in {"balanced", "precision", "recall", "auc"}:
        objective = "balanced"

    if objective == "precision":
        weighted = deltas["precision"]
    elif objective == "recall":
        weighted = deltas["recall"]
    elif objective == "auc":
        weighted = deltas["roc_auc"]
    else:
        weighted = (
            0.2 * deltas["accuracy"]
            + 0.2 * deltas["precision"]
            + 0.2 * deltas["recall"]
            + 0.2 * deltas["f1"]
            + 0.2 * deltas["roc_auc"]
        )

    winner = "logistic_regression" if weighted > 0 else "rule_baseline"

    explanation = {
        "balanced": "Cân bằng toàn bộ metric để đánh giá tổng thể.",
        "precision": "Ưu tiên giảm false positive khi đề xuất quảng cáo tốt.",
        "recall": "Ưu tiên bắt được nhiều trường hợp chuyển đổi tốt nhất.",
        "auc": "Ưu tiên khả năng phân tách tổng quát của mô hình.",
    }[objective]

    return {
        "objective": objective,
        "winner": winner,
        "weighted_delta": round(float(weighted), 6),
        "metric_deltas": deltas,
        "explanation": explanation,
    }


def build_defense_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    balanced = experiment_decision(metrics, "balanced")
    precision = experiment_decision(metrics, "precision")
    recall = experiment_decision(metrics, "recall")
    auc = experiment_decision(metrics, "auc")

    rule = metrics.get("rule_baseline", {})
    model = metrics.get("logistic_regression", {})

    if balanced["winner"] == "rule_baseline":
        final_recommendation = "Dùng rule_baseline nếu ưu tiên sự ổn định và độ chính xác cao khi đánh giá quảng cáo tốt."
    else:
        final_recommendation = "Dùng logistic_regression nếu ưu tiên khả năng tổng quát và tự động hóa quyết định."

    if recall["winner"] == "logistic_regression":
        final_recommendation += " Mô hình phù hợp hơn khi mục tiêu là không bỏ sót tập quảng cáo có khả năng chuyển đổi."

    return {
        "dataset": metrics.get("dataset", {}),
        "winners": {
            "balanced": balanced["winner"],
            "precision": precision["winner"],
            "recall": recall["winner"],
            "auc": auc["winner"],
        },
        "headline": final_recommendation,
        "key_points": [
            f"Rule baseline precision={float(rule.get('precision', 0.0)):.4f}, recall={float(rule.get('recall', 0.0)):.4f}",
            f"Logistic regression precision={float(model.get('precision', 0.0)):.4f}, recall={float(model.get('recall', 0.0)):.4f}",
            f"F1 delta={float(model.get('f1', 0.0)) - float(rule.get('f1', 0.0)):.4f}",
            f"ROC AUC delta={float(model.get('roc_auc', 0.0)) - float(rule.get('roc_auc', 0.0)):.4f}",
        ],
    }


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _estimate_confusion_from_pr(
    precision: float,
    recall: float,
    total_rows: int,
    positive_rate: float,
) -> dict[str, Any]:
    positives = int(round(total_rows * positive_rate))
    positives = max(0, min(positives, total_rows))
    negatives = total_rows - positives

    tp = int(round(recall * positives))
    tp = max(0, min(tp, positives))
    fn = positives - tp

    if precision <= 0:
        fp = negatives
    else:
        fp = int(round(tp * ((1.0 / precision) - 1.0)))
        fp = max(0, min(fp, negatives))

    tn = negatives - fp

    estimated_precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    estimated_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    estimated_accuracy = (tp + tn) / total_rows if total_rows > 0 else 0.0
    estimated_f1 = (
        (2 * estimated_precision * estimated_recall) / (estimated_precision + estimated_recall)
        if (estimated_precision + estimated_recall) > 0
        else 0.0
    )

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "estimated_precision": round(estimated_precision, 6),
        "estimated_recall": round(estimated_recall, 6),
        "estimated_accuracy": round(estimated_accuracy, 6),
        "estimated_f1": round(estimated_f1, 6),
    }


def build_model_evidence(metrics: dict[str, Any]) -> dict[str, Any]:
    dataset = metrics.get("dataset", {})
    test_rows = int(_safe_float(dataset.get("test_rows", 0), 0.0))
    positive_rate = _safe_float(dataset.get("positive_rate", 0.0), 0.0)

    rule = metrics.get("rule_baseline", {})
    model = metrics.get("logistic_regression", {})

    rule_precision = _safe_float(rule.get("precision", 0.0), 0.0)
    rule_recall = _safe_float(rule.get("recall", 0.0), 0.0)
    model_precision = _safe_float(model.get("precision", 0.0), 0.0)
    model_recall = _safe_float(model.get("recall", 0.0), 0.0)

    rule_conf = _estimate_confusion_from_pr(rule_precision, rule_recall, test_rows, positive_rate)
    model_conf = _estimate_confusion_from_pr(model_precision, model_recall, test_rows, positive_rate)

    # We do not store per-threshold probabilities in artifacts yet, so threshold rows
    # are an estimated sensitivity profile around the trained logistic model point.
    threshold_rows: list[dict[str, Any]] = []
    for threshold in [0.3, 0.5, 0.7]:
        shift = threshold - 0.5
        est_precision = min(0.999, max(0.001, model_precision + 0.35 * shift))
        est_recall = min(0.999, max(0.001, model_recall - 0.45 * shift))
        est_f1 = (2 * est_precision * est_recall) / (est_precision + est_recall)
        threshold_rows.append(
            {
                "threshold": threshold,
                "estimated_precision": round(est_precision, 6),
                "estimated_recall": round(est_recall, 6),
                "estimated_f1": round(est_f1, 6),
            }
        )

    recommended = max(threshold_rows, key=lambda row: row["estimated_f1"])

    return {
        "assumptions": {
            "type": "estimated_from_metrics",
            "note": "Ma trận nhầm lẫn và trade-off theo ngưỡng được ước lượng từ metrics test đã lưu vì xác suất theo từng mẫu chưa được lưu lâu dài.",
            "test_rows": test_rows,
            "positive_rate": round(positive_rate, 6),
        },
        "confusion_matrices": {
            "rule_baseline": rule_conf,
            "logistic_regression": model_conf,
        },
        "threshold_tradeoff": threshold_rows,
        "recommended_threshold_by_f1": {
            "threshold": recommended["threshold"],
            "estimated_f1": recommended["estimated_f1"],
        },
    }
