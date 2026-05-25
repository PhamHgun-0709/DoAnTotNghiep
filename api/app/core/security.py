from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import jwt
from fastapi import Depends, Header, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.db import User, Session as UserSession, get_db


def _require_auth_secret() -> str:
    secret = os.getenv("AUTH_SECRET", "").strip() or os.getenv("SECRET_KEY", "").strip()
    if not secret:
        raise RuntimeError("AUTH_SECRET or SECRET_KEY must be set")
    return secret


AUTH_ALGORITHM = os.getenv("AUTH_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["sha256_crypt", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password, scheme="sha256_crypt")


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    if not username or not password:
        return None
    normalized = username.strip().lower()
    user = db.query(User).filter(User.username == normalized).first()
    if user:
        if not verify_password(password, user.hashed_password):
            return None
        return user
    return None


def create_access_token_for_user(user: User, expires_minutes: int | None = None) -> dict[str, Any]:
    expires_minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=int(expires_minutes))
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "jti": jti,
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, _require_auth_secret(), algorithm=AUTH_ALGORITHM)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "full_name": getattr(user, "full_name", user.username),
        "role": user.role,
        "expires_at": expires_at,
        "jti": jti,
    }


def verify_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, _require_auth_secret(), algorithms=[AUTH_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Missing authorization token")
    payload = verify_access_token(token.strip())
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Support demo tokens whose sub is formatted as 'demo:<username>'
    if isinstance(user_id, str) and user_id.startswith("demo:"):
        username = user_id.split(":", 1)[1]
        return {
            "id": user_id,
            "username": username,
            "full_name": payload.get("full_name", username),
            "role": payload.get("role"),
            "expires_at": datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc).isoformat(),
        }

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    # Validate session jti exists and is active (token revocation support)
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=401, detail="Invalid token payload: missing jti")

    session_row = (
        db.query(UserSession)
        .filter(UserSession.session_token == jti, UserSession.user_id == int(user_id))
        .first()
    )
    if not session_row or not session_row.is_active:
        raise HTTPException(status_code=401, detail="Session revoked or not found")

    # ensure session expiry hasn't been passed
    if session_row.expires_at:
        sess_exp = session_row.expires_at
        if sess_exp.tzinfo is None:
            sess_exp = sess_exp.replace(tzinfo=timezone.utc)
        if sess_exp < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
    return {
        "id": user.id,
        "username": user.username,
        "full_name": getattr(user, "full_name", user.username),
        "role": user.role,
        "expires_at": datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc).isoformat(),
    }


def require_role(roles: list[str]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    allowed_roles = {role.strip().lower() for role in roles if role.strip()}

    def checker(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if str(current_user.get("role", "")).lower() not in allowed_roles:
            raise HTTPException(status_code=403, detail="Không đủ quyền")
        return current_user

    return checker
