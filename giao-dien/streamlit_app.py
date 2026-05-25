"""Streamlit UI: Phân tích & tối ưu chiến dịch quảng cáo (Big Data/Spark/ML)."""

import io
import os
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Use wide layout for more horizontal space
try:
    st.set_page_config(page_title="Hệ thống phân tích quảng cáo", layout="wide", initial_sidebar_state="expanded")
except Exception:
    pass

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

from api_client import api_delete, api_get, api_get_bytes, api_patch_json, api_post_file, api_post_json
from dashboard_context import load_dashboard_context
try:
    from admin_pages import (
        render_ml_page,
        render_sessions_page,
        render_spark_page,
        render_user_management_page,
        render_dataset_admin_page,
    )
    _ADMIN_IMPORT_ERROR = None
except Exception as _admin_exc:  # pragma: no cover - runtime import may fail in some environments
    _ADMIN_IMPORT_ERROR = _admin_exc

    def _import_error_renderer(*args, **kwargs):
        st.error(f"Admin UI failed to load: {_ADMIN_IMPORT_ERROR}")

    # provide fallbacks so the app doesn't crash at import time
    render_ml_page = _import_error_renderer
    render_sessions_page = _import_error_renderer
    render_spark_page = _import_error_renderer
    render_user_management_page = _import_error_renderer
    render_dataset_admin_page = _import_error_renderer
from local_analytics import (
    aggregate_performance as la_aggregate_performance,
    budget_recommendation as la_budget_recommendation,
    calculate_kpis as la_calculate_kpis,
    check_system_health as la_check_system_health,
    coerce_numeric_metrics_inplace as la_coerce_numeric_metrics_inplace,
    convert_money_columns_to_vnd_inplace as la_convert_money_columns_to_vnd_inplace,
    detect_columns as la_detect_columns,
    kpi_trends_from_timeseries as la_kpi_trends_from_timeseries,
    prepare_timeseries as la_prepare_timeseries,
    spark_processing_panel as la_spark_processing_panel,
)
from page_sections import (
    render_ads_page,
    render_analytics_page,
    render_dashboard_page,
    render_profile_page,
    render_reports_page,
)
try:
    from navigation import build_nav_options, nav_label
except Exception:
    # Fallbacks to avoid runtime crash if navigation module isn't importable
    def build_nav_options(role: str) -> list[str]:
        if role == "user":
            return ["dashboard", "profile", "upload", "ads"]
        if role == "analyst":
            return ["dashboard", "profile", "analytics", "reports", "upload"]
        if role == "admin":
            return ["dashboard", "analytics", "upload", "user_management", "admin"]
        return ["dashboard", "profile"]

    def nav_label(key: str) -> str:
        icons = {
            "dashboard": "🏠",
            "profile": "👤",
            "ads": "📊",
            "analytics": "📈",
            "reports": "🧾",
            "upload": "📁",
            "user_management": "👥",
            "admin": "🛡️",
        }
        labels = {
            "dashboard": "Bảng điều khiển",
            "profile": "Hồ sơ",
            "ads": "Dữ liệu quảng cáo",
            "analytics": "Phân tích",
            "reports": "Báo cáo",
            "upload": "Tải dữ liệu",
            "user_management": "Quản lý người dùng",
            "admin": "Phiên đăng nhập",
        }
        return f"{icons.get(key, '')} {labels.get(key, key)}"

