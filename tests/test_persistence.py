from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.main import app

URL = "/api/v1/events"


def test_events_survive_a_restart(client, engine, monkeypatch):
    created = client.post(URL, json={"event_type": "invoice.paid", "payload": {"a": 1}}).json()

    # Simulate a restart: drop the old connection pool and build a fresh app client
    # with a brand-new session factory. Only the database carries state across.
    engine.dispose()
    monkeypatch.setattr(
        "app.db.session.get_session_factory",
        lambda: sessionmaker(bind=engine, expire_on_commit=False),
    )
    with TestClient(app) as restarted:
        resp = restarted.get(f"{URL}/{created['id']}")
        assert resp.status_code == 200
        assert resp.json() == created
        assert restarted.get(URL).json()["total"] == 1
