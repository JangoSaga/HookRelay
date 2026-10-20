from uuid import uuid4

import pytest

from app.middleware import MAX_BODY_BYTES

URL = "/api/v1/events"


def make_event(**overrides):
    body = {"event_type": "invoice.paid", "payload": {"invoice_id": "inv_1", "amount": 100}}
    body.update(overrides)
    return body


# --- valid input ---------------------------------------------------------


def test_create_event_returns_201_with_server_fields(client):
    resp = client.post(URL, json=make_event(occurred_at="2026-10-20T10:00:00+05:30"))
    assert resp.status_code == 201
    data = resp.json()
    assert set(data) == {"id", "event_type", "payload", "occurred_at", "received_at", "status"}
    assert data["event_type"] == "invoice.paid"
    assert data["payload"] == {"invoice_id": "inv_1", "amount": 100}
    assert data["status"] == "accepted"
    assert data["received_at"]
    assert data["occurred_at"].startswith("2026-10-20T10:00:00")


def test_created_event_can_be_fetched(client):
    created = client.post(URL, json=make_event(idempotency_key="key-1")).json()
    resp = client.get(f"{URL}/{created['id']}")
    assert resp.status_code == 200
    assert resp.json() == created
    assert "idempotency_key" not in resp.json()


def test_occurred_at_is_optional(client):
    resp = client.post(URL, json=make_event())
    assert resp.status_code == 201
    assert resp.json()["occurred_at"] is None


# --- invalid input -------------------------------------------------------


@pytest.mark.parametrize("event_type", ["", "   ", "x" * 101])
def test_invalid_event_type_rejected(client, event_type):
    resp = client.post(URL, json=make_event(event_type=event_type))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "unprocessable_content"


def test_naive_occurred_at_rejected(client):
    resp = client.post(URL, json=make_event(occurred_at="2026-10-20T10:00:00"))
    assert resp.status_code == 422
    assert resp.json()["error"]["details"][0]["loc"] == ["body", "occurred_at"]


@pytest.mark.parametrize("payload", ["a string", [1, 2], 42, None])
def test_non_object_payload_rejected(client, payload):
    resp = client.post(URL, json=make_event(payload=payload))
    assert resp.status_code == 422


@pytest.mark.parametrize("field", ["id", "event_id", "received_at", "status"])
def test_server_owned_fields_rejected(client, field):
    resp = client.post(URL, json=make_event(**{field: "client-value"}))
    assert resp.status_code == 422


@pytest.mark.parametrize("key", ["", "k" * 201])
def test_invalid_idempotency_key_rejected(client, key):
    resp = client.post(URL, json=make_event(idempotency_key=key))
    assert resp.status_code == 422


def test_oversized_body_rejected(client):
    big = make_event(payload={"blob": "x" * (MAX_BODY_BYTES + 1)})
    resp = client.post(URL, json=big)
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "request_entity_too_large"


# --- missing events ------------------------------------------------------


def test_unknown_event_returns_404(client):
    resp = client.get(f"{URL}/{uuid4()}")
    assert resp.status_code == 404
    assert resp.json() == {
        "error": {"code": "not_found", "message": "Event not found", "details": []}
    }


def test_malformed_event_id_returns_422(client):
    resp = client.get(f"{URL}/not-a-uuid")
    assert resp.status_code == 422


# --- pagination ----------------------------------------------------------


def test_list_empty(client):
    resp = client.get(URL)
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "limit": 20, "offset": 0, "total": 0}


def test_list_paginates_newest_first(client):
    ids = [client.post(URL, json=make_event(payload={"n": i})).json()["id"] for i in range(5)]

    page1 = client.get(URL, params={"limit": 2, "offset": 0}).json()
    assert page1["total"] == 5
    assert [e["id"] for e in page1["items"]] == [ids[4], ids[3]]

    page3 = client.get(URL, params={"limit": 2, "offset": 4}).json()
    assert [e["id"] for e in page3["items"]] == [ids[0]]

    beyond = client.get(URL, params={"limit": 2, "offset": 10}).json()
    assert beyond["items"] == [] and beyond["total"] == 5


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "abc"}]
)
def test_invalid_pagination_rejected(client, params):
    resp = client.get(URL, params=params)
    assert resp.status_code == 422
