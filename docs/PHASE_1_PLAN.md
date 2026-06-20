# AI Verkenner — Phase 1 Plan: "Viable First Phase"

> Authorised by [ADR 0001](decisions/0001-graph-vector-visual-stack.md). This plan operationalises
> the adoption of **Qdrant** (vectors), **Neo4j** (graph), and **Cosmograph** (visualisation) into
> the existing core loop. Inference is **hybrid** (cloud LLM + local embeddings); all services run
> **locally via Docker Compose**; the first phase is a **thin vertical slice** — narrow scope, but
> the *entire* stack working end to end.

## 1. What "viable first phase" means

A single, complete pass of the enhanced core loop, on a deliberately small set of sources, with
all three new technologies actually carrying weight:

> A handful of curated sources are ingested, semantically de-duplicated into **events**, enriched
> and mined for **entities + timestamped relationships**, written to **SQLite (record) + Qdrant
> (vectors) + Neo4j (graph)**, ranked with both the priority rule *and* graph-convergence signals,
> shown as a **Core Radar list + a live Cosmograph graph/timeline**, and rolled into a
> **GraphRAG-grounded weekly digest** — all reproducible with one `docker compose up` and one run
> command.

It is "viable" when a real week of AI news produces a digest the user actually reads to the end
*and* a graph view that surfaces at least one genuine convergence the flat list would have missed.

Out of scope for Phase 1 (deferred to Phase 2): many sources, sophisticated entity resolution,
Postgres, alerting/notifications, scenario modelling, multi-user, auth.

## 2. The enhanced core loop

```
source
  → fetch (RawItem, source URL preserved, fail-safe per source)
  → DEDUP  ── content hash ──▶ Qdrant ANN (cosine ≥ τ) ──▶ group near-dups into EVENTS
  → ENRICH ── hybrid LLM ──▶ 5 scores (hype inverted) + summary/why/action (fact ≠ interpretation)
            └─ extract ENTITIES + timestamped RELATIONSHIPS  (NEON-style triples)
  → PERSIST ── SQLite (record) ─ Qdrant (embeddings) ─ Neo4j (Item/Source/Entity/Event nodes + edges)
  → RANK   ── priority.py  +  graph signals (entity convergence, source diversity, centrality)
            └─ hype as demotion, never additive
  → DASHBOARD ── Core Radar list  +  Cosmograph graph/timeline (Horizon view)
  → FEEDBACK ── useful / not_useful / save / ignore  → ranking
  → DIGEST ── GraphRAG: Qdrant retrieve → Neo4j expand → LLM compose (decisions, not links)
```

**Invariant added by [ADR 0001](decisions/0001-graph-vector-visual-stack.md):** SQLite is the
source of truth; Qdrant and Neo4j are *rebuildable derived indices*. A re-index job reconstructs
both from SQLite. A vector/graph write failure must never lose the SQLite record.

## 3. Target architecture (Phase 1)

```
                         ┌───────────────────────────── Frontend (React/Vite/TS) ─────────────┐
                         │  Core Radar list  ·  Cosmograph graph + Timeline + Search           │
                         └───────────▲───────────────────────────▲──────────────────────────┘
                                     │ /items, /digests          │ /graph (nodes, links)
                         ┌───────────┴───────────────────────────┴──────────── Backend (FastAPI) ┐
                         │  api ·  ingestion ·  enrichment ·  scoring/priority.py ·  graph ·  rag │
                         └───┬───────────────┬────────────────────┬───────────────────┬─────────┘
                             │ record        │ vectors            │ graph             │ inference
                       ┌─────▼─────┐   ┌──────▼──────┐      ┌──────▼──────┐    ┌───────▼────────┐
                       │  SQLite   │   │   Qdrant    │      │   Neo4j     │    │ Cloud LLM +     │
                       │ (truth)   │   │ embeddings  │      │ knowledge   │    │ local embeddings│
                       │           │   │ + dedup     │      │ graph       │    │ (sentence-tx)   │
                       └───────────┘   └─────────────┘      └─────────────┘    └────────────────┘
                            └──────────── docker compose up (qdrant, neo4j, backend, frontend) ──┘
```

### Data model (SQLite — system of record)

`Source · RawItem · Event · EnrichedItem · Entity · Relationship · Feedback · Digest`, plus a
`RunLog`. `Event` groups near-duplicate `RawItem`s. `Entity`/`Relationship` mirror what is written
to Neo4j so the graph is always rebuildable from SQLite.

### Graph schema (Neo4j)

