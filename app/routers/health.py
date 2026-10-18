from fastapi import APIRouter
router = APIRouter(prefix="/health", tags=["health"])

@router.get("/live", summary="Liveness probe")
def health_live() -> dict[str, str]:
    return {"status": "alive"}

@router.get(
    "/ready",
    summary="Check whether the application is ready",
)
def health_ready() -> dict[str, str]:
    return {"status": "ready"}