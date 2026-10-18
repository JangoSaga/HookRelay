from fastapi import FastAPI
from app.routers import health

app = FastAPI(
    title="HookRelay API",
    version="0.1.0",
    description=(
        "A reliable webhook delivery platform for ingesting events, "
        "managing webhook destinations, and tracking event delivery. "
        "Built with FastAPI."
    ),
)

app.include_router(health.router)