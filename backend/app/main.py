"""AI Verkenner API — application entry point.

Serves the health check and the curated source registry (`GET /sources`, milestone M1). Ingestion
runs as a job, not an endpoint, at this milestone; database, enrichment, and the graph/vector
stores arrive in later milestones.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, sources
from app.core.config import settings

app = FastAPI(title="AI Verkenner API", version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check + curated source registry. Other resource routers arrive in later milestones.
app.include_router(health.router)
app.include_router(sources.router)
