from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.db_service import get_connection, init_db_schema


SESSION_TTL_MINUTES = 120
VALID_ROLES = {"guest", "analyst", "admin"}


def _hash_password(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


def _validate_username(username: str) -> str:
    normalized = username.strip().lower()
    if len(normalized) < 3 or len(normalized) > 50:
        raise ValueError("Username must be 3-50 characters.")
    if not normalized.replace("_", "").isalnum():
        raise ValueError("Username must contain only letters, numbers, underscore.")
    return normalized


def _validate_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")
    return normalized


def _validate_password(password: str) -> str:
    raw = password.strip()
    if len(raw) < 6:
        raise ValueError("Password must be at least 6 characters.")
    return raw


_DEFAULT_USERS: list[tuple[str, str, str, str]] = [
    ("guest", _hash_password("guest123"), "guest", "Khach Demo"),
    ("analyst", _hash_password("analyst123"), "analyst", "Phan Tich Vien"),
    ("admin", _hash_password("admin123"), "admin", "Quan Tri Demo"),
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_default_users() -> None:
    init_db_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            for username, password_hash, role, full_name in _DEFAULT_USERS:
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, role, full_name)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                    """,
                    (username, password_hash, role, full_name),
                )


def _purge_expired_sessions() -> None:
    init_db_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM auth_sessions WHERE expires_at <= NOW()")


def authenticate_user(username: str, password: str) -> dict[str, str] | None:
    try:
        normalized_username = _validate_username(username)
    except ValueError:
        return None
    _seed_default_users()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, password_hash, role, full_name FROM users WHERE username = %s",
                (normalized_username,),
            )
            row = cur.fetchone()

    if not row:
        return None

    db_username, password_hash, role, full_name = row

    if not hmac.compare_digest(_hash_password(password), str(password_hash)):
        return None

    return {
        "username": str(db_username),
        "role": str(role),
        "full_name": str(full_name),
    }


def create_session(user: dict[str, str]) -> dict[str, Any]:
    _purge_expired_sessions()

    token = secrets.token_urlsafe(32)
    issued_at = _utc_now()
    expires_at = _utc_now() + timedelta(minutes=SESSION_TTL_MINUTES)

    init_db_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_sessions (token, username, role, full_name, issued_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    token,
                    user["username"],
                    user["role"],
                    user["full_name"],
                    issued_at,
                    expires_at,
                ),
            )

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
        "full_name": user["full_name"],
        "expires_at": expires_at.isoformat(),
    }


def revoke_session(token: str) -> None:
    init_db_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM auth_sessions WHERE token = %s", (token,))


def get_current_session(token: str) -> dict[str, Any] | None:
    _purge_expired_sessions()
    init_db_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT token, username, role, full_name, issued_at, expires_at
                FROM auth_sessions
                WHERE token = %s
                """,
                (token,),
            )
            row = cur.fetchone()

    if not row:
        return None

    token_value, username, role, full_name, issued_at, expires_at = row
    return {
        "token": token_value,
        "username": username,
        "role": role,
        "full_name": full_name,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }


def require_roles(session: dict[str, Any] | None, allowed_roles: set[str]) -> None:
    if not session:
        raise PermissionError("Unauthorized. Please login.")
    if session["role"] not in allowed_roles:
        raise PermissionError(f"Forbidden for role '{session['role']}'.")


def list_users() -> list[dict[str, str]]:
    result = list_users_page(page=1, page_size=1000)
    return result["items"]


def list_users_page(
    page: int = 1,
    page_size: int = 20,
    query: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    _seed_default_users()
    normalized_page = max(1, int(page))
    normalized_size = max(1, min(200, int(page_size)))
    offset = (normalized_page - 1) * normalized_size

    where_clauses: list[str] = []
    params: list[Any] = []

    if query and query.strip():
        like_term = f"%{query.strip().lower()}%"
        where_clauses.append("(LOWER(username) LIKE %s OR LOWER(full_name) LIKE %s)")
        params.extend([like_term, like_term])

    if role and role.strip():
        normalized_role = _validate_role(role)
        where_clauses.append("role = %s")
        params.append(normalized_role)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM users {where_sql}", tuple(params))
            total = int(cur.fetchone()[0])

            cur.execute(
                f"""
                SELECT username, role, full_name
                FROM users
                {where_sql}
                ORDER BY username
                LIMIT %s OFFSET %s
                """,
                tuple(params + [normalized_size, offset]),
            )
            rows = cur.fetchall()

    items = [
        {"username": str(row[0]), "role": str(row[1]), "full_name": str(row[2])}
        for row in rows
    ]
    return {
        "total": total,
        "page": normalized_page,
        "page_size": normalized_size,
        "items": items,
    }


def create_user_account(username: str, password: str, role: str, full_name: str) -> dict[str, str]:
    _seed_default_users()
    normalized_username = _validate_username(username)
    normalized_role = _validate_role(role)
    raw_password = _validate_password(password)
    normalized_name = full_name.strip() or normalized_username

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE username = %s", (normalized_username,))
            if cur.fetchone():
                raise ValueError("Username already exists.")

            cur.execute(
                """
                INSERT INTO users (username, password_hash, role, full_name)
                VALUES (%s, %s, %s, %s)
                """,
                (normalized_username, _hash_password(raw_password), normalized_role, normalized_name),
            )

    return {"username": normalized_username, "role": normalized_role, "full_name": normalized_name}


def update_user_account(
    username: str,
    role: str | None = None,
    full_name: str | None = None,
    password: str | None = None,
) -> dict[str, str]:
    _seed_default_users()
    normalized_username = _validate_username(username)

    fields: list[str] = []
    values: list[str] = []

    if role is not None:
        normalized_role = _validate_role(role)
        fields.append("role = %s")
        values.append(normalized_role)
    if full_name is not None:
        cleaned_name = full_name.strip() or normalized_username
        fields.append("full_name = %s")
        values.append(cleaned_name)
    if password is not None:
        raw_password = _validate_password(password)
        fields.append("password_hash = %s")
        values.append(_hash_password(raw_password))

    if not fields:
        raise ValueError("No fields to update.")

    values.append(normalized_username)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT role, full_name FROM users WHERE username = %s", (normalized_username,))
            existing = cur.fetchone()
            if not existing:
                raise ValueError("User not found.")

            cur.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE username = %s",
                tuple(values),
            )

            cur.execute("SELECT username, role, full_name FROM users WHERE username = %s", (normalized_username,))
            updated = cur.fetchone()

    return {
        "username": str(updated[0]),
        "role": str(updated[1]),
        "full_name": str(updated[2]),
    }


def delete_user_account(username: str) -> None:
    _seed_default_users()
    normalized_username = _validate_username(username)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT role FROM users WHERE username = %s", (normalized_username,))
            row = cur.fetchone()
            if not row:
                raise ValueError("User not found.")

            role = str(row[0])
            if role == "admin":
                cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
                admin_count = int(cur.fetchone()[0])
                if admin_count <= 1:
                    raise ValueError("Cannot delete the last admin account.")

            cur.execute("DELETE FROM auth_sessions WHERE username = %s", (normalized_username,))
            cur.execute("DELETE FROM users WHERE username = %s", (normalized_username,))


def change_own_password(username: str, old_password: str, new_password: str) -> None:
    normalized_username = _validate_username(username)
    current_user = authenticate_user(normalized_username, old_password)
    if not current_user:
        raise ValueError("Old password is incorrect.")

    raw_new_password = _validate_password(new_password)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE username = %s",
                (_hash_password(raw_new_password), normalized_username),
            )
