# Task 016 — Mention weight: a passing reference is not participation

**Status: NOT STARTED** — authorised by [D-057](../docs/DECISIONS.md).

## Why now (the three-use-case threshold)

`CLAUDE.md` says **no abstraction before three real use cases**. This is the third:

1. **The original M7.5 8-item cluster** — items admitted on a shared generic "LLM" hub, each merely
   mentioning the category.
2. **[D-036](../docs/DECISIONS.md), Firefox** — one of two cluster items was a Mozilla release-cadence
   story with **no AI content at all**.
3. **[D-052](../docs/DECISIONS.md), Claude Code** — two of three items are substantively about it;
   the third, The Register's NextBSD revival story, **references it once, in passing**.

Each was individually deferred as "corpus scope, not selection" and each was a reasonable deferral in
isolation. Three occurrences is the pattern, and it is the same pattern every time: **an entity
mention is counted as if it were an entity's development.** The floor from Task 013 makes clusters
big enough to be real; it cannot tell whether the items are *about* the driver.

## Goal

An item counts toward a driver's cluster only if the driver is **substantively present**, not merely
named.

## Context

`GraphSignal.driver` and the convergence read count **mentions** — every extracted entity occurrence
is worth the same. So a 2,000-word analysis of Claude Code and a BSD retrospective that name-checks it
once contribute equally to the cluster and to the "N independent sources" claim on the draft.

That number is the load-bearing claim of the whole Weak Signal piece. If one of its four sources only
mentioned the subject in passing, the claim is inflated in exactly the way the M7.5 review was
convened to stop.

## Scope

- A **weight** on each entity–item link, distinguishing *substantive* from *passing* presence. Start
  with the cheapest signal that works, in this order of preference:
  1. mention **count within the item** (a driver named once in a long body is passing; named
     repeatedly is substantive);
  2. presence in **title or lead** versus body-only;
  3. the enrichment output already available — the item's `category` and `tags`.
  Do **not** add an LLM call for this without a separate cost decision.
- A threshold (`CLUSTER_MEMBER_MIN_WEIGHT`) below which an item is **excluded from cluster
  membership** — it stays in the corpus, in the graph, and in every other section. This is a
  membership filter, exactly like Task 013's stoplist is a selection filter.
- The `N independent sources` count must be computed **after** weighting, so the published number
  counts only sources that substantively covered the driver.
- Report, for the selected cluster, each item's weight and why it qualified — the claim must be
  auditable from the run output.

## Non-goals

- **No topicality gate.** "Is this about AI at all" is a different question, belongs to the source
  registry (Task 011, largely done) and the classifier, and is explicitly out of scope here.
- No new LLM calls, no embeddings, no re-enrichment.
- No change to convergence maths, `GRAPH_MIN_SOURCES`, IDF dampening, Task 013's floors or stoplist,
  or `priority.py` (D-014).
- Items excluded by weight are **not** deleted from anything. Membership only.

## Acceptance criteria

- Replaying 2026-07-14 → 07-21: the NextBSD item (D-052) does **not** count toward the `Claude Code`
  cluster, and the Mozilla release item (D-036) does **not** count toward `Firefox`.
- Both remain present in the corpus, the graph, and the noise/other digest sections — verify
  explicitly, do not assume.
- The published "N independent sources" for the selected cluster reflects the post-weighting count.
- If weighting drops a cluster below Task 013's floors, the honest degradation path fires. **That is
  a correct outcome** — a smaller true claim beats a larger inflated one.
- Every source URL preserved (URL invariant).
- Suite green — re-verify the baseline yourself (D-022).

## Test plan

- `test_passing_mention_excluded_from_cluster` — an item naming the driver once, body-only, is not a
  member; pins D-052's NextBSD case by name.
- `test_substantive_mention_included` — title/lead or repeated mention qualifies.
- `test_excluded_item_remains_in_corpus_and_graph` — exclusion is membership-only; the item is still
  present elsewhere.
- `test_source_count_computed_after_weighting` — the published claim uses the filtered set.
- `test_weighting_can_drop_cluster_below_floor` — falling under Task 013's floor degrades honestly
  rather than back-filling with weak members.

## Files likely to change

`backend/app/scoring/graph_signals.py` · `backend/app/digests/sections.py` ·
`backend/app/core/config.py` · `backend/tests/`

---

## Agent prompt (paste-ready)

```
Read HANDOFF.md, then CLAUDE.md, then docs/AGENT_ADDENDUM.md, then docs/DECISIONS.md
entries D-036, D-052 and D-057, then tasks/016-mention-weight.md. All binding.

WHY THIS EXISTS: three separate clusters have now been polluted by items that merely
NAME the driving entity rather than being about it — the original 8-item "LLM" cluster,
Firefox's Mozilla release story (no AI content at all, D-036), and Claude Code's NextBSD
retrospective (one passing reference, D-052). Each was deferred individually; three is
the pattern, and CLAUDE.md's "no abstraction before three real use cases" threshold is
now met.

THE DEFECT: the convergence read counts MENTIONS, all weighted equally. A 2,000-word
analysis and a one-line name-check contribute the same amount to a cluster and to the
"N independent sources" claim printed on the draft. That number is the load-bearing
claim of the entire Weak Signal piece.

IMPLEMENT
- A weight per entity-item link separating SUBSTANTIVE from PASSING presence. Use the
  cheapest signal that works, in this preference order: (1) mention count within the
  item, (2) title/lead presence vs body-only, (3) the existing enrichment category and
  tags. DO NOT add an LLM call — that needs a separate cost decision.
- CLUSTER_MEMBER_MIN_WEIGHT: below it, an item is excluded from CLUSTER MEMBERSHIP only.
  It stays in the corpus, the graph, and every other digest section. This is a
  membership filter exactly as task 013's stoplist is a selection filter.
- Compute "N independent sources" AFTER weighting, so the published number counts only
  sources that substantively covered the driver.
- Log each selected-cluster item's weight and why it qualified — the claim must be
  auditable from the run output.

HARD CONSTRAINTS
- NO topicality gate. "Is this about AI at all" is a different question owned by the
  source registry and the classifier. Out of scope here — do not drift into it.
- No new LLM calls, no embeddings, no re-enrichment.
- No change to convergence maths, GRAPH_MIN_SOURCES, IDF dampening, task 013's floors
  or stoplist, or priority.py (D-014).
- Nothing is deleted from the corpus or the graph. Membership only.

TESTS: the five named in the task file, with the NextBSD and Mozilla cases pinned by
name so these specific regressions cannot return.

VERIFY ON REAL DATA
No --now flag exists (D-023); reproduce the window via build_digest_data directly,
period_days=7, now=2026-07-21 10:45Z, as the prior sessions did. Confirm explicitly
that the excluded items are STILL PRESENT in the corpus and graph — do not assume it.
Report the selected cluster with per-item weights and the post-weighting source count.

ACCEPTANCE
- NextBSD does not count toward Claude Code; the Mozilla item does not count toward
  Firefox; both still exist everywhere else.
- Published source count reflects post-weighting membership.
- Suite green — re-verify the baseline yourself (D-022).

STOP CONDITIONS
- If weighting drops the cluster below task 013's floors, that is a CORRECT result.
  Ship the honest degradation. A smaller true claim beats a larger inflated one. Do NOT
  lower CLUSTER_MEMBER_MIN_WEIGHT or task 013's floors to keep a cluster alive.
- If no cheap signal separates substantive from passing on the real data, STOP and
  report rather than reaching for an LLM call.

Check the highest D-NNN in docs/DECISIONS.md before appending. Merge into HANDOFF.md
rather than overwriting other sessions' entries.
```
