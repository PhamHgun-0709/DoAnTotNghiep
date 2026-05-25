"""
KPI and ML routes for advanced analytics.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Query, Depends
from app.core.role_checker import require_admin, require_analyst_or_admin
from app.schemas.analytics_schema import AnalyticsOverviewResponse, HighROICampaignsResponse, RetrainResponse
from app.services.kpi_service import (
    build_advanced_summary,
    identify_high_roi_campaigns,
    calculate_cpm,
    calculate_roi,
    calculate_roas,
)
from app.services.data_store import load_scored_ads
from app.ml.classifier import CampaignClassifier
from app.ml.predictor import ConversionPredictor


router = APIRouter(prefix="/api/ml", tags=["ml-analytics"])


@router.get("/advanced-summary", response_model=AnalyticsOverviewResponse)
def get_advanced_summary(
    campaign_id: str | None = Query(default=None),
    current_user: dict = Depends(require_analyst_or_admin()),
) -> AnalyticsOverviewResponse:
    """Get advanced KPI summary including CPM, ROI, ROAS."""
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    
    if campaign_id:
        records = [r for r in records if str(r.get("campaign_id", "")) == campaign_id]
    
    return build_advanced_summary(records)


@router.get("/analytics", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    campaign_id: str | None = Query(default=None),
    current_user: dict = Depends(require_analyst_or_admin()),
) -> AnalyticsOverviewResponse:
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if campaign_id:
        records = [r for r in records if str(r.get("campaign_id", "")) == campaign_id]

    return build_advanced_summary(records)


@router.get("/high-roi-campaigns", response_model=HighROICampaignsResponse)
def get_high_roi_campaigns(
    revenue_per_conversion: float = Query(default=10.0, gt=0),
    top_n: int = Query(default=5, ge=1, le=20),
    current_user: dict = Depends(require_analyst_or_admin()),
) -> HighROICampaignsResponse:
    """Identify campaigns with highest ROI potential."""
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    
    campaigns = identify_high_roi_campaigns(records, revenue_per_conversion=revenue_per_conversion, top_n=top_n)
    return {"total": len(campaigns), "campaigns": campaigns}


@router.post("/campaign-classifier/train")
def train_campaign_classifier(
    current_user: dict = Depends(require_admin()),
) -> dict[str, Any]:
    """Train campaign effectiveness classifier."""
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    
    classifier = CampaignClassifier()
    result = classifier.train(records)
    return result


@router.post("/campaign-classifier/predict")
def predict_campaign_effectiveness(
    ctr: float = Query(..., gt=0),
    cvr: float = Query(..., gt=0),
    cpc: float = Query(..., gt=0),
    cpm: float = Query(..., gt=0),
    current_user: dict = Depends(require_analyst_or_admin()),
) -> dict[str, Any]:
    """Predict campaign effectiveness category."""
    classifier = CampaignClassifier()
    if not classifier.load():
        raise HTTPException(status_code=400, detail="Classifier model not trained. Train first using /train endpoint.")
    
    return classifier.predict(ctr, cvr, cpc, cpm)


@router.post("/conversion-predictor/train")
def train_conversion_predictor(
    current_user: dict = Depends(require_admin()),
) -> dict[str, Any]:
    """Train conversion prediction model."""
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    
    predictor = ConversionPredictor()
    result = predictor.train(records)
    return result


@router.post("/conversion-predictor/predict")
def predict_conversions(
    impressions: float = Query(..., ge=0),
    clicks: float = Query(..., ge=0),
    spend: float = Query(..., ge=0),
    ctr: float = Query(..., ge=0),
    cpc: float = Query(..., ge=0),
    current_user: dict = Depends(require_analyst_or_admin()),
) -> dict[str, Any]:
    """Predict expected conversions."""
    predictor = ConversionPredictor()
    if not predictor.load():
        raise HTTPException(status_code=400, detail="Predictor model not trained. Train first using /train endpoint.")
    
    return predictor.predict(impressions, clicks, spend, ctr, cpc)


@router.post("/retrain", response_model=RetrainResponse)
def retrain_models(
    current_user: dict = Depends(require_admin()),
) -> RetrainResponse:
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    classifier = CampaignClassifier()
    predictor = ConversionPredictor()
    classifier_result = classifier.train(records)
    predictor_result = predictor.train(records)
    return {"classifier": classifier_result, "predictor": predictor_result}
