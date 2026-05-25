from __future__ import annotations

import os
from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from api_client import api_delete, api_get, api_post_json, api_patch_json


def render_spark_page(api_base: str, role: str, token: str | None, token_invalid_message: str) -> None:
    st.markdown("<h2 class='section-header'>Quản lý Spark</h2>", unsafe_allow_html=True)
    if role != "admin":
        st.error("Access denied: admin only")
        return
    if not token:
        st.info(token_invalid_message)
        return

    spark_input = st.text_input("Đường dẫn đầu vào", value=os.getenv("SPARK_INPUT_PATH", "data/data_100_campaigns_high_cvr.csv"))
    if st.button("Chạy Spark pipeline", use_container_width=True):
        try:
            result = api_post_json(api_base, f"/api/spark/pipeline/run?input_path={spark_input}&pipeline_type=full", {}, token=token)
            st.success("Đã khởi chạy pipeline")
            if isinstance(result, dict):
                cols = st.columns(3)
                cols[0].metric("Trạng thái", str(result.get("status", "started")))
                cols[1].metric("Tác vụ", str(result.get("task", result.get("pipeline_type", "full"))))
                cols[2].metric("Đầu vào", os.path.basename(str(result.get("input_path", spark_input))))
                st.caption("Tác vụ Spark đã được gửi. Trạng thái mới nhất nằm bên dưới.")
            else:
                st.write(result)
        except Exception as exc:
            st.error(str(exc))
    try:
        status = api_get(api_base, "/api/spark/pipeline/status", token=token)
        if isinstance(status, dict):
            cols = st.columns(4)
            cols[0].metric("Pipeline", str(status.get("pipeline", status.get("name", "Spark"))))
            cols[1].metric("Trạng thái", str(status.get("state", status.get("status", "không rõ"))))
            cols[2].metric("Cập nhật", str(status.get("updated_at", status.get("last_run", "-"))))
            cols[3].metric("Số dòng", status.get("rows", status.get("count", 0)))
            st.caption("Chỉ hiển thị tóm tắt để tránh rối giao diện.")
        else:
            st.write(status)
    except Exception as exc:
        st.info(str(exc))


def render_ml_page(api_base: str, role: str, token: str | None, token_invalid_message: str) -> None:
    st.markdown("<h2 class='section-header'>Quản lý ML</h2>", unsafe_allow_html=True)
    if role != "admin":
        st.error("Access denied: admin only")
        return
    if not token:
        st.info(token_invalid_message)
        return

    if st.button("Huấn luyện lại mô hình", use_container_width=True):
        try:
            result = api_post_json(api_base, "/api/ml/retrain", {}, token=token)
            st.success("Đã huấn luyện lại")
            if isinstance(result, dict):
                cols = st.columns(4)
                cols[0].metric("Trạng thái", str(result.get("status", "xong")))
                cols[1].metric("Mô hình", str(result.get("model_name", result.get("model", "ml"))))
                cols[2].metric("Số dòng", result.get("rows", result.get("trained_rows", 0)))
                cols[3].metric("Thời gian", f"{float(result.get('duration_sec', 0.0) or 0.0):.1f}s")
                st.caption("Kết quả được tóm tắt, không hiển thị payload thô.")
            else:
                st.write(result)
        except Exception as exc:
            st.error(str(exc))


def render_user_management_page(api_base: str, role: str, token: str | None, token_invalid_message: str) -> None:
    st.markdown("<h2 class='section-header'>Quản lý người dùng</h2>", unsafe_allow_html=True)
    if role != "admin":
        st.error("Access denied: admin only")
        return
    if not token:
        st.info(token_invalid_message)
        return

    try:
        # Load users and sessions to compute KPIs and last-login
        users_resp = api_get(api_base, "/api/admin/users", token=token)
        sessions_resp = api_get(api_base, "/api/admin/sessions", token=token)

        users = users_resp.get("items", []) if isinstance(users_resp, dict) else []
        total_users = users_resp.get("total", len(users)) if isinstance(users_resp, dict) else len(users)

        sessions = sessions_resp.get("items", []) if isinstance(sessions_resp, dict) else []
        active_sessions = [s for s in sessions if s.get("is_active")]
        active_sessions_count = len(active_sessions)
        active_users_set = set([s.get("username") for s in active_sessions if s.get("username")])
        active_users_count = len(active_users_set)

        # KPIs row
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Users", str(total_users))
        # analysts count
        analysts_count = sum(1 for u in users if (u.get("role") or "").lower() == "analyst")
        k2.metric("Active Sessions", str(active_sessions_count))
        k3.metric("Active Users", str(active_users_count))
        k4.metric("Analysts", str(analysts_count))

        st.markdown("---")
        st.subheader("User list")

        if not users:
            st.info("Không tìm thấy người dùng")
        else:
            # Build last-login map from sessions (most recent created_at)
            last_login = {}
            for s in sessions:
                uname = s.get("username")
                ts = s.get("created_at") or s.get("expires_at")
                if not uname:
                    continue
                prev = last_login.get(uname)
                if not prev or (ts and ts > prev):
                    last_login[uname] = ts

            # Render simplified table rows with actions
            for u in users:
                uid = u.get("id")
                uname = u.get("username")
                urole = u.get("role") or "user"
                is_active = bool(u.get("is_active", True))
                status = "Disabled" if not is_active else ("Online" if uname in active_users_set else "Offline")
                lj = last_login.get(uname, "-")

                cols = st.columns([2, 1, 1, 1, 2])
                with cols[0]:
                    st.text(uname)
                with cols[1]:
                    st.text(urole)
                with cols[2]:
                    st.text(status)
                with cols[3]:
                    st.text(lj)
                with cols[4]:
                    # Action buttons
                    if is_active:
                        if st.button("Disable", key=f"disable-{uid}"):
                            try:
                                api_patch_json(api_base, f"/api/admin/users/{uid}", {"is_active": False}, token=token)
                                st.success(f"Disabled {uname}")
                            except Exception as exc:
                                st.error(str(exc))
                    else:
                        if st.button("Enable", key=f"enable-{uid}"):
                            try:
                                api_patch_json(api_base, f"/api/admin/users/{uid}", {"is_active": True}, token=token)
                                st.success(f"Enabled {uname}")
                            except Exception as exc:
                                st.error(str(exc))

                    if st.button("Delete", key=f"delete-{uid}"):
                        try:
                            api_delete(api_base, f"/api/admin/users/{uid}", token=token)
                            st.success(f"Deleted {uname}")
                        except Exception as exc:
                            st.error(str(exc))

                    if st.button("Reset role", key=f"resetrole-{uid}"):
                        try:
                            api_patch_json(api_base, f"/api/admin/users/{uid}", {"role": "user"}, token=token)
                            st.success(f"Role reset for {uname}")
                        except Exception as exc:
                            st.error(str(exc))
    except Exception as exc:
        st.error(str(exc))


