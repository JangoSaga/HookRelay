# Phase 1 — API Foundation, HTTP, and Pydantic

## Outcome

A runnable FastAPI service with a documented event-ingestion API. Events are held in memory only in this phase; data loss on restart is expected and explicitly acceptable until Phase 2.

## Scope

### Required endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health/live` | Process is alive |
| GET | `/health/ready` | Phase 1 readiness; no external dependencies yet |
| POST | `/api/v1/events` | Validate and accept an event |
| GET | `/api/v1/events/{event_id}` | Retrieve a previously accepted in-memory event |
| GET | `/api/v1/events` | List events with pagination |

Use a consistent API prefix `/api/v1`. FastAPI's `/docs` and `/openapi.json` should remain enabled for development.

## Event contract

### Create-event request

Required:
- `event_type`: string, 1–100 characters; use a namespaced value such as `invoice.paid`.
- `payload`: JSON object, not an arbitrary scalar or array.
- `idempotency_key`: optional string, 1–200 characters.

Optional:
- `occurred_at`: timezone-aware datetime supplied by the client.

Rules:
- Reject empty/whitespace event types.
- Reject a naive `occurred_at` without timezone information.
- Set `received_at` on the server.
- Generate a UUID for `event_id`.
- Do not allow clients to set server-owned fields such as `event_id`, `received_at`, or internal delivery status.
- Establish a maximum request body size; document the chosen limit.

### Event response

Return:
- `id`
- `event_type`
- `payload`
- `occurred_at` (nullable)
- `received_at`
- `status` (initially `accepted`)

Do not return internal implementation details or secrets.

### List response

Return:
- `items`: list of event responses
- `limit`
- `offset`
- `total`

Choose whether the first version uses `offset` or `skip`; document the choice and keep it consistent.

## Concepts to learn and apply

- FastAPI app instance and ASGI application.
- Path parameters versus query parameters versus request body.
- HTTP methods and status codes: 200, 201, 202, 204, 400, 404, 409, 422, 500.
- Pydantic v2 `BaseModel`, field types, constraints, validators, nested models, optional fields, defaults, and `model_dump`.
- Request models versus response models.
- UUID and timezone-aware datetime handling.
- Dependency injection at a basic level.
- `APIRouter`, tags, summaries, response status codes, and OpenAPI schema.
- Exception handling and consistent error responses.
- Why an in-memory list is not persistent storage.

## Requirements

1. Use type hints for route parameters and return values.
2. Define separate input and output Pydantic models.
3. Do not use a single model for every request and response just for convenience.
4. Return 201 for a newly created event, or justify a different code.
5. Return 404 for unknown event IDs.
6. Validate pagination bounds (for example, `limit` 1–100 and `offset` >= 0).
7. Use meaningful response descriptions and endpoint summaries so Swagger UI is useful.
8. Keep route handlers small enough to understand.
9. Add tests for valid input, invalid input, missing events, and pagination.
10. Make clear in the README that storage is temporary in Phase 1.

## Acceptance checklist

- [ ] Application starts using the documented command.
- [ ] `/docs` renders all Phase 1 endpoints and request schemas.
- [ ] Valid event is accepted and can be fetched.
- [ ] Invalid event types and naive timestamps are rejected.
- [ ] Unknown IDs return 404.
- [ ] Pagination limits are validated.
- [ ] Automated tests pass.
- [ ] Restarting the app loses events, and this limitation is documented.

## Out of scope

PostgreSQL, ORM, migrations, API-key authentication, outbound HTTP delivery, queues, retries, deployment.

## Self-review questions

1. Why is `payload` an object rather than a string containing JSON?
2. What is the difference between a Pydantic model and a database model?
3. Why should response models be explicit?
4. When would 202 Accepted be more appropriate than 201 Created?
5. What does FastAPI use Pydantic schemas for in Swagger/OpenAPI?
