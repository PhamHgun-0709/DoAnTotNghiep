# Web Service Deployment (Docker Compose)

This stack runs the project as a complete web service:

- PostgreSQL database
- FastAPI backend
- Nginx frontend (serves dashboard and proxies `/api` + `/health`)

## Prerequisites

- Docker Desktop installed and running
- Ports available: `5432`, `8000`, `8080`

## Start

From project root:

- `docker compose -f infra/docker/docker-compose.webservice.yml up -d --build`

Or use helper script:

- `powershell -ExecutionPolicy Bypass -File scripts/run/run_webservice_stack.ps1`

## Endpoints

- Web app: `http://127.0.0.1:8080`
- API (direct): `http://127.0.0.1:8000`
- Health via web proxy: `http://127.0.0.1:8080/health`

## Stop

- `docker compose -f infra/docker/docker-compose.webservice.yml down`

## Notes

- The API container mounts `data/` from host to `/workspace/data` so outputs and uploads persist on your machine.
- DB data is persisted in Docker volume `postgres_data`.
- In web service mode, dashboard blocks marked for internal/demo usage are hidden automatically.
- CORS is restricted by `CORS_ORIGINS` in compose (`http://127.0.0.1:8080,http://localhost:8080`).
- `REQUIRE_UPLOAD_DATA=true`: analytics endpoints return empty datasets until at least one upload log exists.
