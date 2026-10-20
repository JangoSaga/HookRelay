import hashlib
import json
from datetime import timezone
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import EventRow
from app.db.session import get_db
from app.models.event import EventRequest


class IdempotencyConflict(Exception):
    """The idempotency key was already used with a different request."""


def compute_request_hash(body: EventRequest) -> str:
    """Fingerprint of the event content, used to tell a replay from a conflict.

    occurred_at is normalised to UTC so the same instant in two offsets matches.
    """
    occurred_at = body.occurred_at.astimezone(timezone.utc).isoformat() if body.occurred_at else None
    canonical = json.dumps(
        {"event_type": body.event_type, "payload": body.payload, "occurred_at": occurred_at},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


class EventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, body: EventRequest) -> tuple[EventRow, bool]:
        """Insert an event. Returns (row, created); created is False for an idempotent replay.

        Duplicate keys are rejected by the database's unique constraint, not by a
        check-then-insert, so concurrent requests with the same key cannot both succeed.
        """
        row = EventRow(
            event_type=body.event_type,
            payload=body.payload,
            occurred_at=body.occurred_at,
            idempotency_key=body.idempotency_key,
            request_hash=compute_request_hash(body),
        )
        self.session.add(row)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            if body.idempotency_key is None:
                raise
            existing = self._get_by_key(body.idempotency_key)
            if existing is None:
                raise  # not a duplicate key, so a different integrity failure
            if existing.request_hash != row.request_hash:
                raise IdempotencyConflict from None
            return existing, False
        return row, True

    def get(self, event_id: UUID) -> EventRow | None:
        return self.session.get(EventRow, event_id)

    def list(self, limit: int, offset: int) -> tuple[list[EventRow], int]:
        total = self.session.scalar(select(func.count()).select_from(EventRow)) or 0
        # Newest first; id breaks ties so pages are deterministic.
        stmt = (
            select(EventRow)
            .order_by(EventRow.received_at.desc(), EventRow.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt)), total

    def _get_by_key(self, key: str) -> EventRow | None:
        return self.session.scalar(select(EventRow).where(EventRow.idempotency_key == key))


def get_event_repository(session: Session = Depends(get_db)) -> EventRepository:
    return EventRepository(session)