I18N = {
        "vi": {
            "lang_label": "Ngôn ngữ / Language",
            "account": "Tài khoản",
            "logged_in_as": "Đã đăng nhập",
            "session_expires": "Hết hạn phiên",
            "logout": "Đăng xuất",
            "username": "Tên đăng nhập",
            "password": "Mật khẩu",
            "login": "Đăng nhập",
            "guest_mode": "Bạn đang ở chế độ khách. Một số tính năng bị giới hạn.",
            "session_invalid": "Phiên đăng nhập không còn hợp lệ. Vui lòng đăng nhập lại.",
            "nav_title": "🧭 Điều hướng",
            "nav_upload": "Tải dữ liệu",
            "nav_ml": "ML",
            "header_title": "📊 Hệ thống phân tích quảng cáo",
            "header_subtitle": "Big Data • Apache Spark • Tối ưu ngân sách • Phân tích ML",
            "online": "● TRỰC TUYẾN",
            "system_arch": "Kiến trúc hệ thống",
            "runtime_status": "Trạng thái chạy",
            "upload_info_dashboard": "Vào mục 'Tải dữ liệu' để tải CSV và chạy phân tích.",
            "upload_section_title": "📥 Tải dữ liệu CSV & phân tích",
            "upload_requires_role": "Tải lên API yêu cầu quyền 'Phân tích' hoặc 'Quản trị'. (Xem/phân tích CSV trên giao diện vẫn dùng được)",
            "upload_csv": "Chọn tệp CSV",
            "upload_hint": "Gợi ý cột: campaign_id, date, platform, age_group, impressions, clicks, conversions, spend, revenue...",
            "analyze": "Phân tích",
            "dataset_info_records": "📊 Số dòng",
            "dataset_info_columns": "📋 Số cột",
            "dataset_info_size": "💾 Dung lượng",
            "dataset_info_campaigns": "🎯 Số chiến dịch",
            "kpi_title": "📌 Chỉ số hiệu suất",
            "kpi_ctr_label": "Tỷ lệ nhấp (CTR)",
            "kpi_cvr_label": "Tỷ lệ chuyển đổi (CVR)",
            "kpi_definitions": "CVR = Chuyển đổi / Lượt nhấp. CTR = Lượt nhấp / Lượt hiển thị.",
            "spark_engine": "⚡ Bộ máy xử lý Spark",
            "etl_stages": "Các giai đoạn ETL (phân tán)",
            "spark_dataset": "Dữ liệu",
            "spark_partitions": "Phân vùng",
            "spark_memory_est": "Bộ nhớ (ước tính)",
            "spark_exec_time_est": "Thời gian chạy (ước tính)",
            "rows_unit": "dòng",
            "stage_ingest": "Nhập dữ liệu",
            "stage_validate": "Kiểm tra",
            "stage_clean": "Làm sạch",
            "stage_aggregate": "Tổng hợp",
            "stage_optimize": "Tối ưu",
            "spark_timing": "Đọc cục bộ: {read_sec:.2f}s | Chuẩn bị phân tích: {prep_sec:.2f}s | Spark (ước tính): {spark_sec:.2f}s",
            "opt_recos": "🎯 Khuyến nghị tối ưu",
            "insight_engine": "💡 Insight & gợi ý nhanh",
            "smart_analytics": "📈 Phân tích chiến dịch",
            "conversion_funnel": "Phễu chuyển đổi",
            "funnel_impressions": "Lượt hiển thị",
            "funnel_clicks": "Lượt nhấp",
            "funnel_conversions": "Chuyển đổi",
            "trend_analysis": "Phân tích xu hướng (CTR/CVR)",
            "trend_caption": "Tổng hợp theo ngày từ toàn bộ dữ liệu trong CSV (không chỉ 1 chiến dịch).",
            "roi_by_platform": "ROI theo nền tảng",
            "spend_vs_revenue": "Chi tiêu vs Doanh thu",
            "no_time_series": "Không đủ cột date/spend/revenue để vẽ chuỗi thời gian.",
            "ctr_heatmap": "CTR theo nhóm tuổi & nền tảng (bảng màu)",
            "budget_optimization": "💸 Tối ưu ngân sách",
            "optimization_table": "Bảng tối ưu (theo nền tảng)",
            "spark_perf": "⚙️ Hiệu năng Spark",
            "top_campaigns": "🏆 Top chiến dịch hiệu quả",
            "ml_title": "🤖 Tóm tắt & gợi ý",
            "predicted_cvr": "CVR hiện tại",
            "best_platform": "Nền tảng tốt nhất",
            "efficiency_score": "Điểm hiệu quả chi tiêu",
            "risk_level": "Mức biến động kết quả",
            "risk_low": "Thấp",
            "risk_medium": "Trung bình",
            "risk_high": "Cao",
            "ml_caption": "CVR là số đo hiện tại từ dữ liệu tải lên. Điểm hiệu quả chi tiêu (0–100) là thang điểm heuristic dựa trên ROAS và CPA (tham khảo, không phải mô hình ML huấn luyện). Mức biến động dựa trên độ phân tán ROI giữa các chiến dịch.",
            "data_preview": "📋 Xem trước dữ liệu (một phần)",
            "data_preview_hint": "Dữ liệu thô chỉ để kiểm tra định dạng; trọng tâm là insight/tối ưu.",
            "export": "💾 Xuất dữ liệu",
            "export_csv": "📥 CSV",
            "export_kpi": "📊 KPI",
            "export_excel_ready": "Excel: Sẵn sàng",
            "export_pdf_ready": "PDF: Sẵn sàng",
            "upload_info_empty": "Tải tệp CSV để chạy phân tích + tối ưu theo phong cách Spark.",
            "workers": "Số worker",
            "enabled": "Bật",
            "api_upload_rbac": "⚙️ Tải lên API (RBAC)",
            "api_upload_button": "⬆️ Tải lên API",
            "api_upload_ok": "API OK",
            "token_invalid": "Token không hợp lệ. Vui lòng đăng nhập lại.",
            "ml_upload_caption": "Dùng tab 'Tải dữ liệu' để nạp dữ liệu → insight ML được suy diễn từ tín hiệu tổng hợp.",
            "reco_increase_budget_title": "Tăng ngân sách cho {name}",
            "reco_increase_budget_action": "Tăng ngân sách cho kênh hiệu quả để tối đa hóa lợi nhuận (phân bổ theo Spark).",
            "reco_reduce_spend_title": "Giảm chi tiêu cho {name}",
            "reco_reduce_spend_action": "Cắt ngân sách / tối ưu targeting & landing để giảm chi phí mỗi chuyển đổi.",
            "reco_prioritize_segment_title": "Ưu tiên phân khúc: {name}",
            "reco_prioritize_segment_action": "Tập trung bid + creative cho nhóm đối tượng chuyển đổi tốt nhất.",
            "reco_derisk_segment_title": "Giảm rủi ro phân khúc: {name}",
            "reco_derisk_segment_action": "Loại trừ/retarget phân khúc kém hiệu quả để bảo vệ ngân sách.",
            "reco_scale_campaign_title": "Scale chiến dịch {name}",
            "reco_scale_campaign_detail": "ROAS cao nhất {roas:.2f}x | Chuyển đổi {conversions}",
            "reco_scale_campaign_action": "Tăng ngân sách + mở rộng tiếp cận; theo dõi tần suất & CPA biên.",
            "reco_pause_campaign_title": "Tạm dừng/sửa chiến dịch {name}",
            "reco_pause_campaign_action": "Tối ưu creative/targeting hoặc dừng để tránh lãng phí.",
            "ml_page_title": "🤖 Dự đoán ML",
            "ml_page_info": "ML tập trung vào: dự báo chuyển đổi, chấm điểm hiệu quả ngân sách, phát hiện rủi ro chiến dịch.",
            "advanced_title": "📈 Phân tích nâng cao",
            "advanced_info": "Heatmap, Correlation, Segmentation - Sắp có",
            "footer": "",
            "chart_roi_platform": "Hồ sơ ROI theo nền tảng",
            "chart_platform": "Nền tảng",
            "chart_age_group": "Nhóm tuổi",
            "chart_roi": "ROI (%)",
            "chart_roas": "ROAS (x)",
            "chart_spend_revenue": "Chi tiêu vs Doanh thu (chuỗi thời gian)",
            "chart_spend": "Chi tiêu",
            "chart_revenue": "Doanh thu",
            "chart_ctr_heatmap": "Bản đồ nhiệt CTR (Nhóm tuổi × Nền tảng)",
            "chart_budget_opt": "Tối ưu ngân sách (hiện tại vs khuyến nghị)",
            "chart_spark_perf": "Hồ sơ hiệu năng Spark (ước tính)",
            "chart_dataset_size": "Kích thước dữ liệu (triệu dòng)",
            "chart_exec_time": "Thời gian chạy (giây)",
            "chart_top_campaigns": "Top chiến dịch theo ROAS (màu theo ROI)",
            "chart_current_spend": "Chi tiêu hiện tại",
            "chart_recommended_spend": "Chi tiêu khuyến nghị",
            "chart_est_spark_time": "Thời gian Spark (ước tính)",
            "insight_dataset_scale": "📦 Quy mô dữ liệu: {rows:,} dòng → phù hợp ETL kiểu Spark",
            "insight_overall": "📈 CTR tổng: {ctr} | CVR: {cvr}",
            "insight_best_platform": "🏆 Nền tảng tốt nhất (ROAS): {name} → {roas:.2f}x",
            "insight_cost_risk": "🧨 Nền tảng rủi ro chi phí (CPA): {name} → {cpa_fmt}",
            "insight_top_campaign": "🎯 Chiến dịch nên scale: {name} (ROAS {roas:.2f}x)",
            "insight_negative_roi": "⚠️ ROI âm: ưu tiên tối ưu ngân sách + targeting để giảm lãng phí",
        },
        "en": {
            "lang_label": "Language / Ngôn ngữ",
            "account": "Account",
            "logged_in_as": "Logged in as",
            "session_expires": "Session expires",
            "logout": "Logout",
            "username": "Username",
            "password": "Password",
            "login": "Login",
            "guest_mode": "You are in guest mode. Some features are restricted.",
            "session_invalid": "Session is invalid. Please login again.",
            "nav_title": "🧭 Navigation",
            "nav_upload": "Upload",
            "nav_ml": "ML",
            "header_title": "📊 Advertising Analytics System",
            "header_subtitle": "Big Data • Apache Spark • Budget Optimization • ML Analytics",
            "online": "● ONLINE",
            "system_arch": "System Architecture",
            "runtime_status": "Runtime Status",
            "upload_info_dashboard": "Go to 'Upload' to upload CSV and run analytics.",
            "upload_section_title": "📥 Upload CSV & analyze",
            "upload_requires_role": "Uploading to API requires 'Analyst' or 'Admin' permissions. (Local CSV analysis in the UI is still available)",
            "upload_csv": "Choose CSV file",
            "upload_hint": "Suggested columns: campaign_id, date, platform, age_group, impressions, clicks, conversions, spend, revenue...",
            "analyze": "Analyze",
            "dataset_info_records": "📊 Records",
            "dataset_info_columns": "📋 Columns",
            "dataset_info_size": "💾 Size",
            "kpi_title": "📌 Performance metrics",
            "spark_engine": "⚡ Spark Processing Engine",
            "etl_stages": "ETL Stages (Distributed)",
            "spark_dataset": "Dataset",
            "spark_partitions": "Partitions",
            "spark_memory_est": "Memory (est)",
            "spark_exec_time_est": "Exec Time (est)",
            "rows_unit": "rows",
            "stage_ingest": "Ingest",
            "stage_validate": "Validate",
            "stage_clean": "Clean",
            "stage_aggregate": "Aggregate",
            "stage_optimize": "Optimize",
            "spark_timing": "Local read: {read_sec:.2f}s | Analytics prep: {prep_sec:.2f}s | Spark est: {spark_sec:.2f}s",
            "opt_recos": "🎯 Optimization Recommendations",
            "insight_engine": "💡 Insight Engine",
            "smart_analytics": "📈 Campaign analytics",
            "conversion_funnel": "Conversion Funnel",
            "funnel_impressions": "Impressions",
            "funnel_clicks": "Clicks",
            "funnel_conversions": "Conversions",
            "trend_analysis": "Trend Analysis (CTR/CVR)",
            "trend_caption": "Daily aggregation from the entire CSV (not a single best campaign).",
            "roi_by_platform": "ROI by platform",
            "spend_vs_revenue": "Spend vs revenue",
            "no_time_series": "No usable date/spend/revenue columns for time series.",
            "ctr_heatmap": "CTR by age group & platform (heatmap)",
            "budget_optimization": "💸 Budget Optimization",
            "optimization_table": "Optimization table (platform)",
            "spark_perf": "⚙️ Spark Performance",
            "top_campaigns": "🏆 Top campaigns (optimization targets)",
            "ml_title": "🤖 Summary & Suggestions",
            "predicted_cvr": "Current CVR",
            "best_platform": "Best Platform",
            "efficiency_score": "Spend efficiency score",
            "risk_level": "Result volatility",
            "risk_low": "Low",
            "risk_medium": "Medium",
            "risk_high": "High",
            "ml_caption": "CVR is computed from the uploaded data. Efficiency score (0–100) is a heuristic based on ROAS and CPA (reference only, not a trained ML model). Volatility is based on ROI dispersion across campaigns.",
            "data_preview": "📋 Data Preview (raw rows)",
            "data_preview_hint": "Raw rows are for format checks; focus is insights/optimization.",
            "export": "💾 Export",
            "export_csv": "📥 CSV",
            "export_kpi": "📊 KPI",
            "export_excel_ready": "Excel: Ready",
            "export_pdf_ready": "PDF: Ready",
            "upload_info_empty": "Upload a CSV file to run Spark-like processing + optimization.",
            "workers": "Workers",
            "enabled": "Enabled",
            "api_upload_rbac": "⚙️ API Upload (RBAC)",
            "api_upload_button": "⬆️ Upload to API",
            "api_upload_ok": "API OK",
            "token_invalid": "Token is invalid. Please login again.",
            "ml_upload_caption": "Use Upload tab to load data → ML insights are derived from aggregated signals.",
            "reco_increase_budget_title": "Increase budget on {name}",
            "reco_increase_budget_action": "Scale winners to maximize return (Spark-driven allocation).",
            "reco_reduce_spend_title": "Reduce spend on {name}",
            "reco_reduce_spend_action": "Cut budget / fix targeting & landing to reduce cost per acquisition.",
            "reco_prioritize_segment_title": "Prioritize segment: {name}",
            "reco_prioritize_segment_action": "Focus bid + creatives for best converting audience segment.",
            "reco_derisk_segment_title": "De-risk segment: {name}",
            "reco_derisk_segment_action": "Exclude/retarget low-efficiency segment to protect budget.",
            "reco_scale_campaign_title": "Scale campaign {name}",
            "reco_scale_campaign_detail": "Highest ROAS {roas:.2f}x | Conversions {conversions}",
            "reco_scale_campaign_action": "Increase budget + broaden reach; monitor frequency & marginal CPA.",
            "reco_pause_campaign_title": "Pause/repair campaign {name}",
            "reco_pause_campaign_action": "Fix creatives/targeting or stop to prevent waste.",
            "ml_page_title": "🤖 ML Predictions",
            "ml_page_info": "ML focuses on: conversion forecasting, budget efficiency scoring, campaign risk detection.",
            "advanced_title": "📈 Advanced Analytics",
            "advanced_info": "Heatmap, Correlation, Segmentation - Coming soon",
            "footer": "🚀 Advertising Analytics System | Thesis: Big Data + Spark + ML",
            "chart_roi_platform": "ROI by Platform (Optimization Target)",
            "chart_platform": "Platform",
            "chart_age_group": "Age group",
            "chart_roi": "ROI (%)",
            "chart_roas": "ROAS (x)",
            "chart_spend_revenue": "Spend vs Revenue (Time Series)",
            "chart_spend": "Spend",
            "chart_revenue": "Revenue",
            "chart_ctr_heatmap": "CTR Heatmap (Age Group × Platform)",
            "chart_budget_opt": "Budget Optimization (Current vs Recommended)",
            "chart_spark_perf": "Spark Performance Profile (Estimated)",
            "chart_dataset_size": "Dataset Size (Million rows)",
            "chart_exec_time": "Execution Time (s)",
            "chart_top_campaigns": "Top Campaigns by ROAS (with ROI color)",
            "chart_current_spend": "Current Spend",
            "chart_recommended_spend": "Recommended Spend",
            "chart_est_spark_time": "Estimated Spark Time (s)",
            "insight_dataset_scale": "📦 Dataset scale: {rows:,} rows → Spark-friendly ETL",
            "insight_overall": "📈 Overall CTR: {ctr} | CVR: {cvr}",
            "insight_best_platform": "🏆 Best platform (ROAS): {name} → {roas:.2f}x",
            "insight_cost_risk": "🧨 Cost risk platform (CPA): {name} → {cpa_fmt}",
            "insight_top_campaign": "🎯 Top campaign to scale: {name} (ROAS {roas:.2f}x)",
            "insight_negative_roi": "⚠️ Negative ROI: prioritize budget + targeting optimization",
        },
    "en": {
        "lang_label": "Language / Ngôn ngữ",
        "account": "Account",
        "logged_in_as": "Logged in as",
        "session_expires": "Session expires",
        "logout": "Logout",
        "username": "Username",
        "password": "Password",
        "login": "Login",
        "guest_mode": "You are in guest mode. Some features are restricted.",
        "session_invalid": "Session is invalid. Please login again.",
        "nav_title": "🧭 Navigation",
        "nav_upload": "Upload",
        "nav_ml": "ML",
        "header_title": "📊 Advertising Analytics System",
        "header_subtitle": "Big Data • Apache Spark • Budget Optimization • ML Analytics",
        "online": "● ONLINE",
        "system_arch": "System Architecture",
        "runtime_status": "Runtime Status",
        "upload_info_dashboard": "Go to 'Upload' to upload CSV and run analytics.",
        "upload_section_title": "📥 Upload CSV & analyze",
        "upload_requires_role": "Uploading to API requires 'Analyst' or 'Admin' permissions. (Local CSV analysis in the UI is still available)",
        "upload_csv": "Choose CSV file",
        "upload_hint": "Suggested columns: campaign_id, date, platform, age_group, impressions, clicks, conversions, spend, revenue...",
        "analyze": "Analyze",
        "dataset_info_records": "📊 Records",
        "dataset_info_columns": "📋 Columns",
        "dataset_info_size": "💾 Size",
        "kpi_title": "📌 Performance metrics",
        "spark_engine": "⚡ Spark Processing Engine",
        "etl_stages": "ETL Stages (Distributed)",
        "spark_dataset": "Dataset",
        "spark_partitions": "Partitions",
        "spark_memory_est": "Memory (est)",
        "spark_exec_time_est": "Exec Time (est)",
        "rows_unit": "rows",
        "stage_ingest": "Ingest",
        "stage_validate": "Validate",
        "stage_clean": "Clean",
        "stage_aggregate": "Aggregate",
        "stage_optimize": "Optimize",
        "spark_timing": "Local read: {read_sec:.2f}s | Analytics prep: {prep_sec:.2f}s | Spark est: {spark_sec:.2f}s",
        "opt_recos": "🎯 Optimization Recommendations",
        "insight_engine": "💡 Insight Engine",
        "smart_analytics": "📈 Campaign analytics",
        "conversion_funnel": "Conversion Funnel",
        "funnel_impressions": "Impressions",
        "funnel_clicks": "Clicks",
        "funnel_conversions": "Conversions",
        "trend_analysis": "Trend Analysis (CTR/CVR)",
        "trend_caption": "Daily aggregation from the entire CSV (not a single best campaign).",
        "roi_by_platform": "ROI by platform",
        "spend_vs_revenue": "Spend vs revenue",
        "no_time_series": "No usable date/spend/revenue columns for time series.",
        "ctr_heatmap": "CTR by age group & platform (heatmap)",
        "budget_optimization": "💸 Budget Optimization",
        "optimization_table": "Optimization table (platform)",
        "spark_perf": "⚙️ Spark Performance",
        "top_campaigns": "🏆 Top campaigns (optimization targets)",
        "ml_title": "🤖 Summary & Suggestions",
        "predicted_cvr": "Current CVR",
        "best_platform": "Best Platform",
        "efficiency_score": "Spend efficiency score",
        "risk_level": "Result volatility",
        "risk_low": "Low",
        "risk_medium": "Medium",
        "risk_high": "High",
        "ml_caption": "CVR is computed from the uploaded data. Efficiency score (0–100) is a heuristic based on ROAS and CPA (reference only, not a trained ML model). Volatility is based on ROI dispersion across campaigns.",
        "data_preview": "📋 Data Preview (raw rows)",
        "data_preview_hint": "Raw rows are for format checks; focus is insights/optimization.",
        "export": "💾 Export",
        "export_csv": "📥 CSV",
        "export_kpi": "📊 KPI",
        "export_excel_ready": "Excel: Ready",
        "export_pdf_ready": "PDF: Ready",
        "upload_info_empty": "Upload a CSV file to run Spark-like processing + optimization.",
        "workers": "Workers",
        "enabled": "Enabled",
        "api_upload_rbac": "⚙️ API Upload (RBAC)",
        "api_upload_button": "⬆️ Upload to API",
        "api_upload_ok": "API OK",
        "token_invalid": "Token is invalid. Please login again.",
        "ml_upload_caption": "Use Upload tab to load data → ML insights are derived from aggregated signals.",
        "reco_increase_budget_title": "Increase budget on {name}",
        "reco_increase_budget_action": "Scale winners to maximize return (Spark-driven allocation).",
        "reco_reduce_spend_title": "Reduce spend on {name}",
        "reco_reduce_spend_action": "Cut budget / fix targeting & landing to reduce cost per acquisition.",
        "reco_prioritize_segment_title": "Prioritize segment: {name}",
        "reco_prioritize_segment_action": "Focus bid + creatives for best converting audience segment.",
        "reco_derisk_segment_title": "De-risk segment: {name}",
        "reco_derisk_segment_action": "Exclude/retarget low-efficiency segment to protect budget.",
        "reco_scale_campaign_title": "Scale campaign {name}",
        "reco_scale_campaign_detail": "Highest ROAS {roas:.2f}x | Conversions {conversions}",
        "reco_scale_campaign_action": "Increase budget + broaden reach; monitor frequency & marginal CPA.",
        "reco_pause_campaign_title": "Pause/repair campaign {name}",
        "reco_pause_campaign_action": "Fix creatives/targeting or stop to prevent waste.",
        "ml_page_title": "🤖 ML Predictions",
        "ml_page_info": "ML focuses on: conversion forecasting, budget efficiency scoring, campaign risk detection.",
        "advanced_title": "📈 Advanced Analytics",
        "advanced_info": "Heatmap, Correlation, Segmentation - Coming soon",
        "footer": "🚀 Advertising Analytics System | Thesis: Big Data + Spark + ML",
        "chart_roi_platform": "ROI by Platform (Optimization Target)",
        "chart_platform": "Platform",
        "chart_age_group": "Age group",
        "chart_roi": "ROI (%)",
        "chart_roas": "ROAS (x)",
        "chart_spend_revenue": "Spend vs Revenue (Time Series)",
        "chart_spend": "Spend",
        "chart_revenue": "Revenue",
        "chart_ctr_heatmap": "CTR Heatmap (Age Group × Platform)",
        "chart_budget_opt": "Budget Optimization (Current vs Recommended)",
        "chart_spark_perf": "Spark Performance Profile (Estimated)",
        "chart_dataset_size": "Dataset Size (Million rows)",
        "chart_exec_time": "Execution Time (s)",
        "chart_top_campaigns": "Top Campaigns by ROAS (with ROI color)",
        "chart_current_spend": "Current Spend",
        "chart_recommended_spend": "Recommended Spend",
        "chart_est_spark_time": "Estimated Spark Time (s)",
        "insight_dataset_scale": "📦 Dataset scale: {rows:,} rows → Spark-friendly ETL",
        "insight_overall": "📈 Overall CTR: {ctr} | CVR: {cvr}",
        "insight_best_platform": "🏆 Best platform (ROAS): {name} → {roas:.2f}x",
        "insight_cost_risk": "🧨 Cost risk platform (CPA): {name} → {cpa_fmt}",
        "insight_top_campaign": "🎯 Top campaign to scale: {name} (ROAS {roas:.2f}x)",
        "insight_negative_roi": "⚠️ Negative ROI: prioritize budget + targeting optimization",
    },
}
def t(key: str) -> str:
    lang = str(st.session_state.get("lang") or "vi")
    if lang not in I18N:
        lang = "vi"
    vi_val = I18N["vi"].get(key, key)
    return I18N.get(lang, I18N["vi"]).get(key, vi_val)


