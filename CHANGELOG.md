# Changelog — AI Verkenner

Notable changes per task/milestone. Newest first. History lives in git; this file records *what
changed and why it mattered*, at the granularity of a task file.

## Task 011 — Source scope correction + fetch-health surfacing (2026-08-04)

**Every enabled source is now either AI-scoped or knowingly whole-publication, and a source that
yields nothing is visible instead of silent.**

Raised by [D-017]. Two defects, both cheap. Decisions: [D-037]…[D-041].

### Changed — Defect 1: three site-wide feeds narrowed to their AI topic

- **`sources/sources.yaml`** — `MIT Technology Review`, `The Register` and `Hacker News (front
  page)` replaced by their topic-scoped equivalents and renamed so the dashboard shows the
  narrower scope. D-017 traced all 19 off-topic items in a 266-item corpus (7%) to these three;
  zero came from a topic-filtered feed. Each replacement URL was fetched before committing —
  **50 / 10 / 20 entries**, all well-formed. Scope now lives in the URL, not the classifier
  (classifier-level topicality is Task 012's, deliberately separate). Existing corpus rows are
  untouched: they are historical fact and age out of the digest window naturally.

### Added — Defect 2: per-source fetch health

The fail-safe isolation invariant works — one bad source never aborts a run — but it has a blind
side: a source that *never* yields is equally silent, so the registry goes on claiming coverage
the corpus does not have. **Reporting only**: no retries, no backoff, no circuit breaker, no
auto-disable.

- **`backend/app/models/entities.py`** — new `SourceHealth` table, upserted by source name like
  `Source`: last run / last non-erroring fetch / **last actual yield**, the fetched / kept / new /
  skipped counts kept separate, last error, and the consecutive zero-yield streak.
- **`backend/app/ingestion/health.py`** *(new)* — classifies each source, because "0 rows" turned
  out to be **four unrelated diagnoses** and only two are faults ([D-040]): `error` · `no-items`
  (200 that parses to zero entries — the genuinely broken case) · `stale-window` (healthy, just
  quieter than `SOURCE_MAX_AGE_DAYS`) · `no-token` (a `github_*` source with no `GITHUB_TOKEN`,
  skipped by ADR 0002 design) · `never-run`.
- **`backend/app/ingestion/orchestrator.py`** — `SourceRunResult` gains `fetched_count`,
  `new_count`, `skipped_count` and `needs_token`. `fetched_count` vs `item_count` is what
  separates a dead feed from a quiet one.
- **`backend/app/storage/`** — `upsert_source_health()` records the outcome, called from
  `ingest_and_store` **after** the records are committed, so a health write can never affect what
  was stored.
- **`backend/app/cli.py`** — `python -m app.cli sources --health` lists every enabled source
  (including ones that have never run); `run` ends with a loud, non-fatal warning for any source
  yielding nothing across `SOURCE_ZERO_YIELD_WARN` (default 3) consecutive runs.

### Resolved — the eight silent sources

**LangChain Blog fixed** (`blog.langchain.dev/rss/` now 302s to an HTML page; the feed moved to
`www.langchain.com/blog/rss.xml` — 100 entries). **Anthropic News** and **Neo4j Releases**
disabled with inline evidence: Anthropic publishes no feed at any of seven probed paths, and
`neo4j/neo4j` stopped publishing GitHub Releases in 2017 while continuing to tag ([D-038]). The
seven `github_*` sources are `no-token`, reported as such. **LlamaIndex Releases** and **Eugene
Yan** are **healthy and stay enabled** — they merely publish less often than the window, and
disabling a working source to make a metric look right is the failure `AGENT_ADDENDUM` §5 names
([D-037]).

### Correcting D-017

The effective `SOURCE_MAX_AGE_DAYS` is **7** (direnv-injected, not the documented 30), and that
cap — not broken feeds — is the dominant cause of zero yield. The audit's list of eight is wrong
in both directions: `Qdrant Releases` and `VentureBeat AI` also yield zero and were never named
(11 flagged on a live 3-run probe), while two of the eight are not broken at all. Raising the cap
is a tuning decision with a cost, so it is escalated rather than taken ([D-041]).

### Verified

Three real ingestion runs against a **scratch** database (`qdrant_client=None`, `enricher=None`,
`graph_store=None` — no vector or graph writes, no LLM spend). Run 2 hit a live transient arXiv
failure, was isolated, and the run completed — the fail-safe invariant demonstrated in the wild
rather than only in a fixture. `sources --health` output pasted into the session report.

**Tests:** `backend/tests/test_source_health.py` — the four named in the task file plus six more.
Full backend suite **green**.

## Task 010 — Defect 1: convergence cluster coherence (2026-08-03)

**A convergence may now be claimed only when the items share one driving entity.**

Remediation of M7.5, raised at the review gate by
[`docs/reviews/2026-07-25-m7.5-draft-review.md`](docs/reviews/2026-07-25-m7.5-draft-review.md). The
2026-07-21 Weak Signal drafts asserted *"8 items converging across 9 independent sources"* when the
eight items converged on eight **different** entities — a false converging claim, failing Task 009's
own acceptance criterion.

### Changed

- **`backend/app/digests/sections.py`** — new `coherent_cluster(items, *, min_items)`: groups
  weak-signal candidates by their **shared driving entity** and returns the largest such group, or
  `((), "")` when none reaches the minimum. Replaces the per-item `it.convergence > 0` filter that
  collected items converging on unrelated entities. `DigestData` gained `weak_driver` (the shared
  entity name; `""` = no coherent cluster) and `DigestItem` gained `driver` / `driver_uid`.
- **`backend/app/scoring/graph_signals.py`** — `GraphSignal` gained `driver_uid`, the driving
  entity's normalised uid. Grouping keys off the uid, never the display name. No new graph query:
  the value was already computed and discarded.
- **`backend/app/posts/generator.py`**
  - the cluster **label** is now the driving entity, not `items[0].title` (a publisher's headline
    cannot label a cluster);
  - **`_publishers()` is scoped to the driver** — "N independent sources" is now N sources behind
    *one* claim, not the union across unrelated items;
  - the lead item's `why_it_matters` is **attributed to that item**, never presented as the
    cluster's interpretation;
  - **tier disclosure**: a piece drawn from `archive`-tier items says so on all three surfaces and
    claims no top-tier provenance (D-016 ruling D).
- **`backend/app/core/config.py`** — new `WEAK_CLUSTER_MIN_ITEMS` (default **2**): the coherence
  floor below which the piece degrades honestly. A coherence floor, not a scoring threshold.
- **`backend/tests/posts_fixtures.py`** — fixed a pre-existing latent bug: `_BASE.replace(day=…+6)`
  raised `ValueError: day 33` whenever the fixture base landed after the 25th (D-022).

### Verified on the real corpus

`data/dev_corpus.db`, `--days 7`, 2026-07-14 → 2026-07-21, graph rebuilt from SQLite first.
**The coherent-cluster path fired** (not the degradation): 84 converging quadrant items resolve to
**30 distinct drivers**, and the largest group is 12 items on `OpenAI`. The previous incoherent
membership is gone — VEHBench, 3D-Fit, Output Reset, the interview-question repo, the spam-salting
piece and the Spring AI repo no longer appear. Every source URL is preserved on both paths.

**Open, escalated, not fixed here (D-024):** the largest group's driver is the corpus's biggest hub,
so the draft is now *mechanically* coherent but still reads as an overstatement
("Weak signal of the week: OpenAI"). Driver **eligibility** is out of Task 010's scope — fixing it
means touching convergence scoring, which this task forbids. Needs a ruling and its own task file.

### Tests

Six new tests in `backend/tests/test_cluster_coherence.py` (plus one guard):
`test_mixed_drivers_do_not_converge` · `test_shared_driver_converges` ·
`test_cluster_label_is_entity_not_headline` · `test_publisher_count_scoped_to_driver` ·
`test_no_cluster_degrades_honestly` · `test_archive_tier_cluster_is_disclosed`.
Backend suite: **181 passed, 1 skipped, 0 failed** (baseline 174 + 7).

### Not in this change

Defect 2 (X thread character limit) and Defect 3 (Noise Report cap) — separate session, per the task
file. `backend/app/scoring/priority.py` untouched (standing ruling, D-014). No threshold changed.
