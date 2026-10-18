# Phase 2 — PostgreSQL, SQLAlchemy, and Migrations

## Outcome

Events survive restarts. The API uses PostgreSQL through SQLAlchemy 2.x, with schema changes managed by Alembic.

## Scope

Keep the Phase 1 API contract stable unless a documented correction is necessary. Replace in-memory event storage with a database.

## Database schema: `events`

| Column | Type / rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Generated server-side |
| `event_type` | VARCHAR(100), NOT NULL | Non-empty |
| `payload` | JSONB, NOT NULL | Must represent a JSON object at API boundary |
| `occurred_at` | TIMESTAMPTZ, nullable | Original event time |
| `received_at` | TIMESTAMPTZ, NOT NULL | Server-side UTC timestamp |
| `status` | VARCHAR or enum, NOT NULL | Start with `accepted` |
| `idempotency_key` | VARCHAR(200), nullable | Phase 2 uniqueness policy below |

Recommended constraints/indexes:
- Primary key on `id`.
- Index on `received_at`.
- Index on `event_type`.
- If idempotency keys are globally unique in this phase, use a unique constraint on the non-null key. PostgreSQL allows multiple NULL values in a normal unique constraint.
- Document how idempotency scope changes when client authentication is introduced in Phase 3.

## Concepts to learn

- Relational database basics, SQL, JSONB, indexes and constraints.
- SQLAlchemy declarative models and mapped columns.
- Engine, connection pool, session, commit, rollback, and session lifetime.
- FastAPI dependencies for providing a database session.
- Sync versus async SQLAlchemy trade-offs; choose one deliberately and use it consistently.
- Alembic revision, upgrade, downgrade, and migration review.
- Environment variables and database connection strings.
- Transaction boundaries and unique-constraint violations.
- UTC timestamps and serialization.

## Requirements

1. Run PostgreSQL locally, preferably using Docker Compose.
2. Put connection settings in environment variables; do not commit secrets.
3. Use a database session per request with deterministic cleanup.
4. Handle transaction rollback when an operation fails.
5. Add an initial Alembic migration and prove both upgrade and downgrade work.
6. Keep Pydantic schemas separate from SQLAlchemy models.
7. Preserve the existing response contract.
8. Map expected database errors to appropriate HTTP responses; do not expose raw SQL or stack traces.
9. Make list queries deterministic (for example, sort by `received_at` and then `id`).
10. Test against PostgreSQL, not only SQLite, because JSONB, constraints, and concurrency behaviour differ.

## Idempotency behaviour

For requests with an `idempotency_key`:
- Repeating the same key must not silently create another event.
- Define what happens if the same key is reused with a different payload. Prefer `409 Conflict`.
- Return a documented response for a replayed request.
- Enforce uniqueness in the database; a check-then-insert application-only approach is vulnerable to races.
- In Phase 3, revise uniqueness to be scoped to the authenticated client.

## Acceptance checklist

- [ ] Data persists after application restart.
- [ ] Migrations create the schema from an empty database.
- [ ] A downgrade and re-upgrade work in a disposable development database.
- [ ] Duplicate idempotency keys follow the documented contract.
- [ ] Conflicting reuse of a key returns 409.
- [ ] Database sessions close correctly and failed transactions roll back.
- [ ] Tests run against PostgreSQL.
- [ ] No credentials are hard-coded.

## Out of scope

Client accounts/API keys, destination management, outbound deliveries, worker queue, retry scheduling, production deployment.
