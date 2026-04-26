# Ad Campaign Analytics & Optimization Project Structure

This workspace is organized for a graduation project using Apache Spark and Hadoop.
Goal: keep backend, UI, big data pipeline, and documentation clearly separated.

## Suggested workflow
1. Put source data in `data/raw`.
2. Run ETL in `etl/` and Spark jobs in `spark/jobs`.
3. Store transformed data in `data/processed` and final data marts in `data/curated`.
4. Expose results via API in `api/`.
5. Visualize KPI and recommendations in `giao-dien/`.

## Top-level folders
- `api/`: Backend API for dashboard and recommendation endpoints.
- `button/`: Reusable UI button components (shared by pages).
- `giao-dien/`: Frontend interface (pages, layouts, services).
- `spark/`: Spark jobs, pipelines, and Spark configs.
- `hadoop/`: HDFS, Hive, YARN scripts and local cluster configs.
- `etl/`: Ingestion -> transformation -> serving stages.
- `data/`: Raw/processed/curated/external datasets.
- `docs/`: Architecture notes, report assets, meeting notes.
- `scripts/`: Setup/run/deploy helper scripts.
- `monitoring/`: Logs and metrics.
- `infra/`: Docker and Hadoop compose files.
- `notebooks/`: Exploration notebooks.
- `tests/`: Cross-module integration or E2E tests.

## Important note
You already have `data/data.csv` and `data/data_extended.csv`.
You can keep them as-is, or move copies into `data/raw/` when starting your pipeline.

## PostgreSQL for Accounts and Authorization
The API now persists accounts, auth sessions, and upload logs in PostgreSQL.

1. Create database:
	- `CREATE DATABASE ad_analytics;`
2. Set environment variable (PowerShell):
	- `$env:DATABASE_URL="postgresql://postgres:07092004@localhost:5432/ad_analytics"`
3. Start API:
	- `./scripts/run/run_api.ps1`

## Full quality gate (recommended before every demo)
Run all smoke tests in one command:

- `./scripts/run/run_full_quality_gate.ps1`

## Deterministic defense demo reset
Rebuild a stable demo state from baseline data and regenerate artifacts:

- `powershell -ExecutionPolicy Bypass -File scripts/run/run_demo_reset.ps1`

Related defense docs:

- `docs/DEMO_REHEARSAL_CHECKLIST.md`
- `docs/DEFENSE_TALK_TRACK_10_MIN.md`

Quick launch for rehearsal:

- `powershell -ExecutionPolicy Bypass -File scripts/run/run_defense_stack.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run/run_defense_stack.ps1 -WithStreamlit`

## Run as full web service (Docker)

- `powershell -ExecutionPolicy Bypass -File scripts/run/run_webservice_stack.ps1`

After startup:

- Web app: `http://127.0.0.1:8080`
- Health: `http://127.0.0.1:8080/health`

Detailed guide: `infra/docker/README.md`

Default demo accounts are seeded automatically on first run:
- `guest / guest123`
- `analyst / analyst123`
- `admin / admin123`

Account management endpoints (admin role):
- `GET /api/auth/users`
- `POST /api/auth/users`
- `PATCH /api/auth/users/{username}`
- `DELETE /api/auth/users/{username}`

Self-service endpoint:
- `POST /api/auth/change-password`

If PostgreSQL is unavailable, auth/account endpoints return HTTP `503` with clear error message.
