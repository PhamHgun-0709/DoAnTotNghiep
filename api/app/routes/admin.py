from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.core.role_checker import require_admin
from app.models.db import get_db, Session as UserSessionModel, User
from app.services.audit_service import log_admin_session_action, log_admin_user_action


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def list_users(
    user_id: int | None = Query(default=None),
    username: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    role: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin()),
) -> dict[str, Any]:
    q = db.query(User)
    if user_id is not None:
        q = q.filter(User.id == int(user_id))
    if username:
        q = q.filter(User.username == username.strip().lower())
    if active is not None:
        q = q.filter(User.is_active == bool(active))
    if role:
        q = q.filter(User.role == role.strip().lower())

    total = q.count()
    rows = q.order_by(User.id.asc()).offset(offset).limit(limit).all()

    items = []
    for user in rows:
        items.append(
            {
                "id": user.id,
                "username": user.username,
                "full_name": getattr(user, "full_name", None),
                "email": getattr(user, "email", None),
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
                "updated_at": user.updated_at.isoformat() if getattr(user, "updated_at", None) else None,
            }
        )

    return {"total": total, "items": items}


@router.post("/users")
def create_user(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin()),
) -> dict[str, Any]:
    username = str(payload.get("username") or "").strip().lower()
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")
    role = str(payload.get("role") or "analyst").strip().lower()
    is_active = bool(payload.get("is_active", True))

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    if role not in {"admin", "analyst", "user", "guest"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    existing_username = db.query(User).filter(User.username == username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already exists")
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")

    from app.core.security import get_password_hash

    # Keep the primary-key sequence aligned with the actual table contents.
    # This avoids duplicate key errors when the sequence lags behind max(id).
    db.execute(text("SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 0) + 1, false)"))

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    actor = db.query(User).filter(User.id == int(admin_user.get("id", 0) or 0)).first()
    log_admin_user_action(
        "user_create",
        actor_username=str(getattr(actor, "username", admin_user.get("username", "unknown"))),
        actor_email=getattr(actor, "email", None),
        target_user_id=int(user.id),
        target_username=user.username,
        target_email=user.email,
        extra={"role": user.role, "is_active": bool(user.is_active)},
    )

    return {
        "message": "User created",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": bool(user.is_active),
            "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
            "updated_at": user.updated_at.isoformat() if getattr(user, "updated_at", None) else None,
        },
    }


@router.patch("/users/{user_id}")
def update_user(
    user_id: int = Path(..., ge=1),
    payload: dict[str, Any] | None = None,
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin()),
) -> dict[str, Any]:
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    actor_id = int(admin_user.get("id", 0) or 0)
    if actor_id == int(user.id):
        raise HTTPException(status_code=400, detail="Cannot modify your own account")

    payload = payload or {}
    changes: dict[str, Any] = {}
    if "is_active" in payload:
        user.is_active = bool(payload.get("is_active"))
        changes["is_active"] = user.is_active
    if "role" in payload:
        role = str(payload.get("role") or "").strip().lower()
        if role not in {"admin", "analyst", "user", "guest"}:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = role
        changes["role"] = user.role

    if not changes:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    db.add(user)
    db.commit()
    db.refresh(user)

    actor = db.query(User).filter(User.id == actor_id).first()
    log_admin_user_action(
        "user_update",
        actor_username=str(getattr(actor, "username", admin_user.get("username", "unknown"))),
        actor_email=getattr(actor, "email", None),
        target_user_id=int(user.id),
        target_username=user.username,
        target_email=user.email,
        extra=changes,
    )

    return {
        "message": "User updated",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": bool(user.is_active),
            "updated_at": user.updated_at.isoformat() if getattr(user, "updated_at", None) else None,
        },
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin()),
) -> dict[str, Any]:
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    actor_id = int(admin_user.get("id", 0) or 0)
    if actor_id == int(user.id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    actor = db.query(User).filter(User.id == actor_id).first()
    target_username = user.username
    target_email = user.email
    db.delete(user)
    db.commit()

    log_admin_user_action(
        "user_delete",
        actor_username=str(getattr(actor, "username", admin_user.get("username", "unknown"))),
        actor_email=getattr(actor, "email", None),
        target_user_id=int(user_id),
        target_username=target_username,
        target_email=target_email,
    )

    return {"message": "User deleted", "user_id": int(user_id)}


@router.get("/sessions")
def list_sessions(
    user_id: int | None = Query(default=None),
    username: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin()),
) -> dict[str, Any]:
    q = db.query(UserSessionModel)
    if user_id is not None:
        q = q.filter(UserSessionModel.user_id == int(user_id))
    if username:
        user = db.query(User).filter(User.username == username.strip().lower()).first()
        if not user:
            return {"total": 0, "items": []}
        q = q.filter(UserSessionModel.user_id == user.id)
    if active is not None:
        q = q.filter(UserSessionModel.is_active == bool(active))

    total = q.count()
    # eager-load the related User so we can include username in the response
    rows = (
        q.options(joinedload(UserSessionModel.user))
        .order_by(UserSessionModel.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for r in rows:
        username = None
        try:
            if getattr(r, 'user', None):
                username = getattr(r.user, 'username', None)
        except Exception:
            username = None

        items.append(
            {
                "jti": r.session_token,
                "user_id": r.user_id,
                "username": username,
                "ip_address": r.ip_address,
                "user_agent": r.user_agent,
                "is_active": bool(r.is_active),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
        )

    return {"total": total, "items": items}


@router.post("/sessions/{jti}/revoke")
def revoke_session(
    jti: str = Path(...),
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin()),
) -> dict[str, Any]:
    sess = db.query(UserSessionModel).filter(UserSessionModel.session_token == jti).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    actor = db.query(User).filter(User.id == int(admin_user.get("id"))).first()
    if not sess.is_active:
        log_admin_session_action(
            "session_revoke_noop",
            actor_username=str(getattr(actor, "username", admin_user.get("username", "unknown"))),
            actor_email=getattr(actor, "email", None),
            target_jti=jti,
            target_username=getattr(getattr(sess, "user", None), "username", None),
            target_user_id=sess.user_id,
            extra={"reason": "already_inactive"},
        )
        return {"message": "Session already inactive", "jti": jti}
    sess.is_active = False
    db.add(sess)
    db.commit()
    log_admin_session_action(
        "session_revoke",
        actor_username=str(getattr(actor, "username", admin_user.get("username", "unknown"))),
        actor_email=getattr(actor, "email", None),
        target_jti=jti,
        target_username=getattr(getattr(sess, "user", None), "username", None),
        target_user_id=sess.user_id,
    )
    return {"message": "Session revoked", "jti": jti}


@router.delete("/sessions/{jti}")
def delete_session(
    jti: str = Path(...),
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin()),
) -> dict[str, Any]:
    sess = db.query(UserSessionModel).filter(UserSessionModel.session_token == jti).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    actor = db.query(User).filter(User.id == int(admin_user.get("id"))).first()
    target_username = getattr(getattr(sess, "user", None), "username", None)
    target_user_id = sess.user_id
    db.delete(sess)
    db.commit()
    log_admin_session_action(
        "session_delete",
        actor_username=str(getattr(actor, "username", admin_user.get("username", "unknown"))),
        actor_email=getattr(actor, "email", None),
        target_jti=jti,
        target_username=target_username,
        target_user_id=target_user_id,
    )
    return {"message": "Session deleted", "jti": jti}