- **Nodes:** `Item`, `Source`, `Entity` (`:Org`/`:Model`/`:Person`/`:Tool`/`:Concept`), `Event`,
  `Topic`.
- **Edges (timestamped where relevant):** `(Item)-[:FROM]->(Source)`, `(Item)-[:IN_EVENT]->(Event)`,
  `(Item)-[:MENTIONS {ts}]->(Entity)`, `(Entity)-[:INTERACTS_WITH {ts, kind}]->(Entity)`,
  `(Item)-[:ABOUT]->(Topic)`, `(Item)-[:SIMILAR_TO {score}]->(Item)`.
- **Convergence signal:** entities whose incident edges grow across *distinct sources* within a
  short window = a forming cluster → candidate weak signal / Horizon item.

### Vector store (Qdrant)

- Collection `items`: item-summary embeddings (local `sentence-transformers`, e.g. `bge-small`/
  `all-MiniLM`). Payload: `item_id`, `event_id`, `source`, `published_at`, priority class.
- Used for: (a) dedup/event clustering (ANN cosine, threshold τ≈0.92, tunable), (b) GraphRAG
  retrieval, (c) Cosmograph embedding-projection coordinates.

### Visualisation (Cosmograph)

`@cosmograph/react`, fed `nodes [{id,…}]` + `links [{source,target,…}]` from a backend `/graph`
endpoint (projected from Neo4j). Two views: **Network** (entities/events) and **Embedding**
(Qdrant projection), both with the Timeline scrubber for the temporal story.

## 4. What we borrow (research → decisions)

The field is well-trodden; we reuse rather than reinvent. Mapping from the scan:

- **Horizon** (Thysrael) — closest twin: fetch → dedup → score → filter → enrich → briefing, with
  a pluggable multi-LLM provider and 0–N scoring. *Borrow:* the provider abstraction and the
  briefing-generation shape; *keep ours:* the 5-axis scores + inverted hype + `priority.py`.
- **auto-news** (finaldie) — multi-source (RSS/Reddit/YouTube/X) + LLM via LangChain. *Borrow:*
  source-connector structure and orchestration patterns for Phase 2 source growth.
- **news-aggregator** (tony-stark-eth) — AI categorisation/summarisation **with rule-based
  fallback**, digests, full-text search. *Borrow:* the fail-safe fallback (degrade gracefully when
  the LLM is unavailable) — fits our per-source/per-store fail-safe invariant.
- **Precis** (leozqin) — extensible self-hosted reader centred on notifications. *Borrow:* the
  alerting model, parked for the Phase 2 Early-Warning push channel.
- **Official Qdrant + Neo4j GraphRAG** tutorial & reference repos (athrael-soju,
  rileylemm/graphrag-hybrid) and the **Lettria** case (+20% accuracy). *Borrow:* the hybrid
  retrieval pattern verbatim — embed → Qdrant ANN → map to Neo4j → traverse → compose.
- **NEON** (news entity-interaction KG) + LLM-as-extractor guides. *Borrow:* entities-as-nodes,
  **timestamped** interactions-as-edges, LLM emitting structured triples.
- **SemDeDup / news-dedup designs** — embed → cluster → cosine ≥ threshold → keep representative;
  two-stage (cheap hash → semantic vector). *Borrow:* the two-stage dedup and the ~0.92–0.95
  threshold for collapsing coverage into events.
- **Horizon-scanning methodology** (OECD/ITONICS/futures literature) — weak signals converge into
  trends across independent indicators. *Borrow:* operationalise "convergence across distinct
  sources" as the Horizon-Scanner ranking signal.

## 5. Milestones (the build ladder)

Each milestone is one reviewable slice ending at a **human review gate** (per `CLAUDE.md`). Each
has a single acceptance gate that must be demonstrably true before the next starts. `M0` is done.

