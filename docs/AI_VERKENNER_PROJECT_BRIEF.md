# AI Verkenner — Project Brief

This is the **canonical brief** for AI Verkenner. When any other document, task file, or piece
of code disagrees with this one on intent, this document wins (and the disagreement should be
fixed). Architectural decisions that change direction are recorded as ADRs in
[`decisions/`](decisions/).

## 1. Purpose

AI Verkenner is a **personal AI intelligence and early-warning system**. The field
moves faster than any one person can read. AI Verkenner watches a curated set of trusted sources
on your behalf and turns the firehose into a short, ranked, decision-oriented briefing.

For every development it surfaces, it helps you answer five questions:

1. **What happened?** — the source fact, stated plainly, with the link preserved.
2. **Why does it matter?** — the interpretation, kept clearly separate from the fact.
3. **Does it affect my work?** — relevance to *your* stack, projects, and interests.
4. **Is it a weak signal?** — low current relevance but high potential future importance.
5. **What should I do?** — a concrete recommended action, or an explicit "nothing, just aware".

The goal is **decisions, not links**. A good day's output looks like: *"Here are 7 developments.
Two affect you now, one is a weak signal worth watching, the rest are noise — handled."*

## 2. The three modules

- **Core Radar** — the day-to-day ranked feed across your trusted sources: deduplicated,
  enriched, prioritised by relevance to you.
- **Horizon Scanner** — weak-signal detection. Surfaces the low-current-relevance /
  high-future-importance quadrant that a pure relevance ranking would bury.
- **Early Warning System** — the urgent lane. Security advisories, breaking changes, and
  shifts in tools you depend on — the things that should reach you the same day.

## 3. Curated pipeline, not a crawler

AI Verkenner is deliberately a **curated pipeline, not a broad web crawler**. It pulls from a
hand-maintained registry of high-trust sources (`sources/sources.yaml`) over their RSS/Atom
feeds and public APIs. We optimise for **signal quality and trust**, not coverage breadth. This
keeps the system legible, cheap, fail-safe, and free of the noise, legal exposure, and
operational weight that a general crawler would bring. Adding a source is a deliberate editorial
act, not an emergent side effect.

## 4. MVP scope

**In scope (the MVP build, Tasks 001–008):**

- A curated YAML source registry (RSS/Atom, GitHub releases, arXiv queries).
- Ingestion that fetches each source, failing safely per source.
- Storage in SQLite with deduplication of raw items.
- LLM enrichment: classification, scoring, summary, why-it-matters, recommended action.
- A ranked dashboard (Core Radar) with item cards.
- Lightweight feedback (useful / not useful / save / ignore) that informs ranking.
- A weekly digest that is decision-oriented, not a link dump.

**Explicitly excluded (do not build without a dedicated task file):**

Postgres · vector DB (Qdrant) · Redis · Kubernetes · production Docker · auth · graph database ·
broad web crawler · browser automation · billing · multi-user · Slack/Teams/email integrations ·
complex multi-agent systems · plugin framework.

## 5. Data model

Five core entities (fields illustrative; the schema is finalised in Task 004):

- **Source** — a curated origin. `name`, `source_type` (rss | github_releases | arxiv | …),
  `url`, optional `repo_owner`/`repo_name`/`arxiv_query`, `enabled`, `trust_level`.
- **RawItem** — one fetched entry as received. Source reference, title, **source URL (always
  preserved)**, published timestamp, raw content, dedup hash.
- **EnrichedItem** — a RawItem after LLM enrichment. Category/tags, the five scores, summary,
  why-it-matters, connection-to-user-work, recommended action, derived **priority class**.
- **Feedback** — a user signal on an item: `useful` | `not_useful` | `save` | `ignore`, with
  timestamp. Feeds back into ranking.
- **Digest** — a generated periodic briefing referencing the items it drew from.

The pipeline that connects them is the core loop:
`source → raw item → deduplication → enrichment → ranking → dashboard → feedback → digest`.

## 6. API surface (target)

