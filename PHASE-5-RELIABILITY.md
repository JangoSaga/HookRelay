# Phase 5 — Background Workers, Retries, Idempotency, and Replay

## Outcome

Delivery no longer depends on the ingestion request remaining open. Work is queued durably, retried according to policy, and recoverable after failure.

## Architecture change

Use PostgreSQL as the durable source of truth. Introduce a queue and worker only after defining the delivery state machine. Redis may be used for queue transport, but do not treat a Redis-only enqueue as the sole durable record of an accepted event.

Choose and document one implementation:
- A worker framework with Redis-backed jobs, plus a durable database outbox; or
- A PostgreSQL outbox and a dispatcher that publishes jobs to Redis.

The outbox pattern closes the gap between committing a database transaction and publishing work to an external queue.

## Schema additions / changes

### `outbox_messages`

| Column | Type / rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Message identity |
| `aggregate_type` | VARCHAR, NOT NULL | For example, `event` |
| `aggregate_id` | UUID, NOT NULL | Event/delivery reference |
| `message_type` | VARCHAR, NOT NULL | For example, `delivery.requested` |
| `payload` | JSONB, NOT NULL | Minimal internal message |
| `created_at` | TIMESTAMPTZ, NOT NULL | UTC |
| `published_at` | TIMESTAMPTZ, nullable | Null until dispatched |
| `publish_attempts` | INTEGER, NOT NULL, default 0 | Dispatcher attempts |
| `last_error` | TEXT, nullable | Sanitized error |

Add any lease/claim columns required by the chosen dispatcher. Use safe row-claiming patterns so multiple dispatchers do not process the same row simultaneously.

### Delivery fields

Add:
- `max_attempts` or use a centrally configured policy.
- `next_attempt_at`.
- `last_error_category`.
- `dead_lettered_at`, nullable.
- Optional `replay_of_delivery_id`, nullable, if replay creates a new delivery record.

Document the difference between an original delivery retry and an operator-requested replay.

## Retry policy

Implement an explicit policy, for example:
- Retry connection errors, timeouts, HTTP 408, HTTP 429, and selected 5xx responses.
- Do not retry ordinary permanent 4xx responses by default; document exceptions.
- Use exponential backoff with jitter.
- Respect a valid `Retry-After` response where appropriate.
- Enforce a finite maximum attempt count.
- After exhaustion, mark the delivery dead-lettered and make it visible to the client.
- Store the next attempt time rather than sleeping inside a request handler.

Make the exact base delay, maximum delay, jitter, retryable statuses, and attempt limit configuration explicit.

## Reliability and correctness rules

1. Event acceptance and creation of delivery work must be atomic from the application's perspective. Use a transaction plus outbox or another justified durable mechanism.
2. Workers must tolerate duplicate job messages.
3. Claim work safely when multiple workers run concurrently.
4. Update attempt counts and state consistently.
5. A timeout is ambiguous: the receiver may already have processed the request. Send a stable event/delivery ID and document at-least-once delivery.
6. Do not automatically retry every 4xx response.
7. Ensure retries are scheduled, not implemented as long sleeps in API requests.
8. Define what happens when a destination is disabled or deleted while work is queued.
9. Make manual replay authorized, rate-limited, audited, and idempotent with respect to duplicate replay requests.
10. Add graceful worker shutdown and recovery of abandoned/in-progress jobs.

## Required endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/deliveries` | Filter by status and destination |
| POST | `/api/v1/deliveries/{delivery_id}/replay` | Request a replay under documented rules |
| GET | `/api/v1/deliveries/{delivery_id}/attempts` | Full attempt history |
| GET | `/health/ready` | Include database and queue/worker dependency checks as appropriate |

## Concepts to learn

- Durable queues and background workers.
- Outbox pattern and transactional boundaries.
- At-least-once processing and idempotent consumers.
- Exponential backoff, jitter, Retry-After.
- Dead-letter queues and replay semantics.
- Race conditions, row locking/claiming, and concurrent workers.
- Graceful shutdown, job leases, and crash recovery.
- State-machine invariants.

## Acceptance checklist

- [ ] API acceptance does not wait for the destination's response.
- [ ] Accepted events cannot be silently lost between database commit and enqueue.
- [ ] Transient failures are retried according to policy.
- [ ] Permanent failures do not retry indefinitely.
- [ ] Exhausted deliveries are visible as dead-lettered.
- [ ] A worker restart recovers eligible work.
- [ ] Duplicate queue messages do not corrupt state or create unbounded duplicate attempts.
- [ ] Concurrent workers do not claim the same delivery simultaneously.
- [ ] Manual replay is authenticated, authorized, and tested.
- [ ] Tests cover timeout ambiguity, duplicate jobs, retry exhaustion, and worker restart.
