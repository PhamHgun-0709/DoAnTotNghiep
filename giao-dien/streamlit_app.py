from __future__ import annotations

import io
from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


st.set_page_config(page_title="Phân tích quảng cáo", page_icon="📊", layout="wide")


DEFAULT_API = "http://127.0.0.1:8000"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def fmt_vn_number(value: float | int, digits: int = 2) -> str:
    text = f"{float(value):,.{digits}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def style_action_rows(df: pd.DataFrame, action_col: str) -> Any:
    def _row_style(row: pd.Series) -> list[str]:
        action = str(row.get(action_col, ""))
        if action == "Tăng ngân sách":
            bg = "background-color: rgba(42,157,143,0.16);"
        elif action == "Giảm ngân sách":
            bg = "background-color: rgba(187,62,3,0.16);"
        else:
            bg = "background-color: rgba(0,95,115,0.12);"
        return [bg for _ in row.index]

    return df.style.apply(_row_style, axis=1)


def round_numeric_df(df: pd.DataFrame, digits: int = 2) -> pd.DataFrame:
    rounded = df.copy()
    numeric_cols = rounded.select_dtypes(include=["number"]).columns
    rounded[numeric_cols] = rounded[numeric_cols].round(digits)
    return rounded


def build_summary_insights(summary: dict[str, Any]) -> list[str]:
    insights: list[str] = []

    avg_ctr = float(summary.get("avg_ctr", 0.0))
    avg_cvr = float(summary.get("avg_cvr", 0.0))
    avg_cpa = float(summary.get("avg_cpa", 0.0))
    dist = summary.get("quality_distribution", {})
    total_ads = int(summary.get("total_ads", 0))

    if total_ads > 0:
        good_ratio = float(dist.get("good", 0)) / total_ads
        insights.append(f"Tỷ lệ quảng cáo tốt hiện tại là {fmt_pct(good_ratio)} trên tổng số mẫu.")

    insights.append(f"Tỷ lệ nhấp trung bình (CTR) đạt {fmt_pct(avg_ctr)}.")
    insights.append(f"Tỷ lệ chuyển đổi sau nhấp (CVR) đạt {fmt_pct(avg_cvr)}.")
    insights.append(f"Chi phí cho mỗi chuyển đổi (CPA) trung bình là {avg_cpa:.2f}.")

    if avg_cpa > 30:
        insights.append("CPA đang khá cao, nên ưu tiên nhóm có recommendation_score cao để giảm chi phí.")
    elif avg_cpa > 0:
        insights.append("CPA đang ở mức chấp nhận được; có thể tối ưu thêm bằng A/B test theo nhóm tuổi và giới tính.")

    return insights


