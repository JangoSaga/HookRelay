# Phase 6 — Testing, Observability, and Deployment

## Outcome

A reproducible, observable deployment with automated checks and documented operational behaviour. “Production-ready” is a standard to validate, not a label earned merely by deploying a container.

## Testing requirements

### Unit tests
- Pydantic validation and domain rules.
- Retryability classification and backoff calculation.
- Event subscription matching.
- State transition rules.
- Idempotency-key conflict handling.

### Integration tests
- API routes against PostgreSQL.
- Migrations from an empty database.
- API-key creation, revocation, and authorization.
- Cross-client data isolation.
- Outbox creation and dispatch.
- Delivery attempt persistence.
- Transaction rollback on failure.

### Worker / resilience tests
- Local mock receiver returns 2xx, 4xx, 429, and 5xx.
- Receiver is slow or times out.
- Connection is refused.
- Worker crashes after claiming work.
- Duplicate job is received.
- Two workers compete for work.
- Retry budget is exhausted.
- Receiver succeeds but sender times out.
- Unsafe URL and redirect attempts are rejected.

Do not depend on real external webhook endpoints in automated tests.

## Observability

Implement:
- Structured logs with request ID, event ID, delivery ID, and attempt number.
- Redaction of API keys, authorization headers, and sensitive payload fields.
- Metrics for accepted events, successful/failed deliveries, retries, queue age, and processing duration.
- Health endpoints with distinct liveness and readiness semantics.
- Error categories that are useful but do not leak secrets or response bodies.
- A documented retention policy for payloads and attempt records.

Use an instrumentation library and metrics backend only when you can explain what each metric is intended to reveal. Do not add dashboards just for screenshots.

## Configuration and security

- Validate required environment variables at startup.
- Keep secrets out of source control and container images.
- Use separate development and production configurations.
- Apply request size limits and reasonable timeouts.
- Configure database connection pooling.
- Use least-privilege database credentials.
- Run containers as a non-root user where practical.
- Pin dependencies and scan/update them periodically.
- Restrict CORS if browser clients are added; CORS is not API authentication.
- Protect Swagger UI or disable public interactive docs in production if appropriate.
- Use HTTPS at the deployment edge.
- Revisit SSRF defence, DNS resolution, redirects, and egress restrictions before public launch.

## Deployment deliverables

1. Dockerfile for the API.
2. Dockerfile or shared image/command for the worker if applicable.
3. Docker Compose for local API, PostgreSQL, Redis, and worker.
4. Production environment variable template with placeholder values only.
5. CI pipeline that installs dependencies, lints, tests, and validates migrations.
6. Deployment instructions for a host/platform of your choice.
7. A safe migration procedure for deployment.
8. A rollback and backup/restore note.
9. API examples using curl or an HTTP client.
10. Architecture diagram and a concise explanation of key design decisions.

## Performance and load checks

Choose a small, realistic test profile and record:
- Requests per second for event ingestion.
- p50/p95/p99 latency.
- Error rate.
- Queue age under load.
- Worker throughput and retry volume.
- Database connection usage.

Do not claim a performance target without measuring it. Document hardware, deployment size, test tool, and limitations.

## Operational runbook

Document how to:
- Identify a failing destination.
- Inspect a delivery and its attempts.
- Pause/deactivate a destination.
- Replay a dead-lettered delivery safely.
- Rotate/revoke an API key.
- Recover a stuck worker or queue.
- Apply/roll back a migration.
- Restore the database from backup.
- Investigate a spike in retries or queue age.

## Final acceptance checklist

- [ ] CI runs tests on every change.
- [ ] API and worker can be started reproducibly.
- [ ] Migrations work on a fresh database and an existing deployment.
- [ ] Logs and metrics expose failures without leaking secrets.
- [ ] Readiness accurately reports critical dependency health.
- [ ] Load-test results and limitations are documented.
- [ ] Deployment and recovery procedures are written and tested.
- [ ] README includes architecture, local setup, endpoint docs, security notes, and known limitations.
- [ ] Public deployment has reviewed SSRF and abuse controls.
- [ ] No unsupported claim of exactly-once delivery or guaranteed uptime is made.

## Suggested final repository structure

The exact layout is your decision, but aim to separate:
- API routes
- Pydantic schemas
- SQLAlchemy models
- Database/session setup
- Domain/service logic
- Delivery/queue worker
- Configuration
- Tests (unit, integration, worker)
- Migrations
- Deployment files
- Documentation

Avoid splitting into dozens of files before there is enough code to justify the boundaries.
