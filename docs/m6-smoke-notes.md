# M6 — Real-data smoke notes

**First real-world validation of the whole stack** (ingest → dedup → embed → LLM enrich → graph →
dashboard). Run on **2026-06-20**.

## What was run

- **Stores:** `docker compose up qdrant neo4j` (live).
- **Embedder:** real local `sentence-transformers` (`BAAI/bge-small-en-v1.5`, 384-dim),
  `pip install -e ".[embeddings]"`.
- **LLM:** real cloud Anthropic, `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-opus-4-8` (the default).
- **Command:** `python -m app.cli run` once.
- **Sources (scoping decision — flagged):** to bound LLM cost/time for the gate, the run used a
  **representative real subset** of `sources.yaml` (genuine live feeds), not all 16:
  GitHub Blog, LangChain Blog, Simon Willison's Weblog, arXiv cs.CL, arXiv cs.LG
  (`SOURCES_FILE=/tmp/m6_smoke_sources.yaml`, `ARXIV_MAX_RESULTS=8`). Result:
  **56 items fetched → 56 events → 56 enriched (all `method=llm`) → 56 projected to Neo4j**;
  237 entities, 246 relationships. (LangChain Blog returned 0 entries — no failure, just empty.)
  A full-`sources.yaml` run is the reviewer's to make; the subset was enough to answer the gate's
  questions below.

## Are the five scores sane on real articles? — **Mostly yes**

Priority-class distribution: `archive: 41`, `operational_update: 14`, `immediate_priority: 1`.

- The single `immediate_priority` was *"Claude Fable is relentlessly proactive"* (Simon Willison on
  using Claude Code on a real task) — genuinely the most relevant item to an AI-developer-tooling
  user. Correct call.
- The flood of `archive` is right: arXiv cs.CL/cs.LG papers and Willison's misc posts are
  low-relevance to *this* user's specific stack, so they floor out — exactly the quadrant `/horizon`
  exists to mine.
- `operational_update` captured GitHub tooling posts and substantive releases. Sane.

## Does hype catch marketing? — **Yes, encouragingly**

Hype (0 = signal, 5 = noise) distribution: mostly `1` (40 items), a tail at `2–3` (13), one `4`.

- `hype=4`: a **satirical** McSweeney's "AI Economics" piece — correctly flagged as near-pure noise.
- `hype=3`: promotional GitHub posts ("how we built Qubot", Copilot CLI for beginners) — fair.
- `hype=0–1`: substantive releases (`datasette-agent 0.2a0`, an LSP config guide) — fair.

No false "hype = important" inversion observed; hype behaved as a demotion, and `priority.py` kept
relevance-driven classes independent of it.

## Are extracted entities/relationships meaningful (not hallucinated)? — **Largely yes, with caveats**

237 entities (`concept: 118, tool: 59, model: 28, person: 17, org: 15`), 246 relationships.

- Grounded and recognisable: `GitHub(org)`, `GitHub Copilot(tool)`, `Git(tool)`,
  `Language Server Protocol(concept)`, `Claude Fable 5(model)`, `Anthropic(org)`, real author names.
  No obvious hallucinations spotted in the sample.
- **Caveat — granularity/sprawl:** many `concept` entities are very fine-grained
  (`pull request limits`, `context handling`, `model routing`). Not wrong, but they inflate the
  entity count and dilute the graph. The per-item cap (12) helps but the concept lane is noisy.
- **Caveat — author-as-entity:** authors are extracted as `person` entities. Because one author
  (Simon Willison) writes many of the items, his node becomes a **high-degree hub** (degree 15) that
  dominates centrality. Same for `GitHub` as an org hub.

## Does /horizon surface a plausible weak signal? — **Partially. This is the headline finding.**

`/horizon` correctly returns **only** the `horizon_signal`/`archive` quadrant (operational/immediate
excluded) and ranks by the graph signal. But on real data the top results converge on **hub
entities, not quietly-emerging niche ones**:

```
conv=4 score=5.52 archive :: Making secret scanning more trustworthy ...
   why: convergence: 'GitHub' across 4 sources; central: 'GitHub' degree 7
conv=4 score=5.52 archive :: Accelerating ... multilingual AI ...
   why: convergence: 'GitHub' across 4 sources; central: 'GitHub' degree 7
... (then Simon-Willison-centred archive items, degree 15)
```

This is **exactly the risk PHASE_1_PLAN §7 anticipated**: *"Convergence may measure 'loud now'
rather than 'quietly emerging.'"* The smoke confirms it empirically — `'GitHub'` is mentioned
everywhere, so it "converges" trivially; the signal rewards ubiquity/centrality, not emergence.

**What looked wrong / to fix (mostly Phase-2 per §7, one fixed now):**

1. **🐞 Fixed now — Qdrant dimension drift.** The live `items` collection had been created at
   **dim 256** by earlier M5 live tests (hashing embedder); the real embedder is **384**. Every ANN
   search/upsert failed (`expected dim 256, got 384`). Degrade-don't-crash worked perfectly — the
   run fell back to **hash-only dedup**, `embedded=0`, SQLite/enrichment/graph unaffected — but
   semantic dedup didn't run this time. **Fix applied:** `qdrant_index.ensure_collection` now
   self-heals on a dim mismatch (drops + recreates the rebuildable collection); covered by
   `tests/test_qdrant_index.py`. A `python -m app.cli reindex` would re-embed at 384.
2. **⚠️ Hub-dominated convergence (Phase-2, §7).** The signal should **dampen hub entities** — e.g.
   weight by inverse document frequency (rare entities converging matter more than `GitHub`),
   exclude author `person` nodes from convergence, or require convergence across *independent*
   sources within a *short* window rather than corpus-wide. The Phase-2 "convergence quality" scope
   already names this.
3. **⚠️ `contributing_sources` vs `convergence` mismatch.** A card can say *"convergence: 'GitHub'
   across 4 sources"* while its `contributing_sources` lists only `['GitHub Blog']`. They measure
   different things — convergence is corpus-wide on the *driving entity*; `contributing_sources` is
   *this event's* coverage. Both are individually honest but read as inconsistent. Reconcile in M7:
   show the distinct sources touching the driving entity as the evidence behind the `why`.
4. **Note — single-feed corpus limits convergence.** With only ~4 working feeds (and most entities
   confined to one feed), genuine cross-source convergence is thin. A real weekly run over the full
   `sources.yaml` (more independent feeds covering the same developments) is where the weak-signal
   value should actually appear — re-evaluate `/horizon` then.

## Endpoints (served live against the real data)

- `GET /items` — ranked Core Radar; top = the `immediate_priority` Claude item; `graph_why` present.
- `GET /horizon` — `graph_available: true`, only the weak-signal quadrant, ranked by convergence.
- `GET /graph` — `available: true`, **80 nodes / 146 links, `truncated: true`** at `limit=80`
  (capped + events+top-entities only → renders legibly), node kinds `{entity, event}`.

## Verdict

The pipeline **works end to end on genuine articles**: scores are defensible, hype catches
noise/marketing, extraction is grounded, the dashboard renders the intelligence, and the
degrade-don't-crash invariant held under a real failure (Qdrant dim drift). The **weak-signal
ranking needs hub-dampening** before `/horizon` reliably surfaces "quietly emerging" signals — a
known Phase-2 item, now backed by real evidence rather than a hunch.