The MVP backend exposes a small REST surface (built out across tasks, not all in 001):

- `GET /health` — liveness/readiness. **(Implemented in Task 001.)**
- `GET /sources` — list the configured sources.
- `GET /items` — the ranked, enriched feed (Core Radar); filterable.
- `GET /items/{id}` — a single enriched item.
- `POST /items/{id}/feedback` — record feedback.
- `GET /digests` / `GET /digests/{id}` — list and read generated digests.

## 7. Build order

The system is built one reviewable slice at a time, with a human review gate between each:

1. **001 — repo-scaffold** — runnable skeleton, docs, tasks, prompts, source stub, health check.
2. **002 — source-registry** — load and validate `sources.yaml`; expose `GET /sources`.
3. **003 — rss-github-ingestion** — fetch sources (RSS + GitHub releases + arXiv), fail-safe.
4. **004 — storage-deduplication** — SQLite persistence and raw-item deduplication.
5. **005 — llm-enrichment** — classification, the five scores, summary, action; priority class.
6. **006 — react-dashboard** — Core Radar UI with real enriched items.
7. **007 — feedback-actions** — useful / not useful / save / ignore, wired into ranking.
8. **008 — weekly-digest** — the decision-oriented periodic briefing.

## 8. Scoring model and priority rule

AI Verkenner enriches each item with five scores and derives a priority class from them. The
exact convention below is **authoritative** and is reproduced verbatim in
`tasks/005-llm-enrichment.md` and encoded in `backend/app/scoring/priority.py`.

<!-- BEGIN CANONICAL SCORING SECTION (verbatim — keep in sync with priority.py and task 005) -->

### Scores (each 0–5 integer)

- **relevance** — how directly this affects the user's current work and stack.
  Higher = more relevant. `5` means "requires immediate attention".
- **novelty** — how new or surprising this is versus what is already known.
  Higher = more novel.
- **actionability** — how clearly this implies a concrete action the user could take.
  Higher = more actionable.
- **strategic_potential** — how much this could matter to the user's future direction,
  independent of today's relevance. Higher = more strategic.
- **hype** — how much this is noise / marketing / overstatement rather than substance.
  **INVERTED polarity: `0` = strong signal, `5` = pure noise.**

### Polarity rule (do not get this wrong)

`relevance`, `novelty`, `actionability`, and `strategic_potential` all run **higher = more
salient**. `hype` is **inverted**. Never sum `hype` additively with the other four. Treat it as
a **penalty / demotion** (or a filter): a high-hype item is pushed down or out, never lifted.

### Priority classes

Items are bucketed into one of four priority classes, computed **only** by the canonical rule in
`backend/app/scoring/priority.py` (`compute_priority_class`). Do not re-derive this inline
anywhere else — import it.

- **immediate_priority** — needs attention now.
- **operational_update** — relevant to ongoing work; read soon.
- **horizon_signal** — low current relevance, high future importance (the weak-signal quadrant).
- **archive** — neither relevant now nor strategically promising; keep but demote.

The rule (canonical):

- `relevance >= 5` → **immediate_priority**, *regardless of strategic_potential*. A maximally
  relevant item (e.g. a security advisory in our own stack) is never demoted just because it
  isn't "strategic".
- else `relevance >= 4` **and** `strategic_potential >= 3` → **immediate_priority**.
- else `relevance >= 3` → **operational_update**.
- else (`relevance <= 2`) `strategic_potential >= 4` → **horizon_signal**.
- else → **archive**.

<!-- END CANONICAL SCORING SECTION -->

## 9. Agent rules

Work in this repository is governed by [`../CLAUDE.md`](../CLAUDE.md). In short: protect the core
loop; keep the MVP stack fixed; build nothing that lacks a task file; honour the invariants
(preserve every source URL, fail safely per source, separate fact from interpretation, respect
the hype inversion, one source of truth for the priority rule); one slice at a time; human review
gate before merge; clear structure over clever abstractions.

## Change log

- 2026-06-18 — Initial scaffold (Task 001).
