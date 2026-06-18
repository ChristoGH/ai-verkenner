"""AI Verkenner API — application entry point.

Task 001 scope: a runnable FastAPI app that serves a health check and registers placeholder
routers. No ingestion, no enrichment, no database yet.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import settings

app = FastAPI(title="AI Verkenner API", version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check (implemented). Other resource routers arrive in later tasks.
app.include_router(health.router)
