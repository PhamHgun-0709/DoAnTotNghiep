"""seed admin user

Revision ID: 002_seed_admin
Revises: 001_initial_schema
Create Date: 2026-05-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import os
from passlib.context import CryptContext
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '002_seed_admin'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    ctx = op.get_context()
    conn = op.get_bind()
    pwd = os.getenv('ADMIN_PASSWORD', '').strip()
    email = os.getenv('ADMIN_EMAIL', 'admin@example.com').strip()
    username = os.getenv('ADMIN_USERNAME', 'admin').strip()
    if not pwd:
        raise RuntimeError('ADMIN_PASSWORD must be set for admin seed migration')
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_ctx.hash(pwd)
    now = datetime.utcnow().isoformat()

    # Insert admin if not exists
    insert_sql = text(
        """
        INSERT INTO users (username, email, hashed_password, role, is_active, created_at, updated_at)
        SELECT :username, :email, :hashed, :role, true, :now, :now
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = :username)
        """
    )
    conn.execute(insert_sql, {
        'username': username,
        'email': email,
        'hashed': hashed,
        'role': 'admin',
        'now': now,
    })


def downgrade():
    conn = op.get_bind()
    username = os.getenv('ADMIN_USERNAME', 'admin').strip()
    delete_sql = text("DELETE FROM users WHERE username = :username")
    conn.execute(delete_sql, {'username': username})
