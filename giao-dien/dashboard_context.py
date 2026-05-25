from __future__ import annotations

from typing import Any

from api_client import api_get


def load_dashboard_context(api_base: str, token: str | None) -> dict[str, Any]:
    context: dict[str, Any] = {"has_data": False, "summary": {}, "active_dataset": None}
    if not token:
        return context

    try:
        loaded = api_get(api_base, "/api/dashboard", token=token)
    except Exception:
        return context

    if isinstance(loaded, dict):
        context.update(loaded)
    return context