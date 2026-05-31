from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.db_service import get_connection, init_db_schema
from app.services.upload_log_service import read_upload_logs_page


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _metadata_dir() -> Path:
    return _project_root() / "data" / "metadata"


def _active_dataset_file() -> Path:
    return _metadata_dir() / "current_dataset.json"


def _dataset_history_file() -> Path:
    return _metadata_dir() / "dataset_history.json"


def _ensure_metadata_dir() -> None:
    _metadata_dir().mkdir(parents=True, exist_ok=True)


def _fallback_load_active_dataset() -> dict[str, Any] | None:
    file_path = _active_dataset_file()
    if not file_path.exists():
        return None
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _fallback_save_active_dataset(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_metadata_dir()
    def _to_serializable(obj: Any):
        try:
            from datetime import datetime

            if isinstance(obj, datetime):
                return obj.isoformat()
        except Exception:
            pass
        return obj

    with _active_dataset_file().open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=_to_serializable)
    return payload


def _fallback_load_dataset_history(limit: int = 10) -> list[dict[str, Any]]:
    file_path = _dataset_history_file()
    if not file_path.exists():
        return []
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)][: max(1, int(limit))]


def _fallback_save_dataset_history(entry: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    history = _fallback_load_dataset_history(limit=limit * 5)
    history.insert(0, entry)
    trimmed = history[: max(1, int(limit))]
    _ensure_metadata_dir()
    def _to_serializable(obj: Any):
        try:
            from datetime import datetime

            if isinstance(obj, datetime):
                return obj.isoformat()
        except Exception:
            pass
        return obj

    with _dataset_history_file().open("w", encoding="utf-8") as handle:
        json.dump(trimmed, handle, ensure_ascii=False, indent=2, default=_to_serializable)
    return trimmed


def load_active_dataset() -> dict[str, Any] | None:
    init_db_schema()
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, filename, file_path, uploaded_by, uploaded_role, scored_rows, segment_rows, created_at, updated_at
                    FROM datasets
                    WHERE active = TRUE
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
    except Exception:
        return _fallback_load_active_dataset()

    if not row:
        return None

    return {
        "id": int(row[0]),
        "active_dataset": str(row[1] or ""),
        "file_name": str(row[1] or ""),
        "file_path": str(row[2] or ""),
        "uploaded_by": str(row[3] or ""),
        "uploaded_role": str(row[4] or ""),
        "scored_rows": int(row[5] or 0),
        "segment_rows": int(row[6] or 0),
        "created_at": row[7] if row[7] else None,
        "updated_at": row[8] if row[8] else None,
    }


def save_active_dataset(
    *,
    file_name: str,
    file_path: str,
    uploaded_by: str,
    uploaded_role: str,
    scored_rows: int,
    segment_rows: int,
) -> dict[str, Any]:
    payload = {
        "active_dataset": file_name,
        "file_name": file_name,
        "file_path": file_path,
        "uploaded_by": uploaded_by,
        "uploaded_role": uploaded_role,
        "scored_rows": int(scored_rows),
        "segment_rows": int(segment_rows),
    }

    try:
        init_db_schema()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE datasets SET active = FALSE WHERE active = TRUE")
                cur.execute(
                    """
                    INSERT INTO datasets
                    (filename, file_path, uploaded_by, uploaded_role, active, scored_rows, segment_rows, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, TRUE, %s, %s, NOW(), NOW())
                    RETURNING id, created_at, updated_at
                    """,
                    (file_name, file_path, uploaded_by, uploaded_role, int(scored_rows), int(segment_rows)),
                )
                row = cur.fetchone()
    except Exception:
        payload["updated_at"] = ""
        return _fallback_save_active_dataset(payload)

    if row:
        payload["id"] = int(row[0])
        payload["created_at"] = row[1] if row[1] else None
        payload["updated_at"] = row[2] if row[2] else None
    return payload


def load_dataset_history(limit: int = 10) -> list[dict[str, Any]]:
    init_db_schema()
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, filename, file_path, uploaded_by, uploaded_role, active, scored_rows, segment_rows, created_at, updated_at
                    FROM datasets
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (max(1, int(limit)),),
                )
                rows = cur.fetchall()
    except Exception:
        return _fallback_load_dataset_history(limit=limit)

    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "id": int(row[0]),
                "active_dataset": str(row[1] or ""),
                "file_name": str(row[1] or ""),
                "file_path": str(row[2] or ""),
                "uploaded_by": str(row[3] or ""),
                "uploaded_role": str(row[4] or ""),
                "active": bool(row[5]),
                "scored_rows": int(row[6] or 0),
                "segment_rows": int(row[7] or 0),
                "created_at": row[8] if row[8] else None,
                "updated_at": row[9] if row[9] else None,
            }
        )
    return items


def deactivate_active_dataset() -> dict[str, Any] | None:
    """Set any active dataset to inactive. Returns the previously active payload or None."""
    try:
        init_db_schema()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, filename, file_path, uploaded_by FROM datasets WHERE active = TRUE ORDER BY created_at DESC LIMIT 1"
                )
                row = cur.fetchone()
                cur.execute("UPDATE datasets SET active = FALSE WHERE active = TRUE")
    except Exception:
        # fallback: remove current_dataset.json
        payload = _fallback_load_active_dataset()
        try:
            file = _active_dataset_file()
            if file.exists():
                file.unlink(missing_ok=True)
        except Exception:
            pass
        return payload

    if not row:
        return None

    return {
        "id": int(row[0]),
        "file_name": str(row[1] or ""),
        "file_path": str(row[2] or ""),
        "uploaded_by": str(row[3] or ""),
    }


def activate_dataset_by_id(dataset_id: int) -> dict[str, Any] | None:
    """Mark the dataset with given id as active and return its payload. Falls back to None on failure."""
    try:
        init_db_schema()
        with get_connection() as conn:
            with conn.cursor() as cur:
                # ensure the requested id exists
                cur.execute(
                    "SELECT id, filename, file_path, uploaded_by, uploaded_role, scored_rows, segment_rows FROM datasets WHERE id = %s",
                    (int(dataset_id),),
                )
                row = cur.fetchone()
                if not row:
                    return None
                # deactivate others then activate this id
                cur.execute("UPDATE datasets SET active = FALSE WHERE active = TRUE")
                cur.execute("UPDATE datasets SET active = TRUE WHERE id = %s", (int(dataset_id),))
    except Exception:
        return None

    return {
        "id": int(row[0]),
        "file_name": str(row[1] or ""),
        "file_path": str(row[2] or ""),
        "uploaded_by": str(row[3] or ""),
        "uploaded_role": str(row[4] or ""),
        "scored_rows": int(row[5] or 0),
        "segment_rows": int(row[6] or 0),
    }


def append_dataset_history(entry: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    # The datasets table itself is the history source of truth.
    return load_dataset_history(limit=limit)


def has_runtime_dataset() -> bool:
    active_dataset = load_active_dataset()
    if active_dataset:
        return True

    try:
        page = read_upload_logs_page(page=1, page_size=1)
        return int(page.get("total", 0)) > 0
    except Exception:
        return False


def load_dataset_state(limit: int = 5) -> dict[str, Any]:
    active_dataset = load_active_dataset()
    history = load_dataset_history(limit=limit)
    return {
        "active_dataset": active_dataset,
        "dataset_history": history,
        "has_data": bool(active_dataset) or has_runtime_dataset(),
    }
