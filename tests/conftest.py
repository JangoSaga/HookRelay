from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db.session import make_engine
from app.main import app

ROOT = Path(__file__).resolve().parent.parent


def alembic_config(url: str) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = get_settings().test_database_url
    if not url:
        pytest.exit("TEST_DATABASE_URL is not set. Copy .env.example to .env.", returncode=2)
    return url


@pytest.fixture(scope="session")
def engine(test_database_url):
    eng = make_engine(test_database_url)
    try:
        eng.connect().close()
    except OperationalError:
        pytest.exit("Cannot reach the test database. Run: docker compose up -d db-test", returncode=2)
    # Build the schema from migrations so tests exercise the real schema.
    cfg = alembic_config(test_database_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine, monkeypatch):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE events"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    # Point the app's real get_db at the test database.
    monkeypatch.setattr("app.db.session.get_session_factory", lambda: factory)
    return factory


@pytest.fixture
def client(session_factory):
    with TestClient(app) as c:
        yield c
