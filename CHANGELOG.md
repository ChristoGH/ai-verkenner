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

## Task 013 — Driver eligibility: the weak signal is the *quietest* corroborated entity (2026-08-04)

**The Weak Signal of the Week now names the quietest corroborated driver, never the loudest.**

Remediation of the residual Task 010 left behind, escalated as [D-024] and ruled by [D-026]. With
shared-driver grouping in place, `coherent_cluster()` still selected the **largest** group — and on
a hub-shaped corpus that is structurally the loudest entity, producing the self-refuting hook
*"OpenAI is quietly converging across 7 independent sources"*. A weak signal is *corroborated but
not yet loud*, so group size optimised for the inverse of the definition. This was a specification
defect, not an implementation defect.

### Changed

- **`backend/app/digests/sections.py`** — `coherent_cluster()` keeps the membership rule (shared
  `driver_uid`) and replaces the **selection** rule: among groups clearing the corroboration bar
  (`len(group) >= WEAK_CLUSTER_MIN_ITEMS`, driver not stoplisted), the winner is the driver with the
  **lowest ambient mention count**. Ties break lower mentions → larger group → higher summed
  `graph_score` → lower uid, so selection is deterministic and stable under input order. The chosen
  driver's stats (mentions / distinct sources / group size, and how many groups were eligible) are
  logged at INFO, so the choice is auditable from the run output.
- **`backend/app/scoring/graph_signals.py`** — `GraphSignal` gained `driver_mentions`, the driving
  entity's ambient volume over the convergence window. **No new graph query**: the value already
  came back on `ConvergenceStat.mentions` from the same convergence read and was being discarded.
  `DigestItem` carries it through to the digest layer.
- **`backend/app/core/config.py`** — new `WEAK_DRIVER_STOPLIST` (with `_DEFAULT_WEAK_DRIVER_STOPLIST`
  seeded and commented by class of term: the field itself, model-class nouns, sub-discipline names).
  Generic concept nodes may never *label* a weak signal — they are the category, not an entity
  within it, and the original eight-item incoherent cluster passed precisely by sharing a generic
  "LLM" hub. **Selection only**: nothing is removed from the graph, from scoring, or from any other
  section. Human-editable in config or overridable wholesale via the env var; matched
  case-insensitively on the normalised entity identity (`normalise_entity_name`).

### Verified on the real corpus

`data/dev_corpus.db`, `--days 7`, window reproduced exactly as **2026-07-14 15:06 → 2026-07-21
10:45** (221 events, body 34 / noise 187) via `build_digest_data` directly (D-023 — there is still
no `--now` flag). Graph checked before concluding anything: **2130 nodes / 3666 relationships**, so
no reindex was needed. LLM-free, $0.

**The coherent-cluster path fired**, and the selected driver is **`Firefox`** — 2 ambient mentions,
2 distinct sources, group size 2 — *the quietest of 12 eligible groups out of 30 shared-driver
groups*. `OpenAI` (17 mentions, 12 items) now sorts last; `AI`, `LLM`, `LLMs`, `Large language
models` and `Artificial Intelligence` are excluded as stoplisted concepts. Regenerated hook:

> The AI signal most feeds will miss this week: Firefox is quietly converging across 2 independent
> sources.

Tier disclosure (D-016 D) still fires on all three surfaces (the cluster is `archive`-tier) and
every source URL is preserved. Drafts in `outputs/posts/2026-08-04-*` (git-ignored).

**Finding, not fixed here (D-036):** the winning cluster is coherent and genuinely quiet, but its
second item (a Firefox release-cadence story) is only marginally an AI signal — a corpus-scope
symptom (D-017), not a selection defect.

### Tests

Six new tests in `backend/tests/test_driver_eligibility.py`: `test_quietest_eligible_driver_wins` ·
`test_concept_nodes_are_ineligible_drivers` · `test_min_items_still_enforced` ·
`test_all_candidates_ineligible_degrades_honestly` · `test_driver_selection_is_deterministic` (plus
`test_stoplist_is_configurable_and_seeded`). Backend suite: **187 passed, 1 skipped, 0 failed**
— against a **re-verified** 181-passed baseline measured today on a clean HEAD worktree, not the
recorded number (D-022 / addendum §4).

### Not in this change

