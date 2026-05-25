from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from app.core.security import get_current_user
from app.core.role_checker import require_admin, require_analyst_or_admin
from app.schemas.analytics_schema import SummaryResponse
from app.schemas.dataset_schema import DashboardResponse, UploadResponse
from app.schemas.report_schema import ReportsResponse
from app.services.analytics_service import (
    build_summary,
    chart_campaign_kpi,
    chart_kpi_by_age,
    chart_kpi_by_gender,
    chart_quality_distribution,
    filter_ads,
)
from app.services.data_store import (
    append_dataset_history,
    load_budget_recommendations,
    load_scored_ads,
    read_active_dataset_metadata,
    read_dataset_history,
    reload_budget_recommendations,
    reload_scored_ads,
    write_active_dataset_metadata,
)
from app.services.ingestion_service import build_analysis_from_csv, save_uploaded_file
from app.services.recommendation_service import add_explanations, budget_plan, explain_segment, filter_segments
from app.services.upload_log_service import append_upload_log, read_upload_logs_page


router = APIRouter(prefix="/api", tags=["ads"])


def _load_scored_ads_or_404() -> list[dict[str, Any]]:
    try:
        return load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _load_budget_recommendations_or_404() -> list[dict[str, Any]]:
    try:
        return load_budget_recommendations()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _load_budget_recommendations_optional() -> list[dict[str, Any]]:
    try:
        return load_budget_recommendations()
    except FileNotFoundError:
        return []


def _load_scored_ads_optional() -> list[dict[str, Any]]:
    try:
        return load_scored_ads()
    except FileNotFoundError:
        return []


def _filter_scored_ads(
    records: list[dict[str, Any]],
    campaign_id: str | None = None,
    age_group: str | None = None,
    quality_label: str | None = None,
    min_ctr: float | None = None,
    max_cpa: float | None = None,
) -> list[dict[str, Any]]:
    return filter_ads(
        records,
        campaign_id=campaign_id,
        age_group=age_group,
        quality_label=quality_label,
        min_ctr=min_ctr,
        max_cpa=max_cpa,
    )


def _filter_recommendations(
    records: list[dict[str, Any]],
    campaign_id: str | None = None,
    age_group: str | None = None,
    suggested_action: str | None = None,
) -> list[dict[str, Any]]:
    return filter_segments(
        records,
        campaign_id=campaign_id,
        age_group=age_group,
        suggested_action=suggested_action,
    )


