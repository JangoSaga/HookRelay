import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventRow(Base):
    """Database model for an accepted event. API schemas live in app/models."""

    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("length(btrim(event_type)) > 0", name="ck_events_event_type_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="accepted")
    # Unique when present; Postgres allows many NULLs in a unique column.
    # Phase 3 will scope this per client: UNIQUE (client_id, idempotency_key).
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    # SHA-256 of event_type + payload + occurred_at, used to tell a replay from a conflict.
    request_hash: Mapped[str | None] = mapped_column(String(64))
