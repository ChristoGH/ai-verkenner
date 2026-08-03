# Task 012 (M8 calibration) — Decouple `strategic_potential` from `relevance`

**Status: NOT STARTED** — raised by [D-018](../docs/DECISIONS.md), which corrects D-014.

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

## Non-goals

- **`backend/app/scoring/priority.py` is untouchable** (standing ruling, D-014). No threshold change.
- No change to the five axes, their names, ranges, or the hype inversion.
- No change to `HORIZON_CLASSES`, ranking, or the digest sections.
- Do not re-enrich the whole corpus without a cost decision from Christo first.

## Acceptance criteria

- A/B on a **held-out sample of ≥40 items** re-enriched under the new prompt, compared to their
  existing scores:
  - **r(relevance, strategic_potential) drops below 0.5.**
  - At least one item lands at `relevance <= 2 AND strategic_potential >= 4` — i.e. the quadrant is
    demonstrably reachable.
  - `relevance` and `actionability` each reach ≥4 on at least one item (top of scale in use).
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