| # | Milestone | New tech | Gate (must be true to proceed) |
|---|-----------|----------|--------------------------------|
| **M0** | Scaffold | — | ✅ Done (Task 001): backend/frontend run, `priority.py` tested. |
| **M1** | Source registry + ingestion | — | `sources.yaml` validated; a run yields in-memory `RawItem`s; one broken source is skipped, not fatal; every item keeps its URL. |
| **M2** | Infra up (Docker Compose) | Qdrant, Neo4j | `docker compose up` starts qdrant + neo4j + backend + frontend; `/health` reports all three reachable; clients connect; teardown clean. |
| **M3** | Storage + embeddings + semantic dedup | Qdrant | Items persist to SQLite; embeddings land in Qdrant; two-stage dedup groups a known duplicate set into one `Event`; re-run adds no duplicates. |
| **M4** | Enrichment + entity/relationship extraction | (cloud LLM) | Each new item → 5 scores (hype inverted) + summary/why/action with fact≠interpretation, **and** a set of entities + timestamped relationship triples; priority class comes from `priority.py` (imported, not re-derived). |
| **M5** | Graph write + graph-aware ranking | Neo4j | Nodes/edges written to Neo4j and rebuildable from SQLite; ranking blends `priority.py` with a convergence/centrality signal; a contrived converging set ranks above an isolated item. |
| **M6** | Dashboard + Cosmograph | Cosmograph | `/graph` serves nodes/links; Core Radar list renders real ranked items; Cosmograph Network + Timeline render the week and highlight a cluster; source links preserved. |
| **M5.5** | Convergence quality (hub-dampening) | — | *Inserted after M6's real-data smoke surfaced hub-dominated convergence (§7).* Hub-dampening (IDF + ≥2-distinct-source independence gate + singleton suppression) makes `/horizon` rank rare cross-source entities above ubiquitous hubs ('GitHub'/authors); the `why` evidence matches the listed sources; re-validated on a larger real feed set with semantic dedup actually running (`embedded > 0`). |
| **M6.5** | Source breadth | — | *Inserted after the M5.5 re-run showed the corpus lacks cross-publisher overlap.* Implement the four curated `github_*` fetchers (ADR 0002 — watched orgs/users/topics/packages via the API, NOT a crawler; honest star-velocity via persisted snapshots), add a per-source recency cap so archive feeds (HF 803, Eugene 210) don't blow up a run, and broaden the registry with independent reputable outlets so cross-publisher convergence can actually fire. Re-validated: does `/horizon` surface a cross-publisher convergence rather than arXiv cross-listing? |
| **M7** | Feedback + GraphRAG digest | (Qdrant+Neo4j) | Feedback persists and shifts ranking; weekly digest generated via Qdrant-retrieve → Neo4j-expand → LLM-compose; all 10 digest sections present; noise count honest. |
| **M7.5** | Post generator (LinkedIn + Medium) | — | The week's intelligence renders as a **Weak Signal of the Week** + **Noise Report** draft for LinkedIn (hook+image) and Medium (long-form), with a Cosmograph image export; **draft-only, human-approved, no auto-posting**; source links + fact≠interpretation preserved. |
| **M8** | First-phase hardening + demo gate | — | Full week, real sources, one `compose up` + one run command; all three stores consistent; viz renders; re-index rebuilds Qdrant+Neo4j from SQLite; **digest surfaces ≥1 real convergence the flat list missed.** |
| **M8.5** | Read-only MCP server | (MCP) | `verkenner.search / weak_signals / entity / digest / noise_report` + graph/digest resources served locally over MCP; an agent can query the radar; a test proves the surface is **read-only** (no writes/posts/triggers). |

### Milestone detail

**M1 — Source registry + ingestion.** Implements existing task files 002 + 003 (no new infra).
Validated `Source` model, configurable `SOURCES_FILE`, `GET /sources`; RSS/GitHub/arXiv fetchers;
per-source failure isolation. The registry also validates the **curated GitHub-intelligence
`source_type`s** (`github_star_velocity`, `github_new_repos`, `github_advisories`,
`github_changes`) from watched orgs/users/topics — GitHub API, rate-limited, fail-safe, *not* a
crawler ([ADR 0002](decisions/0002-mcp-server-and-github-intelligence.md);
[SIGNATURE_OUTPUTS §4](SIGNATURE_OUTPUTS.md)). *Risk:* feed flakiness / GitHub rate limits →
fixtures, timeouts, per-source token handling.

**M2 — Infra up.** Flesh out the (currently inert) `docker-compose.yml`: `qdrant`, `neo4j`,
`backend`, `frontend`. Add `backend/app/db` clients for Qdrant and Neo4j; extend `/health` to a
readiness check that pings both and reports per-dependency status (degrade, don't crash, if one is
down). `.env` gains connection settings. *Risk:* RAM footprint → document minimums; make Neo4j/
Qdrant optional-degraded so the app still boots.

**M3 — Storage + embeddings + dedup.** SQLite persistence (extends task 004) for `Source`,
`RawItem`, `Event`. Local embedding model wired; embeddings written to Qdrant. Two-stage dedup:
content hash (cheap) → Qdrant ANN cosine ≥ τ → group survivors into `Event`s. GitHub-intelligence
items (new repos, advisories, README/topic text) are embedded and de-duplicated here alongside RSS/
arXiv. *Borrows* SemDeDup / news-dedup. *Risk:* threshold tuning → make τ configurable; ship a small
labelled dup/near-dup/distinct fixture to calibrate; metric = no false-merge on the fixture.

