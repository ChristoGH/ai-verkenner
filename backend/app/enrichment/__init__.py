"""Enrichment + entity/relationship extraction (M4).

Per **Event** (not per duplicate), a cloud LLM produces the five scores (hype inverted) +
summary/why/connection/action and a structured entity + timestamped-relationship payload; results
persist to SQLite (`EnrichedItem`, `Entity`, `Relationship`). The priority class is imported from
`app.scoring.priority` — never re-derived here. Inference is provider-abstracted and injectable; a
missing/failed LLM call degrades to a deterministic rule-based fallback (fail-safe per item).

No Neo4j writes yet — that is M5; the graph is written to SQLite so M5 can project it.
"""

from app.enrichment.enricher import Enricher, enrich_new_events
from app.enrichment.provider import LLMProvider, get_provider

__all__ = ["Enricher", "enrich_new_events", "LLMProvider", "get_provider"]
