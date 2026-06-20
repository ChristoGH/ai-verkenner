"""Application configuration.

Resolves environment settings, including the configurable root-level content paths
(``PROMPTS_DIR`` and ``SOURCES_FILE``). These live at the repository root, not under
``backend/`` — see docs/TECHNICAL_DESIGN.md. Paths are resolved against the repo root (the
parent of ``backend/``) unless given as absolute paths.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# backend/app/core/config.py -> parents[3] == repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]

# Load a .env from the repo root if present (no-op if absent).
load_dotenv(REPO_ROOT / ".env")


def _resolve(path_value: str) -> Path:
    """Resolve a path against the repo root unless it is absolute."""
    p = Path(path_value)
    return p if p.is_absolute() else (REPO_ROOT / p)


class Settings:
    """Plain settings holder (kept simple; no pydantic dependency in Task 001)."""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "AI Verkenner API")
        self.app_version: str = os.getenv("APP_VERSION", "0.1.0")
        self.service_name: str = "ai-verkenner"
        self.frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

        # Root-level content, configurable. Defaults match the repo layout.
        self.prompts_dir: Path = _resolve(os.getenv("PROMPTS_DIR", "prompts"))
        self.sources_file: Path = _resolve(os.getenv("SOURCES_FILE", "sources/sources.yaml"))

        # Ingestion HTTP behaviour. Polite user agent + a real timeout so one slow source
        # can't hang a run (the per-source fail-safe invariant).
        self.http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "10"))
        self.user_agent: str = os.getenv(
            "USER_AGENT",
            "AI-Verkenner/0.1 (+https://github.com/ChristoGH/ai-verkenner; personal intelligence tool)",
        )
        # arXiv API max results per query (bounded so a query can't pull an unbounded page).
        self.arxiv_max_results: int = int(os.getenv("ARXIV_MAX_RESULTS", "25"))

        # SQLite is the system of record (ADR 0001). Arrived at M3.
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/ai_verkenner.db")

        # Derived stores (ADR 0001), brought up via docker compose at M2. Defaults point at the
        # locally-mapped container ports so a host-run backend reaches `docker compose up`.
        self.qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password: str = os.getenv("NEO4J_PASSWORD", "verkenner_dev_pw")
        # Keep health pings snappy when a store is down (seconds).
        self.store_ping_timeout: float = float(os.getenv("STORE_PING_TIMEOUT", "2"))

        # Embeddings + semantic dedup (M3). The local model is loaded lazily and only used by the
        # SentenceTransformerEmbedder; tests/CI use the deterministic HashingEmbedder instead.
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        # "sentence-transformers" (real, local model) or "hashing" (deterministic, no download).
        self.embedder: str = os.getenv("EMBEDDER", "sentence-transformers")
        self.hashing_embedding_dim: int = int(os.getenv("HASHING_EMBEDDING_DIM", "256"))
        # Cosine threshold for stage-(b) semantic dedup. Higher = stricter (fewer merges).
        self.dedup_tau: float = float(os.getenv("DEDUP_TAU", "0.92"))

        # Enrichment (M4). Cloud LLM by default; "fake"/"none" disable it (tests inject a fake
        # provider directly). The SDK + key are only needed for the real "anthropic" provider.
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
        self.llm_model: str = os.getenv("LLM_MODEL", "claude-opus-4-8")
        self.llm_api_key: str | None = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4000"))
        # Cap entities extracted per item to contain sprawl (ADR/plan M4 risk mitigation).
        self.max_entities_per_item: int = int(os.getenv("MAX_ENTITIES_PER_ITEM", "12"))
        # The user's stack/projects/interests — fed to the LLM so relevance is about *this* user.
        self.user_context: str = os.getenv(
            "USER_CONTEXT",
            "A solo engineer building AI Verkenner: a personal AI intelligence and early-warning "
            "system. Stack: Python, FastAPI, SQLite, Qdrant, Neo4j, React/TypeScript, local "
            "sentence-transformers embeddings, and a cloud LLM. Interests: LLM tooling, RAG, "
            "vector/graph databases, agentic systems, and AI developer tooling.",
        )

        # Graph-aware ranking (M5). A transparent, documented adjustment layered ON TOP OF the
        # canonical priority class — it reorders within/across classes, never redefines the class,
        # and always respects the hype inversion. Window = how far back convergence is counted
        # (0 disables the window → count all). Weights blend convergence / centrality / recency.
        self.convergence_window_days: int = int(os.getenv("GRAPH_CONVERGENCE_WINDOW_DAYS", "30"))
        self.graph_convergence_weight: float = float(os.getenv("GRAPH_CONVERGENCE_WEIGHT", "1.0"))
        self.graph_degree_weight: float = float(os.getenv("GRAPH_DEGREE_WEIGHT", "0.5"))
        self.graph_recency_weight: float = float(os.getenv("GRAPH_RECENCY_WEIGHT", "0.5"))
        # How strongly the graph signal blends into the (hype-aware) salience tiebreak.
        self.graph_signal_weight: float = float(os.getenv("GRAPH_SIGNAL_WEIGHT", "1.0"))


settings = Settings()
