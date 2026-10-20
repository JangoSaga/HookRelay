# HookRelay
HookRelay is a production-oriented webhook delivery platform built with FastAPI, PostgreSQL, and Redis. It enables applications to send events to registered webhook endpoints with reliable delivery, automatic retries, API-key authentication, idempotency, delivery tracking, and failure recovery.

## Status: Phase 2 (PostgreSQL persistence)

Events are stored in PostgreSQL through SQLAlchemy 2.x (sync), with schema changes managed by Alembic. Events survive restarts.

## Run locally

Requires Docker Desktop (with WSL2 on Windows).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

cp .env.example .env            # local-only settings; .env is git-ignored
docker compose up -d            # dev DB on :5432, test DB on :5433
alembic upgrade head            # create the tables
uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

Useful commands:

```bash
docker compose down             # stop databases, dev data kept
docker compose down -v          # stop and delete all data
docker compose exec db psql -U hookrelay -d hookrelay   # SQL prompt
alembic downgrade base          # undo all migrations (dev only)
```

## Run tests

Tests run against real PostgreSQL (the `db-test` container, data in RAM) and build the schema from the Alembic migrations.

```bash
docker compose up -d db-test
pytest
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health/live` | Process is alive |
| GET | `/health/ready` | Ready to serve (no external dependencies in Phase 1) |
| POST | `/api/v1/events` | Validate and accept an event (201) |
| GET | `/api/v1/events/{event_id}` | Fetch an accepted event (404 if unknown) |
| GET | `/api/v1/events` | List events, newest first |

### Create an event

```bash
curl -X POST http://127.0.0.1:8000/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{"event_type": "invoice.paid", "payload": {"invoice_id": "inv_1"}, "occurred_at": "2026-10-20T10:00:00Z"}'
```

Rules:
- `event_type`: 1-100 characters, not whitespace-only. Use namespaced names such as `invoice.paid`.
- `payload`: must be a JSON object (not a string, array or scalar).
- `idempotency_key`: optional, 1-200 characters. See Idempotency below.
- `occurred_at`: optional, must include a timezone.
- Server-owned fields (`id`, `received_at`, `status`) and any unknown fields are rejected.

## API conventions

- **Pagination:** `limit` (1-100, default 20) and `offset` (>= 0, default 0). Responses return `items`, `limit`, `offset`, `total`.
- **Request body limit:** 256 KiB. Larger bodies get `413`.
- **Errors:** every error uses one shape:

```json
{"error": {"code": "not_found", "message": "Event not found", "details": []}}
```

Validation errors (`422`) list each problem in `details` with `loc`, `msg` and `type`.

## Idempotency

Send an `idempotency_key` to make retries safe. Uniqueness is enforced by a database unique constraint, so concurrent requests cannot create duplicates.

| Request | Response |
|---|---|
| No key, or a new key | `201 Created` |
| Same key, same request (`event_type`, `payload`, `occurred_at`) | `200 OK` with the original event and header `Idempotent-Replayed: true` |
| Same key, different request | `409 Conflict` |

"Same request" compares a SHA-256 fingerprint of `event_type`, `payload` and `occurred_at` (as a UTC instant, key order ignored). Keys are globally unique in Phase 2. In Phase 3 they become unique per authenticated client: `UNIQUE (client_id, idempotency_key)`.

## Database notes

- Timestamps are stored as `timestamptz` and returned in UTC.
- Lists are ordered by `received_at` then `id`, newest first, so pages are stable.
- If the database is unreachable the API returns `503` with a generic message; SQL and driver errors are never exposed.
