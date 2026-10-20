from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.event import EventListResponse, EventRequest, EventResponse
from app.store import EventRecord, EventStore, get_store

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest an event",
    response_description="The accepted event with server-assigned fields",
    responses={
        413: {"description": "Request body exceeds the size limit"},
        422: {"description": "Invalid event body"},
    },
)
def create_event(
    body: EventRequest, store: EventStore = Depends(get_store)
) -> EventResponse:
    record = store.add(EventRecord(**body.model_dump()))
    return EventResponse.model_validate(record)


@router.get(
    "/{event_id}",
    summary="Get an event by ID",
    response_description="The requested event",
    responses={404: {"description": "Event not found"}},
)
def get_event(
    event_id: UUID, store: EventStore = Depends(get_store)
) -> EventResponse:
    record = store.get(event_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(record)


@router.get(
    "",
    summary="List events",
    response_description="A page of events, newest first",
)
def list_events(
    limit: int = Query(default=20, ge=1, le=100, description="Page size (1-100)"),
    offset: int = Query(default=0, ge=0, description="Number of events to skip"),
    store: EventStore = Depends(get_store),
) -> EventListResponse:
    records, total = store.list(limit=limit, offset=offset)
    return EventListResponse(
        items=[EventResponse.model_validate(r) for r in records],
        limit=limit,
        offset=offset,
        total=total,
    )
