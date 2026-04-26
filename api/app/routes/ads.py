from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, File, Header, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel

from app.services.analytics_service import (
    build_summary,
    chart_campaign_kpi,
    chart_kpi_by_age,
    chart_kpi_by_gender,
    chart_quality_distribution,
    filter_ads,
)
from app.services.data_store import (
    load_budget_recommendations,
    load_scored_ads,
    reload_budget_recommendations,
    reload_scored_ads,
)
from app.services.experiment_service import (
    build_defense_summary,
    build_model_evidence,
    experiment_decision,
    load_experiment_metrics,
    load_top_features,
)
from app.services.auth_service import (
    authenticate_user,
    change_own_password,
    create_session,
    create_user_account,
    delete_user_account,
    get_current_session,
    list_users_page,
    require_roles,
    revoke_session,
    update_user_account,
)
from app.services.ingestion_service import build_analysis_from_csv, save_uploaded_file
from app.services.recommendation_service import add_explanations, budget_plan, explain_segment, filter_segments
from app.services.upload_log_service import append_upload_log, read_upload_logs_page


router = APIRouter(prefix="/api", tags=["ads"])


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str
    full_name: str


class UpdateUserRequest(BaseModel):
    role: str | None = None
    full_name: str | None = None
    password: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization must use Bearer token.")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid bearer token.")
    return token


def _require_session(authorization: str | None) -> dict[str, Any]:
    token = _extract_bearer_token(authorization)
    try:
        session = get_current_session(token)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid token.")
    return session


@router.post("/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    try:
        user = authenticate_user(payload.username.strip(), payload.password)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
    if not user:
        raise HTTPException(status_code=401, detail="Sai ten dang nhap hoac mat khau.")
    return create_session(user)


@router.get("/auth/me")
def me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    session = _require_session(authorization)
    return {
        "username": session["username"],
        "full_name": session["full_name"],
        "role": session["role"],
        "expires_at": session["expires_at"].isoformat(),
    }


@router.post("/auth/logout")
def logout(authorization: str | None = Header(default=None)) -> dict[str, str]:
    token = _extract_bearer_token(authorization)
    revoke_session(token)
    return {"message": "Da dang xuat."}


@router.get("/auth/users")
def get_users(
    authorization: str | None = Header(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
    role: str | None = Query(default=None),
) -> dict[str, Any]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    try:
        result = list_users_page(page=page, page_size=page_size, query=q, role=role)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
    return result


@router.post("/auth/users")
def create_user(payload: CreateUserRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"admin"})
        created = create_user_account(
            username=payload.username,
            password=payload.password,
            role=payload.role,
            full_name=payload.full_name,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    return {"message": "Tao tai khoan thanh cong.", "user": created}


@router.patch("/auth/users/{username}")
def update_user(
    username: str,
    payload: UpdateUserRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"admin"})
        updated = update_user_account(
            username=username,
            role=payload.role,
            full_name=payload.full_name,
            password=payload.password,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    return {"message": "Cap nhat tai khoan thanh cong.", "user": updated}


@router.delete("/auth/users/{username}")
def delete_user(username: str, authorization: str | None = Header(default=None)) -> dict[str, str]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"admin"})
        if session["username"] == username:
            raise ValueError("Cannot delete current logged in admin.")
        delete_user_account(username)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    return {"message": "Da xoa tai khoan."}


