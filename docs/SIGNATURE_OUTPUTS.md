# AI Verkenner — Signature Outputs

> What AI Verkenner *publishes*. The differentiator is not "a list of news" — everyone has that.
> It is **convergence intelligence**: surfacing what is quietly converging *before* it gets loud,
> with the graph as evidence. This document defines the flagship artifacts, the three distribution
> surfaces, and the GitHub-intelligence signals that feed them. It is referenced by
> [`PHASE_1_PLAN.md`](PHASE_1_PLAN.md) (milestones M7.5 and M8.5) and
> [ADR 0002](decisions/0002-mcp-server-and-github-intelligence.md).

## 1. The flagship: "Weak Signal of the Week"

Each cycle, the system finds the single strongest **emerging convergence** — multiple
independent, individually-weak indicators (a niche paper, two new repos, a startup, a lab post)
pointing the same direction — and writes an evidence-backed narrative:

> "Three weeks ago this was 4 scattered items. This week: 11 across 6 independent sources. Here is
> the cluster, the timeline, and why it matters — before it is a headline."

Why it is curious/interesting: it is **a prediction with a receipt**. Most feeds report what is
loud; this reports what is converging. It ships with a Cosmograph snapshot of the cluster forming
over the timeline.

**Detection (graph-native):** an `Entity`/`Topic` whose incident edges grow across *distinct
sources* within a short window — the `horizon_signal` quadrant made measurable. Evidence = the
contributing items (with source URLs), the participating entities, and the growth curve.

The credibility flywheel: months of these produce the killer retrospective — **"Verkenner flagged
this N weeks before it trended"** — which is the strongest possible Medium long-form.

## 2. Supporting formats (same engine, different cut)

- **The Noise Report** — contrarian, highly shareable. Uses the **inverted hype score** to name
  what was loudest-but-emptiest this week (high `hype` = pure noise). Honest, funny, and
  structurally impossible for hype-driven feeds to publish about themselves.
- **Connection of the Week** — a single surprising edge from the graph ("a vector DB and a
  robotics lab now both depend on X"). A serendipity engine; graphs produce these for free.
- **The Field Map** — a periodic annotated Cosmograph export: "what the AI landscape looked like
  this week." Visual, distinctive, instantly recognisable as the project's brand.
- **Trajectory retrospective** — track a previously-flagged weak signal becoming mainstream;
  pure credibility content.

Every published claim keeps its source link and separates **source fact** from **interpretation**
(the core invariants apply to outputs, not just internal data).

## 3. Three distribution surfaces of one intelligence

The weekly intelligence is generated once, then projected to three surfaces by a **post
generator** (milestone M7.5):

- **LinkedIn** — the hook: 1 strong opening line + 3 bullets + the Cosmograph image + a CTA.
  Short, scroll-stopping.
- **Medium** — the narrative: the convergence story, the timeline, embedded graph, evidence
  links, and a short methodology footnote (how the signal was detected). Long-form.
- **MCP server** — the queryable surface: the same intelligence exposed read-only so the user's
  *agents* can ask the radar instead of re-searching the web (milestone M8.5; see §5).

Generation is **draft-first, human-in-the-loop**: the system produces drafts; the user approves
before anything is posted. No auto-posting in Phase 1.

## 4. GitHub intelligence (a source type, not a crawler)

Code ships before blog posts, so GitHub is often the **earliest** signal. The hard guardrail:
this stays a **curated pipeline via the GitHub API**, driven by watched orgs / users / topics in
`sources.yaml` — it is **not** the broad GitHub crawler excluded by `CLAUDE.md`. New
`source_type`s and signals:

- **`github_releases`** (already in `sources.yaml`) — version changes, breaking changes.
- **`github_star_velocity`** — *rate* of stars (not absolute) for repos under watched topics
  (`topic:llm`, `topic:rag`, …). The classic weak-signal indicator: "repos gaining stars
  unusually fast this week." This is the curious one and a prime convergence feeder.
- **`github_new_repos`** — new repositories from watched labs/people (a tracked lab open-sourcing
  something; a tracked developer creating/starring a repo).
- **`github_advisories`** — security / dependency advisories for repos **in the user's own
  stack**. Pure Early Warning; maps directly to relevance-5 → `immediate_priority` (the exact
  case [`backend/app/scoring/priority.py`](../backend/app/scoring/priority.py) protects).
- **`github_changes`** — deprecation RFCs / breaking-change issues/PRs in depended-on tools.

**Into the graph:** repo READMEs/topics become `Entity`/`Topic` nodes with `repo↔org↔concept`
edges, so "5 new repos this week around the same concept" *becomes a detectable convergence* —
directly feeding the flagship output. Rate-limited and fail-safe per source like every other
source.

## 5. The MCP server — "your radar as an API for your agents"

Expose Verkenner **read-only** over MCP so Claude and other agents query it instead of the open
web. Proposed tool surface (read-only in Phase 1; see
[ADR 0002](decisions/0002-mcp-server-and-github-intelligence.md)):

- `verkenner.search(query)` — hybrid GraphRAG over the corpus (Qdrant retrieve → Neo4j expand).
- `verkenner.weak_signals(window)` — current convergences with evidence.
- `verkenner.entity(name)` — dossier + graph neighbourhood for a lab/model/tool.
- `verkenner.digest(period)` / `verkenner.noise_report()` — the latest published pieces.
- `verkenner.why_it_matters(item_id)` — the enrichment for one item.
- **Resources:** the current graph snapshot and the stored digests.

Borrowable pattern: the `graphrag-hybrid` reference repo from the research scan already ships an
MCP integration over a Qdrant+Neo4j store.

## 6. How this changes the roadmap (pointers)

- GitHub-intelligence source types fold into **M3** (ingest + embed + dedup) and **M5** (graph
  write + convergence), not a separate track.
- **M7.5 — Post generator**: turn the weekly graph intelligence into LinkedIn + Medium drafts
  (human-approved), with a Cosmograph image export.
- **M8.5 — Read-only MCP server**: expose the §5 surface for agentic use.

Both sit *after* the data lives in SQLite+Qdrant+Neo4j (M7), because they are projections of that
intelligence, not new pipelines.
