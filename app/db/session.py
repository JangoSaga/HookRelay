from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def make_engine(url: str) -> Engine:
    # pool_pre_ping drops dead connections (e.g. after a database restart).
    # timezone=utc makes every timestamp come back as UTC regardless of server settings.
    return create_engine(url, pool_pre_ping=True, connect_args={"options": "-c timezone=utc"})


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """One session per request: rolled back on failure, always closed."""
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