**M4 — Enrichment + extraction.** Hybrid enrichment (extends task 005): cloud LLM produces the 5
scores + summary/why/action (fact≠interpretation, URL preserved) **and** a structured
entity+relationship payload (NEON-style timestamped triples) via the `prompts/` templates (add
`extract_graph.md`). Priority class via `compute_priority_class` (imported). *Risk:* extraction
noise / entity sprawl → constrain entity types, cap per item, validate triples; keep Phase-1
entity resolution to exact+normalised string match (defer fuzzy/embedding merge to Phase 2).

**M5 — Graph write + ranking.** Persist Items/Sources/Entities/Events + timestamped edges to
Neo4j (mirrored in SQLite so it's rebuildable). Add a graph-signal ranker that *demotes/promotes*
on top of `priority.py`: convergence (distinct sources touching the same entity in a window),
degree/centrality, recency — combined as a transparent, documented adjustment that **respects the
hype inversion**. GitHub items contribute `repo↔org↔concept` edges, so "several new repos around
one concept this week" and **star-velocity** become first-class convergence inputs — the strongest
feeder for the Weak Signal of the Week output. *Risk:* graph/SQLite drift → single write path + a
`reindex` command + a consistency test.

**M6 — Dashboard + Cosmograph.** Backend `/graph` endpoint projects Neo4j into `nodes`/`links`
(+ optional Qdrant projection coords). Frontend: real `ItemCard`s wired to `/items` (extends task
006) **and** a Cosmograph view (`@cosmograph/react`) with Network + Timeline + Search; clicking an
entity filters the list. *Risk:* graph too dense to read → cap nodes, filter by window/priority,
lean on the Timeline; start with events+top entities only.

**M7 — Feedback + GraphRAG digest.** Feedback (task 007) persisted and folded into ranking.
Digest (task 008) upgraded to GraphRAG: embed the week's themes → Qdrant retrieve → Neo4j expand →
LLM compose the 10 decision-oriented sections, with Horizon/Research-radar drawn from the
convergence signal. *Risk:* digest becomes a link list → enforce the "decisions, not links" rubric
in the prompt and the acceptance check.

**M7.5 — Post generator (LinkedIn + Medium).** Turn the week's intelligence into publishable
drafts: the **Weak Signal of the Week** and the **Noise Report**, projected to a LinkedIn cut
(hook + 3 bullets + Cosmograph image + CTA) and a Medium cut (narrative + timeline + embedded
graph + evidence links + methodology footnote). **Draft-only and human-approved — no auto-posting
in Phase 1.** Outputs preserve source links and keep fact separate from interpretation. See
[SIGNATURE_OUTPUTS §1–3](SIGNATURE_OUTPUTS.md). *Risk:* generic-sounding posts → template on real
graph evidence (the cluster, the growth curve), not prose alone.

**M8 — Hardening + demo gate.** One-command bring-up; a real week ingested; consistency + re-index
verified; the viz renders; and the headline proof: the system surfaces at least one genuine
convergence (a forming cluster across independent sources) that the flat relevance list buried.
This is the gate that declares the first phase *viable*.

**M8.5 — Read-only MCP server.** Expose the intelligence over MCP for agentic use:
`verkenner.search / weak_signals / entity / digest / noise_report / why_it_matters`, plus graph and
digest resources, served locally and read-only. An agent can "ask the radar" instead of searching
the open web. Borrows the `graphrag-hybrid` MCP pattern from the research scan. See
[ADR 0002](decisions/0002-mcp-server-and-github-intelligence.md) and
[SIGNATURE_OUTPUTS §5](SIGNATURE_OUTPUTS.md). *Risk:* surface drifts from store schema / accidental
writes → keep it a thin read-only projection with a test asserting no mutation.

## 6. Dependency order

```
M0 ✅ ─▶ M1 ─▶ M2 ─▶ M3 ─▶ M4 ─▶ M5 ─▶ M6 ─▶ M5.5 ─▶ M6.5 ─▶ M7 ─▶ M8 (viable)
                 (infra)  (vectors) (LLM)  (graph) (viz) (conv.  (source  (rag)  │
                                                          quality) breadth)       │
                                                    ├─▶ M7.5 post generator (LinkedIn/Medium)
                                                    └─▶ M8.5 read-only MCP server
```

**M5.5 and M6.5 are corrective slices** the M6 real-data smoke forced: M5.5 fixed the convergence
*signal* (it favoured hubs); M6.5 fixes the convergence *fuel* (the corpus lacked independent
cross-publisher sources, and the `github_*` early-signal feeds were still stubs). Both tighten the
weak-signal lane before M7's GraphRAG digest leans on `/horizon`.

M1 and M2 are independent and could run in parallel; everything after M3 is linear because each
store/stage feeds the next. **M7.5 and M8.5 are projections of the M7 intelligence** — they depend
on the stores being populated but not on each other, so they can be built in either order (or in
parallel) once M7 lands.

## 7. Risks & mitigations (top of the list)

- **Entity resolution is hard.** Same lab/model, many names. *Mitigation:* Phase 1 stays at
  exact+normalised match; fuzzy/embedding merge is explicit Phase 2 scope. Accept some duplicate
  entities now; don't let it block the slice.
- **Operational weight of 3 services.** *Mitigation:* local Docker Compose, documented RAM
  minimums, degrade-don't-crash health model, and SQLite-as-truth so the heavy stores are
  disposable/rebuildable.
- **Cloud-LLM cost on every item.** *Mitigation:* enrich only *new, de-duplicated* items (dedup
  before enrich), batch, cache by content hash, and keep a rule-based fallback (borrowed from
  news-aggregator).
- **Graph/vector vs SQLite drift.** *Mitigation:* single write path, `reindex` rebuild command,
  consistency test in M5/M8.
- **Viz unreadable at scale.** *Mitigation:* window + priority filters, cap nodes, default to
  events + top entities, lean on the Timeline.
- **Convergence may measure "loud now" rather than "quietly emerging."** The M5 signal is a
  *windowed snapshot* of distinct-source count on an entity, which correlates with current
  relevance/loudness; and because MENTIONS is attached from every item in an Event (correct for
  source diversity), it cannot yet distinguish **independent convergence** (many sources, many
  angles, genuinely emerging) from **syndication amplification** (one PR reprinted by many outlets).
  *Mitigation / Phase 2:* compute convergence **trajectory** (week-over-week growth rate, per
  [SIGNATURE_OUTPUTS §1](SIGNATURE_OUTPUTS.md)'s "4 → 11 items" framing), not just the snapshot;
  weight sources by independence. Phase 1 ships the snapshot as a v1 proxy and the weak-signal
  *selection* (filter to the horizon/archive quadrant, rank by graph score) is an explicit M7/M7.5
  deliverable — the Core Radar's class-first ranking deliberately does **not** surface weak signals
  on its own.

## 8. Definition of done (Phase 1)

`docker compose up` brings the whole system online; a documented run command ingests a real week
from the curated sources; items are de-duplicated into events, enriched, extracted, and written to
SQLite + Qdrant + Neo4j consistently; the dashboard shows a ranked Core Radar **and** a live
Cosmograph graph/timeline; a GraphRAG weekly digest reads as decisions; `reindex` rebuilds the
derived stores from SQLite; and the system demonstrably surfaces at least one real convergence the
flat list missed. The phase delivers its **value** at M7.5 (a publishable Weak Signal of the Week +
Noise Report for LinkedIn/Medium, human-approved) and M8.5 (a read-only MCP server so agents can
query the radar). At that point CLAUDE.md and TECHNICAL_DESIGN.md are updated to match, and **Phase
2** is planned: scale sources; fuzzy/embedding **entity resolution**; **convergence trajectory**
(growth-rate, not snapshot) and **source-independence weighting** (independent convergence vs
syndication amplification); alerting/notifications; scenario analytics; read/write MCP.

## 9. Immediate next actions

1. Review & merge this plan + [ADR 0001](decisions/0001-graph-vector-visual-stack.md) +
   [ADR 0002](decisions/0002-mcp-server-and-github-intelligence.md) +
   [SIGNATURE_OUTPUTS.md](SIGNATURE_OUTPUTS.md).
2. Update `CLAUDE.md` (move Qdrant/Neo4j/graph out of exclusions; note the read-only MCP surface
   and curated GitHub source types; keep the rest of the exclusions intact) and
   `TECHNICAL_DESIGN.md` (promote "later architecture" to current) — one change set.
3. Rewrite the task files into the M1–M8.5 ladder (extend existing 002–008; add infra, embeddings,
   extraction, graph-write, Cosmograph, post-generator, and MCP tasks).
4. Start **M1** (source registry + ingestion) — no new infra, unblocks everything.
