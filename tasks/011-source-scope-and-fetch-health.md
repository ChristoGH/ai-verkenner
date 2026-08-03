# Task 011 — Source scope correction + fetch-health surfacing

**Status: NOT STARTED** — raised by [D-017](../docs/DECISIONS.md) (source registry audit, 2026-08-03).

Two defects found in the same audit. Both are cheap; together they remove ~7% of corpus noise and
close a fail-safe blind spot.

## Goal

Every enabled source is either AI-scoped or knowingly whole-publication, and a source that yields
zero items is **visible**, not silent.

---

## Defect 1 — Three whole-publication feeds dilute the corpus

**Evidence (D-017):** 19 of 266 raw items (7%) are plainly off-topic. Every one traces to one of
three site-wide feeds. Zero off-topic items came from a topic-filtered feed. Title-level AI-term
density: Register 22%, HN 33%, MIT TR 63% — versus 69% for the scoped Ars `/ai/` feed.

Observed off-topic examples: *"There's a lot of hype around perimenopause. Don't buy it."* (MIT TR,
the item that reached the published Noise Report) · *"Why heat pumps are still so hot in the US"*
(MIT TR) · *"Viking 1 landed on Mars 50 years ago"* (Register) · *"Ransomware curdles production at
Coca-Cola's Fairlife dairy biz"* (Register) · *"A Koi Pond Mosaic Made from 10 Pounds of 3D Printer
Waste"* (HN).

### Scope — exact edits to `sources/sources.yaml`

**1. The Register** — replace:

```yaml
  - name: The Register
    source_type: rss
    url: https://www.theregister.com/headlines.atom
    enabled: true
    trust_level: medium
```

with:

```yaml
  - name: The Register — AI/ML
    source_type: rss
    url: https://www.theregister.com/software/ai_ml/headlines.atom
    enabled: true
    trust_level: medium
```

**2. MIT Technology Review** — replace:

```yaml
  - name: MIT Technology Review
    source_type: rss
    url: https://www.technologyreview.com/feed/
    enabled: true
    trust_level: high
```

with:

```yaml
  - name: MIT Technology Review — AI
    source_type: rss
    url: https://www.technologyreview.com/topic/artificial-intelligence/feed/
    enabled: true
    trust_level: high
```

**3. Hacker News** — replace:

```yaml
  - name: Hacker News (front page)
    source_type: rss
    url: https://hnrss.org/frontpage
    enabled: true
    trust_level: low
```

with:

```yaml
  - name: Hacker News (AI/LLM, ≥100 points)
    source_type: rss
    url: https://hnrss.org/newest?q=AI+OR+LLM+OR+GPT+OR+%22machine+learning%22&points=100
    enabled: true
    trust_level: low
```

**Verify each replacement URL returns a well-formed feed before committing.** If one 404s or returns
an empty feed, STOP and report — do not silently revert to the site-wide URL.

### Non-goals

