# Phase 3 — Client Authentication and Destination Management

## Outcome

Multiple API clients can securely use the service. Each client can register destinations and see only its own resources.

## Schema additions

### `clients`

| Column | Type / rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Server-generated |
| `name` | VARCHAR(120), NOT NULL | Client display name |
| `created_at` | TIMESTAMPTZ, NOT NULL | UTC |

### `api_keys`

| Column | Type / rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Server-generated |
| `client_id` | UUID, FK to clients, NOT NULL | Owner |
| `key_prefix` | VARCHAR, NOT NULL | Safe identifier for lookup/display |
| `key_hash` | VARCHAR, NOT NULL | Store a secure hash, never the raw key |
| `created_at` | TIMESTAMPTZ, NOT NULL | UTC |
| `revoked_at` | TIMESTAMPTZ, nullable | Revocation marker |

Generate a cryptographically random secret once and display it once. Because a high-entropy API key is not a human password, a cryptographic hash such as SHA-256 with a server-side pepper can be appropriate; protect the pepper. Do not store plaintext keys.

### `destinations`

| Column | Type / rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Server-generated |
| `client_id` | UUID, FK to clients, NOT NULL | Owner |
| `url` | TEXT, NOT NULL | HTTPS required outside local development |
| `description` | VARCHAR(200), nullable | Human-readable label |
| `subscribed_event_types` | JSONB or normalized table | Define supported subscription model |
| `is_active` | BOOLEAN, NOT NULL | Defaults true |
| `created_at` | TIMESTAMPTZ, NOT NULL | UTC |

Add indexes for owner lookups. Use migrations for every schema change.

## Required endpoints

### Client / API key lifecycle

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/clients` | Development/admin operation to create a client and initial API key |
| POST | `/api/v1/api-keys` | Create an additional API key for the authenticated client |
| GET | `/api/v1/api-keys` | List key metadata, never secret values |
| DELETE | `/api/v1/api-keys/{key_id}` | Revoke a key |

For a personal learning deployment, decide how the initial client is provisioned without exposing an unauthenticated public client-creation endpoint. A CLI/admin command or seeded development client is acceptable.

### Destination management

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/destinations` | Register a destination |
| GET | `/api/v1/destinations` | List the current client's destinations |
| GET | `/api/v1/destinations/{destination_id}` | Retrieve one destination |
| PATCH | `/api/v1/destinations/{destination_id}` | Update allowed fields |
| DELETE | `/api/v1/destinations/{destination_id}` | Delete or deactivate a destination |

All event and destination endpoints that belong to a client must require authentication.

## Concepts to learn

- FastAPI `Depends` and dependency composition.
- HTTP bearer authentication or a documented `X-API-Key` header.
- Secret generation, hashing, revocation, and rotation.
- Authorization versus authentication.
- Multi-tenant data isolation.
- Database foreign keys and cascade behaviour.
- Pydantic validation for URL fields and enum-like inputs.
- Security risks of accepting arbitrary callback URLs.

## Security requirements

1. Every client-owned database query is scoped by authenticated `client_id`.
2. Guessing another client's UUID must not reveal their resource. Return 404 for inaccessible resources if that is your documented anti-enumeration policy.
3. Never log full API keys or authorization headers.
4. Enforce payload and URL length limits.
5. Block localhost, loopback, private, link-local, multicast, and reserved IP destinations.
6. Resolve DNS and validate all resulting IP addresses before connecting; defend against DNS rebinding and re-check on delivery.
7. Do not allow URL schemes other than HTTP/HTTPS; require HTTPS in non-local environments.
8. Avoid redirect-following to unvalidated destinations, or validate every redirect target.
9. Keep key-management operations restricted to the owning client.
10. Use least privilege and keep secrets in environment/secret configuration.

SSRF defence is not a trivial URL regex. Do not expose arbitrary destination delivery publicly until this threat is handled robustly.

## Acceptance checklist

- [ ] Authenticated client can manage its destinations.
- [ ] Missing, invalid, and revoked keys are rejected.
- [ ] API key secret is shown only at creation and is never stored plaintext.
- [ ] Client A cannot read, modify, or delete Client B's destinations or events.
- [ ] URL validation rejects unsafe local/private targets.
- [ ] Key revocation takes effect immediately or within a documented bounded cache period.
- [ ] Tests cover cross-client access attempts.
- [ ] Alembic migrations work from the prior phase.

## Out of scope

Outbound event delivery, retries, Redis, dead-letter queue, production deployment.