def render_sessions_page(api_base: str, role: str, token: str | None) -> None:
    st.markdown("<h2 class='section-header'>Phiên đăng nhập</h2>", unsafe_allow_html=True)
    if role != "admin":
        st.error("Access denied: admin only")
        return

    try:
        data = api_get(api_base, "/api/admin/sessions", token=token)
        items = data.get("items", [])
        st.write(f"Tổng phiên: {data.get('total', 0)}")
        for row in items:
            jti = row.get("jti")
            cols = st.columns([2, 2, 2, 2, 1, 1])
            with cols[0]:
                st.text(row.get("username") or row.get("user_id"))
            with cols[1]:
                st.text(row.get("ip_address"))
            with cols[2]:
                st.text(row.get("user_agent"))
            with cols[3]:
                st.text(row.get("expires_at"))
            with cols[4]:
                if row.get("is_active"):
                    if st.button("Thu hồi", key=f"revoke-{jti}"):
                        try:
                            api_post_json(api_base, f"/api/admin/sessions/{jti}/revoke", {}, token=token)
                            st.success(f"Đã thu hồi {jti}")
                            st.rerun()
                        except Exception as exc:
                            resp = getattr(exc, "response", None)
                            if resp is not None and getattr(resp, "status_code", None) == 404:
                                st.info(f"Phiên không tồn tại: {jti}")
                            else:
                                st.error(str(exc))
                else:
                    st.write("Không hoạt động")
            with cols[5]:
                if st.button("Xóa", key=f"delete-{jti}"):
                    try:
                        api_delete(api_base, f"/api/admin/sessions/{jti}", token=token)
                        st.success(f"Đã xóa {jti}")
                        st.rerun()
                    except Exception as exc:
                        resp = getattr(exc, "response", None)
                        if resp is not None and getattr(resp, "status_code", None) == 404:
                            st.info(f"Phiên không tìm thấy hoặc đã bị xóa: {jti}")
                        else:
                            st.error(str(exc))
    except Exception as exc:
        st.error(str(exc))


def render_dataset_admin_page(api_base: str, role: str, token: str | None, token_invalid_message: str) -> None:
    st.markdown("<h2 class='section-header'>Quản lý Dữ liệu (Admin)</h2>", unsafe_allow_html=True)
    if role != "admin":
        st.error("Access denied: admin only")
        return
    if not token:
        st.info(token_invalid_message)
        return

    try:
        # reuse dashboard endpoint to get active dataset + history
        dash = api_get(api_base, "/api/dashboard", token=token)
        active = dash.get("active_dataset") if isinstance(dash, dict) else None
        history = dash.get("dataset_history", []) if isinstance(dash, dict) else []

        st.subheader("Active dataset")
        if not active:
            st.info("Không có dataset đang hoạt động")
        else:
            st.write(active)
            if st.button("Vô hiệu hóa dataset đang hoạt động", use_container_width=True):
                try:
                    resp = api_delete(api_base, "/api/dataset/active", token=token)
                    st.success(resp.get("message", "Đã vô hiệu hóa"))
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        st.markdown("---")
        st.subheader("Lịch sử dataset")
        if not history:
            st.info("Không tìm thấy lịch sử dataset")
            return

        # Build options mapping
        options = [f"[{row.get('id')}] {row.get('file_name')} — {row.get('created_at', '')}" for row in history]
        choice = st.selectbox("Chọn phiên để kích hoạt", options=options)
        idx = options.index(choice)
        selected = history[idx]

        cols = st.columns(3)
        with cols[0]:
            st.text("File:")
            st.text(selected.get("file_name"))
        with cols[1]:
            st.text("Uploaded by:")
            st.text(selected.get("uploaded_by", "-"))
        with cols[2]:
            st.text("Rows:")
            st.text(selected.get("scored_rows", selected.get("segment_rows", 0)))

        if st.button("Kích hoạt phiên đã chọn", use_container_width=True):
            try:
                resp = api_post_json(api_base, f"/api/dataset/active/{selected.get('id')}", {}, token=token)
                st.success(resp.get("message", "Đã kích hoạt"))
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    except Exception as exc:
        st.error(str(exc))