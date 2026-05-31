from __future__ import annotations

import json
from typing import Any

from app.core.logging_config import logger


def log_admin_session_action(
    action: str,
    *,
    actor_username: str,
    actor_email: str | None,
    target_jti: str,
    target_username: str | None = None,
    target_user_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "action": action,
        "actor_username": actor_username,
        "actor_email": actor_email,
        "target_jti": target_jti,
        "target_username": target_username,
        "target_user_id": target_user_id,
    }
    if extra:
        payload.update(extra)

    logger.info("AUDIT %s", json.dumps(payload, ensure_ascii=False, sort_keys=True))


def log_admin_user_action(
    action: str,
    *,
    actor_username: str,
    actor_email: str | None,
    target_user_id: int,
    target_username: str | None = None,
    target_email: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "action": action,
        "actor_username": actor_username,
        "actor_email": actor_email,
        "target_user_id": target_user_id,
        "target_username": target_username,
        "target_email": target_email,
    }
    if extra:
        payload.update(extra)

    logger.info("AUDIT %s", json.dumps(payload, ensure_ascii=False, sort_keys=True))
