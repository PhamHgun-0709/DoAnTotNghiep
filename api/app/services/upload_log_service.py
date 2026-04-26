from __future__ import annotations

from typing import Any

from app.services.db_service import get_connection, init_db_schema

def append_upload_log(
    file_name: str,
    file_path: str,
    scored_rows: int,
    segment_rows: int,
    uploader_role: str,
    uploader_name: str,
) -> None:
    init_db_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO upload_logs
                (file_name, file_path, scored_rows, segment_rows, uploader_role, uploader_name)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (file_name, file_path, scored_rows, segment_rows, uploader_role, uploader_name),
            )


def read_upload_logs(limit: int = 100) -> list[dict[str, Any]]:
    result = read_upload_logs_page(page=1, page_size=limit)
    return result["items"]


def read_upload_logs_page(
    page: int = 1,
    page_size: int = 50,
    uploader_name: str | None = None,
    file_name: str | None = None,
) -> dict[str, Any]:
    init_db_schema()
    normalized_page = max(1, int(page))
    normalized_size = max(1, min(500, int(page_size)))
    offset = (normalized_page - 1) * normalized_size

    where_clauses: list[str] = []
    params: list[Any] = []

    if uploader_name and uploader_name.strip():
        where_clauses.append("LOWER(uploader_name) LIKE %s")
        params.append(f"%{uploader_name.strip().lower()}%")
    if file_name and file_name.strip():
        where_clauses.append("LOWER(file_name) LIKE %s")
        params.append(f"%{file_name.strip().lower()}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM upload_logs {where_sql}", tuple(params))
            total = int(cur.fetchone()[0])

            cur.execute(
                f"""
                SELECT uploaded_at, file_name, file_path, scored_rows, segment_rows, uploader_role, uploader_name
                FROM upload_logs
                {where_sql}
                ORDER BY uploaded_at DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [normalized_size, offset]),
            )
            rows = cur.fetchall()

    items = [
        {
            "uploaded_at": row[0].isoformat() if row[0] else "",
            "file_name": str(row[1] or ""),
            "file_path": str(row[2] or ""),
            "scored_rows": int(row[3] or 0),
            "segment_rows": int(row[4] or 0),
            "uploader_role": str(row[5] or ""),
            "uploader_name": str(row[6] or ""),
        }
        for row in rows
    ]
    return {
        "total": total,
        "page": normalized_page,
        "page_size": normalized_size,
        "items": items,
    }
