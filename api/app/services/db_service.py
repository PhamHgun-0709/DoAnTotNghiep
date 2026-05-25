from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg import Connection


DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/ad_analytics"
_SCHEMA_INITIALIZED = False
_SCHEMA_LOCK = threading.Lock()


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _normalize_for_psycopg(dsn: str) -> str:
    # SQLAlchemy uses the driver-prefix form 'postgresql+psycopg://',
    # but psycopg.connect expects a normal libpq-style DSN starting with
    # 'postgresql://'. Normalize here so both can share the same env var.
    if dsn.startswith("postgresql+psycopg://"):
        return dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    return dsn

@contextmanager
def get_connection() -> Iterator[Connection]:
    raw = get_database_url()
    conn = psycopg.connect(_normalize_for_psycopg(raw), connect_timeout=3)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db_schema(force: bool = False) -> None:
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED and not force:
        return

    with _SCHEMA_LOCK:
        if _SCHEMA_INITIALIZED and not force:
            return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS upload_logs (
                    id BIGSERIAL PRIMARY KEY,
                    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    scored_rows INTEGER NOT NULL,
                    segment_rows INTEGER NOT NULL,
                    uploader_role TEXT NOT NULL,
                    uploader_name TEXT NOT NULL
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    id BIGSERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    uploaded_by TEXT NOT NULL,
                    uploaded_role TEXT NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT FALSE,
                    scored_rows INTEGER NOT NULL DEFAULT 0,
                    segment_rows INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_datasets_active_created_at
                ON datasets (active, created_at DESC);
                """
            )

    _SCHEMA_INITIALIZED = True

def is_db_ready() -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False
