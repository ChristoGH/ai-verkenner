# Task 018 — Source portfolio rebalance: the corpus does not cover the user it is for

**Status: NOT STARTED.** Raised by a measured hit-rate audit of the 436-item corpus (2026-08-19).

> **GATED. Do not start this until `GITHUB_TOKEN` is set and one full `run` has completed with all
> 26 enabled sources live.** Seven of the twenty-six are currently dark for want of a token, and they
> are precisely the curated, high-precision ones. Rebalancing a registry while a quarter of it has
> never fetched would be optimising against an instrument that is switched off.

## Goal

The corpus contains a materially higher proportion of items that touch the stack
`docs/USER_CONTEXT.md` names, at the same or lower fetch volume.

## Context — the measurement

Measured 2026-08-19 over all 436 raw items in `data/dev_corpus.db` by whole-word, separator-tolerant
matching of the technologies `USER_CONTEXT.md` lists under **Active work** and **Strong relevance
signals**. String matching only — no LLM, no embeddings — deliberately dumber than enrichment so it
can act as an **external** check on it (`CLAUDE.md`: the maker is not the checker).

**Corpus-wide: 29 of 436 items (6.7%) name a listed technology unambiguously.** A further 50 (11.5%)
match only an ambiguous term (`RAG`, `AKS`, `Claude`, `React`, `STT`, `SQLite`, `agentic`,
`embeddings`) and are reported separately rather than folded into the headline — `AKS` matching
"breaks" is exactly how a hit rate lies.

| source | items | unambiguous hits | rate |
|---|---:|---:|---:|
| arXiv cs.CL | 58 | 1 | 2% |
| arXiv cs.AI | 50 | 2 | 4% |
| arXiv cs.LG | 50 | 1 | 2% |
| The Register (site-wide, replaced) | 53 | 0 | **0%** |
| The Register — AI/ML (replacement) | 3 | 0 | 0% |
| OpenAI Blog | 22 | 0 | **0%** |
| MIT Technology Review (both feeds) | 17 | 0 | 0% |
| New repos under topic:rag | 13 | 0 | 0% |
| GitHub Blog | 11 | 0 | 0% |
| LangChain Blog | 7 | 0 | **0%** |
| Hacker News (front page) | 24 | 2 | 8% |
| Hacker News (AI/LLM, ≥100 pts) | 20 | 1 | 5% |
| Ars Technica AI | 37 | 4 | 11% |
| Simon Willison's Weblog | 44 | 8 | **18%** |
| VentureBeat AI | 5 | 5 | **100%** |
| FastAPI Releases | 2 | 2 | **100%** |
| Qdrant Releases | 1 | 1 | **100%** |
| Cursor Changelog | 2 | 1 | 50% |

**Three findings, in order of consequence:**

1. **arXiv is 158 items — 36% of the corpus — and yields 4 hits.** Broad category feeds
   (`cat:cs.AI`, `cat:cs.CL`, `cat:cs.LG`) are the single largest volume-to-signal mismatch in the
   registry. They are not *wrong*: they are unfiltered. The question this task must answer is
   whether a **narrowed arXiv query** recovers the signal, or whether arXiv belongs on a different
   cadence from news sources.
2. **The Register contributes 56 items and zero hits, across both feeds.** Task 011 already replaced
   the site-wide feed with the AI/ML one (D-017); the replacement has fetched 3 items and hit none.
   The swap fixed the volume, not the relevance.
3. **The highest-precision sources are the smallest.** VentureBeat AI (5/5), FastAPI Releases (2/2),
   Qdrant Releases (1/1) and Simon Willison (8/44, the best volume source) together produce more
   hits than 158 arXiv items. VentureBeat's last fetch returned **zero new** — a 100%-precision
   source that is currently contributing nothing needs its cadence understood before conclusions.

**Mean `relevance` on unambiguous hits is 2.26 against 1.20 corpus-wide** — so enrichment *does*
separate the user's stack by roughly 2×, even scored against the 309-character stub. **The binding
constraint is not scoring. It is that there is little in the corpus to find.** That is the whole
argument for this task and it is why it follows task 017 rather than preceding it: until the context
was wired, "the corpus is thin" and "the scorer is blind" were indistinguishable.

## Scope

1. **Adopt the measurement as a committed instrument.** `backend/scripts/hit_rate.py` — the script
   the numbers above came from. It must be re-runnable against any corpus and any window so the
   before/after is reproducible, not a one-off analysis.
2. **Re-measure with all 26 sources live** (the gate above). Report the table again. The seven
   `github_*` sources are curated by construction — watched topics, watched packages, own-stack
   advisories — so the prior is that they score far above 6.7%. **If they do not, that is the more
   interesting finding** and it reopens ADR 0002's premise rather than this task's.
3. **Propose registry changes, each with its measured justification**, as edits to
   `sources/sources.yaml` with a dated comment in the style the file already uses. Candidates the
   data supports: narrowing the arXiv queries from bare categories; disabling or re-scoping The
   Register; understanding VentureBeat's cadence before acting on 5 items; adding sources in the
   named gaps — **Qdrant, Neo4j, Anthropic engineering, pgvector/Lakebase, tree-sitter, Knative** —
   which `USER_CONTEXT.md` calls strong signals and which no current source covers.
4. **Report fetch volume against hit yield per source**, so the trade is visible: a source that
   costs 158 fetches for 4 hits is a different proposition from one that costs 5 for 5.

## Non-goals

- **No broad crawler.** The registry stays a curated editorial act (`CLAUDE.md`, project brief §3).
  A source is added because it is trusted, not because it is prolific.
- **No scoring, prompt, or enrichment change.** This task moves *what enters the corpus*. Confounding
  intake with interpretation is what task 015 did and D-062 reverted.
- `backend/app/scoring/priority.py` untouchable (D-014).
- **No auto-disabling.** `sources --health` surfaces; humans decide. Disabling a source is an
  editorial act with a dated comment, exactly as D-017 did it.
- No re-enrichment. Hit rate is string matching over text already stored; it costs nothing.

## Acceptance criteria

- `hit_rate.py` committed, runnable against an arbitrary corpus and `--since` window, with the
  ambiguous-term tier reported separately from the headline number.
- The full table re-measured with all 26 sources live, published in `docs/` alongside the
  2026-08-19 baseline so the change is attributable.
- Every proposed registry change carries its measured justification and a dated comment in
  `sources.yaml`.
- **At least one new source proposed for each of the uncovered strong signals** named in scope 3, or
  a statement that no trustworthy feed exists for it — which is itself a finding worth recording.
- **A stated, falsifiable prediction** of the post-change hit rate, made before the change lands.
- The measurement is honest about its own limits: it cannot see an item that is *about* a listed
  technology without naming it. Report the false-negative risk; do not claim the number is truth.

## Test plan

- `test_hit_rate_whole_word` — `AKS` does not match "breaks"; `RAG` does not match "drag".
- `test_hit_rate_separator_tolerant` — `tree-sitter` ≡ `tree sitter` ≡ `treesitter`.
- `test_ambiguous_terms_reported_separately` — an ambiguous-only item never counts in the headline.
- `test_hit_rate_window` — `--since` filters on `published_at`, not `created_at`.

## Files likely to change

`backend/scripts/hit_rate.py` (new) · `sources/sources.yaml` · `backend/tests/` ·
`docs/` (the measurement record) · `CHANGELOG.md` · `docs/DECISIONS.md`

## What happens after this

The fresh-ingest hit rate becomes a **standing metric**, not a one-off audit — the honest answer to
"is AI Verkenner working?" is not how many items it ingests but what fraction of them touch the work
of the one person it is for.
