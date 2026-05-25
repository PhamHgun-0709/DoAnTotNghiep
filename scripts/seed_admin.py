"""Seed an admin user into the database for development.

Usage:
    python scripts/seed_admin.py --username admin --password <set-password> --email admin@example.com

This script is intended for local/dev only.
"""

import argparse
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "api"))

from app.models.db import SessionLocal, init_db, User
from app.core.security import get_password_hash


def main(username: str, password: str, email: str, role: str = "admin"):
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"User {username} already exists")
            return
        hashed = get_password_hash(password)
        user = User(username=username, email=email, hashed_password=hashed, role=role)
        db.add(user)
        db.commit()
        print(f"Created user {username} with role {role}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD", ""))
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", "admin@example.com"))
    parser.add_argument("--role", default=os.getenv("ADMIN_ROLE", "admin"))
    args = parser.parse_args()
    if not args.password:
        raise SystemExit("ADMIN_PASSWORD must be set or passed with --password")
    main(args.username, args.password, args.email, args.role)
