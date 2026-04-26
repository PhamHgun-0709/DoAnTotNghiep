# Defense Talk Track (10 Minutes)

This script is aligned with the current system implementation and dashboard.

## 0:00 - 1:00 Problem & Goal

- Present the business problem: optimize ad budget allocation with measurable KPIs.
- State objective: combine data engineering + analytics + ML + dashboard for decision support.

## 1:00 - 2:30 Architecture Overview

- Data source: campaign CSV.
- Spark job 1: compute quality metrics and labels (`data/processed/ad_quality`).
- Spark job 2: segment-level recommendation scoring (`data/curated/budget_recommendations`).
- Model training: logistic regression + metrics and feature importance artifacts.
- Serving layer: FastAPI endpoints + PostgreSQL for auth/session/logs.
- UI layer: dashboard for KPI, recommendation, experiment, and evidence.

## 2:30 - 4:00 Data & KPI Demonstration

- Open dashboard, filter by campaign/age/gender.
- Explain KPI cards (CTR, CVR, CPA) and chart slices.
- Emphasize reproducibility by showing deterministic reset script in project docs.

## 4:00 - 6:00 Recommendation Logic

- Show top segment table and recommendation actions.
- Explain recommendation score as weighted combination of normalized metrics.
- Run budget simulation and interpret expected conversions.

## 6:00 - 8:00 Experiment & Model Evidence

- Compare rule-baseline and logistic regression metrics.
- Explain objective-based winner (balanced/precision/recall/auc).
- Show model evidence panel:
  - estimated confusion matrix
  - threshold tradeoff table
  - recommended threshold by estimated F1

## 8:00 - 9:00 Reliability & Quality Assurance

- Show `/health` readiness status:
  - database readiness
  - required artifacts readiness
  - data freshness metadata
- Mention full quality gate running 3 smoke tests.

## 9:00 - 10:00 Conclusion & Contributions

- Summarize technical contributions:
  - Spark data processing pipeline
  - recommendation system
  - ML experiment framework
  - production-style API + auth + monitoring checks
- State limitations and future work:
  - persist per-sample probabilities for exact threshold analysis
  - add online A/B tracking loop
  - extend model comparison set
