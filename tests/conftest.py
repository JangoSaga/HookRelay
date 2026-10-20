import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import EventStore, get_store


@pytest.fixture
def client():
    # Fresh store per test so tests never share events
    store = EventStore()
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
