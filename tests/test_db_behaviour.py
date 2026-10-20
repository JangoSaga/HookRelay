import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.db.models import EventRow
from app.db.session import get_db
from app.main import app
from app.models.event import EventRequest
from app.repositories.events import EventRepository


def count(session_factory) -> int:
    with session_factory() as s:
        return s.scalar(select(func.count()).select_from(EventRow))


def test_get_db_rolls_back_on_error_and_closes(session_factory):
    gen = get_db()
    session = next(gen)
    session.add(EventRow(event_type="x", payload={}))
    session.flush()
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))
    assert not session.in_transaction()
    assert count(session_factory) == 0


def test_get_db_closes_after_success(session_factory):
    gen = get_db()
    session = next(gen)
    session.execute(select(1))
    assert session.in_transaction()
    gen.close()
    assert not session.in_transaction()


def test_failed_insert_rolls_back_and_session_stays_usable(session_factory):
    # Bypasses API validation to hit the database CHECK constraint directly.
    blank = EventRequest.model_construct(
        event_type="   ", payload={}, idempotency_key=None, occurred_at=None
    )
    with session_factory() as session:
        repo = EventRepository(session)
        with pytest.raises(IntegrityError):
            repo.create(blank)
        assert repo.list(limit=10, offset=0) == ([], 0)
    assert count(session_factory) == 0


def test_database_outage_returns_503_without_details(client):
    def broken():
        raise OperationalError("SELECT secret", {}, Exception("connection to host db.internal refused"))
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = broken
    try:
        resp = client.get("/api/v1/events")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "service_unavailable"
    assert "db.internal" not in resp.text and "SELECT" not in resp.text