def tf(key: str, **kwargs) -> str:
    return t(key).format(**kwargs)


# Default API base for local dev (override with env var)
DEFAULT_API = os.getenv("API_URL", "http://localhost:8000")

# Currency conversion default (allow override via env)
USD_TO_VND_RATE: float = float(os.getenv("USD_TO_VND_RATE", "25000"))


def setup_auth(api_base: str) -> dict:
    """Simple auth UI: login/logout stored in `st.session_state['auth']`.

    Returns a dict with keys `token` and `role` (and `username` when available).
    """
    if "auth" not in st.session_state:
        st.session_state["auth"] = {}

    with st.expander(t("account"), expanded=False):
            auth = st.session_state.get("auth") or {}
            # Helper callbacks for login/logout to avoid using experimental_rerun
            def _do_logout():
                try:
                    tok = st.session_state.get("auth", {}).get("token")
                    if tok:
                        api_post_json(api_base, "/api/auth/logout", {}, token=tok)
                except Exception:
                    pass
                st.session_state.pop("auth", None)

            def _do_login():
                # Read username/password from session_state (inputs use these keys)
                uname = st.session_state.get("login_username", "")
                pwd = st.session_state.get("login_password", "")
                try:
                    payload = {"username": uname, "password": pwd}
                    res = api_post_json(api_base, "/api/auth/login", payload)
                    token = res.get("access_token")
                    role = res.get("role", "guest")
                    st.session_state["auth"] = {"token": token, "role": role, "username": res.get("username")}
                    # show a success indicator next render
                    st.session_state["_auth_success"] = f"{t('logged_in_as')}: {res.get('username')}"
                except Exception as exc:
                    st.session_state["_auth_error"] = str(exc)

            # If already logged in, show simple status + logout
            if auth and auth.get("token"):
                # show a neutral persistent status; avoid duplicate success banners
                st.info(f"{t('logged_in_as')}: {auth.get('username')}")
                st.button(t("logout"), on_click=_do_logout)
            else:
                # Inputs bind to session_state keys so callback can access them
                st.text_input(t("username"), value=st.session_state.get("login_username", ""), key="login_username")
                st.text_input(t("password"), value="", type="password", key="login_password")
                st.button(t("login"), on_click=_do_login)

            # Display any messages produced by callbacks (errors only; success shown via persistent status)
            if st.session_state.get("_auth_error"):
                st.error(st.session_state.pop("_auth_error"))

    return st.session_state.get("auth", {})


