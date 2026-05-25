"""Initial schema for thesis scope.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-05-07 03:42:20.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upload_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("scored_rows", sa.Integer(), nullable=False),
        sa.Column("segment_rows", sa.Integer(), nullable=False),
        sa.Column("uploader_role", sa.String(length=100), nullable=False),
        sa.Column("uploader_name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "spark_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_name", sa.String(length=255), nullable=False),
        sa.Column("pipeline_type", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("input_path", sa.String(length=500), nullable=True),
        sa.Column("output_path", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("execution_time_seconds", sa.Float(), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "model_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_type", sa.String(length=100), nullable=True),
        sa.Column("metric_name", sa.String(length=100), nullable=True),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("dataset_size", sa.Integer(), nullable=True),
        sa.Column("training_time_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("model_metrics")
    op.drop_table("spark_jobs")
    op.drop_table("upload_logs")