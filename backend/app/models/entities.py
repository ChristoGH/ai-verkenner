"""SQLModel tables for the SQLite system of record (M3).

Schema notes (kept legible and forward-compatible):

- **Source** — one curated registry entry, upserted by its stable `name`.
- **RawItem** — one fetched item. Carries the **source URL intact** (core invariant), two hashes,
  and a nullable `event_id` FK. The two hashes are distinct on purpose:
    * `dedup_key`   — *identity* hash over (source, url, title, published). UNIQUE; this is what
                      makes re-runs idempotent (an already-stored item is recognised, not
                      re-inserted). Two different sources reporting the same story keep their own
                      rows — different URLs → different `dedup_key` — and are grouped by `event_id`.
    * `content_hash` — *content* fingerprint over normalised title+summary. NOT unique; it powers
                      stage-(a) of dedup (identical text → same event), and lets distinct sources
                      with byte-identical coverage collapse into one Event.
- **Event** — one real-world development covered by N RawItems.
- `embedded` — True once the item's vector is in Qdrant. A Qdrant write failure leaves it False
  (the SQLite record still persists); `reindex` / a later run can embed it.

M4 adds (enrichment + extraction; SQLite only — Neo4j projection is M5):

- **EnrichedItem** — one per `Event` (enrich once per real-world development, not per duplicate):
  the five scores (hype inverted), the human-facing fields with **fact separated from
  interpretation**, and a `priority_class` derived **only** by `app/scoring/priority.py`.
- **Entity** — a normalised org/model/person/tool/concept; basic Phase-1 resolution is
  exact + normalised-string match (`normalised_name` + `type` is unique).
- **Relationship** — a NEON-style **timestamped** triple (subject → predicate → object) tied to
  the source event/item, ready for M5 to project into Neo4j.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Source(SQLModel, table=True):
    """A curated source, mirrored from the YAML registry. Upserted by `name`."""

    __tablename__ = "source"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    source_type: str
    url: str
    repo_owner: str | None = None
    repo_name: str | None = None
    arxiv_query: str | None = None
    enabled: bool = True
    trust_level: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Event(SQLModel, table=True):
    """A cluster of near-duplicate RawItems describing one development."""

    __tablename__ = "event"

    id: int | None = Field(default=None, primary_key=True)
    title: str  # taken from the representative (first) item, for legibility
    representative_item_id: int | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class RawItem(SQLModel, table=True):
    """One fetched item. The source URL is preserved verbatim."""

    __tablename__ = "raw_item"

    id: int | None = Field(default=None, primary_key=True)
    source_id: int | None = Field(default=None, foreign_key="source.id", index=True)
    source_name: str
    source_type: str
    title: str
    url: str  # canonical link — ALWAYS preserved (core invariant)
    published_at: datetime | None = None
    summary: str | None = None

    dedup_key: str = Field(index=True, unique=True)  # identity → idempotency
    content_hash: str = Field(index=True)            # content fingerprint → stage-(a) dedup

    event_id: int | None = Field(default=None, foreign_key="event.id", index=True)
    embedded: bool = Field(default=False, index=True)  # vector present in Qdrant?
    created_at: datetime = Field(default_factory=_utcnow)


class EnrichedItem(SQLModel, table=True):
    """The LLM (or fallback) enrichment of one Event. One row per Event (unique)."""

    __tablename__ = "enriched_item"

    id: int | None = Field(default=None, primary_key=True)
    # One enrichment per Event — the UNIQUE constraint makes re-enrichment idempotent.
    event_id: int = Field(foreign_key="event.id", index=True, unique=True)
    # The representative RawItem that was enriched (its URL is preserved).
    raw_item_id: int | None = Field(default=None, foreign_key="raw_item.id", index=True)
    source_url: str  # preserved verbatim from the representative item

    category: str
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # The five scores (0–5). hype is INVERTED: 0 = strong signal, 5 = pure noise. Never summed
    # additively with the other four — see app/scoring/priority.py and the ranking helper.
    relevance: int
    novelty: int
    actionability: int
    strategic_potential: int
    hype: int

    # SOURCE FACT — only what the source states.
    summary: str
    # INTERPRETATION — the model's reading; kept in separate fields, never presented as fact.
    why_it_matters: str
    connection_to_user_work: str
    recommended_action: str

    # Weak-signal annotation (Horizon Scanner lane).
    is_weak_signal: bool = Field(default=False)
    horizon: str | None = None  # "near" | "mid" | "far" when is_weak_signal

    # Derived ONLY by app/scoring/priority.compute_priority_class — never re-derived inline.
    priority_class: str = Field(index=True)
    # How this enrichment was produced: "llm" or "fallback" (rule-based degrade).
    method: str = Field(default="llm")
    # True once this Event has been projected into Neo4j (M5). A graph write failure leaves it
    # False (the SQLite record stands); a later run / `graph-reindex` re-projects it — the
    # Neo4j analogue of RawItem.embedded for Qdrant.
    projected: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class Entity(SQLModel, table=True):
    """A normalised entity (org/model/person/tool/concept). Phase-1 resolution: exact+normalised."""

    __tablename__ = "entity"

    id: int | None = Field(default=None, primary_key=True)
    name: str  # the surface form first seen
    normalised_name: str = Field(index=True)  # lower/trim/collapse — the resolution key
    type: str = Field(index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class Relationship(SQLModel, table=True):
    """A timestamped relationship triple (NEON-style), tied to its source event/item."""

    __tablename__ = "relationship"

    id: int | None = Field(default=None, primary_key=True)
    subject_entity_id: int = Field(foreign_key="entity.id", index=True)
    predicate: str  # the interaction kind, e.g. "released", "integrates_with", "depends_on"
    object_entity_id: int = Field(foreign_key="entity.id", index=True)
    # Timestamp of the interaction — defaults to the item's published time when known.
    ts: datetime | None = Field(default=None, index=True)
    event_id: int | None = Field(default=None, foreign_key="event.id", index=True)
    raw_item_id: int | None = Field(default=None, foreign_key="raw_item.id", index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class RepoStarSnapshot(SQLModel, table=True):
    """A per-run snapshot of a watched repo's absolute star count (M6.5).

    `github_star_velocity` is honest about velocity: it does NOT fake a rate from absolute stars.
    Each run snapshots `stars` for a repo; the *velocity* is the delta against the previous snapshot
    for the same repo. The first run for a repo seeds the baseline and emits nothing.
    """

    __tablename__ = "repo_star_snapshot"

    id: int | None = Field(default=None, primary_key=True)
    repo_full_name: str = Field(index=True)  # "owner/name"
    stars: int
    captured_at: datetime = Field(default_factory=_utcnow, index=True)


class SourceHealth(SQLModel, table=True):
    """The latest fetch outcome for one source, plus its zero-yield streak (task 011 defect 2).

    One row per source `name` (upserted, like `Source`). This exists because the fail-safe
    isolation invariant — one bad source never aborts a run — has a blind side: a source that
    *never* yields stays silent, and the registry then claims coverage the corpus does not have.
    D-017 found eight enabled sources contributing 0 rows to a 266-item corpus, none of them
    visible anywhere.

    The counts mirror `ingestion.orchestrator.SourceRunResult` and are kept separate on purpose:
    `last_fetched_count` high with `last_item_count` 0 is a *healthy* source publishing less often
    than SOURCE_MAX_AGE_DAYS, which is a completely different situation from `last_fetched_count`
    0 (dead URL / non-feed page), and different again from `needs_token`.

    Reporting only. Nothing here retries, backs off, or disables a source — the human decides.
    """

    __tablename__ = "source_health"

    id: int | None = Field(default=None, primary_key=True)
    source_name: str = Field(index=True, unique=True)
    source_type: str

    last_run_at: datetime = Field(default_factory=_utcnow)
    # The last run whose fetch did not raise. A 200 that parses to zero entries still counts as
    # "did not error" — which is precisely why `last_yield_at` is tracked separately.
    last_ok_at: datetime | None = None
    # The last run that actually delivered >= 1 item to storage. This is the honest answer to
    # "when did we last hear anything from this source?".
    last_yield_at: datetime | None = None

    last_fetched_count: int = 0   # returned by the fetcher, before the recency cap
    last_item_count: int = 0      # survived the recency cap
    last_new_count: int = 0       # newly persisted to SQLite
    last_skipped_count: int = 0   # capped away or already stored
    last_error: str | None = None

    consecutive_zero_yield: int = 0
    needs_token: bool = False     # token-gated and GITHUB_TOKEN absent: skipped, not broken

    updated_at: datetime = Field(default_factory=_utcnow)


class Feedback(SQLModel, table=True):
    """One feedback action on an Event (M7).

    Feedback is keyed by `event_id` — the dashboard's item id is the Event id, and enrichment is
    per-Event, so a useful/ignore decision is about the development, not a single duplicate. The
    action is folded into ranking by `app/scoring/feedback.py` as a transparent, documented
    within-class tiebreak (it never changes the canonical priority class, and hype still demotes).
    Feedback is append-only history; the *latest* action per Event wins (see scoring/feedback.py).
    """

    __tablename__ = "feedback"

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id", index=True)
    action: str = Field(index=True)  # useful | not_useful | save | ignore
    created_at: datetime = Field(default_factory=_utcnow, index=True)


class Digest(SQLModel, table=True):
    """A generated decision-oriented digest (M7).

    SQLite is the source of truth (ADR 0001); the digest is *composed over already-enriched Events*
    — it never re-runs enrichment. `content_md` is the rendered briefing (LLM-composed when a
    provider is configured, else the deterministic fallback render). `noise_count` is the honest
    count of archived / high-hype Events excluded from the body. `event_ids` records every Event the
    digest drew from, so each referenced item keeps its source link.
    """

    __tablename__ = "digest"

    id: int | None = Field(default=None, primary_key=True)
    period_start: datetime | None = None
    period_end: datetime | None = None
    generated_at: datetime = Field(default_factory=_utcnow, index=True)
    content_md: str
    method: str = Field(default="llm")  # "llm" | "fallback"
    item_count: int = 0                 # Events considered for the body
    noise_count: int = 0                # archived / high-hype Events excluded (honest count)
    graphrag: bool = False              # True when Qdrant-retrieve / Neo4j-expand actually ran
    event_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
