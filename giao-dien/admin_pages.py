from __future__ import annotations

import os
from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from api_client import api_delete, api_get, api_get_nocache, api_post_json, api_patch_json
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except Exception:
    from datetime import timezone as ZoneInfo  # fallback; will show UTC

_DISPLAY_TZ = ZoneInfo("Asia/Ho_Chi_Minh") if hasattr(ZoneInfo, '__class__') or True else None

def _format_ts(ts: any) -> str:
    if not ts:
        return "-"
    try:
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts)
            except Exception:
                # fallback parse
                from dateutil import parser

                dt = parser.parse(ts)
        elif isinstance(ts, datetime):
            dt = ts
        else:
            return str(ts)
        # if naive, assume UTC
        if dt.tzinfo is None:
            from datetime import timezone

            dt = dt.replace(tzinfo=timezone.utc)
        # convert to display tz
        try:
            dt_local = dt.astimezone(_DISPLAY_TZ)
        except Exception:
            dt_local = dt
        return dt_local.strftime("%Y-%m-%d %H:%M:%S %z")
    except Exception:
        return str(ts)


def _safe_rerun() -> None:
    """Attempt to rerun the Streamlit app in a backwards-compatible way.

    Tries `st.experimental_rerun()` first, then `st.rerun()`. If neither exists
    (older/newer Streamlit builds), toggles a session_state flag to trigger
    a re-render.
    """
    try:
        # prefer experimental if available
        if hasattr(st, "experimental_rerun"):
            try:
                st.experimental_rerun()
                return
            except Exception:
                pass
        if hasattr(st, "rerun"):
            try:
                st.rerun()
                return
            except Exception:
                pass
    except Exception:
        pass
    # fallback: toggle a session_state key to force rerender
    st.session_state["_refresh"] = not st.session_state.get("_refresh", False)


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
            cols[2].metric("Cập nhật", _format_ts(status.get("updated_at", status.get("last_run", "-"))))
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


