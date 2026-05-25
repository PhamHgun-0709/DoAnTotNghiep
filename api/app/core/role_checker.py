from __future__ import annotations

from typing import Callable

from fastapi import Depends

from app.core import security


# Predefined role dependencies
def require_admin() -> Callable:
    return security.require_role(["admin"])


def require_analyst_or_admin() -> Callable:
    return security.require_role(["analyst", "admin"])


def require_roles(roles: list[str]) -> Callable:
    return security.require_role(roles)
