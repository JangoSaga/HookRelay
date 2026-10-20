# HookRelay
HookRelay is a production-oriented webhook delivery platform built with FastAPI, PostgreSQL, and Redis. It enables applications to send events to registered webhook endpoints with reliable delivery, automatic retries, API-key authentication, idempotency, delivery tracking, and failure recovery.

## Status: Phase 1 (API Foundation)

> **Storage is temporary.** Events are held in process memory only. Restarting the app loses every event. Persistent storage arrives in Phase 2 (PostgreSQL).

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

## Run tests

```bash
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
- `idempotency_key`: optional, 1-200 characters. Stored but not enforced until Phase 2.
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
