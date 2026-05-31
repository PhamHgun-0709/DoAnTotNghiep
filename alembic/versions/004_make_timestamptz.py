"""Make timestamp columns timezone-aware (TIMESTAMPTZ)

Revision ID: 004_make_timestamptz
Revises: 003_dataset_lifecycle
Create Date: 2026-05-31 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_make_timestamptz'
down_revision = '003_dataset_lifecycle'
branch_labels = None
depends_on = None


def _alter_to_timestamptz_if_needed(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    try:
        columns = {col["name"]: col for col in inspector.get_columns(table_name)}
    except Exception:
        return

    column = columns.get(column_name)
    if not column:
        return

    column_type = str(column.get("type", "")).lower()
    if "timestamp with time zone" in column_type or "timestamptz" in column_type:
        return

    op.execute(
        sa.text(
            f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE timestamptz USING {column_name} AT TIME ZONE 'UTC'"
        )
    )


def upgrade():
    # Convert common datetime columns to timestamptz (UTC assumed for existing values)
    # This is done conditionally to avoid aborting the transaction on missing columns
    # or columns that are already timezone-aware.
    for table_name, column_name in [
        ("users", "created_at"),
        ("users", "updated_at"),
        ("sessions", "created_at"),
        ("sessions", "expires_at"),
        ("predictions", "created_at"),
        ("predictions", "updated_at"),
        ("upload_logs", "created_at"),
        ("datasets", "created_at"),
        ("datasets", "updated_at"),
        ("spark_jobs", "started_at"),
        ("spark_jobs", "completed_at"),
        ("spark_jobs", "created_at"),
        ("model_metrics", "created_at"),
        ("model_metrics", "updated_at"),
    ]:
        _alter_to_timestamptz_if_needed(table_name, column_name)


def downgrade():
    # Convert back to timestamp without time zone, interpreting stored timestamptz as UTC
    for table_name, column_name in [
        ("users", "updated_at"),
        ("users", "created_at"),
        ("sessions", "expires_at"),
        ("sessions", "created_at"),
        ("predictions", "updated_at"),
        ("predictions", "created_at"),
        ("upload_logs", "created_at"),
        ("datasets", "updated_at"),
        ("datasets", "created_at"),
        ("spark_jobs", "created_at"),
        ("spark_jobs", "completed_at"),
        ("spark_jobs", "started_at"),
        ("model_metrics", "updated_at"),
        ("model_metrics", "created_at"),
    ]:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        try:
            columns = {col["name"]: col for col in inspector.get_columns(table_name)}
        except Exception:
            continue
        column = columns.get(column_name)
        if not column:
            continue
        column_type = str(column.get("type", "")).lower()
        if "timestamp with time zone" not in column_type and "timestamptz" not in column_type:
            continue
        op.execute(
            sa.text(
                f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE timestamp without time zone USING ({column_name} AT TIME ZONE 'UTC')"
            )
        )
