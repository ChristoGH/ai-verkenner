# Task 012 (M8 calibration) — Decouple `strategic_potential` from `relevance`

**Status: ✅ CLOSED — ATTEMPT 2 ACCEPTED (2026-08-04, [D-057](../docs/DECISIONS.md)).** Raised by
[D-018](../docs/DECISIONS.md), which corrects D-014.

All six scope points are implemented and the same 45-item sample has been re-measured under each.
**The quadrant is reachable for the first time — `rel ≤ 2 AND sp ≥ 4` went 0 → 2 and
`horizon_signal` is non-zero (2) — but `r` is 0.693, not below 0.5**, the named regression fixture
(event 54, *Inkling*) still missed at `rel 2 / sp 3`, and `relevance` / `actionability` reach 4
nowhere. Three of five acceptance criteria unmet, so the stop condition applies: reported, **not
iterated a third time**. Full numbers, the gap distribution, the 10-item hand spot-check, the cost
and the reading are in [`docs/m8-calibration-notes.md`](../docs/m8-calibration-notes.md); the ruling
needed is [D-056](../docs/DECISIONS.md).

Two things the ruling should weigh: attempt 1's **`relevance` anchors now over-demote** stack-adjacent
items (so part of the quadrant's reachability was bought there, and fixing it would *raise* `r`), and
on this sample **`r` may be the wrong instrument** — it is held up by items that genuinely belong on
the diagonal, while quadrant occupancy and the `sp − rel` gap (0 → 4 items) both moved. The
criterion was **not** changed to fit the result.

Earlier context: [D-045](../docs/DECISIONS.md) corrects D-018's "6 items would become
`horizon_signal`" to **0**; [D-046](../docs/DECISIONS.md) is attempt 1's stop;
[D-049](../docs/DECISIONS.md) authorised scope point 6.

## Goal

Make the `horizon_signal` quadrant reachable by fixing **enrichment scoring**, without touching
`backend/app/scoring/priority.py`.

## Context — the measured defect

`horizon_signal` requires `strategic_potential >= relevance + 2`. Measured across the 246-item
corpus (D-018):

- **r(relevance, strategic_potential) = 0.842.**
- `strategic_potential` **never exceeds `relevance + 1`** except for **one item in 246**.
- Max relevance 4 (one item); max `strategic_potential` 4 (seven items); `actionability` never
  exceeds 3; mean relevance 1.2.

The quadrant is therefore **structurally unreachable** — not because the threshold is wrong, but
because the LLM scores `strategic_potential` as a near-copy of `relevance`. D-014 called this
top-of-scale compression; that is real but secondary. The primary defect is **collinearity**.

The likely cause, `prompts/classify_item.md:56-58`:

> "Score honestly; when unsure, prefer the lower end of relevance and the higher end of hype (i.e.
> assume noise until shown otherwise)."

A blanket downward tiebreaker on relevance, applied every time. The only decoupling instruction is
one clause on line 31-32 — *"independent of today's relevance"* — with no anchors and no example.
The same text is mirrored in `backend/app/enrichment/fallback.py:25`.

## Scope — `prompts/classify_item.md` only

1. **Narrow the tiebreaker to hype.** Keep "assume noise until shown otherwise" for `hype`; remove
   the blanket downward pull on `relevance`.
2. **Add 0–5 anchors per axis**, including explicitly what a 4 and a 5 look like. Anchors must be
   concrete enough to be applied consistently across items.
3. **Add an explicit decoupling instruction**: score `strategic_potential` independently of, and
   before, `relevance`. State plainly that an item can be `relevance 0–1` **and**
   `strategic_potential 4–5` — that combination is the product's whole point (the quiet thing that
   matters later), not an error.
4. **Add one worked few-shot example** of a low-relevance / high-strategic item, with the reasoning
   made explicit.
5. Mirror any wording change into `backend/app/enrichment/fallback.py:25` so the two do not drift.
6. **Re-frame `strategic_potential`'s frame of reference** (ADDED 2026-08-04 by
   [D-049](../docs/DECISIONS.md), after attempt 1 hit the stop condition).

   Attempt 1 implemented points 1–5 and `r` fell only 0.889 → 0.749. The measured cause is deeper
   than D-018's tiebreaker: **`strategic_potential`'s own anchors are conditioned on the user's
   current stack** — a 3 is "a credible alternative to something already in the stack", a 4 is a
   shift "in an area they build in". That is precisely what `relevance` measures, so the two axes
   are collinear **by definition** and no tiebreaker rewrite can reach it.

   Redefine `strategic_potential` against **the shape of the problem space Christo works in** —
   agentic pipelines, retrieval and knowledge graphs, evaluation and traceability, trust-sensitive
   domains — **not** the contents of his current stack. An item can be irrelevant to today's code and
   still reshape the problem within a year; that combination is the product's entire purpose.

   **Regression fixture:** event 54 (Inkling — open-weights 975B under Apache-2.0), scored
   `rel 2 / sp 3` in attempt 1, is the textbook quadrant item and should land at `rel 1–2 / sp 4–5`.

