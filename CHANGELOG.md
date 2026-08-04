# Changelog — AI Verkenner

Notable changes per task/milestone. Newest first. History lives in git; this file records *what
changed and why it mattered*, at the granularity of a task file.

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
