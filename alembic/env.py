"""Alembic Migration Environment Configuration

This script is run whenever the alembic command is executed.
It controls the database connection and migration context.
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "api"))

# Import database models, with a fallback resolver so startup doesn't fail
# if the model module in the running image is older than the repo copy.
try:
    from app.models.db import Base, resolve_database_url
except Exception:
    from app.models.db import Base

    def resolve_database_url() -> str:
        database_url = os.getenv("DATABASE_URL", "").strip()
        if database_url:
            return database_url

        host = os.getenv("DB_HOST", "localhost").strip() or "localhost"
        port = os.getenv("DB_PORT", "5432").strip() or "5432"
        name = os.getenv("DB_NAME", "ad_analytics").strip() or "ad_analytics"
        user = os.getenv("DB_USER", "postgres").strip() or "postgres"
        password = os.getenv("DB_PASSWORD", "").strip()
        auth_segment = f"{user}:{password}@" if password else f"{user}@"
        return f"postgresql+psycopg://{auth_segment}{host}:{port}/{name}"

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set SQLAlchemy URL from environment
database_url = os.getenv("DATABASE_URL", "").strip() or resolve_database_url()
config.set_main_option("sqlalchemy.url", database_url)

# Model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the create_engine() call
    we don't even need a DBAPI to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = os.getenv("DATABASE_URL", "").strip() or resolve_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
