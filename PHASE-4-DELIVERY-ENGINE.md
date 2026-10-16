# Phase 4 — Outbound Delivery and Attempt History

## Outcome

An accepted event can be sent to each matching destination. Every delivery attempt is recorded, and API users can inspect delivery outcomes.

## Schema additions

### `deliveries`

| Column | Type / rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Delivery identity |
| `event_id` | UUID, FK to events, NOT NULL | Event being delivered |
| `destination_id` | UUID, FK to destinations, NOT NULL | Target |
| `status` | VARCHAR/enum, NOT NULL | `pending`, `succeeded`, `failed` |
| `attempt_count` | INTEGER, NOT NULL, default 0 | Number of attempts |
| `next_attempt_at` | TIMESTAMPTZ, nullable | Used in Phase 5 |
| `created_at` | TIMESTAMPTZ, NOT NULL | UTC |
| `completed_at` | TIMESTAMPTZ, nullable | Final completion time |

Recommended constraint: unique `(event_id, destination_id)` for the original delivery. Replays should have explicitly defined semantics rather than accidentally bypassing this constraint.

### `delivery_attempts`

| Column | Type / rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Attempt identity |
| `delivery_id` | UUID, FK to deliveries, NOT NULL | Parent delivery |
| `attempt_number` | INTEGER, NOT NULL | Starts at 1 per delivery |
| `started_at` | TIMESTAMPTZ, NOT NULL | UTC |
| `finished_at` | TIMESTAMPTZ, nullable | UTC |
| `http_status` | INTEGER, nullable | Null for connection failures |
| `duration_ms` | INTEGER, nullable | Non-negative |
| `error_category` | VARCHAR, nullable | Sanitized classification |
| `response_excerpt` | TEXT, nullable | Small, sanitized and size-limited |

Recommended constraint: unique `(delivery_id, attempt_number)`.

## Delivery behaviour

1. Persist the event first.
2. Determine active destinations belonging to the same client whose subscriptions match the event type.
3. Create one delivery record per matching destination.
4. Send a POST request containing a documented event envelope and JSON body.
5. Set strict connection/read/write timeouts and a maximum response-body size.
6. Record HTTP status, duration, and a sanitized failure category.
7. For this phase, make a single attempt and mark it `succeeded` for a 2xx response; otherwise mark it `failed`.
8. Do not let a destination response or exception crash the whole API process.
9. Never send one client's event to another client's destination.
10. Do not hold a database transaction open while waiting for a remote HTTP request.

## Event envelope

Define and document a stable JSON envelope. It should include:
- Event ID
- Event type
- Event occurrence/receipt timestamp
- Payload

Add a delivery identifier if useful for receiver-side deduplication. Do not expose internal database details.

## Required endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/deliveries` | List current client's deliveries with filters/pagination |
| GET | `/api/v1/deliveries/{delivery_id}` | Inspect delivery |
| GET | `/api/v1/deliveries/{delivery_id}/attempts` | Inspect attempt history |

The event-ingestion endpoint should create delivery records for matching destinations. In Phase 4, delivery may run inline after persistence; document that requests may take longer. Phase 5 moves delivery to background processing.

## Concepts to learn

- HTTPX and outbound HTTP requests.
- Async I/O versus blocking I/O.
- Network timeouts, connection errors, non-2xx responses.
- Database transactions and avoiding long-held transactions.
- Delivery state machines and invariants.
- Safe logging and response-body truncation.
- Why a remote server may process an event even when the sender times out.

## Acceptance checklist

- [ ] Event is delivered to matching active destinations.
- [ ] Non-matching and inactive destinations receive nothing.
- [ ] 2xx responses are recorded as successful.
- [ ] Non-2xx responses and network failures are recorded as failed.
- [ ] Each attempt is persisted and inspectable.
- [ ] One failing destination does not prevent attempts to other destinations.
- [ ] Destination SSRF controls from Phase 3 are applied at connection time.
- [ ] Tests use a local mock receiver, never a real third-party endpoint.
- [ ] No transaction remains open during the outbound network request.
