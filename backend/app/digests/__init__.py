"""Digests (M7) — the decision-oriented weekly briefing.

A GraphRAG digest composed over already-enriched Events: embed the period's themes → Qdrant
retrieve → Neo4j expand → one composition LLM call (or the deterministic fallback render). Reuses
the canonical ranking and priority rule; never re-runs enrichment. See `generator.generate_digest`.
"""

from app.digests.generator import build_digest_data, generate_digest
from app.digests.sections import SECTION_HEADINGS, DigestData, DigestItem

__all__ = ["generate_digest", "build_digest_data", "DigestData", "DigestItem", "SECTION_HEADINGS"]