- No change to enrichment, scoring, or `classify_item.md` (topicality at the *classifier* level is
  Task 012's concern, deliberately separate).
- No new sources. No change to `trust_level` semantics.
- Do **not** retro-delete the 19 off-topic items already in the corpus — they are historical fact and
  the URL invariant applies. They age out of the digest window naturally.

### Acceptance criteria

- The three sources are AI-scoped; renamed so the dashboard shows the narrower scope.
- A fetch against each new URL returns ≥1 item.
- No other registry entry is modified.

---

## Defect 2 — Eight enabled sources yield nothing, silently

**Evidence (D-017):** these enabled sources contributed **0 rows** to a 266-item corpus —
Anthropic News (its `url` points at an HTML page, `https://www.anthropic.com/news`, not a feed),
LangChain Blog, LlamaIndex Releases, Neo4j Releases, Eugene Yan, `github_star_velocity`,
`github_advisories`, `github_changes`.

This is a **fail-safe-isolation gap**. `CLAUDE.md` requires one bad source never to break a run —
correct, and it works. But a source that *never* yields must not be invisible: the registry claims
coverage the corpus does not have, which is a silent correctness failure in an early-warning system.

### Scope

- Per-source fetch outcome recorded per run: items fetched, new, skipped, and error (if any).
- `python -m app.cli sources --health` prints one line per enabled source: last successful fetch,
  items last run, consecutive zero-yield runs.
- A source with **zero yield across N consecutive runs** (`SOURCE_ZERO_YIELD_WARN`, default 3) is
  reported loudly at the end of every run — non-fatal, never aborts.
- Fix the Anthropic News entry: point it at an actual feed, or set `enabled: false` with an inline
  comment saying why. Do not leave a URL that cannot parse.
- Investigate the other seven and either fix the URL or disable with a reason. The three `github_*`
  ones may simply need `GITHUB_TOKEN` — if so, say so in the health output rather than reporting
  them as broken.

### Non-goals

- No retries, no backoff, no circuit breaker, no scheduling. Reporting only.
- Do not auto-disable a source. Surfacing is the whole job; the human decides.

### Acceptance criteria

- `sources --health` lists every enabled source with its last outcome.
- A source yielding 0 for ≥3 consecutive runs is flagged in the run summary.
- A fetch failure still never aborts the run (existing invariant, add a regression test).
- Every one of the eight sources is either fixed or explicitly disabled with a stated reason.

### Test plan

- `test_zero_yield_source_is_flagged_not_fatal`
- `test_fetch_error_isolated_run_continues` (pins the existing invariant)
- `test_health_lists_all_enabled_sources`
- `test_github_sources_report_missing_token_distinctly` — a missing token reads as "needs
  `GITHUB_TOKEN`", not "broken feed".

## Files likely to change

`sources/sources.yaml` · `backend/app/ingestion/` · `backend/app/cli.py` ·
`backend/app/core/config.py` · `backend/tests/`

---

## Agent prompt (paste-ready)

```
Read HANDOFF.md, then CLAUDE.md, then tasks/011-source-scope-and-fetch-health.md.
All binding.

Implement BOTH defects in this task file. They are small and related.

DEFECT 1 is a pure sources/sources.yaml edit — the three replacement blocks are given
verbatim in the task file. Apply them exactly. BEFORE committing, fetch each new URL
once and confirm it returns a well-formed feed with >= 1 entry. If any URL 404s or
returns empty, STOP and report — do NOT fall back to the site-wide URL.

DEFECT 2 adds per-source fetch-outcome reporting and a `sources --health` CLI view.
Reporting ONLY: no retries, no backoff, no circuit breaker, no auto-disable. A source
that yields zero across SOURCE_ZERO_YIELD_WARN (default 3) consecutive runs is flagged
loudly in the run summary and never aborts the run.

Then resolve all eight zero-yield sources listed in the task file: fix the URL or set
enabled: false WITH an inline reason. Anthropic News currently points at an HTML page,
not a feed. The three github_* sources may just need GITHUB_TOKEN — if so, the health
output must say that distinctly rather than calling them broken.

HARD CONSTRAINTS
- Do not touch enrichment, scoring, priority.py, or prompts/classify_item.md.
- Do not delete or rewrite existing corpus rows (URL invariant; they age out).
- Do not add new sources.
- Never print or log a secret value. Names only. GITHUB_TOKEN is env-injected by
  direnv — if missing, follow ~/.config/secrets/README.md, do not work around it.

TESTS: the four named in the task file.

ACCEPTANCE: full backend suite green (baseline 174 passed / 1 skipped / 0 failed) plus
the new tests; `sources --health` output pasted into the session report; every one of
the eight sources fixed or disabled-with-reason.

Append a D-NNN entry to docs/DECISIONS.md for every choice made without asking, and
overwrite HANDOFF.md at session end (CLAUDE.md session protocol).
```
