"""AI Verkenner API — application entry point.

Serves the health/readiness checks and the curated source registry (`GET /sources`). At milestone
M2 the backend also carries thin clients for the derived stores (Qdrant, Neo4j) and reports their
reachability via /health; persistence, enrichment, and graph writes arrive in later milestones.

The app boots even when the stores are down — connectivity is checked lazily, never at import.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import digests, feedback, graph, health, horizon, items, sources
from app.core.config import settings
from app.db import neo4j, qdrant


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Nothing to open eagerly (clients connect lazily). On shutdown, release them cleanly.
    yield
    qdrant.close()
    neo4j.close()


app = FastAPI(title="AI Verkenner API", version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health/readiness + curated source registry + the M6 dashboard surface.
app.include_router(health.router)
app.include_router(sources.router)
app.include_router(items.router)     # /items — ranked Core Radar
app.include_router(graph.router)     # /graph — Cosmograph nodes/links
app.include_router(horizon.router)   # /horizon — weak-signal quadrant by convergence
app.include_router(feedback.router)  # /items/{id}/feedback — record feedback (M7)
app.include_router(digests.router)   # /digests — decision-oriented briefings (M7)
