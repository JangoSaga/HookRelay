import threading
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select

from app.db.models import EventRow
from app.models.event import EventRequest
from app.repositories.events import EventRepository, IdempotencyConflict

URL = "/api/v1/events"


def event(**overrides):
    body = {
        "event_type": "invoice.paid",
        "payload": {"invoice_id": "inv_1"},
        "idempotency_key": "key-1",
    }
    body.update(overrides)
    return body


def count(session_factory) -> int:
    with session_factory() as s:
        return s.scalar(select(func.count()).select_from(EventRow))


def test_new_key_creates_event(client):
    resp = client.post(URL, json=event())
    assert resp.status_code == 201
    assert "Idempotent-Replayed" not in resp.headers


def test_same_key_same_request_replays_original(client, session_factory):
    first = client.post(URL, json=event())
    second = client.post(URL, json=event())
    assert second.status_code == 200
    assert second.headers["Idempotent-Replayed"] == "true"
    assert second.json() == first.json()
    assert count(session_factory) == 1


def test_equivalent_offsets_count_as_same_request(client):
    a = event(occurred_at="2026-10-20T10:00:00+05:30")
    b = event(occurred_at="2026-10-20T04:30:00+00:00")
    assert client.post(URL, json=a).status_code == 201
    assert client.post(URL, json=b).status_code == 200


def test_payload_key_order_does_not_matter(client):
    a = event(payload={"x": 1, "y": 2})
    b = event(payload={"y": 2, "x": 1})
    assert client.post(URL, json=a).status_code == 201
    assert client.post(URL, json=b).status_code == 200


def test_same_key_different_payload_conflicts(client, session_factory):
    client.post(URL, json=event())
    resp = client.post(URL, json=event(payload={"invoice_id": "inv_2"}))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"
    assert count(session_factory) == 1


def test_same_key_different_event_type_conflicts(client):
    client.post(URL, json=event())
    assert client.post(URL, json=event(event_type="invoice.failed")).status_code == 409


def test_same_key_different_occurred_at_conflicts(client):
    client.post(URL, json=event(occurred_at="2026-10-20T10:00:00Z"))
    resp = client.post(URL, json=event(occurred_at="2026-10-21T10:00:00Z"))
    assert resp.status_code == 409


def test_conflict_does_not_expose_internals(client):
    client.post(URL, json=event())
    text = client.post(URL, json=event(payload={"z": 1})).text.lower()
    for leaked in ("sql", "constraint", "integrity", "traceback", "events_"):
        assert leaked not in text


def test_requests_without_key_always_create(client, session_factory):
    body = event(idempotency_key=None)
    assert client.post(URL, json=body).status_code == 201
    assert client.post(URL, json=body).status_code == 201
    assert count(session_factory) == 2


def test_different_keys_create_separate_events(client):
    assert client.post(URL, json=event(idempotency_key="a")).status_code == 201
    assert client.post(URL, json=event(idempotency_key="b")).status_code == 201


def _race(session_factory, bodies):
    """Fire one create per body from separate sessions, released together."""
    barrier = threading.Barrier(len(bodies))

    def attempt(body):
        with session_factory() as session:
            repo = EventRepository(session)
            barrier.wait()
            try:
                return "created" if repo.create(body)[1] else "replayed"
            except IdempotencyConflict:
                return "conflict"

    with ThreadPoolExecutor(max_workers=len(bodies)) as pool:
        return list(pool.map(attempt, bodies))


def test_concurrent_identical_requests_create_exactly_one(session_factory):
    body = EventRequest(**event())
    results = _race(session_factory, [body] * 10)
    assert results.count("created") == 1
    assert results.count("replayed") == 9
    assert count(session_factory) == 1


def test_concurrent_conflicting_requests_create_exactly_one(session_factory):
    bodies = [EventRequest(**event(payload={"n": i})) for i in range(10)]
    results = _race(session_factory, bodies)
    assert results.count("created") == 1
    assert results.count("conflict") == 9
    assert count(session_factory) == 1
