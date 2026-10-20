from fastapi import FastAPI

from app.errors import register_exception_handlers
from app.middleware import BodySizeLimitMiddleware
from app.routers import events, health

app = FastAPI(
    title="HookRelay API",
    version="0.1.0",
    description=(
        "A reliable webhook delivery platform for ingesting events, "
        "managing webhook destinations, and tracking event delivery. "
        "Built with FastAPI."
    ),
)

app.add_middleware(BodySizeLimitMiddleware)
register_exception_handlers(app)

app.include_router(health.router)
app.include_router(events.router)
