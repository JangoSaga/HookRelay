from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.models.event import EventListResponse, EventRequest, EventResponse
from app.repositories.events import (
    EventRepository,
    IdempotencyConflict,
    get_event_repository,
)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest an event",
    response_description="The accepted event with server-assigned fields",
    responses={
        200: {
            "model": EventResponse,
            "description": (
                "Idempotent replay: this idempotency_key was already used with the same "
                "request. The original event is returned and the response carries "
                "the header `Idempotent-Replayed: true`."
            ),
        },
        409: {"description": "idempotency_key was already used with a different request"},
        413: {"description": "Request body exceeds the size limit"},
        422: {"description": "Invalid event body"},
    },
)
def create_event(
    body: EventRequest,
    response: Response,
    repo: EventRepository = Depends(get_event_repository),
) -> EventResponse:
    try:
        row, created = repo.create(body)
    except IdempotencyConflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="idempotency_key was already used with a different request",
        )
    if not created:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replayed"] = "true"
    return EventResponse.model_validate(row)


@router.get(
    "/{event_id}",
    summary="Get an event by ID",
    response_description="The requested event",
    responses={404: {"description": "Event not found"}},
)
def get_event(
    event_id: UUID, repo: EventRepository = Depends(get_event_repository)
) -> EventResponse:
    row = repo.get(event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(row)


@router.get(
    "",
    summary="List events",
    response_description="A page of events, newest first",
)
def list_events(
    limit: int = Query(default=20, ge=1, le=100, description="Page size (1-100)"),
    offset: int = Query(default=0, ge=0, description="Number of events to skip"),
    repo: EventRepository = Depends(get_event_repository),
) -> EventListResponse:
    rows, total = repo.list(limit=limit, offset=offset)
    return EventListResponse(
        items=[EventResponse.model_validate(r) for r in rows],
        limit=limit,
        offset=offset,
        total=total,
    )