def build_experiment_insights(metrics: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    rule = metrics.get("rule_baseline", {})
    model = metrics.get("logistic_regression", {})

    rule_precision = float(rule.get("precision", 0.0))
    model_precision = float(model.get("precision", 0.0))
    rule_recall = float(rule.get("recall", 0.0))
    model_recall = float(model.get("recall", 0.0))

    insights = [
        f"Theo mục tiêu '{decision.get('objective')}', mô hình khuyến nghị sử dụng là: {decision.get('winner')}.",
        f"Rule-based có Precision {fmt_pct(rule_precision)} và Recall {fmt_pct(rule_recall)}.",
        f"Logistic Regression có Precision {fmt_pct(model_precision)} và Recall {fmt_pct(model_recall)}.",
    ]

    if model_recall > rule_recall:
        insights.append("Mô hình học máy bắt được nhiều trường hợp chuyển đổi hơn (Recall cao hơn).")
    if rule_precision > model_precision:
        insights.append("Rule-based chính xác hơn khi gắn nhãn tốt (Precision cao hơn), phù hợp khi cần hạn chế false positive.")

    return insights


def format_action_label(action: str) -> str:
    mapping = {
        "increase_budget": "Tăng ngân sách",
        "keep_and_test": "Giữ ngân sách và tiếp tục A/B test",
        "reduce_budget": "Giảm ngân sách",
    }
    return mapping.get(action, action)


def _auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def setup_auth(api_base: str) -> dict[str, str | None]:
    st.sidebar.header("Tài khoản")
    st.sidebar.caption("Demo có sẵn: guest / analyst / admin (mật khẩu dạng <ten>123)")

    if "auth_token" not in st.session_state:
        st.session_state.auth_token = None
    if "role" not in st.session_state:
        st.session_state.role = "guest"
    if "username" not in st.session_state:
        st.session_state.username = "anonymous"
    if "full_name" not in st.session_state:
        st.session_state.full_name = "Khách"
    if "expires_at" not in st.session_state:
        st.session_state.expires_at = None

    if st.session_state.auth_token:
        try:
            me_data = api_get(api_base, "/api/auth/me", token=st.session_state.auth_token)
            st.session_state.role = me_data.get("role", "guest")
            st.session_state.username = me_data.get("username", "anonymous")
            st.session_state.full_name = me_data.get("full_name", "Khách")
            st.session_state.expires_at = me_data.get("expires_at")
        except Exception:
            st.session_state.auth_token = None
            st.session_state.role = "guest"
            st.session_state.username = "anonymous"
            st.session_state.full_name = "Khách"
            st.session_state.expires_at = None
            st.sidebar.warning("Phiên đăng nhập không còn hợp lệ. Vui lòng đăng nhập lại.")

    if st.session_state.auth_token:
        st.sidebar.success(
            f"Đã đăng nhập: {st.session_state.username} ({st.session_state.role})"
        )
        if st.session_state.expires_at:
            st.sidebar.caption(f"Hết hạn phiên: {st.session_state.expires_at}")
        if st.sidebar.button("Đăng xuất", use_container_width=True):
            try:
                api_post_json(api_base, "/api/auth/logout", {}, token=st.session_state.auth_token)
            except Exception:
                pass
            st.session_state.auth_token = None
            st.session_state.role = "guest"
            st.session_state.username = "anonymous"
            st.session_state.full_name = "Khách"
            st.session_state.expires_at = None
            api_get.clear()
            st.rerun()
    else:
        username = st.sidebar.text_input("Tên đăng nhập", value="guest")
        password = st.sidebar.text_input("Mật khẩu", type="password")
        if st.sidebar.button("Đăng nhập", use_container_width=True):
            try:
                payload = api_post_json(
                    api_base,
                    "/api/auth/login",
                    {"username": username.strip(), "password": password},
                )
                st.session_state.auth_token = payload.get("access_token")
                st.session_state.role = payload.get("role", "guest")
                st.session_state.username = payload.get("username", "anonymous")
                st.session_state.full_name = payload.get("full_name", "Khách")
                st.session_state.expires_at = payload.get("expires_at")
                api_get.clear()
                st.rerun()
            except requests.HTTPError as exc:
                st.sidebar.error(f"Đăng nhập thất bại: {exc}")

        st.sidebar.info("Bạn đang ở chế độ khách. Một số tính năng bị giới hạn.")

    return {
        "token": st.session_state.auth_token,
        "role": st.session_state.role,
        "username": st.session_state.username,
    }


@st.cache_data(ttl=20)
def api_get(
    api_base: str,
    path: str,
    params: dict[str, Any] | None = None,
    token: str | None = None,
) -> Any:
    res = requests.get(
        f"{api_base}{path}",
        params=params,
        headers=_auth_headers(token),
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


def api_post_json(
    api_base: str,
    path: str,
    payload: dict[str, Any],
    token: str | None = None,
) -> Any:
    res = requests.post(
        f"{api_base}{path}",
        json=payload,
        headers=_auth_headers(token),
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


def api_patch_json(
    api_base: str,
    path: str,
    payload: dict[str, Any],
    token: str | None = None,
) -> Any:
    res = requests.patch(
        f"{api_base}{path}",
        json=payload,
        headers=_auth_headers(token),
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


def api_delete(api_base: str, path: str, token: str | None = None) -> Any:
    res = requests.delete(
        f"{api_base}{path}",
        headers=_auth_headers(token),
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


def api_get_bytes(
    api_base: str,
    path: str,
    params: dict[str, Any] | None = None,
    token: str | None = None,
) -> bytes:
    res = requests.get(
        f"{api_base}{path}",
        params=params,
        headers=_auth_headers(token),
        timeout=30,
    )
    res.raise_for_status()
    return res.content


def api_post_file(
    api_base: str,
    path: str,
    file_name: str,
    file_bytes: bytes,
    token: str,
) -> Any:
    files = {"file": (file_name, io.BytesIO(file_bytes), "text/csv")}
    res = requests.post(
        f"{api_base}{path}",
        files=files,
        headers=_auth_headers(token),
        timeout=120,
    )
    res.raise_for_status()
    return res.json()


def sidebar_filters(options: dict[str, Any]) -> dict[str, Any]:
    st.sidebar.header("Bộ lọc dữ liệu")

    campaign = st.sidebar.selectbox("Campaign", ["Tất cả"] + options.get("campaign_ids", []))
    age = st.sidebar.selectbox("Độ tuổi", ["Tất cả"] + options.get("ages", []))
    gender = st.sidebar.selectbox("Giới tính", ["Tất cả"] + options.get("genders", []))
    quality = st.sidebar.selectbox("Chất lượng", ["Tất cả"] + options.get("quality_labels", []))

    min_ctr = st.sidebar.number_input("CTR tối thiểu", min_value=0.0, value=0.0, step=0.0001, format="%.4f")
    max_cpa = st.sidebar.number_input("CPA tối đa (0 = bỏ qua)", min_value=0.0, value=0.0, step=0.5)

    return {
        "campaign_id": None if campaign == "Tất cả" else campaign,
        "age": None if age == "Tất cả" else age,
        "gender": None if gender == "Tất cả" else gender,
        "quality_label": None if quality == "Tất cả" else quality,
        "min_ctr": min_ctr if min_ctr > 0 else None,
        "max_cpa": max_cpa if max_cpa > 0 else None,
    }


def upload_section(api_base: str, role: str, token: str | None) -> None:
    st.subheader("Tải dữ liệu quảng cáo (CSV)")

    if role == "guest":
        st.warning("Tính năng tải dữ liệu yêu cầu quyền 'Phân tích' hoặc 'Quản trị'.")
        return

    uploaded = st.file_uploader("Chọn file CSV để phân tích", type=["csv"])
    c1, c2 = st.columns([1, 5])
    with c1:
        run_upload = st.button("Tải lên và phân tích", use_container_width=True)
    with c2:
        st.caption("Yêu cầu các cột chính: campaign_id, age, gender, impressions, clicks, spent, approved_conversion...")

    if run_upload:
        if uploaded is None:
            st.warning("Bạn cần chọn file CSV trước khi tải lên.")
            return
        if not token:
            st.error("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.")
            return
        try:
            payload = api_post_file(
                api_base,
                "/api/data/upload",
                uploaded.name,
                uploaded.getvalue(),
                token=token,
            )
            st.success(
                f"Tải lên thành công. Số dòng phân tích: {payload.get('scored_rows', 0)}, "
                f"số phân khúc recommendation: {payload.get('segment_rows', 0)}"
            )
            api_get.clear()
        except Exception as exc:
            st.error(f"Không thể xử lý file tải lên: {exc}")


def show_summary(summary: dict[str, Any]) -> None:
    st.subheader("Tổng quan chiến dịch")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng số quảng cáo", int(summary.get("total_ads", 0)))
    m2.metric("Tổng chi tiêu", fmt_vn_number(summary.get("total_spent", 0), 2))
    m3.metric("Tổng chuyển đổi", fmt_vn_number(summary.get("total_approved_conversion", 0), 0))
    m4.metric("CTR trung bình", fmt_pct(float(summary.get("avg_ctr", 0.0))))

    m5, m6, m7 = st.columns(3)
    m5.metric("CVR trung bình", fmt_pct(float(summary.get("avg_cvr", 0.0))))
    m6.metric("CPC trung bình", fmt_vn_number(summary.get("avg_cpc", 0), 2))
    m7.metric("CPA trung bình", fmt_vn_number(summary.get("avg_cpa", 0), 2))

    st.markdown("**Nhận xét tự động:**")
    for line in build_summary_insights(summary):
        st.write(f"- {line}")


def show_charts(api_base: str, filters: dict[str, Any]) -> None:
    quality = api_get(api_base, "/api/charts/quality-distribution", {
        "campaign_id": filters["campaign_id"],
        "age": filters["age"],
        "gender": filters["gender"],
    })
    age_kpi = api_get(api_base, "/api/charts/age-kpi", {
        "campaign_id": filters["campaign_id"],
        "gender": filters["gender"],
    })
    gender_kpi = api_get(api_base, "/api/charts/gender-kpi", {
        "campaign_id": filters["campaign_id"],
        "age": filters["age"],
    })
    campaign_kpi = api_get(api_base, "/api/charts/campaign-kpi", {
        "quality_label": filters["quality_label"],
        "group_by": "campaign_id",
        "top_n": 12,
    })

    c1, c2 = st.columns(2)
    with c1:
        fig_quality = px.pie(names=quality["labels"], values=quality["values"], title="Phân bố chất lượng quảng cáo")
        st.plotly_chart(fig_quality)
    with c2:
        age_df = pd.DataFrame({"Độ tuổi": age_kpi["labels"], "CTR": age_kpi["ctr"], "CVR": age_kpi["cvr"]})
        fig_age = px.bar(age_df, x="Độ tuổi", y=["CTR", "CVR"], barmode="group", title="KPI theo độ tuổi")
        st.plotly_chart(fig_age)

    c3, c4 = st.columns(2)
    with c3:
        gender_df = pd.DataFrame({"Giới tính": gender_kpi["labels"], "CTR": gender_kpi["ctr"], "CVR": gender_kpi["cvr"]})
        fig_gender = px.bar(gender_df, x="Giới tính", y=["CTR", "CVR"], barmode="group", title="KPI theo giới tính")
        st.plotly_chart(fig_gender)
    with c4:
        camp_df = pd.DataFrame({"Campaign": campaign_kpi["labels"], "CTR": campaign_kpi["ctr"], "CVR": campaign_kpi["cvr"]})
        fig_campaign = px.bar(camp_df, y="Campaign", x=["CTR", "CVR"], barmode="group", orientation="h", title="Top campaign theo KPI")
        st.plotly_chart(fig_campaign)


def show_recommendations(api_base: str, filters: dict[str, Any]) -> None:
    st.subheader("Khuyến nghị phân bổ ngân sách")
    rec = api_get(api_base, "/api/recommendations/segments", {
        "campaign_id": filters["campaign_id"],
        "age": filters["age"],
        "gender": filters["gender"],
        "limit": 20,
    })
    rec_df = pd.DataFrame(rec.get("items", []))

    if rec_df.empty:
        st.info("Không có dữ liệu khuyến nghị với bộ lọc hiện tại.")
    else:
        display_df = rec_df[["segment_id", "suggested_action", "recommendation_score", "avg_cpa", "good_ratio"]].copy()
        display_df = display_df.rename(
            columns={
                "segment_id": "Mã phân khúc",
                "suggested_action": "Hành động đề xuất",
                "recommendation_score": "Điểm khuyến nghị",
                "avg_cpa": "CPA trung bình",
                "good_ratio": "Tỷ lệ quảng cáo tốt",
            }
        )
        display_df["Hành động đề xuất"] = display_df["Hành động đề xuất"].map(format_action_label)
        display_df["Điểm khuyến nghị"] = display_df["Điểm khuyến nghị"].map(lambda v: fmt_vn_number(v, 2))
        display_df["CPA trung bình"] = display_df["CPA trung bình"].map(lambda v: fmt_vn_number(v, 2))
        display_df["Tỷ lệ quảng cáo tốt"] = display_df["Tỷ lệ quảng cáo tốt"].map(lambda v: fmt_pct(float(v)))
        st.dataframe(style_action_rows(display_df, "Hành động đề xuất"))

        segment_id = st.selectbox("Xem giải thích chi tiết theo segment", rec_df["segment_id"].tolist())
        detail = api_get(api_base, "/api/recommendations/explain", {"segment_id": segment_id})
        st.info(
            f"Phân khúc {detail.get('segment_id')} | "
            f"Hành động: {format_action_label(str(detail.get('suggested_action', '')))}\n\n"
            f"Giải thích: {detail.get('explanation', '')}"
        )

    st.markdown(
        f"[Tải CSV khuyến nghị segment]({api_base}/api/recommendations/segments/export.csv?limit=300)"
    )


def show_budget_plan(api_base: str, filters: dict[str, Any]) -> None:
    st.subheader("Mô phỏng kế hoạch ngân sách")
    c1, c2 = st.columns(2)
    with c1:
        total_budget = st.number_input("Tổng ngân sách", min_value=1000.0, value=50000.0, step=500.0)
    with c2:
        top_n = st.slider("Top N segment", min_value=3, max_value=30, value=8)

    plan = api_get(api_base, "/api/recommendations/budget-plan", {
        "total_budget": total_budget,
        "top_n": top_n,
        "campaign_id": filters["campaign_id"],
    })

    st.caption(
        f"Số segment sử dụng: {plan.get('segments_used', 0)} | "
        f"Expected total conversions: {fmt_vn_number(plan.get('expected_total_conversions', 0), 2)}"
    )

    plan_df = pd.DataFrame(plan.get("allocations", []))
    if not plan_df.empty:
        display_cols = [
            "segment_id",
            "suggested_action",
            "recommendation_score",
            "weight",
            "allocated_budget",
            "expected_conversions",
        ]
        display_df = plan_df[display_cols].copy()
        display_df = display_df.rename(
            columns={
                "segment_id": "Mã phân khúc",
                "suggested_action": "Hành động đề xuất",
                "recommendation_score": "Điểm khuyến nghị",
                "weight": "Tỷ trọng phân bổ",
                "allocated_budget": "Ngân sách phân bổ",
                "expected_conversions": "Chuyển đổi kỳ vọng",
            }
        )
        display_df["Hành động đề xuất"] = display_df["Hành động đề xuất"].map(format_action_label)
        display_df["Điểm khuyến nghị"] = display_df["Điểm khuyến nghị"].map(lambda v: fmt_vn_number(v, 2))
        display_df["Tỷ trọng phân bổ"] = display_df["Tỷ trọng phân bổ"].map(lambda v: fmt_pct(float(v)))
        display_df["Ngân sách phân bổ"] = display_df["Ngân sách phân bổ"].map(lambda v: fmt_vn_number(v, 2))
        display_df["Chuyển đổi kỳ vọng"] = display_df["Chuyển đổi kỳ vọng"].map(lambda v: fmt_vn_number(v, 2))
        st.dataframe(style_action_rows(display_df, "Hành động đề xuất"))

        if "explanation" in plan_df.columns:
            selected_segment = st.selectbox(
                "Xem giải thích kế hoạch theo phân khúc",
                plan_df["segment_id"].tolist(),
                key="budget_segment_explain",
            )
            selected_row = plan_df[plan_df["segment_id"] == selected_segment].iloc[0]
            st.info(str(selected_row.get("explanation", "")))

    st.markdown(
        f"[Tải CSV budget plan]({api_base}/api/recommendations/budget-plan/export.csv?total_budget={total_budget}&top_n={top_n})"
    )


def show_experiments(api_base: str, role: str, token: str | None) -> None:
    st.subheader("So sánh Rule-based và Mô hình")

    if role == "guest":
        st.warning("Mục thực nghiệm mô hình yêu cầu quyền 'Phân tích' hoặc 'Quản trị'.")
        return

    objective = st.selectbox("Mục tiêu đánh giá", ["balanced", "precision", "recall", "auc"])

    metrics = api_get(api_base, "/api/experiments/metrics", token=token)
    decision = api_get(api_base, "/api/experiments/decision", {"objective": objective}, token=token)
    features = api_get(api_base, "/api/experiments/top-features", {"limit": 15}, token=token)
    defense = api_get(api_base, "/api/experiments/defense-summary", token=token)

    compare_df = pd.DataFrame(
        {
            "metric": ["accuracy", "precision", "recall", "f1", "roc_auc"],
            "rule_baseline": [metrics["rule_baseline"][k] for k in ["accuracy", "precision", "recall", "f1", "roc_auc"]],
            "logistic_regression": [metrics["logistic_regression"][k] for k in ["accuracy", "precision", "recall", "f1", "roc_auc"]],
        }
    )
    fig_compare = px.bar(compare_df, x="metric", y=["rule_baseline", "logistic_regression"], barmode="group", title="So sánh metrics")
    st.plotly_chart(fig_compare)

    st.info(
        f"Objective: {decision.get('objective')} | Winner: {decision.get('winner')} | "
        f"Weighted delta: {decision.get('weighted_delta')}"
    )

    feature_df = pd.DataFrame(features.get("items", []))
    if not feature_df.empty:
        st.dataframe(round_numeric_df(feature_df, 2))

    st.markdown("**Nhận xét mô hình tự động:**")
    for line in build_experiment_insights(metrics, decision):
        st.write(f"- {line}")

    st.success(defense.get("headline", ""))
    for point in defense.get("key_points", []):
        st.write(f"- {point}")

    c1, c2 = st.columns(2)
    with c1:
        try:
            metrics_csv = api_get_bytes(api_base, "/api/experiments/metrics/export.csv", token=token)
            st.download_button(
                "Tải CSV metrics",
                data=metrics_csv,
                file_name="experiment_metrics.csv",
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"Không tải được CSV metrics: {exc}")
    with c2:
        try:
            features_csv = api_get_bytes(
                api_base,
                "/api/experiments/top-features/export.csv",
                params={"limit": 50},
                token=token,
            )
            st.download_button(
                "Tải CSV top-features",
                data=features_csv,
                file_name="top_features.csv",
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"Không tải được CSV top-features: {exc}")


def show_upload_logs(api_base: str, role: str, token: str | None) -> None:
    if role != "admin":
        return

    st.subheader("Nhật ký tải dữ liệu")
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1:
        uploader_filter = st.text_input("Tìm theo uploader", key="log_uploader_filter")
    with c2:
        file_filter = st.text_input("Tìm theo file", key="log_file_filter")
    with c3:
        log_page_size = st.selectbox("Rows/trang", [20, 50, 100], index=1, key="log_page_size")
    with c4:
        log_page = st.number_input("Trang", min_value=1, value=1, step=1, key="log_page")

    logs = api_get(
        api_base,
        "/api/data/upload-logs",
        {
            "page": int(log_page),
            "page_size": int(log_page_size),
            "uploader_name": uploader_filter.strip() or None,
            "file_name": file_filter.strip() or None,
        },
        token=token,
    )
    items = logs.get("items", [])
    total = int(logs.get("total", 0))
    st.caption(f"Tổng bản ghi: {total}")

    if not items:
        st.info("Chưa có lịch sử tải dữ liệu.")
        return

    st.dataframe(round_numeric_df(pd.DataFrame(items), 2), use_container_width=True)


def show_user_management(api_base: str, role: str, token: str | None) -> None:
    st.subheader("Tài khoản hệ thống")

    if token:
        with st.expander("Đổi mật khẩu cá nhân", expanded=False):
            old_password = st.text_input("Mật khẩu cũ", type="password", key="self_old_password")
            new_password = st.text_input("Mật khẩu mới", type="password", key="self_new_password")
            if st.button("Đổi mật khẩu", key="btn_change_self_password", use_container_width=True):
                try:
                    api_post_json(
                        api_base,
                        "/api/auth/change-password",
                        {"old_password": old_password, "new_password": new_password},
                        token=token,
                    )
                    st.success("Đổi mật khẩu thành công.")
                except requests.HTTPError as exc:
                    st.error(f"Không đổi được mật khẩu: {exc}")

    if role != "admin":
        st.info("Quản lý tài khoản (tạo/sửa/xóa) chỉ dành cho admin.")
        return

    f1, f2, f3, f4 = st.columns([2, 2, 1, 1])
    with f1:
        user_query = st.text_input("Tìm username/họ tên", key="user_query")
    with f2:
        user_role_filter = st.selectbox("Lọc vai trò", ["Tất cả", "guest", "analyst", "admin"], key="user_role_filter")
    with f3:
        user_page_size = st.selectbox("Rows/trang user", [10, 20, 50], index=1, key="user_page_size")
    with f4:
        user_page = st.number_input("Trang user", min_value=1, value=1, step=1, key="user_page")

    users = api_get(
        api_base,
        "/api/auth/users",
        {
            "page": int(user_page),
            "page_size": int(user_page_size),
            "q": user_query.strip() or None,
            "role": None if user_role_filter == "Tất cả" else user_role_filter,
        },
        token=token,
    )
    user_df = pd.DataFrame(users.get("items", []))
    st.caption(f"Tổng tài khoản: {int(users.get('total', 0))}")

    if user_df.empty:
        st.info("Không có tài khoản.")
    else:
        st.dataframe(user_df, use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Tạo tài khoản mới**")
        new_username = st.text_input("Username", key="new_user_username")
        new_full_name = st.text_input("Họ tên", key="new_user_full_name")
        new_role = st.selectbox("Vai trò", ["guest", "analyst", "admin"], key="new_user_role")
        new_password = st.text_input("Mật khẩu ban đầu", type="password", key="new_user_password")
        if st.button("Tạo tài khoản", key="btn_create_user", use_container_width=True):
            try:
                api_post_json(
                    api_base,
                    "/api/auth/users",
                    {
                        "username": new_username,
                        "password": new_password,
                        "role": new_role,
                        "full_name": new_full_name,
                    },
                    token=token,
                )
                api_get.clear()
                st.success("Đã tạo tài khoản mới.")
                st.rerun()
            except requests.HTTPError as exc:
                st.error(f"Không tạo được tài khoản: {exc}")

    with c2:
        st.markdown("**Sửa hoặc xóa tài khoản**")
        usernames = user_df["username"].tolist() if not user_df.empty else []
        selected_user = st.selectbox("Chọn user", usernames, key="manage_selected_user") if usernames else None

        edit_full_name = st.text_input("Họ tên mới (tùy chọn)", key="edit_user_full_name")
        edit_role = st.selectbox("Vai trò mới", ["(Giữ nguyên)", "guest", "analyst", "admin"], key="edit_user_role")
        edit_password = st.text_input("Mật khẩu mới (tùy chọn)", type="password", key="edit_user_password")

        if st.button("Cập nhật user", key="btn_update_user", use_container_width=True):
            if not selected_user:
                st.warning("Chưa chọn user.")
            else:
                payload: dict[str, Any] = {}
                if edit_full_name.strip():
                    payload["full_name"] = edit_full_name.strip()
                if edit_role != "(Giữ nguyên)":
                    payload["role"] = edit_role
                if edit_password.strip():
                    payload["password"] = edit_password.strip()

                try:
                    api_patch_json(api_base, f"/api/auth/users/{selected_user}", payload, token=token)
                    api_get.clear()
                    st.success("Đã cập nhật user.")
                    st.rerun()
                except requests.HTTPError as exc:
                    st.error(f"Không cập nhật được user: {exc}")

        if st.button("Xóa user", key="btn_delete_user", use_container_width=True):
            if not selected_user:
                st.warning("Chưa chọn user.")
            else:
                try:
                    api_delete(api_base, f"/api/auth/users/{selected_user}", token=token)
                    api_get.clear()
                    st.success("Đã xóa user.")
                    st.rerun()
                except requests.HTTPError as exc:
                    st.error(f"Không xóa được user: {exc}")


def main() -> None:
    st.title("Hệ thống phân tích và tối ưu chiến dịch quảng cáo")
    st.caption("Phiên bản Streamlit: giao diện tiếng Việt có dấu, thao tác ngắn gọn, dễ demo đồ án.")

    api_base = st.sidebar.text_input("API Base URL", value=DEFAULT_API).rstrip("/")
    auth = setup_auth(api_base)
    token = str(auth.get("token") or "") or None
    role = str(auth.get("role") or "guest")

    if role != "guest":
        upload_section(api_base, role, token)

    try:
        options = api_get(api_base, "/api/filters/options")
        filters = sidebar_filters(options)

        summary = api_get(api_base, "/api/summary", filters)
        show_summary(summary)

        show_charts(api_base, filters)
        show_recommendations(api_base, filters)
        show_budget_plan(api_base, filters)
        show_experiments(api_base, role, token)
        show_upload_logs(api_base, role, token)
        show_user_management(api_base, role, token)
    except requests.HTTPError as exc:
        st.error(f"Lỗi HTTP từ API: {exc}")
    except requests.RequestException as exc:
        st.error(f"Không kết nối được API. Kiểm tra server backend. Chi tiết: {exc}")
    except Exception as exc:
        st.error(f"Đã xảy ra lỗi: {exc}")


if __name__ == "__main__":
    main()
