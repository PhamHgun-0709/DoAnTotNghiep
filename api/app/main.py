from contextlib import asynccontextmanager
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging_config import logger
from app.routes.auth import router as auth_router
from app.routes.ads import router as ads_router
from app.routes.ml_analytics import router as ml_router
from app.routes.spark_pipeline import router as spark_router
from app.routes.admin import router as admin_router
from app.models.db import resolve_database_url
from app.services.db_service import init_db_schema, is_db_ready
from app.services.health_service import build_data_health_snapshot


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if raw == "*" or not raw:
        return ["*"]
    return [item.strip() for item in raw.split(",") if item.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 Ad Analytics API Starting...")
    logger.info("=" * 60)
    
    try:
        # Run database migrations
        logger.info("🔄 Running database migrations...")
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        
        try:
            from alembic.config import Config
            from alembic import command
            
            config = Config(str(project_root / "alembic.ini"))
            config.set_main_option("sqlalchemy.url", resolve_database_url())
            command.upgrade(config, "head")
            logger.info("✅ Database migrations completed")
        except ImportError:
            logger.warning("⚠️  Alembic not available, skipping migrations")
        except Exception as e:
            logger.warning(f"⚠️  Migration failed: {e}")
        
        init_db_schema()
        logger.info("✅ PostgreSQL schema initialized")
    except Exception as exc:
        logger.warning(f"⚠️  PostgreSQL init failed: {exc}")
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("🛑 Ad Analytics API Shutting Down...")
    logger.info("=" * 60)


app = FastAPI(
    title="Ad Analytics API",
    version="1.0.0",
    description="Backend API for ad quality filtering and chart data",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ads_router)
app.include_router(auth_router)
app.include_router(ml_router)
app.include_router(spark_router)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "postgres_ready": is_db_ready(),
        **build_data_health_snapshot(),
    }
