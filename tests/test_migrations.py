from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from tests.conftest import alembic_config

SCRATCH_DB = "hookrelay_migration_check"


def test_upgrade_downgrade_upgrade_on_empty_database(test_database_url):
    base = make_url(test_database_url)
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DB}"))
        conn.execute(text(f"CREATE DATABASE {SCRATCH_DB}"))

    scratch_url = base.set(database=SCRATCH_DB).render_as_string(hide_password=False)
    scratch = create_engine(scratch_url)
    cfg = alembic_config(scratch_url)
    try:
        assert "events" not in inspect(scratch).get_table_names()

        command.upgrade(cfg, "head")
        columns = {c["name"] for c in inspect(scratch).get_columns("events")}
        assert columns == {
            "id", "event_type", "payload", "occurred_at",
            "received_at", "status", "idempotency_key", "request_hash",
        }

        command.downgrade(cfg, "base")
        assert "events" not in inspect(scratch).get_table_names()

        command.upgrade(cfg, "head")
        assert "events" in inspect(scratch).get_table_names()
    finally:
        scratch.dispose()
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DB}"))
        admin.dispose()
