from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

class EventRequest(BaseModel):
    # Only defined fields are allowed in the request body
    model_config = ConfigDict(extra="forbid")
    
    event_type: str = Field(min_length=1, max_length=100)
    
    # Json definition of the event payload
    payload: dict[str, Any]
    
    idempotency_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    occurred_at: datetime | None = None
    
    # validators
    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls,value:str) -> str:
        if not value.strip():
            raise ValueError("event_type cannot be empty or whitespace")
        return value
    
    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("occurred_at must include a timezone")
        return value
    
class EventResponse(BaseModel):
    id: UUID
    event_type: str
    payload: dict[str, Any]
    occurred_at: datetime | None
    received_at: datetime
    status: Literal["accepted"]
    
class EventListResponse(BaseModel):
    items: list[EventResponse]
    limit: int
    offset: int
    total: int