## Non-goals

- **`backend/app/scoring/priority.py` is untouchable** (standing ruling, D-014). No threshold change.
- No change to the five axes, their names, ranges, or the hype inversion.
- No change to `HORIZON_CLASSES`, ranking, or the digest sections.
- Do not re-enrich the whole corpus without a cost decision from Christo first.

## Acceptance criteria

- A/B on a **held-out sample of ≥40 items** re-enriched under the new prompt, compared to their
  existing scores:
  - ~~**r(relevance, strategic_potential) drops below 0.5.**~~ **AMENDED by
    [D-057](../docs/DECISIONS.md) — `r` is now a REPORTED DIAGNOSTIC, not a gate.** It is a
    population statistic and was being used to measure a tail property; ~33 of the 45 sampled items
    genuinely belong on the diagonal, so forcing population `r` down would make the scores *less*
    truthful. Report it; do not gate on it.
  - **GATE: quadrant occupancy — at least one item at `relevance <= 2 AND strategic_potential >= 4`.**
    (Attempt 2: **2**. ✅)
  - **GATE: at least three items at `strategic_potential >= relevance + 2`.** (Attempt 2: **4**. ✅)
  - ~~`relevance` and `actionability` each reach ≥4 on at least one item.~~ **Carried to
    [Task 015](015-relevance-anchor-recalibration.md)** — attempt 2 showed the relevance anchors now
    over-demote, which is a separate defect on a separate axis.
  - ~~Event 54 (Inkling) lands in the quadrant.~~ **DROPPED as a hard criterion (D-057)** — its
    "correct" score was asserted without hand-verification; a 3-vs-4 disagreement on one item is not
    evidence of failure.
- Scores remain defensible per item — spot-check 10 by hand; calibration must not become inflation.
- The hype inversion is unchanged and still correct on every sampled item.
- Cost of the sample run recorded in the session notes.

## Test plan

- `test_classify_template_renders` — the template still renders with all required inputs.
- `test_fallback_wording_matches_template` — pins the mirror so the two cannot drift.
- Calibration measurement is a **script + recorded run**, not a unit test — LLM output is not
  deterministic. Commit the measurement script and its output under `docs/m8-calibration-notes.md`.

## Files likely to change

`prompts/classify_item.md` · `backend/app/enrichment/fallback.py` ·
`docs/m8-calibration-notes.md` (new) · `backend/tests/`

---

## Agent prompt (paste-ready)

```
Read HANDOFF.md, then CLAUDE.md, then docs/DECISIONS.md entry D-018, then
tasks/012-enrichment-score-calibration.md. All binding.

GOAL: make the horizon_signal quadrant reachable by fixing the ENRICHMENT PROMPT.
backend/app/scoring/priority.py is UNTOUCHABLE — standing ruling, D-014. Any change
to it fails this task outright.

MEASURED FACTS (verified, do not re-derive):
- r(relevance, strategic_potential) = 0.842 across 246 items.
- strategic_potential never exceeds relevance + 1, except one item in 246.
- horizon_signal needs strategic_potential >= relevance + 2, so it is structurally
  unreachable. The rule is correct; the scores are the problem.
- prompts/classify_item.md:56-58 applies a blanket downward tiebreaker on relevance.
- backend/app/enrichment/fallback.py:25 mirrors the same wording.

WORK: edit prompts/classify_item.md per the task file's five scope points — narrow the
tiebreaker to hype only, add 0-5 anchors per axis, add an explicit decoupling
instruction, add one worked low-relevance/high-strategic example, mirror into
fallback.py.

THEN MEASURE. Re-enrich a held-out sample of >= 40 items under the new prompt and
compare to their existing scores. Report: new r(relevance, strategic_potential), the
per-axis min/max, and how many items now qualify for horizon_signal. Commit the
measurement script and its raw output to docs/m8-calibration-notes.md.

COST GATE: the sample run is billable. Run the >= 40 item sample, and STOP THERE.
Do NOT re-enrich the full 246-item corpus — that needs Christo's cost decision.

CONSTRAINTS
- No new axes, no renaming, no change to the hype inversion (0 = signal, 5 = noise).
- Calibration must not become inflation. Spot-check 10 items by hand and paste your
  reasoning; if scores look inflated rather than better-spread, say so plainly.
- Secrets are env-injected by direnv. Never read, print or log a key value.

ACCEPTANCE: r below 0.5 on the sample; at least one item at relevance <= 2 AND
strategic_potential >= 4; relevance and actionability each reach >= 4 somewhere; full
backend suite green.

STOP CONDITION: if r does NOT drop below 0.5 after the prompt rewrite, STOP and report
with the numbers. Do not iterate the prompt more than twice without checking in — a
third attempt means the hypothesis is wrong and the cause is elsewhere.

Append D-NNN entries to docs/DECISIONS.md for every unasked choice; overwrite
HANDOFF.md at session end.
```