@router.post("/auth/change-password")
def change_password(payload: ChangePasswordRequest, authorization: str | None = Header(default=None)) -> dict[str, str]:
    session = _require_session(authorization)
    try:
        change_own_password(
            username=str(session["username"]),
            old_password=payload.old_password,
            new_password=payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    return {"message": "Doi mat khau thanh cong."}


@router.post("/data/upload")
def upload_ad_data(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"analyst", "admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

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

    append_upload_log(
        file_name=file.filename,
        file_path=str(saved_path),
        scored_rows=int(result.get("scored_rows", 0)),
        segment_rows=int(result.get("segment_rows", 0)),
        uploader_role=session["role"],
        uploader_name=session["username"],
    )

    return {
        "message": "Upload successful and analysis rebuilt.",
        "file_path": str(saved_path),
        **result,
    }


@router.get("/data/upload-logs")
def get_upload_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    uploader_name: str | None = Query(default=None),
    file_name: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

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
def reload_data() -> dict[str, int]:
    records = reload_scored_ads()
    recommendation_rows = reload_budget_recommendations()
    return {"rows": len(records), "recommendation_rows": len(recommendation_rows)}


@router.get("/ads")
def get_ads(
    campaign_id: str | None = Query(default=None),
    age: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    quality_label: str | None = Query(default=None),
    min_ctr: float | None = Query(default=None),
    max_cpa: float | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=2000),
) -> dict[str, Any]:
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filtered = filter_ads(
        records,
        campaign_id=campaign_id,
        age=age,
        gender=gender,
        quality_label=quality_label,
        min_ctr=min_ctr,
        max_cpa=max_cpa,
    )

    return {
        "total": len(filtered),
        "items": filtered[:limit],
    }


@router.get("/summary")
def get_summary(
    campaign_id: str | None = Query(default=None),
    age: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    quality_label: str | None = Query(default=None),
    min_ctr: float | None = Query(default=None),
    max_cpa: float | None = Query(default=None),
) -> dict[str, Any]:
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filtered = filter_ads(
        records,
        campaign_id=campaign_id,
        age=age,
        gender=gender,
        quality_label=quality_label,
        min_ctr=min_ctr,
        max_cpa=max_cpa,
    )

    return build_summary(filtered)


@router.get("/charts/quality-distribution")
def get_quality_distribution_chart(
    campaign_id: str | None = Query(default=None),
    age: str | None = Query(default=None),
    gender: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filtered = filter_ads(records, campaign_id=campaign_id, age=age, gender=gender)
    return chart_quality_distribution(filtered)


@router.get("/charts/campaign-kpi")
def get_campaign_kpi_chart(
    quality_label: str | None = Query(default=None),
    group_by: str = Query(default="campaign_id", pattern="^(campaign_id|fb_campaign_id)$"),
    top_n: int = Query(default=12, ge=3, le=30),
) -> dict[str, Any]:
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filtered = filter_ads(records, quality_label=quality_label)
    return chart_campaign_kpi(filtered, group_by=group_by, top_n=top_n)


@router.get("/charts/age-kpi")
def get_age_kpi_chart(
    campaign_id: str | None = Query(default=None),
    gender: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filtered = filter_ads(records, campaign_id=campaign_id, gender=gender)
    return chart_kpi_by_age(filtered)


@router.get("/charts/gender-kpi")
def get_gender_kpi_chart(
    campaign_id: str | None = Query(default=None),
    age: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filtered = filter_ads(records, campaign_id=campaign_id, age=age)
    return chart_kpi_by_gender(filtered)


@router.get("/recommendations/segments")
def get_recommendation_segments(
    campaign_id: str | None = Query(default=None),
    age: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    suggested_action: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    try:
        records = load_budget_recommendations()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filtered = filter_segments(
        records,
        campaign_id=campaign_id,
        age=age,
        gender=gender,
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
) -> dict[str, Any]:
    try:
        records = load_budget_recommendations()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filtered = filter_segments(
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
    age: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    suggested_action: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> Response:
    try:
        records = load_budget_recommendations()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filtered = filter_segments(
        records,
        campaign_id=campaign_id,
        age=age,
        gender=gender,
        suggested_action=suggested_action,
    )
    ranked = sorted(filtered, key=lambda r: float(r.get("recommendation_score") or 0), reverse=True)[:limit]
    rows = add_explanations(ranked)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "segment_id",
            "campaign_id",
            "age",
            "gender",
            "suggested_action",
            "recommendation_score",
            "recommended_weight",
            "avg_cpa",
            "avg_cvr",
            "good_ratio",
            "explanation",
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="recommendation_segments.csv"'},
    )


@router.get("/recommendations/budget-plan/export.csv")
def export_budget_plan_csv(
    total_budget: float = Query(default=10000.0, gt=0),
    top_n: int = Query(default=10, ge=1, le=50),
    campaign_id: str | None = Query(default=None),
    suggested_action: str | None = Query(default=None),
) -> Response:
    try:
        records = load_budget_recommendations()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filtered = filter_segments(
        records,
        campaign_id=campaign_id,
        suggested_action=suggested_action,
    )

    plan = budget_plan(filtered, total_budget=total_budget, top_n=top_n)
    rows = add_explanations(plan["allocations"])

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "segment_id",
            "campaign_id",
            "age",
            "gender",
            "suggested_action",
            "recommendation_score",
            "weight",
            "allocated_budget",
            "expected_conversions",
            "explanation",
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="budget_plan.csv"'},
    )


@router.get("/recommendations/explain")
def explain_recommendation_segment(segment_id: str = Query(...)) -> dict[str, Any]:
    try:
        records = load_budget_recommendations()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    matched = [r for r in records if str(r.get("segment_id", "")) == segment_id]
    if not matched:
        raise HTTPException(status_code=404, detail=f"Segment not found: {segment_id}")

    row = matched[0]
    return {
        "segment_id": row.get("segment_id"),
        "campaign_id": row.get("campaign_id"),
        "age": row.get("age"),
        "gender": row.get("gender"),
        "suggested_action": row.get("suggested_action"),
        "recommendation_score": row.get("recommendation_score"),
        "explanation": explain_segment(row),
    }


@router.get("/filters/options")
def get_filter_options() -> dict[str, Any]:
    try:
        ad_records = load_scored_ads()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        recommendation_records = load_budget_recommendations()
    except FileNotFoundError:
        recommendation_records = []

    campaign_ids = sorted(
        {
            str(r.get("campaign_id", ""))
            for r in ad_records
            if str(r.get("campaign_id", "")).isdigit()
        }
    )
    ages = sorted(
        {
            str(r.get("age", ""))
            for r in ad_records
            if len(str(r.get("age", "")).split("-")) == 2 and all(part.isdigit() for part in str(r.get("age", "")).split("-"))
        }
    )
    genders = sorted(
        {
            str(r.get("gender", "")).upper()
            for r in ad_records
            if str(r.get("gender", "")).upper() in {"M", "F"}
        }
    )
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
        "ages": ages,
        "genders": genders,
        "quality_labels": quality_labels,
        "suggested_actions": suggested_actions,
    }


@router.get("/experiments/metrics")
def get_experiment_metrics(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"analyst", "admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        return load_experiment_metrics()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/experiments/top-features")
def get_experiment_top_features(
    limit: int = Query(default=20, ge=1, le=100),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"analyst", "admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        items = load_top_features(limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"total": len(items), "items": items}


@router.get("/experiments/decision")
def get_experiment_decision(
    objective: str = Query(default="balanced", pattern="^(balanced|precision|recall|auc)$"),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"analyst", "admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        metrics = load_experiment_metrics()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return experiment_decision(metrics, objective=objective)


@router.get("/experiments/defense-summary")
def get_experiment_defense_summary(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"analyst", "admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        metrics = load_experiment_metrics()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return build_defense_summary(metrics)


@router.get("/experiments/model-evidence")
def get_experiment_model_evidence(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    session = _require_session(authorization)
    try:
        require_roles(session, {"analyst", "admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        metrics = load_experiment_metrics()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return build_model_evidence(metrics)


@router.get("/experiments/metrics/export.csv")
def export_experiment_metrics_csv(authorization: str | None = Header(default=None)) -> Response:
    session = _require_session(authorization)
    try:
        require_roles(session, {"analyst", "admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        metrics = load_experiment_metrics()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["metric", "rule_baseline", "logistic_regression", "delta"])
    writer.writeheader()

    rule = metrics.get("rule_baseline", {})
    model = metrics.get("logistic_regression", {})
    delta = metrics.get("delta", {})

    for metric_name in ["accuracy", "precision", "recall", "f1", "roc_auc"]:
        writer.writerow(
            {
                "metric": metric_name,
                "rule_baseline": rule.get(metric_name),
                "logistic_regression": model.get(metric_name),
                "delta": delta.get(metric_name),
            }
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="experiment_metrics.csv"'},
    )


@router.get("/experiments/top-features/export.csv")
def export_experiment_top_features_csv(
    limit: int = Query(default=30, ge=1, le=200),
    authorization: str | None = Header(default=None),
) -> Response:
    session = _require_session(authorization)
    try:
        require_roles(session, {"analyst", "admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        items = load_top_features(limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["feature", "coefficient", "abs_coefficient"])
    writer.writeheader()
    writer.writerows(items)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="top_features.csv"'},
    )
