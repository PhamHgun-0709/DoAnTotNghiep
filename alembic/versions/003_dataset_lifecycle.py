"""Add persistent dataset lifecycle.

Revision ID: 003_dataset_lifecycle
Revises: 002_seed_admin
Create Date: 2026-05-24 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_dataset_lifecycle"
down_revision: Union[str, None] = "002_seed_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("uploaded_by", sa.String(length=255), nullable=False),
        sa.Column("uploaded_role", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("scored_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("segment_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_datasets_active_created_at", "datasets", ["active", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_datasets_active_created_at", table_name="datasets")
    op.drop_table("datasets")
