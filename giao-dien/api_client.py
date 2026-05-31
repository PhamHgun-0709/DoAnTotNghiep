from __future__ import annotations

import io
from typing import Any

import requests
import streamlit as st


def auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def raise_api_error(method: str, url: str, res) -> None:
    try:
        body = res.json()
    except Exception:
        body = (res.text or "").strip()

    detail = body
    if isinstance(body, dict) and "detail" in body:
        detail = body.get("detail")

    raise requests.HTTPError(f"{method} {url} -> HTTP {res.status_code}: {detail}", response=res)


def _build_url(api_base: str, path: str) -> str:
    """Join api_base and path robustly to avoid doubled segments like '/api/api'."""
    if not api_base:
        return path
    base = api_base.rstrip("/")
    p = path.lstrip("/")
    # If both contain a leading 'api' segment, drop the duplicate from the path
    if base.endswith("/api") and p.startswith("api/"):
        p = p[len("api/"):]
    return f"{base}/{p}"


@st.cache_data(ttl=20)
def api_get(api_base: str, path: str, params: dict | None = None, token: str | None = None):
    url = _build_url(api_base, path)
    res = requests.get(url, params=params, headers=auth_headers(token), timeout=30)
    if not res.ok:
        raise_api_error("GET", url, res)
    return res.json()


def api_get_nocache(api_base: str, path: str, params: dict | None = None, token: str | None = None):
    """GET without Streamlit caching (useful for admin endpoints where freshness matters)."""
    url = _build_url(api_base, path)
    res = requests.get(url, params=params, headers=auth_headers(token), timeout=30)
    if not res.ok:
        raise_api_error("GET", url, res)
    return res.json()


def api_post_json(api_base: str, path: str, payload: dict, token: str | None = None):
    url = _build_url(api_base, path)
    res = requests.post(url, json=payload, headers=auth_headers(token), timeout=30)
    if not res.ok:
        raise_api_error("POST", url, res)
    return res.json()


def api_post_file(api_base: str, path: str, file_name: str, file_bytes: bytes, token: str):
    files = {"file": (file_name, io.BytesIO(file_bytes), "text/csv")}
    url = _build_url(api_base, path)
    res = requests.post(url, files=files, headers=auth_headers(token), timeout=120)
    if not res.ok:
        raise_api_error("POST", url, res)
    return res.json()


def api_patch_json(api_base: str, path: str, payload: dict[str, Any], token: str | None = None) -> Any:
    url = _build_url(api_base, path)
    res = requests.patch(url, json=payload, headers=auth_headers(token), timeout=30)
    if not res.ok:
        raise_api_error("PATCH", url, res)
    return res.json()


def api_delete(api_base: str, path: str, token: str | None = None) -> Any:
    url = _build_url(api_base, path)
    res = requests.delete(url, headers=auth_headers(token), timeout=30)
    if not res.ok:
        raise_api_error("DELETE", url, res)
    try:
        return res.json()
    except Exception:
        return {"status": "ok"}


def api_get_bytes(
    api_base: str,
    path: str,
    params: dict[str, Any] | None = None,
    token: str | None = None,
) -> bytes:
    url = _build_url(api_base, path)
    res = requests.get(url, params=params, headers=auth_headers(token), timeout=30)
    if not res.ok:
        raise_api_error("GET", url, res)
    return res.content