def render_user_management_page(
    api_base: str,
    role: str,
    token: str | None,
    token_invalid_message: str,
    current_username: str | None = None,
) -> None:
    st.markdown("<h2 class='section-header'>Quản lý người dùng</h2>", unsafe_allow_html=True)
    if role != "admin":
        st.error("Access denied: admin only")
        return
    if not token:
        st.info(token_invalid_message)
        return

    try:
        # Load users and sessions to compute KPIs and last-login
        users_resp = api_get_nocache(api_base, "/api/admin/users", token=token)
        sessions_resp = api_get_nocache(api_base, "/api/admin/sessions", token=token)

        users = users_resp.get("items", []) if isinstance(users_resp, dict) else []
        total_users = users_resp.get("total", len(users)) if isinstance(users_resp, dict) else len(users)

        sessions = sessions_resp.get("items", []) if isinstance(sessions_resp, dict) else []
        active_sessions = [s for s in sessions if s.get("is_active")]
        active_sessions_count = len(active_sessions)
        active_users_set = set([s.get("username") for s in active_sessions if s.get("username")])
        active_users_count = len(active_users_set)

        # KPIs row
        k1, k2, k3, k4 = st.columns(4, gap="small")
        k1.metric("Total Users", str(total_users))
        # analysts count
        analysts_count = sum(1 for u in users if (u.get("role") or "").lower() == "analyst")
        k2.metric("Active Sessions", str(active_sessions_count))
        k3.metric("Active Users", str(active_users_count))
        k4.metric("Analysts", str(analysts_count))

        st.markdown("---")
        st.subheader("Tạo tài khoản mới")
        with st.form("create-user-form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            new_username = c1.text_input("Username", placeholder="vd: minh.nguyen")
            new_email = c2.text_input("Email", placeholder="vd: minh@example.com")
            c3, c4 = st.columns(2)
            new_password = c3.text_input("Password", type="password", placeholder="Nhập mật khẩu")
            new_role = c4.selectbox("Role", ["analyst", "user", "guest", "admin"], index=0)
            new_active = st.checkbox("Kích hoạt ngay", value=True)
            submitted = st.form_submit_button("Tạo tài khoản", use_container_width=True)
            if submitted:
                try:
                    result = api_post_json(
                        api_base,
                        "/api/admin/users",
                        {
                            "username": new_username,
                            "email": new_email,
                            "password": new_password,
                            "role": new_role,
                            "is_active": new_active,
                        },
                        token=token,
                    )
                    user = result.get("user", {}) if isinstance(result, dict) else {}
                    st.success(f"Đã tạo tài khoản: {user.get('username', new_username)}")
                    _safe_rerun()
                except Exception as exc:
                    resp = getattr(exc, "response", None)
                    if resp is not None:
                        st.error(f"HTTP {resp.status_code}: {resp.text}")
                    else:
                        st.error(str(exc))

        st.markdown("---")
        st.subheader("User list")
        filter_cols = st.columns([1.6, 1, 1], gap="small")
        search_term = filter_cols[0].text_input("Tìm người dùng", value="", placeholder="Nhập username...", label_visibility="collapsed")
        role_filter = filter_cols[1].selectbox("Role", ["Tất cả", "admin", "analyst", "user"], label_visibility="collapsed")
        status_filter = filter_cols[2].selectbox("Trạng thái", ["Tất cả", "Online", "Offline", "Disabled"], label_visibility="collapsed")

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

            filtered_users = []
            search_lower = search_term.strip().lower()
            for u in users:
                uname = str(u.get("username") or "")
                urole = str(u.get("role") or "user").lower()
                is_active = bool(u.get("is_active", True))
                status = "Disabled" if not is_active else ("Online" if uname in active_users_set else "Offline")
                if search_lower and search_lower not in uname.lower():
                    continue
                if role_filter != "Tất cả" and urole != role_filter:
                    continue
                if status_filter != "Tất cả" and status != status_filter:
                    continue
                filtered_users.append((u, status, urole, is_active))

            st.caption(f"Hiển thị {len(filtered_users)}/{len(users)} người dùng")

            header = st.columns([2.2, 1, 1, 1.4, 2.2], gap="small")
            header[0].markdown("**Người dùng**")
            header[1].markdown("**Vai trò**")
            header[2].markdown("**Trạng thái**")
            header[3].markdown("**Đăng nhập cuối**")
            header[4].markdown("**Hành động**")

            if not filtered_users:
                st.info("Không có người dùng khớp bộ lọc hiện tại.")
                return

            # Render each user as a compact card-like row
            for u, status, urole, is_active in filtered_users:
                uid = u.get("id")
                uname = u.get("username")
                lj = last_login.get(uname, "-")
                is_self = bool(current_username) and uname == current_username

                st.markdown("---")
                cols = st.columns([2.2, 1, 1, 1.4, 2.2], gap="small")
                with cols[0]:
                    st.markdown(f"**{uname}**")
                    st.caption(f"ID: {uid} · {u.get('email') or '-'}")
                with cols[1]:
                    st.markdown(f"<span class='status-badge status-running'>{urole}</span>", unsafe_allow_html=True)
                with cols[2]:
                    status_class = "status-success" if status == "Online" else ("status-danger" if status == "Disabled" else "status-warning")
                    st.markdown(f"<span class='status-badge {status_class}'>{status}</span>", unsafe_allow_html=True)
                with cols[3]:
                    st.caption(_format_ts(lj))

                if is_self:
                    with cols[4]:
                        st.caption("Tài khoản hiện tại")
                        st.info("Không thể vô hiệu hóa, xóa hoặc reset vai trò của chính mình.")
                else:
                    actions = cols[4].columns([1, 1, 1], gap="small")
                    with actions[0]:
                        if st.button("Vô hiệu hóa" if is_active else "Kích hoạt", key=f"toggle-{uid}", use_container_width=True):
                            try:
                                api_patch_json(
                                    api_base,
                                    f"/api/admin/users/{uid}",
                                    {"is_active": (not is_active)},
                                    token=token,
                                )
                                st.success(f"Đã cập nhật {uname}")
                                _safe_rerun()
                            except Exception as exc:
                                st.error(str(exc))

                    with actions[1]:
                        if st.button("Xóa", key=f"delete-{uid}", use_container_width=True):
                            try:
                                api_delete(api_base, f"/api/admin/users/{uid}", token=token)
                                st.success(f"Đã xóa {uname}")
                                _safe_rerun()
                            except Exception as exc:
                                st.error(str(exc))

                    with actions[2]:
                        reset_role = st.selectbox(
                            "Chọn vai trò",
                            ["admin", "analyst", "user", "guest"],
                            index=2 if urole not in {"admin", "analyst", "user", "guest"} else ["admin", "analyst", "user", "guest"].index(urole),
                            key=f"resetrole-select-{uid}",
                            label_visibility="visible",
                        )
                        if st.button("Thay đổi vai trò", key=f"resetrole-{uid}", use_container_width=True):
                            try:
                                api_patch_json(api_base, f"/api/admin/users/{uid}", {"role": reset_role}, token=token)
                                st.success(f"Đã thay đổi vai trò cho {uname} -> {reset_role}")
                                _safe_rerun()
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
        data = api_get_nocache(api_base, "/api/admin/sessions", token=token)
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
                st.text(_format_ts(row.get("expires_at")))
            with cols[4]:
                if row.get("is_active"):
                    if st.button("Thu hồi", key=f"revoke-{jti}"):
                        try:
                            api_post_json(api_base, f"/api/admin/sessions/{jti}/revoke", {}, token=token)
                            st.success(f"Đã thu hồi {jti}")
                            _safe_rerun()
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
                        _safe_rerun()
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
        # Check whether dataset endpoints are present in the running API's OpenAPI spec.
        # If the running API is an older build these endpoints may be missing (404 on calls).
        def _dataset_endpoints_available() -> tuple[bool, bool]:
            try:
                spec = api_get_nocache(api_base, "/openapi.json", token=token)
            except Exception:
                return False, False
            paths = spec.get("paths", {}) if isinstance(spec, dict) else {}
            has_deactivate = "/dataset/active" in paths and ("delete" in paths.get("/dataset/active", {}))
            has_activate = any(p.startswith("/dataset/active/") or p == "/dataset/active/{dataset_id}" for p in paths.keys())
            return has_activate, has_deactivate

        has_activate, has_deactivate = _dataset_endpoints_available()

        # reuse dashboard endpoint to get active dataset + history
        dash = api_get_nocache(api_base, "/api/dashboard", token=token)
        active = dash.get("active_dataset") if isinstance(dash, dict) else None
        history = dash.get("dataset_history", []) if isinstance(dash, dict) else []

        st.subheader("Active dataset")
        if not active:
            st.info("Không có dataset đang hoạt động")
        else:
            # Show a cleaned view with formatted timestamps
            disp = dict(active)
            for k in ("created_at", "updated_at"):
                if k in disp:
                    disp[k] = _format_ts(disp[k])
            st.json(disp)
            if has_deactivate and st.button("Vô hiệu hóa dataset đang hoạt động", use_container_width=True):
                try:
                    resp = api_delete(api_base, "/api/dataset/active", token=token)
                    st.success(resp.get("message", "Đã vô hiệu hóa"))
                    _safe_rerun()
                except Exception as exc:
                    try:
                        resp = getattr(exc, "response", None)
                        if resp is not None:
                            st.error(f"HTTP {resp.status_code}: {resp.text}")
                            if getattr(resp, "status_code", None) == 404:
                                st.info("Lỗi 404: có thể backend đang chạy phiên bản cũ không có endpoint này. Hãy khởi động lại dịch vụ API.")
                        else:
                            st.error(str(exc))
                    except Exception:
                        st.error(str(exc))

        st.markdown("---")
        st.subheader("Lịch sử dataset")
        if not history:
            st.info("Không tìm thấy lịch sử dataset")
            return

        # Build options mapping
        options = [f"[{row.get('id')}] {row.get('file_name')} — {_format_ts(row.get('created_at'))}" for row in history]
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
            st.caption(f"Uploaded at: {_format_ts(selected.get('created_at'))}")
        with cols[2]:
            st.text("Rows:")
            st.text(selected.get("scored_rows", selected.get("segment_rows", 0)))

        if has_activate:
            if st.button("Kích hoạt phiên đã chọn", use_container_width=True):
                try:
                    resp = api_post_json(api_base, f"/api/dataset/active/{selected.get('id')}", {}, token=token)
                    st.success(resp.get("message", "Đã kích hoạt"))
                    _safe_rerun()
                except Exception as exc:
                    try:
                        resp = getattr(exc, "response", None)
                        if resp is not None:
                            st.error(f"HTTP {resp.status_code}: {resp.text}")
                            if getattr(resp, "status_code", None) == 404:
                                st.info("Lỗi 404: có thể backend đang chạy phiên bản cũ không có endpoint này. Hãy khởi động lại dịch vụ API.")
                        else:
                            st.error(str(exc))
                    except Exception:
                        st.error(str(exc))
        else:
            st.info("Tính năng kích hoạt/vô hiệu hóa dataset không khả dụng trên API đang chạy. Hãy cập nhật/khởi động lại dịch vụ API nếu cần.")

    except Exception as exc:
        st.error(str(exc))