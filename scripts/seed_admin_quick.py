import sys
from datetime import datetime
import os

# Ensure package path inside container
sys.path.insert(0, "/workspace/api")

from app.models.db import SessionLocal
from app.core.security import get_password_hash
from sqlalchemy import text

def seed_user(db, username: str, password: str, email: str, role: str):
    existing = db.execute(text("SELECT 1 FROM users WHERE username=:username"), {"username": username}).fetchone()
    if existing:
        print(f"User {username} already exists")
        return
    hashed = get_password_hash(password)
    db.execute(
        text("INSERT INTO users (username, email, hashed_password, role, is_active, created_at, updated_at) VALUES (:username,:email,:hashed,:role, true, :now, :now)"),
        {"username": username, "email": email, "hashed": hashed, "role": role, "now": datetime.utcnow()},
    )
    db.commit()
    print(f"Created user {username} with role {role}")


def main():
    db = SessionLocal()
    try:
        seeds = [
            (
                os.getenv("ADMIN_USERNAME", "admin"),
                os.getenv("ADMIN_PASSWORD", ""),
                os.getenv("ADMIN_EMAIL", "admin@example.com"),
                os.getenv("ADMIN_ROLE", "admin"),
            ),
            (
                os.getenv("ANALYST_USERNAME", "analyst"),
                os.getenv("ANALYST_PASSWORD", ""),
                os.getenv("ANALYST_EMAIL", "analyst@example.com"),
                os.getenv("ANALYST_ROLE", "analyst"),
            ),
            (
                os.getenv("USER_USERNAME", "user"),
                os.getenv("USER_PASSWORD", ""),
                os.getenv("USER_EMAIL", "user@example.com"),
                os.getenv("USER_ROLE", "user"),
            ),
        ]
        for username, password, email, role in seeds:
            if not password:
                raise SystemExit(f"Password missing for seed user {username}")
            seed_user(db, username, password, email, role)
    finally:
        db.close()


if __name__ == '__main__':
    main()
