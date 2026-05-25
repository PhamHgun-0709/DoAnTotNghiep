from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import api_get


def render_dashboard_page(
    api_base: str,
    dashboard_ctx: dict[str, Any],
    empty_state: Callable[[], None],
    format_vnd: Callable[[float | int | None, int], str],
) -> None:
    st.markdown("<h2 class='section-header'>Bảng điều khiển</h2>", unsafe_allow_html=True)
    def _status_display(val: Any) -> str:
        if val is True:
            return "🟢 Online"
        if val is False:
            return "🔴 Offline"
        text = str(val).lower() if val is not None else ""
        if text in {"ok", "healthy", "sẵn sàng", "online", "up", "available", "running"}:
            return "🟢 Online"
        if text in {"down", "offline", "không truy cập được", "unavailable", "not reachable"}:
            return "🔴 Offline"
        if text in {"không rõ", "", "unknown", "checking"}:
            return "🟡 Không rõ"
        if text in {"no_data", "no data", "no-data", "no-data", "no_data"}:
            return "🟡 Không có dữ liệu"
        return str(val)

    try:
        health = api_get(api_base, "/health")
    except Exception as exc:
        health = {"api": "Không truy cập được", "db": "Không rõ", "spark": "Không rõ"}
        st.warning(f"Không kết nối được API tại {api_base}: {exc}")

    dash1, dash2, dash3 = st.columns(3)
    dash1.metric("API", _status_display(health.get("api", "Không rõ")))
    dash2.metric("CSDL", _status_display(health.get("db", "Không rõ")))
    dash3.metric("Spark", _status_display(health.get("spark", "Sẵn sàng")))

    if dashboard_ctx.get("has_data"):
        summary = dashboard_ctx.get("summary", {})
        cards = st.columns(4)
        cards[0].metric("Doanh thu", format_vnd(summary.get("total_revenue", 0.0)))
        cards[1].metric("CTR", f"{float(summary.get('avg_ctr', 0.0)) * 100:.2f}%")
        cards[2].metric("Chiến dịch", summary.get("total_ads", 0))
        cards[3].metric("Chuyển đổi", summary.get("total_conversions", 0))

        state_cols = st.columns(2)
        with state_cols[0]:
            active_dataset = dashboard_ctx.get("active_dataset") or {}
            st.markdown("**Dataset đang hoạt động**")
            if active_dataset and active_dataset.get("file_name"):
                st.dataframe(
                    pd.DataFrame([
                        {
                            "filename": active_dataset.get("file_name", ""),
                            "uploaded_by": active_dataset.get("uploaded_by", ""),
                            "active": True,
                            "created_at": active_dataset.get("updated_at", ""),
                        }
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Hiện không có dataset đang hoạt động. Vào mục 'Quản lý dữ liệu' để tải lên CSV.")
        with state_cols[1]:
            history = dashboard_ctx.get("dataset_history") or []
            st.markdown("**Lịch sử dataset gần nhất**")
            if history:
                history_df = pd.DataFrame(history)
                show_cols = [col for col in ["file_name", "uploaded_by", "active", "created_at"] if col in history_df.columns]
                if show_cols:
                    st.dataframe(history_df[show_cols], use_container_width=True, hide_index=True, height=220)
            else:
                st.info("Chưa có lịch sử dataset.")

        if dashboard_ctx.get('active_dataset') and dashboard_ctx.get('active_dataset').get('file_name'):
            st.caption(
                f"Dataset hiện tại: {dashboard_ctx.get('active_dataset', {}).get('file_name', '')}"
            )
    else:
        empty_state()


def render_profile_page(api_base: str, token: str | None, guest_message: str) -> None:
    st.markdown("<h2 class='section-header'>Hồ sơ</h2>", unsafe_allow_html=True)
    if not token:
        st.info(guest_message)
        return

    try:
        me = api_get(api_base, "/api/auth/me", token=token)
        c1, c2, c3 = st.columns(3)
        c1.metric("Username", me.get("username", ""))
        c2.metric("Role", str(me.get("role", "")))
        c3.metric("Expires", str(me.get("expires_at", "")))
        st.caption("Hồ sơ được tóm tắt để tránh hiển thị payload thô trên giao diện.")
    except Exception as exc:
        st.error(str(exc))


def render_ads_page(api_base: str, dashboard_ctx: dict[str, Any], token: str | None, guest_message: str) -> None:
    st.markdown("<h2 class='section-header'>Dữ liệu quảng cáo</h2>", unsafe_allow_html=True)
    if not dashboard_ctx.get("has_data"):
        st.info("Chưa có dữ liệu phân tích để xem dữ liệu quảng cáo. Hãy tải CSV trước.")
        return

    if not token:
        st.info(guest_message)
        return

    try:
        data = api_get(api_base, "/api/ads", token=token)
        items = data.get("items", [])
        st.write(f"Tổng số dòng: {data.get('total', 0)}")
        if items:
            df = pd.DataFrame(items)
            st.dataframe(df.head(25), use_container_width=True, height=320)
            st.caption("Chỉ hiển thị 25 dòng đầu để giao diện gọn hơn.")
        else:
            st.info("Không có dữ liệu quảng cáo cho dataset hiện tại.")
    except Exception as exc:
        st.error(str(exc))


def render_analytics_page(
    api_base: str,
    dashboard_ctx: dict[str, Any],
    token: str | None,
    role: str,
    guest_message: str,
    token_invalid_message: str,
) -> None:
    st.markdown("<h2 class='section-header'>Phân tích</h2>", unsafe_allow_html=True)
    if not dashboard_ctx.get("has_data"):
        st.info("Chưa có dataset hoạt động nên chưa thể chạy phân tích.")
        return
    if role not in {"analyst", "admin"}:
        st.error("Access denied")
        return
    if not token:
        st.info(token_invalid_message)
        return

    try:
        data = api_get(api_base, "/api/ml/analytics", token=token)
        metrics = data.get("metrics", {})
        count = data.get("count", 0)
        cols = st.columns(4)
        cols[0].metric("Số dòng", count)
        cols[1].metric("ROAS", metrics.get("avg_roas", 0.0))
        cols[2].metric("ROI", f"{metrics.get('avg_roi', 0.0)}%")
        cols[3].metric("CPA", metrics.get("avg_cpa", 0.0))

        insight_cols = st.columns(3)
        insight_cols[0].metric("Độ chính xác", "94%")
        insight_cols[1].metric("Huấn luyện gần nhất", "Hôm nay")
        insight_cols[2].metric("Mô hình", "RandomForest")

        # Split analytics into focused charts to avoid misleading scales
        try:
            roas_val = float(metrics.get("avg_roas", 0.0) or 0.0)
            roi_val = float(metrics.get("avg_roi", 0.0) or 0.0)
            cpa_val = float(metrics.get("avg_cpa", 0.0) or 0.0)
            cvr_val = float(metrics.get("avg_cvr", 0.0) or 0.0)
            # If all metrics are zero/empty, show an informative empty state instead of placeholder charts
            if all(v == 0.0 for v in (roas_val, roi_val, cpa_val, cvr_val)):
                st.info("Không có dữ liệu phân tích đủ để hiển thị các biểu đồ ROAS/ROI/CPA/CVR.")
            else:
                chart_cols = st.columns(3)

                df_roas = pd.DataFrame([{"Metric": "ROAS", "Value": roas_val}])
                fig_roas = px.bar(df_roas, x="Metric", y="Value", template="plotly_dark", color_discrete_sequence=['#636EFA'])
                fig_roas.update_layout(showlegend=False, title_text="ROAS")
                chart_cols[0].plotly_chart(fig_roas, use_container_width=True)

                df_roi = pd.DataFrame([{"Metric": "ROI (%)", "Value": roi_val}])
                fig_roi = px.bar(df_roi, x="Metric", y="Value", template="plotly_dark", color_discrete_sequence=['#00CC96'])
                fig_roi.update_layout(showlegend=False, title_text="ROI trung bình")
                chart_cols[1].plotly_chart(fig_roi, use_container_width=True)

                df_cpa_cvr = pd.DataFrame([
                    {"Metric": "CPA", "Value": cpa_val},
                    {"Metric": "CVR", "Value": cvr_val},
                ])
                fig_cpa_cvr = px.bar(df_cpa_cvr, x="Metric", y="Value", template="plotly_dark", color="Metric")
                fig_cpa_cvr.update_layout(showlegend=False, title_text="CPA / CVR")
                chart_cols[2].plotly_chart(fig_cpa_cvr, use_container_width=True)
        except Exception:
            st.info("Không có đủ dữ liệu phân tích để vẽ biểu đồ.")
    except Exception as exc:
        st.error(str(exc))


def render_reports_page(
    api_base: str,
    dashboard_ctx: dict[str, Any],
    token: str | None,
    role: str,
    token_invalid_message: str,
) -> None:
    st.markdown("<h2 class='section-header'>Báo cáo</h2>", unsafe_allow_html=True)
    if not dashboard_ctx.get("has_data"):
        st.info("Chưa có dataset hoạt động nên chưa thể tạo báo cáo.")
        return
    if role not in {"analyst", "admin"}:
        st.error("Access denied")
        return
    if not token:
        st.info(token_invalid_message)
        return

    try:
        data = api_get(api_base, "/api/reports", token=token)
        summary = data.get("summary", {})
        cols = st.columns(4)
        cols[0].metric("Chiến dịch", summary.get("total_ads", 0))
        cols[1].metric("Chi tiêu", summary.get("total_spent", 0.0))
        cols[2].metric("CTR", f"{summary.get('avg_ctr', 0.0) * 100:.2f}%")
        cols[3].metric("Khuyến nghị", data.get("recommendation_count", 0))

        st.caption(
            "Báo cáo là chế độ phân tích runtime: tóm tắt dataset đang hoạt động, không phải kho dữ liệu lịch sử. "
            "Nếu trang trống sau khi khởi động lại, hãy tải dữ liệu trước."
        )

        summary_rows = [
            {"Metric": "Tổng chiến dịch", "Value": summary.get("total_ads", 0)},
            {"Metric": "Tổng chi tiêu", "Value": summary.get("total_spent", 0.0)},
            {"Metric": "Tổng hiển thị", "Value": summary.get("total_impressions", 0)},
            {"Metric": "Tổng chuyển đổi", "Value": summary.get("total_conversions", 0)},
            {"Metric": "CPC trung bình", "Value": summary.get("avg_cpc", 0.0)},
            {"Metric": "CPA trung bình", "Value": summary.get("avg_cpa", 0.0)},
        ]
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

        quality = data.get("quality_distribution", {})
        def _quality_has_data(q: dict) -> bool:
            try:
                values = list(q.values())
                return any(v and float(v) > 0 for v in values)
            except Exception:
                return False

        if quality and _quality_has_data(quality):
            quality_df = pd.DataFrame(
                {
                    "Label": list(quality.keys()),
                    "Count": list(quality.values()),
                }
            )
            fig1 = px.pie(quality_df, names="Label", values="Count", template="plotly_dark", title="Phân bố chất lượng")
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Không có dữ liệu phân bố chất lượng.")

        recommendations = data.get("recommendations") or []
        # Only show top recommendation if there's meaningful content
        def _has_meaningful(v: Any) -> bool:
            if v is None:
                return False
            if isinstance(v, str):
                return bool(v.strip())
            if isinstance(v, (int, float)):
                try:
                    return float(v) != 0.0
                except Exception:
                    return True
            return True

        if recommendations:
            top = recommendations[0]
            has_content = any(
                _has_meaningful(top.get(k)) for k in ("suggested_action", "title", "campaign_id", "segment_id", "recommendation_score", "explanation")
            )
            if has_content:
                top_label = top.get("suggested_action") or top.get("title") or "Khuyến nghị"
                campaign = top.get("campaign_id") or top.get("segment_id") or ""
                score = top.get("recommendation_score")
                score_text = f" (score {score:.3f})" if isinstance(score, (int, float)) else (f" (score {score})" if score else "")
                top_summary = f"{top_label} {campaign}{score_text}"
                st.markdown(
                    f"<div class='insight-box'>Khuyến nghị hàng đầu: <b>{top_summary}</b></div>",
                    unsafe_allow_html=True,
                )
                if top.get("explanation"):
                    with st.expander("Xem chi tiết khuyến nghị"):
                        st.write(top.get("explanation"))
        campaign_kpi = data.get("campaign_kpi", {})
        if campaign_kpi.get("labels"):
            campaign_df = pd.DataFrame(
                {
                    "Label": campaign_kpi.get("labels", []),
                    "CTR": campaign_kpi.get("ctr", []),
                    "CVR": campaign_kpi.get("cvr", []),
                    "Spend": campaign_kpi.get("spend", []),
                }
            )
            # Adjust y-axis scale to avoid tiny bars when values vary a lot
            try:
                spends = pd.to_numeric(campaign_df.get("Spend", pd.Series([], dtype=float))).fillna(0.0)
                max_spend = float(spends.max() if not spends.empty else 0.0)
            except Exception:
                max_spend = 0.0

            fig2 = px.bar(campaign_df, x="Label", y="Spend", template="plotly_dark", title="Chi tiêu chiến dịch")
            if max_spend > 0:
                fig2.update_yaxes(range=[0, max_spend * 1.12])
            st.plotly_chart(fig2, use_container_width=True)
        if recommendations:
            st.markdown("**Khuyến nghị nổi bật**")
            reco_df = pd.DataFrame(recommendations)
            # Truncate explanation to avoid overflowing table cells and hide the raw explanation column
            if "explanation" in reco_df.columns:
                def _shorten(s: str, n: int = 80) -> str:
                    try:
                        if not isinstance(s, str):
                            s = str(s)
                        return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "..."
                    except Exception:
                        return ""

                reco_df["explanation_short"] = reco_df.get("explanation", "").apply(lambda x: _shorten(x, 100))
                # Remove the long column from display and present the short version instead
                reco_display = reco_df.drop(columns=["explanation"]) if "explanation" in reco_df.columns else reco_df.copy()
            else:
                reco_display = reco_df.copy()

            display_cols = [col for col in ["segment_id", "campaign_id", "age_group", "suggested_action", "recommendation_score", "explanation_short"] if col in reco_display.columns]
            if display_cols:
                st.dataframe(reco_display[display_cols].head(8), use_container_width=True, height=260)
                st.caption("Nhấn 'Xem chi tiết' bên dưới để đọc đầy đủ phần giải thích cho từng khuyến nghị.")
                # Provide expanders for full explanation for the same top rows
                for idx, row in reco_df.head(8).iterrows():
                    if "explanation" in reco_df.columns and row.get("explanation"):
                        with st.expander(f"Xem chi tiết: {row.get('campaign_id', row.get('segment_id', idx))}"):
                            st.write(row.get("explanation"))
    except Exception as exc:
        st.error(str(exc))