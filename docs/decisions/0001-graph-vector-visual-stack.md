# ADR 0001 — Adopt Qdrant + Neo4j + Cosmograph (graph/vector/visual stack)

## Status

Accepted — 2026-06-18. Supersedes the corresponding exclusions in [`../../CLAUDE.md`](../../CLAUDE.md)
("Do NOT build without a task file"). This ADR *is* that authorisation. CLAUDE.md must be updated
in the same change set that begins implementation (see Consequences).

## Date

2026-06-18

## Context

The scaffold (Task 001) deliberately fixed a minimal MVP stack (FastAPI + SQLite + React) and
listed a vector DB, a graph DB, and any broad visualisation tooling as out of scope. That was the
right call for *standing the project up*. It is no longer the right call for the project's stated
ambition.

AI Verkenner's value proposition — "what happened, why it matters, does it affect me, **is it a
weak signal**, what should I do" — is fundamentally a *relationship and convergence* problem, not a
list-of-articles problem. Two of the three modules (Horizon Scanner, Early Warning System) depend
on detecting that *multiple, individually-weak indicators are converging* — scattered papers, a
niche tool, a startup, and a lab all moving toward the same thing. A flat relational feed cannot
express or detect that. The horizon-scanning literature is explicit: weak signals "become trends
when multiple indicators converge", and that convergence is naturally a graph computation.

Three concrete needs follow:

1. **Semantic deduplication and event clustering.** Many sources report the same development in
   different words. Content-hash dedup misses these. The standard solution (SemDeDup, news
   aggregator designs) is embedding similarity + ANN search — i.e. a vector store.
2. **Entity/relationship memory over time.** To detect convergence and answer "how does this
   connect", the system must remember entities (labs, models, people, tools) and their
   timestamped interactions across items — i.e. a temporal knowledge graph.
3. **Legible exploration of that graph.** A personal intelligence tool is only as good as the
   user's ability to *see* the structure: which clusters are forming, what's central, what's new
   on the timeline — i.e. a fast graph/embedding visualiser.

## Decision

Adopt three technologies, integrated around the existing core loop, deployed locally via Docker
Compose for the first phase:

- **Qdrant** as the vector store: item (and later entity) embeddings for semantic dedup / event
  clustering, semantic retrieval, and the Cosmograph embedding projection.
- **Neo4j** as the knowledge graph: `Item`, `Source`, `Entity`, `Event`, `Topic` nodes and
  timestamped edges; the substrate for convergence/weak-signal detection and graph-expansion
  retrieval.
- **Cosmograph** (`@cosmograph/react`) as the visualisation layer: GPU/WebGL rendering of the
  Neo4j graph and the Qdrant embedding space, with its Timeline / Histogram / Search components.

**SQLite remains the system of record** (items, scores, feedback, digests, run logs). The new
stores are *derived indices* over that record, not replacements for it. Inference is **hybrid**:
a cloud LLM for enrichment and entity/relationship extraction (quality-sensitive), local
`sentence-transformers` for embeddings (high-volume, private, free).

Retrieval for the digest follows the established **GraphRAG hybrid pattern** (Qdrant + Neo4j):
embed the query → ANN search in Qdrant → map hits to Neo4j nodes → traverse relationships to
expand context → compose with the LLM.

## Alternatives

- **Stay on the MVP stack (SQLite + full-text + a relevance list).** Cheapest and already
  scaffolded, but structurally cannot detect convergence or answer "how does this connect" — it
  would amputate the Horizon Scanner and weaken the Early Warning System. Rejected against the
  stated ambition.
- **Postgres with `pgvector` + recursive CTEs instead of Qdrant + Neo4j.** One engine, less ops.
  But graph traversals and weak-signal queries are awkward and slow in SQL, and the visual layer
  still needs a graph feed. Reasonable later consolidation; not the right tool for graph-native
  exploration now. Recorded as a possible Phase 2+ simplification.
- **A single embedded library (NetworkX / FAISS) instead of servers.** No containers, but no
  persistence story, no concurrent access, and no path to the visual/timeline experience.
  Rejected.
- **Managed cloud (Qdrant Cloud + Neo4j Aura).** Less ops, but accounts/keys and data leaves the
  machine — at odds with a *personal* tool. Kept as an explicit toggle, not the default.
- **Other visualisers (Neo4j Bloom, Gephi, sigma.js, react-force-graph).** Bloom/Gephi aren't
  embeddable web components for a custom app; sigma/force-graph don't match Cosmograph's
  GPU-scale, embedding-projection, and built-in timeline. Cosmograph chosen for scale + the
  temporal/embedding views this project specifically needs.

## Consequences

**Easier:** weak-signal/convergence detection becomes a first-class graph query; "how does this
connect to my work / to each other" becomes answerable; semantic dedup collapses duplicate
coverage into events; the digest gains GraphRAG-quality grounding; the user gets a genuine map of
the field, not just a list.

**Harder / new cost:** three stateful services to run (Docker Compose, ~a few GB RAM for Neo4j +
Qdrant + an embedding model); two new client integrations and a graph schema to maintain; an
entity-resolution problem (the same lab/model named differently must merge) that is genuinely hard
and will be deliberately *basic* in Phase 1; more failure modes to isolate (the per-source and
per-store fail-safe invariant now extends to "a graph/vector write failure must not lose the
SQLite record").

**Required follow-on work (same change set as first implementation):**

- Update [`../../CLAUDE.md`](../../CLAUDE.md): move Qdrant, Neo4j, and graph DB out of the
  exclusions list into the sanctioned stack, citing this ADR; keep the *remaining* exclusions
  (auth, multi-user, broad crawler, billing, etc.) intact.
- Update [`../TECHNICAL_DESIGN.md`](../TECHNICAL_DESIGN.md) "later architecture" → current.
- New invariant: **SQLite is the source of truth; Qdrant and Neo4j are rebuildable derived
  indices.** A re-index job must be able to reconstruct both from SQLite.

The detailed milestone plan that operationalises this ADR is
[`../PHASE_1_PLAN.md`](../PHASE_1_PLAN.md).
