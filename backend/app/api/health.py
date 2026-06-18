"""Health-check router."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness/readiness probe.

    Returns 200 with the service identity. Used by the frontend health badge.
    """
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.app_version,
    }