def _csv_response(rows: list[dict[str, Any]], fieldnames: list[str], filename: str) -> Response:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/data/upload", response_model=UploadResponse)
def upload_ad_data(
    file: UploadFile = File(...),
    current_user: dict[str, Any] = Depends(require_analyst_or_admin()),
) -> UploadResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        saved_path = save_uploaded_file(file.file, file.filename)
        result = build_analysis_from_csv(saved_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {exc}") from exc
    finally:
        file.file.close()

    reload_scored_ads()
    reload_budget_recommendations()

    active_dataset = write_active_dataset_metadata(
        file_name=file.filename,
        file_path=str(saved_path),
        uploaded_by=str(current_user.get("username", "anonymous")),
        uploaded_role=str(current_user.get("role", "guest")),
        scored_rows=int(result.get("scored_rows", 0)),
        segment_rows=int(result.get("segment_rows", 0)),
    )

    dataset_history = append_dataset_history(
        {
            "active_dataset": file.filename,
            "file_name": file.filename,
            "file_path": str(saved_path),
            "uploaded_by": str(current_user.get("username", "anonymous")),
            "uploaded_role": str(current_user.get("role", "guest")),
            "scored_rows": int(result.get("scored_rows", 0)),
            "segment_rows": int(result.get("segment_rows", 0)),
            "updated_at": active_dataset.get("updated_at"),
        }
    )

    append_upload_log(
        file_name=file.filename,
        file_path=str(saved_path),
        scored_rows=int(result.get("scored_rows", 0)),
        segment_rows=int(result.get("segment_rows", 0)),
        uploader_role=str(current_user.get("role", "guest")),
        uploader_name=str(current_user.get("username", "anonymous")),
    )

    return {
        "message": "Upload successful and analysis rebuilt.",
        "file_path": str(saved_path),
        "active_dataset": active_dataset,
        "dataset_history": dataset_history,
        **result,
    }


@router.get("/data/upload-logs")
def get_upload_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    uploader_name: str | None = Query(default=None),
    file_name: str | None = Query(default=None),
    _admin: dict[str, Any] = Depends(require_admin()),
) -> dict[str, Any]:
    try:
        return read_upload_logs_page(
            page=page,
            page_size=page_size,
            uploader_name=uploader_name,
            file_name=file_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


@router.get("/reload")
def reload_data(_admin: dict[str, Any] = Depends(require_admin())) -> dict[str, int]:
    records = reload_scored_ads()
    recommendation_rows = reload_budget_recommendations()
    return {"rows": len(records), "recommendation_rows": len(recommendation_rows)}


@router.get("/ads")
def get_ads(
    campaign_id: str | None = Query(default=None),
    age_group: str | None = Query(default=None),
    quality_label: str | None = Query(default=None),
    min_ctr: float | None = Query(default=None),
    max_cpa: float | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=2000),
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    records = _load_scored_ads_or_404()
    filtered = _filter_scored_ads(
        records,
        campaign_id=campaign_id,
        age_group=age_group,
        quality_label=quality_label,
        min_ctr=min_ctr,
        max_cpa=max_cpa,
    )

    return {
        "total": len(filtered),
        "items": filtered[:limit],
    }


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    campaign_id: str | None = Query(default=None),
    age_group: str | None = Query(default=None),
    quality_label: str | None = Query(default=None),
    min_ctr: float | None = Query(default=None),
    max_cpa: float | None = Query(default=None),
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> SummaryResponse:
    records = _load_scored_ads_or_404()
    filtered = _filter_scored_ads(
        records,
        campaign_id=campaign_id,
        age_group=age_group,
        quality_label=quality_label,
        min_ctr=min_ctr,
        max_cpa=max_cpa,
    )
    return build_summary(filtered)


@router.get("/charts/quality-distribution")
def get_quality_distribution_chart(
    campaign_id: str | None = Query(default=None),
    age_group: str | None = Query(default=None),
    _current_user: dict[str, Any] = Depends(require_analyst_or_admin()),
) -> dict[str, Any]:
    records = _load_scored_ads_or_404()
    filtered = _filter_scored_ads(records, campaign_id=campaign_id, age_group=age_group)
    return chart_quality_distribution(filtered)


@router.get("/charts/campaign-kpi")
def get_campaign_kpi_chart(
    quality_label: str | None = Query(default=None),
    group_by: str = Query(default="campaign_id", pattern="^(campaign_id|age_group|platform)$"),
    top_n: int = Query(default=12, ge=3, le=30),
    _current_user: dict[str, Any] = Depends(require_analyst_or_admin()),
) -> dict[str, Any]:
    records = _load_scored_ads_or_404()
    filtered = _filter_scored_ads(records, quality_label=quality_label)
    return chart_campaign_kpi(filtered, group_by=group_by, top_n=top_n)


@router.get("/charts/age-kpi")
def get_age_kpi_chart(campaign_id: str | None = Query(default=None), _current_user: dict[str, Any] = Depends(require_analyst_or_admin())) -> dict[str, Any]:
    records = _load_scored_ads_or_404()
    filtered = _filter_scored_ads(records, campaign_id=campaign_id)
    return chart_kpi_by_age(filtered)


@router.get("/charts/gender-kpi")
def get_gender_kpi_chart(campaign_id: str | None = Query(default=None), _current_user: dict[str, Any] = Depends(require_analyst_or_admin())) -> dict[str, Any]:
    records = _load_scored_ads_or_404()
    filtered = _filter_scored_ads(records, campaign_id=campaign_id)
    return chart_kpi_by_gender(filtered)


@router.get("/recommendations/segments")
def get_recommendation_segments(
    campaign_id: str | None = Query(default=None),
    age_group: str | None = Query(default=None),
    suggested_action: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    _current_user: dict[str, Any] = Depends(require_analyst_or_admin()),
) -> dict[str, Any]:
    records = _load_budget_recommendations_or_404()
    filtered = _filter_recommendations(
        records,
        campaign_id=campaign_id,
        age_group=age_group,
        suggested_action=suggested_action,
    )
    ranked = sorted(filtered, key=lambda r: float(r.get("recommendation_score") or 0), reverse=True)
    return {"total": len(ranked), "items": add_explanations(ranked[:limit])}


@router.get("/recommendations/budget-plan")
def get_budget_plan(
    total_budget: float = Query(default=10000.0, gt=0),
    top_n: int = Query(default=10, ge=1, le=50),
    campaign_id: str | None = Query(default=None),
    suggested_action: str | None = Query(default=None),
    _current_user: dict[str, Any] = Depends(require_analyst_or_admin()),
) -> dict[str, Any]:
    records = _load_budget_recommendations_or_404()
    filtered = _filter_recommendations(
        records,
        campaign_id=campaign_id,
        suggested_action=suggested_action,
    )

    if not filtered:
        return {
            "total_budget": round(total_budget, 2),
            "segments_used": 0,
            "expected_total_conversions": 0.0,
            "allocations": [],
        }

    result = budget_plan(filtered, total_budget=total_budget, top_n=top_n)
    result["allocations"] = add_explanations(result["allocations"])
    return result


@router.get("/recommendations/segments/export.csv")
def export_recommendation_segments_csv(
    campaign_id: str | None = Query(default=None),
    age_group: str | None = Query(default=None),
    suggested_action: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    _current_user: dict[str, Any] = Depends(require_analyst_or_admin()),
) -> Response:
    records = _load_budget_recommendations_or_404()
    filtered = _filter_recommendations(
        records,
        campaign_id=campaign_id,
        age_group=age_group,
        suggested_action=suggested_action,
    )
    ranked = sorted(filtered, key=lambda r: float(r.get("recommendation_score") or 0), reverse=True)[:limit]
    rows = add_explanations(ranked)
    return _csv_response(
        rows,
        [
            "segment_id",
            "campaign_id",
            "age_group",
            "suggested_action",
            "recommendation_score",
            "recommended_weight",
            "avg_cpa",
            "avg_cvr",
            "good_ratio",
            "explanation",
        ],
        "recommendation_segments.csv",
    )


@router.get("/recommendations/budget-plan/export.csv")
def export_budget_plan_csv(
    total_budget: float = Query(default=10000.0, gt=0),
    top_n: int = Query(default=10, ge=1, le=50),
    campaign_id: str | None = Query(default=None),
    suggested_action: str | None = Query(default=None),
    _current_user: dict[str, Any] = Depends(require_analyst_or_admin()),
) -> Response:
    records = _load_budget_recommendations_or_404()
    filtered = _filter_recommendations(
        records,
        campaign_id=campaign_id,
        suggested_action=suggested_action,
    )

    plan = budget_plan(filtered, total_budget=total_budget, top_n=top_n)
    rows = add_explanations(plan["allocations"])
    return _csv_response(
        rows,
        [
            "segment_id",
            "campaign_id",
            "age_group",
            "suggested_action",
            "recommendation_score",
            "weight",
            "allocated_budget",
            "expected_conversions",
            "explanation",
        ],
        "budget_plan.csv",
    )


@router.get("/recommendations/explain")
def explain_recommendation_segment(segment_id: str = Query(...), _current_user: dict[str, Any] = Depends(require_analyst_or_admin())) -> dict[str, Any]:
    records = _load_budget_recommendations_or_404()

    matched = [r for r in records if str(r.get("segment_id", "")) == segment_id]
    if not matched:
        raise HTTPException(status_code=404, detail=f"Segment not found: {segment_id}")

    row = matched[0]
    return {
        "segment_id": row.get("segment_id"),
        "campaign_id": row.get("campaign_id"),
        "age_group": row.get("age_group"),
        "suggested_action": row.get("suggested_action"),
        "recommendation_score": row.get("recommendation_score"),
        "explanation": explain_segment(row),
    }


@router.get("/filters/options")
def get_filter_options(_current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    ad_records = _load_scored_ads_or_404()
    recommendation_records = _load_budget_recommendations_optional()

    campaign_ids = sorted(
        {
            str(r.get("campaign_id", ""))
            for r in ad_records
            if str(r.get("campaign_id", ""))
        }
    )
    age_groups = sorted({str(r.get("age_group", "")) for r in ad_records if str(r.get("age_group", ""))})
    quality_labels = sorted({str(r.get("quality_label", "")) for r in ad_records if str(r.get("quality_label", ""))})
    suggested_actions = sorted(
        {
            str(r.get("suggested_action", ""))
            for r in recommendation_records
            if str(r.get("suggested_action", ""))
        }
    )

    return {
        "campaign_ids": campaign_ids,
        "age_groups": age_groups,
        "quality_labels": quality_labels,
        "suggested_actions": suggested_actions,
    }


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard_overview(_current_user: dict[str, Any] = Depends(get_current_user)) -> DashboardResponse:
    records = _load_scored_ads_optional()
    active_dataset = read_active_dataset_metadata()
    dataset_history = read_dataset_history(limit=5)

    return {
        "summary": build_summary(records),
        "total_records": len(records),
        "has_data": bool(records),
        "active_dataset": active_dataset,
        "dataset_history": dataset_history,
    }


@router.delete("/dataset/active")
def delete_active_dataset(_admin: dict[str, Any] = Depends(require_admin())) -> dict[str, Any]:
    """Admin endpoint to deactivate the currently active dataset."""
    try:
        from app.services.data_store import deactivate_active_dataset as _deact

        prev = _deact()
        if prev:
            return {"message": "Active dataset deactivated", "previous": prev}
        return {"message": "No active dataset found"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/dataset/active/{dataset_id}")
def activate_dataset(dataset_id: int, _admin: dict[str, Any] = Depends(require_admin())) -> dict[str, Any]:
    """Admin endpoint to set a historical dataset as active by id."""
    try:
        from app.services.data_store import activate_dataset_by_id as _act

        prev = _act(dataset_id)
        if prev:
            return {"message": "Dataset activated", "dataset": prev}
        raise HTTPException(status_code=404, detail="Dataset not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/reports", response_model=ReportsResponse)
def get_reports(_current_user: dict[str, Any] = Depends(require_analyst_or_admin())) -> ReportsResponse:
    records = _load_scored_ads_optional()
    recommendations = _load_budget_recommendations_or_404()
    summary = build_summary(records)
    explained = add_explanations(recommendations)

    return {
        "summary": summary,
        "quality_distribution": chart_quality_distribution(records),
        "campaign_kpi": chart_campaign_kpi(records),
        "recommendation_count": len(recommendations),
        "recommendations": explained,
        "recommendation_plan": budget_plan(recommendations, total_budget=float(summary.get("total_spent", 0.0) or 0.0)),
    }