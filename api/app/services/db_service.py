from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg import Connection


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ad_analytics"
_SCHEMA_INITIALIZED = False
_SCHEMA_LOCK = threading.Lock()


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


@contextmanager
def get_connection() -> Iterator[Connection]:
    conn = psycopg.connect(get_database_url(), connect_timeout=3)
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
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    role TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    issued_at TIMESTAMPTZ NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at
                ON auth_sessions (expires_at);
                """
            )
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