def format_vnd(value: float | int | None, decimals: int = 0) -> str:
    try:
        if value is None:
            return "0 ₫"
        val = float(value)
        if decimals <= 0:
            return f"{int(round(val)):,} ₫"
        else:
            fmt = f"{{:,.{decimals}f}} ₫"
            return fmt.format(val)
    except Exception:
        return str(value)


def _empty_dashboard_message() -> None:
    st.info(t("upload_info_dashboard"))
st.markdown("""
<style>
:root {
    --primary: #0084ff;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --purple: #a855f7;
    --cyan: #22d3ee;
    --dark: #0f172a;
    --dark-2: #111827;
    --gray: #6b7280;
    --border: #1f2937;
}

/* Page background */
.stApp {
    background: radial-gradient(1200px circle at 10% 0%, rgba(0, 132, 255, 0.10), transparent 55%),
                radial-gradient(900px circle at 90% 10%, rgba(16, 185, 129, 0.08), transparent 55%),
                linear-gradient(180deg, #0b1020 0%, var(--dark) 60%, #070b16 100%);
}

/* Panels */
.panel {
    background: linear-gradient(180deg, rgba(17, 24, 39, 0.92) 0%, rgba(15, 23, 42, 0.92) 100%);
    border: 1px solid var(--border);
    box-shadow: 0 8px 24px rgba(0,0,0,0.28);
    border-radius: 10px;
    padding: 16px 18px;
}

.panel-title {
    font-size: 12px;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 10px;
}

/* KPI Cards */
.kpi-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-left: 4px solid var(--primary);
    padding: 20px;
    border-radius: 8px;
    margin: 10px 0;
    color: white;
    box-shadow: 0 10px 26px rgba(0,0,0,0.25);
    border: 1px solid rgba(31, 41, 55, 0.65);
}

.kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: var(--primary);
    margin: 10px 0 5px 0;
}

.kpi-label {
    font-size: 12px;
    color: var(--gray);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 10px;
}

.kpi-trend {
    font-size: 13px;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #334155;
}

.trend-up {
    color: var(--success);
}

.trend-down {
    color: var(--danger);
}

/* Section Headers */
.section-header {
    font-size: 22px;
    font-weight: 700;
    margin: 34px 0 14px 0;
    padding-bottom: 10px;
    border-bottom: 2px solid var(--primary);
    color: white;
}

/* Status Badge */
.status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin: 0 5px;
}

.status-success {
    background-color: rgba(16, 185, 129, 0.2);
    color: var(--success);
    border: 1px solid var(--success);
}

.status-running {
    background-color: rgba(0, 132, 255, 0.2);
    color: var(--primary);
    border: 1px solid var(--primary);
}

.status-warning {
    background-color: rgba(245, 158, 11, 0.18);
    color: var(--warning);
    border: 1px solid var(--warning);
}

.status-danger {
    background-color: rgba(239, 68, 68, 0.18);
    color: var(--danger);
    border: 1px solid var(--danger);
}

/* Insight Box */
.insight-box {
    background-color: rgba(0, 132, 255, 0.1);
    border-left: 4px solid var(--primary);
    padding: 15px;
    border-radius: 6px;
    margin: 10px 0;
    color: #e2e8f0;
    font-size: 14px;
}

.reco-box {
    background: linear-gradient(180deg, rgba(168, 85, 247, 0.10) 0%, rgba(0, 0, 0, 0.0) 100%);
    border-left: 4px solid var(--purple);
    padding: 14px 14px;
    border-radius: 8px;
    margin: 10px 0;
    color: #e5e7eb;
    border: 1px solid rgba(168, 85, 247, 0.25);
}

.mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 12px;
    color: #cbd5e1;
}
/* Expand main content width */
.main .block-container, .reportview-container .main .block-container {
    max-width: 1400px;
    padding-left: 2.5rem;
    padding-right: 2.5rem;
}
</style>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ====================

def format_number(value, decimals=2):
    """Format số theo kiểu Việt đẹp"""
    if pd.isna(value) or value == 0:
        return "0"
    try:
        value = float(value)
        if value >= 1_000_000:
            return f"{value/1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value/1_000:.1f}K"
        else:
            return f"{value:,.{decimals}f}"
    except:
        return str(value)

def format_percent(value):
    """Format phần trăm"""
    if pd.isna(value):
        return "0%"
    return f"{float(value):.2f}%"

def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    if pd.isna(numerator):
        return 0.0
    return float(numerator) / float(denominator)

def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    cols = {c.lower(): c for c in df.columns}

    def pick(*needles: str, exclude: Tuple[str, ...] = ()) -> Optional[str]:
        for k, original in cols.items():
            if exclude and any(x in k for x in exclude):
                continue
            if any(n in k for n in needles):
                return original
        return None

    def pick_prefer(prefer: Tuple[str, ...], needles: Tuple[str, ...], exclude: Tuple[str, ...] = ()) -> Optional[str]:
        # Pass 1: prefer exact/high-signal names
        for k, original in cols.items():
            if exclude and any(x in k for x in exclude):
                continue
            if any(p in k for p in prefer):
                return original
        # Pass 2: fallback to generic needles
        return pick(*needles, exclude=exclude)

    date_col = pick('date', 'day', 'datetime', 'timestamp')
    platform_col = pick('platform', 'channel', 'source')
    campaign_col = pick('campaign_id', 'campaign', 'campaignid')
    age_col = pick('age_group', 'agegroup', 'age')

    impressions_col = pick('impression')
    clicks_col = pick('click')
    conversions_col = pick_prefer(
        prefer=('total_conversion', 'conversions', 'conversion'),
        needles=('conversion',),
        exclude=('rate', 'ratio', 'cvr', '%'),
    )
    spend_col = pick('spend', 'cost', exclude=('cpc', 'cpm', 'cpa', 'per', 'rate'))
    revenue_col = pick('revenue', 'sales', 'value')

    return {
        'date': date_col,
        'platform': platform_col,
        'campaign_id': campaign_col,
        'age_group': age_col,
        'impressions': impressions_col,
        'clicks': clicks_col,
        'conversions': conversions_col,
        'spend': spend_col,
        'revenue': revenue_col,
    }

def get_trend_indicator(current, previous=None):
    """Tạo trend indicator (↑ ↓ →)"""
    if previous is None or current == previous:
        return "→ Ổn định"
    change = ((current - previous) / abs(previous)) * 100 if previous != 0 else 0
    arrow = "↑" if change > 0 else "↓"
    return f"{arrow} {abs(change):.1f}%"

def render_kpi_card(col, label, value, trend=None, color_css_var="--primary"):
    """Render KPI card với style professional"""
    with col:
        card_html = f"""
        <div class="kpi-card" style="border-left-color: var({color_css_var});">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color: var({color_css_var});">{value}</div>
        """
        if trend:
            trend_class = "trend-up" if "↑" in trend else "trend-down" if "↓" in trend else ""
            card_html += f'<div class="kpi-trend {trend_class}">{trend}</div>'
        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)

def compute_kpis_from_totals(totals: Dict[str, float]) -> Dict[str, float]:
    clicks = totals.get('total_clicks', 0.0)
    impressions = totals.get('total_impressions', 0.0)
    conversions = totals.get('total_conversions', 0.0)
    spend = totals.get('total_spend', 0.0)
    revenue = totals.get('total_revenue', 0.0)

    kpis: Dict[str, float] = dict(totals)
    kpis['ctr'] = _safe_div(clicks, impressions) * 100
    kpis['cvr'] = _safe_div(conversions, clicks) * 100
    kpis['cpc'] = _safe_div(spend, clicks)
    kpis['cpm'] = _safe_div(spend, impressions) * 1000
    kpis['cpa'] = _safe_div(spend, conversions)
    kpis['roi'] = (_safe_div(revenue - spend, spend) * 100) if spend else 0.0
    kpis['roas'] = _safe_div(revenue, spend)
    return kpis

def calculate_kpis(df):
    """Tính toán KPI từ DataFrame"""
    detected = detect_columns(df)
    totals: Dict[str, float] = {}

    if detected['impressions']:
        totals['total_impressions'] = float(df[detected['impressions']].sum())
    if detected['clicks']:
        totals['total_clicks'] = float(df[detected['clicks']].sum())
    if detected['conversions']:
        totals['total_conversions'] = float(df[detected['conversions']].sum())
    if detected['spend']:
        totals['total_spend'] = float(df[detected['spend']].sum())
    if detected['revenue']:
        totals['total_revenue'] = float(df[detected['revenue']].sum())

    return compute_kpis_from_totals(totals)

def prepare_timeseries(df: pd.DataFrame, cols: Dict[str, Optional[str]]) -> Optional[pd.DataFrame]:
    if not cols.get('date'):
        return None
    date_col = cols['date']
    assert date_col is not None

    needed = [date_col]
    for k in ['impressions', 'clicks', 'conversions', 'spend', 'revenue']:
        if cols.get(k):
            needed.append(cols[k])
    tmp = df[needed].copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors='coerce')
    tmp = tmp.dropna(subset=[date_col])
    if tmp.empty:
        return None

    tmp['__date'] = tmp[date_col].dt.date
    agg = {
        cols['impressions']: 'sum' if cols.get('impressions') else 'size',
        cols['clicks']: 'sum' if cols.get('clicks') else 'size',
        cols['conversions']: 'sum' if cols.get('conversions') else 'size',
        cols['spend']: 'sum' if cols.get('spend') else 'size',
        cols['revenue']: 'sum' if cols.get('revenue') else 'size',
    }
    agg = {k: v for k, v in agg.items() if k is not None}

    daily = tmp.groupby('__date', as_index=False).agg(agg).sort_values('__date')
    daily = daily.rename(columns={
        cols.get('impressions') or '': 'impressions',
        cols.get('clicks') or '': 'clicks',
        cols.get('conversions') or '': 'conversions',
        cols.get('spend') or '': 'spend',
        cols.get('revenue') or '': 'revenue',
    })
    for c in ['impressions', 'clicks', 'conversions', 'spend', 'revenue']:
        if c in daily.columns:
            daily[c] = daily[c].fillna(0)

    daily['ctr'] = daily.apply(lambda r: _safe_div(r.get('clicks', 0.0), r.get('impressions', 0.0)) * 100, axis=1)
    daily['cvr'] = daily.apply(lambda r: _safe_div(r.get('conversions', 0.0), r.get('clicks', 0.0)) * 100, axis=1)
    daily['roas'] = daily.apply(lambda r: _safe_div(r.get('revenue', 0.0), r.get('spend', 0.0)), axis=1)
    daily['roi'] = daily.apply(lambda r: (_safe_div(r.get('revenue', 0.0) - r.get('spend', 0.0), r.get('spend', 0.0)) * 100) if r.get('spend', 0.0) else 0.0, axis=1)
    return daily

def kpi_trends_from_timeseries(daily: Optional[pd.DataFrame], window_days: int = 7) -> Dict[str, str]:
    if daily is None or daily.empty or len(daily) < window_days * 2:
        return {}
    cur = daily.tail(window_days)
    prev = daily.tail(window_days * 2).head(window_days)

    def avg(col: str) -> float:
        return float(cur[col].mean()) if col in cur.columns else 0.0

    def avg_prev(col: str) -> float:
        return float(prev[col].mean()) if col in prev.columns else 0.0

    return {
        'ctr': get_trend_indicator(avg('ctr'), avg_prev('ctr')),
        'cvr': get_trend_indicator(avg('cvr'), avg_prev('cvr')),
        'roas': get_trend_indicator(avg('roas'), avg_prev('roas')),
        'roi': get_trend_indicator(avg('roi'), avg_prev('roi')),
    }

def aggregate_performance(df: pd.DataFrame, cols: Dict[str, Optional[str]]) -> Dict[str, pd.DataFrame]:
    imp = cols.get('impressions')
    clk = cols.get('clicks')
    conv = cols.get('conversions')
    spend = cols.get('spend')
    revenue = cols.get('revenue')

    def base_agg(data: pd.DataFrame, group_col: str) -> pd.DataFrame:
        use_cols = [c for c in [imp, clk, conv, spend, revenue] if c]
        agg_map = {c: 'sum' for c in use_cols}
        view_cols = [group_col] + use_cols
        g = data[view_cols].groupby(group_col, as_index=False).agg(agg_map)
        g = g.rename(columns={
            imp or '': 'impressions',
            clk or '': 'clicks',
            conv or '': 'conversions',
            spend or '': 'spend',
            revenue or '': 'revenue',
        })
        for c in ['impressions', 'clicks', 'conversions', 'spend', 'revenue']:
            if c not in g.columns:
                g[c] = 0.0
            g[c] = g[c].fillna(0.0)
        g['ctr'] = g.apply(lambda r: _safe_div(r['clicks'], r['impressions']) * 100, axis=1)
        g['cvr'] = g.apply(lambda r: _safe_div(r['conversions'], r['clicks']) * 100, axis=1)
        g['cpa'] = g.apply(lambda r: _safe_div(r['spend'], r['conversions']), axis=1)
        g['roas'] = g.apply(lambda r: _safe_div(r['revenue'], r['spend']), axis=1)
        g['roi'] = g.apply(lambda r: (_safe_div(r['revenue'] - r['spend'], r['spend']) * 100) if r['spend'] else 0.0, axis=1)
        return g

    out: Dict[str, pd.DataFrame] = {}
    if cols.get('platform'):
        out['platform'] = base_agg(df, cols['platform'])
    if cols.get('campaign_id'):
        out['campaign'] = base_agg(df, cols['campaign_id'])
    if cols.get('age_group') and cols.get('platform'):
        segment_col = '__segment'
        # Only keep minimal columns for segment aggregation to reduce memory
        keep = [cols['platform'], cols['age_group']]
        keep += [c for c in [imp, clk, conv, spend, revenue] if c]
        tmp = df[keep].copy()
        tmp[segment_col] = tmp[cols['platform']].astype(str) + ' | ' + tmp[cols['age_group']].astype(str)
        seg = base_agg(tmp, segment_col).rename(columns={segment_col: 'segment'})
        out['segment'] = seg
    return out

def budget_recommendation(platform_df: pd.DataFrame, total_spend: float) -> pd.DataFrame:
    dfp = platform_df.copy()
    # Score: prefer high ROAS & ROI & CVR; penalize high CPA
    def norm(s: pd.Series) -> pd.Series:
        if s.max() == s.min():
            return pd.Series(np.ones(len(s)), index=s.index)
        return (s - s.min()) / (s.max() - s.min())

    dfp['score'] = (
        0.45 * norm(dfp['roas'].clip(lower=0)) +
        0.35 * norm(dfp['roi']) +
        0.20 * norm(dfp['cvr'])
    ) - (0.25 * norm(dfp['cpa']))
    dfp['score'] = dfp['score'].clip(lower=0)
    if dfp['score'].sum() == 0:
        dfp['score'] = 1.0
    dfp['recommended_spend'] = (dfp['score'] / dfp['score'].sum()) * float(total_spend)
    dfp['delta'] = dfp['recommended_spend'] - dfp['spend']
    return dfp

def build_optimization_recommendations(platform_df: Optional[pd.DataFrame], 
                                       campaign_df: Optional[pd.DataFrame], 
                                       segment_df: Optional[pd.DataFrame]) -> List[Dict[str, str]]:
    recos: List[Dict[str, str]] = []

    if platform_df is not None and not platform_df.empty:
        best = platform_df.sort_values(['roas', 'roi'], ascending=False).head(1).iloc[0]
        worst = platform_df.sort_values(['cpa', 'roi'], ascending=[False, True]).head(1).iloc[0]
        best_name = str(best.get('platform', best.iloc[0]))
        worst_name = str(worst.get('platform', worst.iloc[0]))
        recos.append({
            'level': '✅',
            'title': tf("reco_increase_budget_title", name=best_name),
            'detail': f"ROAS {best['roas']:.2f}x | ROI {best['roi']:.1f}% | CPA {format_vnd(float(best['cpa']))}",
            'action': t("reco_increase_budget_action"),
        })
        recos.append({
            'level': '⚠️',
            'title': tf("reco_reduce_spend_title", name=worst_name),
            'detail': f"CPA {format_vnd(float(worst['cpa']))} | ROI {worst['roi']:.1f}% | CVR {worst['cvr']:.2f}%",
            'action': t("reco_reduce_spend_action"),
        })

    if segment_df is not None and not segment_df.empty:
        seg_best = segment_df.sort_values(['roas', 'cvr'], ascending=False).head(1).iloc[0]
        seg_worst = segment_df.sort_values(['cpa', 'roi'], ascending=[False, True]).head(1).iloc[0]
        segment_name = seg_best.get('segment', 'Segment')
        recos.append({
            'level': '🔥',
            'title': tf("reco_prioritize_segment_title", name=str(segment_name)),
            'detail': f"CVR {seg_best['cvr']:.2f}% | ROAS {seg_best['roas']:.2f}x | CTR {seg_best['ctr']:.2f}%",
            'action': t("reco_prioritize_segment_action"),
        })
        seg_worst_name = seg_worst.get('segment', 'Segment')
        recos.append({
            'level': '🧯',
            'title': tf("reco_derisk_segment_title", name=str(seg_worst_name)),
            'detail': f"CPA {format_vnd(float(seg_worst['cpa']))} | ROI {seg_worst['roi']:.1f}%",
            'action': t("reco_derisk_segment_action"),
        })

    if campaign_df is not None and not campaign_df.empty:
        top = campaign_df.sort_values(['roas', 'conversions'], ascending=False).head(1).iloc[0]
        low = campaign_df.sort_values(['roi', 'roas'], ascending=True).head(1).iloc[0]
        top_name = str(top.get('campaign', top.iloc[0]))
        low_name = str(low.get('campaign', low.iloc[0]))
        recos.append({
            'level': '📈',
            'title': tf("reco_scale_campaign_title", name=top_name),
            'detail': tf(
                "reco_scale_campaign_detail",
                roas=float(top['roas']),
                conversions=f"{int(top['conversions']):,}",
            ),
            'action': t("reco_scale_campaign_action"),
        })
        recos.append({
            'level': '🛑',
            'title': tf("reco_pause_campaign_title", name=low_name),
            'detail': f"ROI {low['roi']:.1f}% | ROAS {low['roas']:.2f}x | CPA {format_vnd(float(low['cpa']))}",
            'action': t("reco_pause_campaign_action"),
        })

    # Limit to a clean set
    return recos[:6]

def create_conversion_funnel(df, kpis):
    """Tạo conversion funnel chart"""
    # Scale funnel by cost: spend -> (CPM) impressions -> (CTR) clicks -> (CVR) conversions
    spend_vnd = float(kpis.get('total_spend', 0.0) or 0.0)
    cpm_vnd = float(kpis.get('cpm', 0.0) or 0.0)
    ctr_pct = float(kpis.get('ctr', 0.0) or 0.0)
    cvr_pct = float(kpis.get('cvr', 0.0) or 0.0)

    # Reasonable fallbacks when dataset is missing fields
    if cpm_vnd <= 0:
        cpm_vnd = float(os.getenv("DEFAULT_CPM_VND", "50000"))  # VND per 1,000 impressions
    if ctr_pct <= 0:
        ctr_pct = float(os.getenv("DEFAULT_CTR_PCT", "2.0"))
    if cvr_pct <= 0:
        cvr_pct = float(os.getenv("DEFAULT_CVR_PCT", "3.0"))

    est_impressions = max(0.0, (spend_vnd / cpm_vnd) * 1000.0) if cpm_vnd else 0.0
    est_clicks = max(0.0, est_impressions * (ctr_pct / 100.0))
    est_conversions = max(0.0, est_clicks * (cvr_pct / 100.0))

    funnel_text = [
        f"{est_impressions:,.0f}",
        f"{est_clicks:,.0f}<br>CTR {ctr_pct:.2f}%",
        f"{est_conversions:,.0f}<br>CVR {cvr_pct:.2f}%",
    ]

    funnel_data = {
        'Stage': [t('funnel_impressions'), t('funnel_clicks'), t('funnel_conversions')],
        'Count': [
            round(est_impressions),
            round(est_clicks),
            round(est_conversions),
        ],
    }
    funnel_df = pd.DataFrame(funnel_data)
    
    fig = go.Figure(
        go.Funnel(
            y=funnel_df['Stage'],
            x=funnel_df['Count'],
            marker=dict(
                color=['#0084ff', '#10b981', '#f59e0b'],
                line=dict(color='rgba(255,255,255,0.25)', width=1),
            ),
            textposition="outside",
            text=funnel_text,
            texttemplate="%{text}",
            textfont=dict(size=14, color="#e5e7eb"),
            hovertemplate="%{label}<br>%{value:,.0f}<extra></extra>",
        )
    )
    _apply_plotly_base_layout(fig, height=520)
    fig.update_layout(margin=dict(l=120, r=30, t=10, b=10))
    return fig

def create_trend_chart(df, kpis):
    """Tạo CTR/CVR trend chart (data-driven nếu có date)"""
    cols = detect_columns(df)
    daily = prepare_timeseries(df, cols)
    fig = go.Figure()

    if daily is None or daily.empty:
        # fallback: show single-point reference
        fig.add_trace(go.Scatter(
            x=[1], y=[kpis.get('ctr', 0.0)],
            name='CTR',
            mode='markers',
            marker=dict(size=10, color='#0084ff')
        ))
        fig.add_trace(go.Scatter(
            x=[1], y=[kpis.get('cvr', 0.0)],
            name='CVR',
            mode='markers',
            marker=dict(size=10, color='#10b981')
        ))
        fig.update_xaxes(visible=False)
    else:
        fig.add_trace(go.Scatter(
            x=daily['__date'], y=daily['ctr'],
            name='CTR',
            mode='lines+markers',
            line=dict(color='#0084ff', width=2),
            marker=dict(size=5)
        ))
        fig.add_trace(go.Scatter(
            x=daily['__date'], y=daily['cvr'],
            name='CVR',
            mode='lines+markers',
            line=dict(color='#10b981', width=2),
            marker=dict(size=5)
        ))
    _apply_plotly_base_layout(fig, height=520)
    fig.update_layout(hovermode='x unified', margin=dict(l=10, r=10, t=20, b=10))
    fig.update_yaxes(title_text="%", ticksuffix="%", rangemode="tozero")
    return fig

def extract_insights(df, kpis):
    """Trích xuất Key Insights"""
    cols = detect_columns(df)
    perf = aggregate_performance(df, cols)
    insights: List[str] = []

    insights.append(t("insight_dataset_scale").format(rows=len(df)))

    if 'ctr' in kpis:
        insights.append(
            t("insight_overall").format(
                ctr=format_percent(kpis['ctr']),
                cvr=format_percent(kpis.get('cvr', 0.0)),
            )
        )

    if cols.get('platform') and 'platform' in perf and not perf['platform'].empty:
        best_plat = perf['platform'].sort_values('roas', ascending=False).head(1).iloc[0]
        worst_plat = perf['platform'].sort_values('cpa', ascending=False).head(1).iloc[0]
        insights.append(
            t("insight_best_platform").format(name=best_plat.iloc[0], roas=float(best_plat['roas']))
        )
        insights.append(
            t("insight_cost_risk").format(
                name=worst_plat.iloc[0],
                cpa_fmt=format_vnd(float(worst_plat['cpa'])),
            )
        )

    if cols.get('campaign_id') and 'campaign' in perf and not perf['campaign'].empty:
        top_campaign = perf['campaign'].sort_values(['roas', 'conversions'], ascending=False).head(1).iloc[0]
        insights.append(
            t("insight_top_campaign").format(name=top_campaign.iloc[0], roas=float(top_campaign['roas']))
        )

    if kpis.get('roi', 0.0) < 0:
        insights.append(t("insight_negative_roi"))

    return insights

def check_system_health(api_base: str) -> Dict[str, str]:
    status = {
        'api': 'UNKNOWN',
        'db': 'UNKNOWN',
        'spark': 'READY',
    }
    if requests is None:
        return status
    try:
        r = requests.get(f"{api_base.rstrip('/')}/health", timeout=2)
        if r.status_code != 200:
            status['api'] = 'OFFLINE'
            return status
        payload = r.json() if hasattr(r, 'json') else {}
        status['api'] = 'ONLINE'
        if isinstance(payload, dict):
            if payload.get('postgres_ready') is True:
                status['db'] = 'ONLINE'
            elif payload.get('postgres_ready') is False:
                status['db'] = 'DEGRADED'
            else:
                status['db'] = 'UNKNOWN'
            # Some health payloads include spark readiness
            if payload.get('spark_ready') is True:
                status['spark'] = 'ACTIVE'
        return status
    except Exception:
        status['api'] = 'OFFLINE'
        return status

def spark_processing_panel(rows: int, file_mb: float, df: pd.DataFrame, 
                           cols: Dict[str, Optional[str]], measured_sec: float) -> Dict[str, float]:
    workers = 4
    partitions = int(min(32, max(8, round(rows / 75000))))
    # deep=False is much faster for large frames; good enough for an estimate
    mem_bytes = int(df.memory_usage(deep=False).sum())
    mem_gb = mem_bytes / (1024 ** 3)

    # Spark-ish estimate: assume Spark is ~3-5x faster than pandas for large data with 4 workers
    spark_est = max(1.2, measured_sec / 3.5)
    return {
        'rows': float(rows),
        'file_mb': float(file_mb),
        'partitions': float(partitions),
        'workers': float(workers),
        'mem_gb': float(mem_gb),
        'pandas_sec': float(measured_sec),
        'spark_est_sec': float(spark_est),
    }

def roi_by_platform_chart(platform_df: pd.DataFrame, platform_col_name: str) -> go.Figure:
    fig = px.bar(
        platform_df.sort_values('roi', ascending=False),
        x=platform_col_name,
        y='roi',
        color='roas',
        labels={platform_col_name: t('chart_platform'), 'roi': t('chart_roi'), 'roas': t('chart_roas')},
        template='plotly_dark',
        color_continuous_scale=['#ef4444', '#f59e0b', '#10b981']
    )
    _apply_plotly_base_layout(fig, height=520)
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    return fig

def spend_vs_revenue_chart(daily: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily['__date'], y=daily.get('spend', pd.Series([0]*len(daily))),
        name=t('chart_spend'), mode='lines', line=dict(color='#ef4444', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=daily['__date'], y=daily.get('revenue', pd.Series([0]*len(daily))),
        name=t('chart_revenue'), mode='lines', line=dict(color='#22d3ee', width=2)
    ))
    _apply_plotly_base_layout(fig, height=520)
    fig.update_layout(title_text="", hovermode='x unified', margin=dict(l=10, r=10, t=35, b=10))
    fig.update_yaxes(tickformat=",.0f")
    return fig

def ctr_heatmap_chart(df: pd.DataFrame, cols: Dict[str, Optional[str]]) -> Optional[go.Figure]:
    if not cols.get('platform') or not cols.get('age_group') or not cols.get('impressions') or not cols.get('clicks'):
        return None
    plat = cols['platform']
    age = cols['age_group']
    imp = cols['impressions']
    clk = cols['clicks']
    assert plat and age and imp and clk

    tmp = df[[plat, age, imp, clk]].copy()
    piv = tmp.groupby([age, plat], as_index=False).agg({imp: 'sum', clk: 'sum'})
    piv['ctr'] = piv.apply(lambda r: _safe_div(r[clk], r[imp]) * 100, axis=1)
    heat = piv.pivot(index=age, columns=plat, values='ctr').fillna(0.0)

    fig = px.imshow(
        heat,
        text_auto='.2f',
        aspect='auto',
        color_continuous_scale=['#0b1020', '#0084ff', '#10b981'],
    )
    _apply_plotly_base_layout(fig, height=560)
    fig.update_layout(margin=dict(l=10, r=10, t=35, b=10))
    fig.update_xaxes(title_text=t('chart_platform'))
    fig.update_yaxes(title_text=t('chart_age_group'))
    return fig

def budget_optimization_chart(reco_df: pd.DataFrame, platform_col_name: str) -> go.Figure:
    show = reco_df.sort_values('delta', ascending=False).head(10)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=show[platform_col_name].astype(str),
        y=show['spend'],
        name=t('chart_current_spend'),
        marker_color='#ef4444'
    ))
    fig.add_trace(go.Bar(
        x=show[platform_col_name].astype(str),
        y=show['recommended_spend'],
        name=t('chart_recommended_spend'),
        marker_color='#10b981'
    ))
    _apply_plotly_base_layout(fig, height=520)
    fig.update_layout(
        barmode='group',
        title_text="",
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
    )
    fig.update_yaxes(tickformat=",.0f")
    return fig

def spark_performance_chart(current_rows: int, spark_est_sec: float, workers: int) -> go.Figure:
    sizes_m = np.array([0.1, 0.25, 0.5, 1.0, 2.0])
    current_m = max(0.05, current_rows / 1_000_000)
    # Calibrate linear model from current estimate
    slope = spark_est_sec / current_m
    est = (sizes_m * slope) / max(1, workers)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sizes_m, y=est,
        mode='lines+markers',
        name=t('chart_est_spark_time'),
        line=dict(color='#f59e0b', width=2),
        marker=dict(size=7)
    ))
    _apply_plotly_base_layout(fig, height=520)
    fig.update_layout(title=t('chart_spark_perf'), xaxis_title=t('chart_dataset_size'), yaxis_title=t('chart_exec_time'))
    return fig


def _apply_plotly_base_layout(fig: go.Figure, height: int = 520) -> None:
    """Apply consistent dark theme and sizing to Plotly figures used in the Streamlit UI."""
    try:
        fig.update_layout(
            template="plotly_dark",
            height=height,
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#0b1220",
            font=dict(color="#e5e7eb"),
            coloraxis_colorbar=dict(title_font=dict(color="#e5e7eb"), tickfont=dict(color="#e5e7eb")),
        )
        # Ensure consistent legend style
        fig.update_layout(legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.06)"))
    except Exception:
        # Non-fatal: ignore layout errors
        pass

# ==================== LAYOUT ====================

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"# {t('header_title')}")
    st.markdown(f"*{t('header_subtitle')}*")

with col2:
    st.markdown(
        """
    <div style='text-align: right; padding-top: 20px;'>
        <span class='status-badge status-running'>"""
        + t("online")
        + """</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# Sidebar: language + auth + navigation
with st.sidebar:
    if "lang" not in st.session_state:
        st.session_state["lang"] = "vi"
    st.session_state["lang"] = "vi"

    auth = setup_auth(DEFAULT_API)
    role = str(auth.get("role") or "guest")
    token = auth.get("token")

    dashboard_ctx: dict[str, Any] = load_dashboard_context(DEFAULT_API, token)

    st.markdown(f"## {t('nav_title')}")
    nav_options = build_nav_options(role)

    nav_mode = st.radio(
        label="",
        options=nav_options,
        format_func=nav_label,
        label_visibility="collapsed",
    )

# ==================== MAIN CONTENT ====================

if nav_mode == "dashboard":
    render_dashboard_page(DEFAULT_API, dashboard_ctx, _empty_dashboard_message, format_vnd)

elif nav_mode == "profile":
    render_profile_page(DEFAULT_API, token, t("guest_mode"))

elif nav_mode == "ads":
    render_ads_page(DEFAULT_API, dashboard_ctx, token, t("guest_mode"))

elif nav_mode == "analytics":
    render_analytics_page(DEFAULT_API, dashboard_ctx, token, role, t("guest_mode"), t("token_invalid"))

elif nav_mode == "reports":
    render_reports_page(DEFAULT_API, dashboard_ctx, token, role, t("token_invalid"))

if nav_mode == "upload":
    # Use the extracted upload page renderer to avoid duplication and styling issues
    try:
        from pages.upload import render_upload_page

        render_upload_page(
            DEFAULT_API,
            dashboard_ctx,
            token,
            role,
            t,
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
            USD_TO_VND_RATE,
        )
    except Exception as exc:
        st.error(f"Upload page error: {exc}")

elif nav_mode == "spark":
    render_spark_page(DEFAULT_API, role, token, t("token_invalid"))

elif nav_mode == "ml":
    render_ml_page(DEFAULT_API, role, token, t("token_invalid"))

elif nav_mode == "user_management":
    render_user_management_page(DEFAULT_API, role, token, t("token_invalid"))

elif nav_mode == "admin":
    # Admin area: sessions + dataset admin
    render_sessions_page(DEFAULT_API, role, token)
    st.markdown("---")
    render_dataset_admin_page(DEFAULT_API, role, token, t("token_invalid"))

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 11px; padding: 20px;'>
    """ + t("footer") + """
</div>
""", unsafe_allow_html=True)
