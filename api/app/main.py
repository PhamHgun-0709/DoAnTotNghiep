from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ads import router as ads_router
from app.services.db_service import init_db_schema, is_db_ready
from app.services.health_service import build_data_health_snapshot


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if raw == "*" or not raw:
        return ["*"]
    return [item.strip() for item in raw.split(",") if item.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db_schema()
    except Exception as exc:
        print(f"[WARN] PostgreSQL init failed at startup: {exc}")
    yield


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


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "postgres_ready": is_db_ready(),
        **build_data_health_snapshot(),
    }