---

## Agent prompt — ATTEMPT 2 (scope point 6) · paste-ready

```
Read HANDOFF.md, then CLAUDE.md, then docs/AGENT_ADDENDUM.md, then
docs/m8-calibration-notes.md, then docs/DECISIONS.md entries D-045, D-046 and D-049,
then tasks/012-enrichment-score-calibration.md. All binding.

Attempt 1's work (scope points 1-5) is ACCEPTED and stays. The stop condition fired
correctly and your diagnosis was right. Implement SCOPE POINT 6 ONLY.

THE DIAGNOSIS YOU ESTABLISHED, NOW AUTHORISED AS THE FIX (D-049)
strategic_potential's anchors are conditioned on the user's CURRENT STACK — a 3 is
"a credible alternative to something already in the stack", a 4 is a shift "in an area
they build in". That is what relevance measures. The axes are collinear BY DEFINITION,
which is why r only moved 0.889 -> 0.749 and no item reached rel <= 2 AND sp >= 4.

WORK: redefine strategic_potential in prompts/classify_item.md against THE SHAPE OF THE
PROBLEM SPACE Christo works in — agentic pipelines, retrieval and knowledge graphs,
evaluation and traceability, trust-sensitive domains — NOT the contents of his current
stack. Rewrite its 0-5 anchors on that basis. Make explicit that an item can be
irrelevant to today's code and still reshape the problem within a year, and that this
combination is the product's entire purpose, not an error. Mirror into fallback.py;
keep the pinning test green.

REGRESSION FIXTURE: event 54 (Inkling, open-weights 975B under Apache-2.0) scored
rel 2 / sp 3 in attempt 1. It is the textbook quadrant item and should land at
rel 1-2 / sp 4-5. Pin it.

MEASURE: re-run the sample. Use THE SAME 45 ITEMS as attempt 1 so the comparison is
clean, and say so. Report r, per-axis min/max, quadrant-qualifying count, and the
event-54 result. Append to docs/m8-calibration-notes.md — do not overwrite attempt 1's
numbers; both runs stay on the record.

COST GATE: ~$1.40 for the sample is APPROVED. Do NOT re-enrich the full 246-item
corpus — that is still a separate decision.

CONSTRAINTS
- No new axes, no renaming, no re-ranging, no change to the hype inversion.
- priority.py UNTOUCHABLE (D-014).
- Calibration must not become inflation. Hand spot-check 10 items and paste the
  reasoning; if the spread looks bought with inflation, say so plainly.
- Keep flagging sampling artefacts as you did in attempt 1 — the stratification caveat
  was correct and material.

ACCEPTANCE: r < 0.5 on the sample; >= 1 item at rel <= 2 AND sp >= 4; relevance and
actionability each reach >= 4 somewhere; event 54 in the quadrant; suite green
(re-verify the baseline yourself — the tree holds several sessions' interleaved work).

STOP CONDITION UNCHANGED: if r still does not clear 0.5, STOP and report. Do not
iterate a third time. At that point the hypothesis is exhausted and the next move is
Christo's — the honest answer may be that the quadrant needs a threshold conversation
that D-014's standing ruling currently forbids.

Coordinate decision numbers before appending to docs/DECISIONS.md — concurrent sessions
have already collided once (D-028..D-036). Highest currently in the log is D-049. Merge
your status into HANDOFF.md rather than overwriting other sessions' entries.
```
