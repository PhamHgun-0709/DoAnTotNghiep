# API Module

Backend service layer for business logic and data access.

## Structure
- `app/routes`: API endpoint definitions.
- `app/controllers`: Request handlers.
- `app/services`: Business logic (optimization, analytics).
- `app/models`: Data model objects.
- `app/schemas`: Request/response validation schemas.
- `app/middlewares`: Auth, logging, error handling.
- `app/utils`: Shared helper utilities.
- `tests`: API unit and integration tests.

## Key defense endpoints
- `GET /health`: API + database + artifact readiness snapshot.
- `GET /api/experiments/model-evidence` (analyst/admin): estimated confusion matrix and threshold tradeoff derived from saved metrics.
