from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import UUID, uuid4


@dataclass
class EventRecord:
    event_type: str
    payload: dict[str, Any]
    occurred_at: datetime | None = None
    idempotency_key: str | None = None
    id: UUID = field(default_factory=uuid4)
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "accepted"


class EventStore:
    """In-memory event store. Phase 1 only: all data is lost on restart."""

    def __init__(self) -> None:
        self._events: dict[UUID, EventRecord] = {}
        self._lock = Lock()

    def add(self, record: EventRecord) -> EventRecord:
        with self._lock:
            self._events[record.id] = record
        return record

    def get(self, event_id: UUID) -> EventRecord | None:
        return self._events.get(event_id)

    def list(self, limit: int, offset: int) -> tuple[list[EventRecord], int]:
        # Newest first; dict preserves insertion order, which matches received_at.
        with self._lock:
            events = list(reversed(self._events.values()))
        return events[offset : offset + limit], len(events)


_store = EventStore()


def get_store() -> EventStore:
    return _store
