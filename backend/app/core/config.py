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


# Driver names that may never LABEL a Weak Signal of the Week (task 013 / D-026, defect B).
# Edit this list — or override it wholesale with a comma-separated WEAK_DRIVER_STOPLIST — without
# touching any logic. Matched case-insensitively against the entity's *normalised* identity
# (`schemas.enrichment.normalise_entity_name`: lower / trim / collapse whitespace).
#
# Why each class of term is here:
#   * the field itself — every item in this corpus is about AI, so "AI is quietly converging" says
#     nothing; it is the category, not an entity within it.
#   * model-class nouns — "LLM" / "model" name the artefact class, and D-024 found the 8-item
#     incoherent M7.5 cluster passed precisely by sharing a generic "LLM" hub.
#   * sub-discipline names — "machine learning" / "deep learning" are fields of study; a convergence
#     on one is a statement about the whole industry, not an early warning.
#
# Stoplisting affects SELECTION ONLY. These entities stay in the graph, keep their scores, and can
# still appear anywhere else in the digest — they simply cannot be the face of a weak signal.
_DEFAULT_WEAK_DRIVER_STOPLIST: tuple[str, ...] = (
    # the field itself
    "ai", "artificial intelligence", "generative ai", "genai",
    # model-class nouns
    "llm", "llms", "large language model", "large language models", "model", "models",
    # sub-discipline names
    "machine learning", "ml", "deep learning", "neural network",
)


