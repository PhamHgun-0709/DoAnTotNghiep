from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session

from app.core import security
from app.models.db import get_db, User, Session as UserSession
from app.schemas.auth_schema import AuthResponse, LoginRequest, UserInfo


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    user = security.authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token_info = security.create_access_token_for_user(user)
    # Create session record
    try:
        sess = UserSession(
            user_id=user.id,
            session_token=token_info.get("jti"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            expires_at=token_info.get("expires_at"),
            is_active=True,
        )
        db.add(sess)
        db.commit()
    except Exception:
        db.rollback()
    return {
        "access_token": token_info["access_token"],
        "token_type": token_info.get("token_type", "bearer"),
        "username": token_info.get("username"),
        "full_name": token_info.get("full_name"),
        "role": token_info.get("role"),
        "expires_at": token_info.get("expires_at"),
    }


@router.get("/me", response_model=UserInfo)
def me(current_user: dict = Depends(security.get_current_user)) -> dict:
    # current_user has expires_at as iso string
    return {
        "username": current_user.get("username"),
        "full_name": current_user.get("full_name"),
        "role": current_user.get("role"),
        "expires_at": datetime.fromisoformat(current_user.get("expires_at")).astimezone(timezone.utc),
    }


@router.get("/profile", response_model=UserInfo)
def profile(current_user: dict = Depends(security.get_current_user)) -> dict:
    return me(current_user)


@router.post("/logout")


def logout(current_user: dict = Depends(security.get_current_user), db: Session = Depends(get_db), authorization: str | None = Header(default=None)) -> dict:
    # Mark session inactive if jti present
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if token:
            try:
                payload = security.verify_access_token(token)
                jti = payload.get("jti")
                if jti:
                    sess = db.query(UserSession).filter(UserSession.session_token == jti).first()
                    if sess:
                        sess.is_active = False
                        db.add(sess)
                        db.commit()
            except Exception:
                pass
    return {"message": "Logged out", "username": current_user.get("username")}