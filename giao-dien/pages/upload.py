"""Upload page extracted from streamlit_app.py

This module exposes `render_upload_page(...)` which receives helper
functions and variables from the main app to avoid circular imports.
"""
from typing import Any, Callable, Dict
import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime

def render_upload_page(
    api_base: str,
    dashboard_ctx: Dict[str, Any],
    token: str,
    role: str,
    t: Callable[[str], str],
    la_check_system_health,
    la_detect_columns,
    la_coerce_numeric_metrics_inplace,
    la_convert_money_columns_to_vnd_inplace,
    la_calculate_kpis,
    la_prepare_timeseries,
    la_kpi_trends_from_timeseries,
    la_aggregate_performance,
    la_spark_processing_panel,
    build_optimization_recommendations,
    extract_insights,
    create_conversion_funnel,
    create_trend_chart,
    roi_by_platform_chart,
    spend_vs_revenue_chart,
    ctr_heatmap_chart,
    la_budget_recommendation,
    budget_optimization_chart,
    render_kpi_card,
    format_vnd,
    format_percent,
    api_post_file,
    USD_TO_VND_RATE: float = 25000.0,
):
    st.markdown(f"<h2 class='section-header'>{t('upload_section_title')}</h2>", unsafe_allow_html=True)

    health = la_check_system_health(api_base)
    arch_left, arch_right = st.columns([3, 2])
    with arch_left:
        st.markdown(
            f"<div class='panel'><div class='panel-title'>{t('system_arch')}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("**Giao diện Streamlit → FastAPI → ETL Spark → Phân tích ML → PostgreSQL**")
        st.markdown(f"<div class='mono'>API_URL: {api_base}</div></div>", unsafe_allow_html=True)
    with arch_right:
        def badge(text: str, state: str) -> str:
            cls = 'status-running'
            if state in ['ONLINE', 'ACTIVE', 'READY']:
                cls = 'status-success'
            elif state in ['DEGRADED']:
                cls = 'status-warning'
            elif state in ['OFFLINE']:
                cls = 'status-danger'
            return f"<span class='status-badge {cls}'>{text}: {state}</span>"

        st.markdown(
            f"<div class='panel'><div class='panel-title'>{t('runtime_status')}</div>"
            + badge('API', health.get('api', 'UNKNOWN'))
            + badge('DB', health.get('db', 'UNKNOWN'))
            + badge('Spark', health.get('spark', 'READY'))
            + "</div>",
            unsafe_allow_html=True,
        )
    st.info(t('upload_info_dashboard'))

    uploaded_file = st.file_uploader(t('upload_csv'), type=['csv'])
    st.caption(t('upload_hint'))

    # Support caching the last processed upload so navigating away and back
    # does not require re-uploading the same file. Stored in Streamlit session_state.
    cached = st.session_state.get('last_upload')
    use_cached = False
    if cached and not uploaded_file:
        with st.expander("Cached upload available", expanded=False):
            st.write(f"File: {cached.get('file_name')} ({cached.get('file_size', 0)/1024/1024:.2f} MB)")
            if st.button("Use cached upload", key="use_cached_upload"):
                use_cached = True
            if st.button("Clear cached upload", key="clear_cached_upload"):
                st.session_state.pop('last_upload', None)
                cached = None

    if uploaded_file or use_cached:
        try:
            # If using cached results, restore variables from session_state
            if use_cached and cached:
                df = cached.get('df')
                cols = cached.get('cols') or {}
                kpis = cached.get('kpis') or {}
                daily = cached.get('daily')
                trends = cached.get('trends') or {}
                perf = cached.get('perf') or {}
                # skip reading/uploading
                uploaded_file = None
            else:
                with st.expander(t('api_upload_rbac'), expanded=False):
                    if role not in {"analyst", "admin"}:
                        st.info(t('upload_requires_role'))
                    elif not token:
                        st.info(t('token_invalid'))
                    else:
                        if st.button(t('api_upload_button'), use_container_width=True):
                            try:
                                with st.spinner("Đang tải tệp..."):
                                    payload = api_post_file(
                                        api_base,
                                        "/api/data/upload",
                                        uploaded_file.name,
                                        uploaded_file.getvalue(),
                                        token=str(token),
                                    )
                                st.success(f"{t('api_upload_ok')}: {payload.get('message', 'done') if isinstance(payload, dict) else payload}")
                                # Refresh dashboard context so main UI shows new data without requiring manual reload
                                try:
                                    from api_client import api_get as _api_get
                                    refreshed = _api_get(api_base, "/api/dashboard", token=token)
                                    if isinstance(refreshed, dict):
                                        dashboard_ctx.update(refreshed)
                                        st.info(t('upload_info_dashboard'))
                                except Exception:
                                    pass
                            except Exception as exc:
                                st.error(str(exc))

            if uploaded_file:
                if hasattr(uploaded_file, 'seek'):
                    uploaded_file.seek(0)

                status_box = st.empty()
                status_box.info("Đang chạy ETL Spark...")
                t0 = time.perf_counter()
                df = pd.read_csv(uploaded_file)
            else:
                # using cached; show a small notice
                status_box = st.empty()
                status_box.info("Sử dụng kết quả upload đã lưu (cached)")
                t0 = time.perf_counter()
            read_sec = time.perf_counter() - t0
            cols = la_detect_columns(df)
            la_coerce_numeric_metrics_inplace(df, cols)
            la_convert_money_columns_to_vnd_inplace(df, cols)
            kpis = la_calculate_kpis(df)
            daily = la_prepare_timeseries(df, cols)
            trends = la_kpi_trends_from_timeseries(daily, window_days=7)
            perf = la_aggregate_performance(df, cols)
            status_box.info("Đang tạo phân tích ML...")

            t1 = time.perf_counter()
            _ = perf.get('platform')
            _ = perf.get('campaign')
            _ = daily
            transform_sec = max(0.001, time.perf_counter() - t1)

            # determine file size safely: prefer uploaded_file, fall back to cached metadata
            file_size_bytes = 0
            if uploaded_file:
                try:
                    file_size_bytes = int(getattr(uploaded_file, 'size', 0) or 0)
                except Exception:
                    try:
                        # fallback: read buffer length
                        file_bytes = uploaded_file.getvalue()
                        file_size_bytes = len(file_bytes) if file_bytes is not None else 0
                    except Exception:
                        file_size_bytes = 0
            else:
                file_size_bytes = int(cached.get('file_size', 0) if cached else 0)

            file_mb = float(file_size_bytes) / 1024 / 1024 if file_size_bytes else 0.0

            spark_meta = la_spark_processing_panel(
                rows=len(df),
                file_mb=file_mb,
                df=df,
                cols=cols,
                measured_sec=(read_sec + transform_sec),
            )
            status_box.empty()

            # Cache processed upload in session_state so revisiting page can reuse
            try:
                st.session_state['last_upload'] = {
                    'file_name': uploaded_file.name if uploaded_file else (cached.get('file_name') if cached else None),
                    'file_size': file_size_bytes if file_size_bytes else (cached.get('file_size') if cached else 0),
                    'df': df,
                    'cols': cols,
                    'kpis': kpis,
                    'daily': daily,
                    'trends': trends,
                    'perf': perf,
                    'processed_at': time.time(),
                }
            except Exception:
                # avoid crashing UI on cache failures
                pass

            m1, m2, m3, m4 = st.columns(4)
            m1.metric(t('dataset_info_records'), f"{len(df):,}")
            m2.metric(t('dataset_info_columns'), len(df.columns)
                      )
            m3.metric(t('dataset_info_size'), f"{file_mb:.1f}MB")
            if cols.get('campaign_id') and cols['campaign_id'] in df.columns:
                m4.metric(t('dataset_info_campaigns'), int(df[cols['campaign_id']].nunique()))
            else:
                m4.metric(t('dataset_info_campaigns'), "--")

            st.markdown('---')
            st.markdown(f"<h2 class='section-header'>{t('kpi_title')}</h2>", unsafe_allow_html=True)
            kpi_cols = st.columns(6)
            render_kpi_card(kpi_cols[0], t('kpi_ctr_label'), format_percent(kpis.get('ctr', 0.0)), trends.get('ctr', None), "--primary")
            render_kpi_card(kpi_cols[1], t('kpi_cvr_label'), format_percent(kpis.get('cvr', 0.0)), trends.get('cvr', None), "--success")
            render_kpi_card(kpi_cols[2], "CPA", format_vnd(kpis.get('cpa', 0.0)), None, "--warning")
            render_kpi_card(kpi_cols[3], "ROAS", f"{kpis.get('roas', 0.0):.2f}x", trends.get('roas', None), "--purple")
            render_kpi_card(kpi_cols[4], t('chart_spend'), format_vnd(kpis.get('total_spend', 0.0)), None, "--danger")
            render_kpi_card(kpi_cols[5], t('chart_revenue'), format_vnd(kpis.get('total_revenue', 0.0)), None, "--cyan")
            st.caption(t('kpi_definitions'))

            # Recommendations, insights, charts (kept concise)
            st.markdown('---')
            st.markdown(f"<h2 class='section-header'>{t('opt_recos')}</h2>", unsafe_allow_html=True)
            platform_df = perf.get('platform')
            campaign_df = perf.get('campaign')
            segment_df = perf.get('segment')
            recos = build_optimization_recommendations(platform_df, campaign_df, segment_df)
            for r in recos:
                st.markdown(
                    f"<div class='reco-box'><b>{r['level']} {r['title']}</b><br/>{r['detail']}<br/><span style='color:#9ca3af'>{r['action']}</span></div>",
                    unsafe_allow_html=True,
                )

            st.markdown(f"<h2 class='section-header'>{t('insight_engine')}</h2>", unsafe_allow_html=True)
            st.caption("Tổng hợp insight tự động từ KPI & phân khúc (mục tiêu: chỉ ra điểm mạnh/yếu và hành động ưu tiên).")
            insights = extract_insights(df, kpis)
            for insight in insights[:6]:
                st.markdown(f"<div class='insight-box'>{insight}</div>", unsafe_allow_html=True)

            st.markdown('---')
            st.markdown(f"<h2 class='section-header'>{t('smart_analytics')}</h2>", unsafe_allow_html=True)
            c_left, c_right = st.columns(2)
            with c_left:
                st.subheader(t('conversion_funnel'))
                st.plotly_chart(create_conversion_funnel(df, kpis), use_container_width=True)
            with c_right:
                st.subheader(t('trend_analysis'))
                st.plotly_chart(create_trend_chart(df, kpis), use_container_width=True)
                st.caption(t('trend_caption'))

            if platform_df is not None and cols.get('platform'):
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader(t('roi_by_platform'))
                    st.plotly_chart(roi_by_platform_chart(platform_df, cols['platform']), use_container_width=True)
                with c2:
                    st.subheader(t('spend_vs_revenue'))
                    if daily is not None and not daily.empty and ('spend' in daily.columns or 'revenue' in daily.columns):
                        st.plotly_chart(spend_vs_revenue_chart(daily), use_container_width=True)
                    else:
                        st.info(t('no_time_series'))

            heat = ctr_heatmap_chart(df, cols)
            if heat is not None:
                st.subheader(t('ctr_heatmap'))
                st.caption("Trục X: nền tảng, trục Y: nhóm tuổi. Số trong ô là CTR (%) = Lượt nhấp / Lượt hiển thị; màu sáng hơn nghĩa là CTR cao hơn.")
                st.plotly_chart(heat, use_container_width=True)

            if platform_df is not None and cols.get('platform'):
                st.markdown(f"<h3 class='section-header'>{t('budget_optimization')}</h3>", unsafe_allow_html=True)
                reco_df = la_budget_recommendation(
                    platform_df.rename(columns={cols['platform']: 'platform'}),
                    float(kpis.get('total_spend', platform_df['spend'].sum() if 'spend' in platform_df.columns else 0.0)),
                )
                reco_df = reco_df.rename(columns={'platform': cols['platform']})
                st.plotly_chart(budget_optimization_chart(reco_df, cols['platform']), use_container_width=True)
                with st.expander(t('optimization_table'), expanded=False):
                    show_cols = [cols['platform'], 'spend', 'recommended_spend', 'delta', 'roas', 'roi', 'cpa', 'cvr', 'ctr']
                    show_cols = [c for c in show_cols if c in reco_df.columns]
                    st.dataframe(reco_df[show_cols].sort_values('delta', ascending=False), use_container_width=True)

            if campaign_df is not None and cols.get('campaign_id'):
                st.markdown(f"<h3 class='section-header'>{t('top_campaigns')}</h3>", unsafe_allow_html=True)
                top = campaign_df.copy().rename(columns={cols['campaign_id']: 'campaign_id'})
                top = top.sort_values(['roas', 'conversions'], ascending=False).head(12)
                # Show a compact table and a simple bar chart for ROAS (if available)
                show_cols = ['campaign_id'] + [c for c in ('roas', 'conversions', 'roi') if c in top.columns]
                st.dataframe(top[show_cols].reset_index(drop=True), use_container_width=True, height=260)
                try:
                    import plotly.express as px

                    if 'roas' in top.columns:
                        fig_top = px.bar(top.head(10), x='campaign_id', y='roas', color='roi' if 'roi' in top.columns else None, template='plotly_dark', title=t('chart_top_campaigns'))
                        fig_top.update_layout(showlegend=False)
                        st.plotly_chart(fig_top, use_container_width=True)
                except Exception:
                    pass

            st.markdown('---')
            st.markdown(f"<h2 class='section-header'>{t('ml_title')}</h2>", unsafe_allow_html=True)
            best_platform = None
            if platform_df is not None and cols.get('platform'):
                best_platform = platform_df.sort_values('roas', ascending=False).head(1).iloc[0]
            pred_cvr = float(kpis.get('cvr', 0.0))
            roas_val = float(kpis.get('roas', 0.0) or 0.0)
            roas_factor = 1.0 - float(np.exp(-max(0.0, roas_val) / 2.0))
            cpa_usd_equiv = (kpis.get('cpa', 0.0) / USD_TO_VND_RATE) if USD_TO_VND_RATE else 0.0
            cpa_factor = 1.0 / (1.0 + (max(0.0, float(cpa_usd_equiv)) / 30.0))
            efficiency = int(round(100.0 * roas_factor * cpa_factor))
            risk = t('risk_low')
            if campaign_df is not None and not campaign_df.empty:
                roi_std = float(campaign_df['roi'].std()) if 'roi' in campaign_df.columns else 0.0
                if roi_std > 80:
                    risk = t('risk_high')
                elif roi_std > 40:
                    risk = t('risk_medium')
            ml1, ml2, ml3, ml4 = st.columns(4)
            ml1.metric(t('predicted_cvr'), format_percent(pred_cvr))
            ml2.metric(t('best_platform'), str(best_platform.iloc[0]) if best_platform is not None else "N/A")
            ml3.metric(t('efficiency_score'), f"{efficiency}/100")
            ml4.metric(t('risk_level'), risk)
            st.caption(t('ml_caption'))

            st.markdown('---')
            with st.expander(t('data_preview'), expanded=False):
                st.caption(t('data_preview_hint'))
                st.dataframe(df.head(50), use_container_width=True, height=320)

            st.markdown('---')
            st.markdown(f"<h2 class='section-header'>{t('export')}</h2>", unsafe_allow_html=True)
            d1, d2, d3, d4 = st.columns(4)
            with d1:
                csv_data = df.to_csv(index=False)
                st.download_button(
                    t('export_csv'),
                    csv_data,
                    f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                )
            with d2:
                kpis_df = pd.DataFrame([kpis])
                st.download_button(
                    t('export_kpi'),
                    kpis_df.to_csv(index=False),
                    f"kpi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                )
            with d3:
                st.info(t('export_excel_ready'))
            with d4:
                st.info(t('export_pdf_ready'))

        except Exception as e:
            st.error(f"{t('analyze')}: {str(e)}")
    else:
        st.info(t('upload_info_empty'))