def _csv_list(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    """A comma-separated env override, or the default. Blank entries are dropped."""
    if value is None:
        return default
    return tuple(part.strip() for part in value.split(",") if part.strip())


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

        # Per-source recency cap (M6.5), applied uniformly in ingestion. Bounds archive-serving
        # feeds (Hugging Face served 803 entries, Eugene Yan 210) so a full sources.yaml run is
        # affordable. AGE skips items older than the window; ITEMS is a hard per-source backstop.
        self.source_max_age_days: int = int(os.getenv("SOURCE_MAX_AGE_DAYS", "30"))
        self.source_max_items: int = int(os.getenv("SOURCE_MAX_ITEMS", "40"))
        # Fetch-health surfacing (task 011 defect 2 / D-017). A source that yields nothing across
        # this many CONSECUTIVE runs is reported loudly at the end of every run. Reporting only —
        # nothing retries, backs off, or auto-disables; the human decides. A registry that claims
        # coverage the corpus does not have is a silent correctness failure in an early-warning
        # system, so the fail-safe isolation invariant must not also make a dead source invisible.
        self.source_zero_yield_warn: int = int(os.getenv("SOURCE_ZERO_YIELD_WARN", "3"))

        # Curated GitHub-intelligence fetchers (ADR 0002 — watched orgs/users/topics, NOT a crawler).
        # A token is required; without it, github_* sources are skipped (degrade, never crash).
        self.github_token: str | None = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        # Hard ceiling on items a single github_* call returns (rate-limit + cost discipline).
        self.github_per_source_items: int = int(os.getenv("GITHUB_PER_SOURCE_ITEMS", "15"))

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
        # M5.5 hub-dampening: an entity must be touched by at least this many DISTINCT sources to
        # count as convergence (a single prolific feed/author is not convergence). Convergence is
        # also IDF-weighted (ubiquitous hubs suppressed) and singletons (1 development) score ~0.
        self.graph_min_sources: int = int(os.getenv("GRAPH_MIN_SOURCES", "2"))

        # Feedback → ranking (M7). How strongly a user's feedback blends into the (hype-aware,
        # within-class) salience tiebreak — exactly like the graph signal, it never changes the
        # priority class. useful/save lift by this much; not_useful demotes; ignore removes from the
        # default feed (see app/scoring/feedback.py).
        self.feedback_weight: float = float(os.getenv("FEEDBACK_WEIGHT", "2.0"))

        # GraphRAG weekly digest (M7). Composed over already-enriched Events (one composition LLM
        # call — enrichment is never re-run). `digest_period_days` bounds the window by published
        # date (0 = the whole current corpus). `digest_high_hype` is the hype floor (inverted: 4–5)
        # that counts an item as noise; `digest_section_limit` caps items per section for legibility.
        self.digest_period_days: int = int(os.getenv("DIGEST_PERIOD_DAYS", "7"))
        self.digest_high_hype: int = int(os.getenv("DIGEST_HIGH_HYPE", "4"))
        self.digest_section_limit: int = int(os.getenv("DIGEST_SECTION_LIMIT", "8"))
        # How many semantic neighbours the GraphRAG retrieve step pulls for the theme query.
        self.digest_retrieve_limit: int = int(os.getenv("DIGEST_RETRIEVE_LIMIT", "40"))
        # --- Weak-signal SELECTION floor (task 013 defect C / D-047). ------------------------------
        # Both settings below gate which driver may be CHOSEN as the Weak Signal of the Week. They
        # are deliberately separate from `graph_min_sources`, which is the global convergence floor
        # inside `graph_signals` — raising that would change scoring product-wide (D-026 rules it
        # out). Nothing here is re-scored; a driver below the floor keeps its convergence, it just
        # cannot be the face of the piece.
        #
        # WHY 3, for both: the selection objective is *quietest corroborated driver* (D-026), and a
        # minimiser lands on whatever the floor allows. At a floor of 2 the winner is 2 mentions /
        # 2 sources / 2 items by construction — which is not distinguishable from coincidence, and
        # on the real corpus produced `Firefox`, whose second item had no AI content at all (D-036).
        # Two sources mentioning something twice is a coincidence; three is a pattern. A weak signal
        # needs enough corroboration to be REAL *and* low ambient volume — the floor supplies the
        # first half, the quietness ordering the second.
        #
        # Smallest group of items sharing ONE driving entity that may be called a convergence
        # (task 010 / D-016 B, floor raised 2 → 3 by D-047). Below this, the weak-signal piece
        # degrades honestly rather than claiming a cluster. This is a coherence floor, NOT a scoring
        # threshold — LOWERING it to manufacture a signal is the failure D-014 forbids.
        self.weak_cluster_min_items: int = int(os.getenv("WEAK_CLUSTER_MIN_ITEMS", "3"))
        # Distinct sources a driver must span to be *selectable* as the weak signal. Selection only:
        # `GRAPH_MIN_SOURCES` (above, default 2) still decides what counts as convergence at all.
        self.weak_driver_min_sources: int = int(os.getenv("WEAK_DRIVER_MIN_SOURCES", "3"))
        # Generic concept nodes that may never be the DRIVER of a weak signal (task 013 / D-026).
        # See `_DEFAULT_WEAK_DRIVER_STOPLIST` above for the list and why each class of term is on it.
        self.weak_driver_stoplist: tuple[str, ...] = _csv_list(
            os.getenv("WEAK_DRIVER_STOPLIST"), _DEFAULT_WEAK_DRIVER_STOPLIST
        )

        # Editorial cap on the Noise Report (task 010 Defect 3): each surface NAMES at most this many
        # demoted items, loudest-first. The true total is always stated in the prose ("187 items were
        # demoted this week; here are the 12 loudest") — the cap is legibility, never a claim about
        # corpus size. It does not touch `is_noise` or the hype threshold; nothing is re-scored.
        self.noise_report_limit: int = int(os.getenv("NOISE_REPORT_LIMIT", "12"))

        # Post generator (M7.5). `posts_output_dir` is the git-ignored working area for generated
        # drafts. `vault_dir` (from VAULT_DIR) is the user's Obsidian vault — when set, drafts are
        # ALSO written as new notes under <vault>/00-Inbox/ (create-only; never modify/delete). It is
        # None unless configured; the `posts --vault-dir` flag overrides it per-run.
        self.posts_output_dir: Path = _resolve(os.getenv("POSTS_OUTPUT_DIR", "outputs/posts"))
        _vault = os.getenv("VAULT_DIR")
        self.vault_dir: Path | None = _resolve(_vault) if _vault else None


settings = Settings()