Convergence maths, IDF dampening, `GRAPH_MIN_SOURCES` and `graph_signals.py` scoring are untouched —
this changes *which group is chosen*, not how convergence is computed.
`backend/app/scoring/priority.py` untouched (standing ruling, D-014). No entity normalisation: that
is Task 014, and it must merge after this one.

### Defect C — the eligibility floor was too low (attempt 2, 2026-08-04)

**A weak signal now needs enough corroboration to be *real*, not just low ambient volume.**

Attempt 1 shipped the *quietest* objective, and the winner was **`Firefox` — 2 mentions / 2 sources /
2 items**, with three groups tied at that floor and one of its two items carrying no AI content at
all (D-036). The cause is structural, not luck: `GRAPH_MIN_SOURCES` and `WEAK_CLUSTER_MIN_ITEMS` were
both **2**, the lowest values that are not "one", so a *minimiser* bottoms out at the corroboration
floor **by construction**. Firefox was the rule's fixed point. Ruled by [D-047].

- **`backend/app/core/config.py`** — new **`WEAK_DRIVER_MIN_SOURCES`** (default **3**) and
  `WEAK_CLUSTER_MIN_ITEMS` raised **2 → 3**, both env-overridable and commented with *why* 3: two
  sources mentioning something twice is not distinguishable from coincidence.
- **`backend/app/digests/sections.py`** — `coherent_cluster()` gains one filter
  (`_driver_sources(group) >= min_sources`) alongside the existing item-count and stoplist gates.
  The tie-break chain is unchanged. The audit log line now reports the floor in force.
- **`GRAPH_MIN_SOURCES` is deliberately NOT changed.** It is the global floor inside `graph_signals`
  below which a convergence contribution is zeroed; raising it would alter convergence scoring
  product-wide, which D-026 rules out. The new floor is **selection-only** — a 2-source driver still
  *scores* as convergence, it just cannot be the *face* of the weak signal.

#### Verified on the real corpus (LLM-free, $0)

Same method and window as attempt 1 — `build_digest_data(period_days=7, now=2026-07-21 10:45Z)`
(D-023), graph already populated (2130 nodes / 3666 rels), no reindex, no fetch, no spend.
**Winner: `Claude Code` — 5 mentions, 4 distinct sources, 3 items**, the quietest of **5 eligible**
groups out of **30** shared-driver groups. The full eligible set after the floor:

| driver | mentions | sources | items | |
|---|---|---|---|---|
| **Claude Code** | **5** | 4 | 3 | ← selected |
| fine-tuning | 6 | 4 | 4 | |
| Microsoft | 9 | 3 | 7 | |
| Google | 9 | 4 | 7 | |
| OpenAI | 17 | 7 | 12 | sorts last |

`Firefox` (2 sources / 2 items) is now excluded, as are `xAI` and `distribution shift` (too few
items) and the whole `AI` / `LLM` / `LLMs` / `Large language models` / `Artificial Intelligence`
concept family (stoplisted). Regenerated hook:

> The AI signal most feeds will miss this week: Claude Code is quietly converging across 4
> independent sources.

Tier disclosure (D-016 D) fires on all three surfaces; every source URL preserved (0 missing).
Drafts in `outputs/posts/2026-08-04-*` (git-ignored).

**Finding, not fixed here ([D-052]):** two of the three items are substantively about Claude Code;
the third references it once, in passing. All three links are genuine — materially better than
D-036's Firefox item, which had no AI content at all — but whether a passing mention should count
toward the item floor is a **mention-weight** question needing its own ruling.

#### Tests

Three added to `backend/tests/test_driver_eligibility.py`: `test_floor_excludes_thin_evidence_drivers`
(pins the Firefox regression by name, and checks each floor bites on its own) ·
`test_quietest_above_floor_wins` · `test_graph_min_sources_unchanged` — which proves the separation
rather than asserting a constant: a 2-source entity still returns a **positive** contribution from
`graph_signals._contribution`, so convergence scoring is demonstrably unaffected.

Nine existing tests failed on the raised floor because their fixtures were built when 2 items /
2 sources was a valid convergence. They were **raised to the new floor, not exempted from it**
([D-051]) — `test_digest._seed` now seeds three converging developments across three sources, and no
production threshold was lowered to make the suite green. Backend suite: **218 passed, 1 skipped,
0 failed**.

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
