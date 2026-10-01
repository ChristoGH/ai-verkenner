# Task 015 — `relevance` anchors over-demote: the top of the scale is unreachable

**Status: RUN ONCE — CRITERIA UNMET, TASK 012 GATES LOST, CHANGE REVERTED** ([D-062](../docs/DECISIONS.md)).
Raised by Task 012 attempt 2, authorised by [D-057](../docs/DECISIONS.md).

The anchors were rewritten per scope points 1–4 and one 45-item sample was run on the same items
(identity verified before spending). Result: `relevance ≥ 4` **0**, `actionability ≥ 4` **0**, and
**both Task 012 gates lost** — quadrant occupancy 2 → **0**, `sp ≥ rel + 2` 4 → **2**. Per this
file's own acceptance rule the change was **not shipped**: `prompts/classify_item.md` and
`fallback.py` are back at their committed attempt-2 state.

**The anchors were not the binding constraint.** They worked as written and correctly returned "no"
on all 45 items, because the `user_context` actually sent is the **309-character default in
`config.py`** — *"…and a cloud LLM"* — which names no products. `docs/USER_CONTEXT.md`, which the
repo itself calls the ground truth for `relevance` and which lists "Claude / Anthropic model + Agent
SDK releases" as a strong signal, **is not wired into the runtime**. Full numbers, the 10-item hand
spot-check, the preserved anchor text and the recommended next move are in
[`docs/m8-calibration-notes.md`](../docs/m8-calibration-notes.md) § Task 015. Cost **$1.73** vs
~$1.60 approved ([D-063](../docs/DECISIONS.md)).

**Do not re-run this task as written.** The next experiment is configuration, not prompting — see
D-062.

**Not a third iteration of Task 012.** Task 012 is closed: it set out to decouple
`strategic_potential` from `relevance` and it succeeded — the `horizon_signal` quadrant is reachable
for the first time. This is a **different defect on a different axis**, discovered *by* that work.

## Goal

`relevance` uses its full 0–5 range, so that genuinely urgent items are distinguishable from merely
useful ones — without giving back the `strategic_potential` decoupling Task 012 bought.

## Context — the measured defect

Task 012 attempt 1 removed the blanket downward tiebreaker on `relevance` and rewrote its anchors.
The tiebreaker fix was right; the anchors over-corrected. Measured across the same 45-item sample:

| | Before | Attempt 1 | Attempt 2 |
|---|---|---|---|
| items at `relevance >= 4` | 1 | 0 | **0** |
| items at `actionability >= 4` | 0 | 0 | **0** |

Three items (events 1, 103, 228) each **lost a relevance point** between the original scoring and
attempt 1. So part of the quadrant's new reachability was bought by **under-scoring relevance**
rather than by lifting `strategic_potential` — the gap widened partly from the wrong end.

Two consequences, both bad:

1. **`immediate_priority` is now nearly unreachable.** `priority.py` needs `relevance >= 5`, or
   `relevance >= 4 AND strategic_potential >= 3`. With max relevance 0 across 45 items, the top
   priority class is as structurally starved as `horizon_signal` was — the same failure D-018
   diagnosed, moved to the other end of the scale.
2. **The corpus cannot say "act on this today".** For an early-warning product, an axis that never
   fires at the top is not measuring urgency.

## Scope — `prompts/classify_item.md` only

1. **Rewrite the `relevance` 4 and 5 anchors** so they are reachable by items that genuinely warrant
   them. A 5 must mean something a real week can contain — a breaking change to something in the
   stack, a security issue with a live exploit path, a deprecation with a dated cutoff. A 4 must not
   require the item to be about the user's exact current file.
2. **Do the same for `actionability`**, which has never exceeded 3 in any run. Define what a 4 and a
   5 look like concretely — an item with a documented migration path, a patch to apply, a config to
   change.
3. **Protect the Task 012 decoupling explicitly.** The `strategic_potential` anchors reframed against
   the problem space (not the stack) **must not be weakened**. State in the prompt that raising
   `relevance` for stack-adjacent items must not pull `strategic_potential` up with it — they read
   different evidence, and Task 012's test asserting the old stack-conditioned wording cannot return
   must stay green.
4. Mirror any wording change into `backend/app/enrichment/fallback.py` as before.

## Non-goals

- `backend/app/scoring/priority.py` remains untouchable (D-014). If the top class is still starved
  after this, that is a *finding*, not a licence to change thresholds.
- No new axes, no renaming, no re-ranging, no change to the hype inversion.
- **Do not revert or dilute Task 012's `strategic_potential` reframe.** If the two genuinely conflict,
  stop and report rather than trading one for the other.
- No re-enrichment of the full corpus — sample only, unless separately authorised.

## Acceptance criteria

- On the same 45-item sample: **at least one item reaches `relevance >= 4`** and **at least one
  reaches `actionability >= 4`**, with the score defensible on hand inspection.
- **Task 012's gates hold:** quadrant occupancy stays `>= 1` and `sp >= rel + 2` count stays `>= 3`.
  Losing either means the trade was made in the wrong direction — report it, do not ship it.
- `r(relevance, strategic_potential)` is **reported, not gated** (D-057). It will likely *rise*, and
  that is expected and acceptable if both gates above hold.
- No inflation: per-axis means reported before and after; a 10-item hand spot-check with misses named.
- Hype inversion unchanged and correct on every sampled item.
- Cost recorded. Expect ~$1.60 for a 45-item sample.

## Test plan

- `test_relevance_anchors_define_four_and_five` — the template names concrete 4 and 5 conditions.
- `test_actionability_anchors_define_four_and_five` — same for `actionability`.
- `test_strategic_potential_reframe_intact` — Task 012's assertion that the stack-conditioned wording
  cannot return **must still pass**; extend it if needed, never weaken it.
- `test_fallback_wording_matches_template` — the existing mirror pin stays green.

## Files likely to change

`prompts/classify_item.md` · `backend/app/enrichment/fallback.py` ·
`docs/m8-calibration-notes.md` (append — do not overwrite prior runs) · `backend/tests/`

---

## Agent prompt (paste-ready)

```
Read HANDOFF.md, then CLAUDE.md, then docs/AGENT_ADDENDUM.md, then
docs/m8-calibration-notes.md (all prior runs), then docs/DECISIONS.md entries D-049 and
D-057, then tasks/015-relevance-anchor-recalibration.md. All binding.

THIS IS NOT A THIRD TASK 012 ITERATION. Task 012 is CLOSED and ACCEPTED — it decoupled
strategic_potential from relevance and made the horizon_signal quadrant reachable for
the first time. This is a different defect on a different axis that its work exposed.

THE DEFECT (measured, do not re-derive)
Task 012 attempt 1 rewrote the relevance anchors and over-corrected. On the same 45-item
sample: items at relevance >= 4 went 1 -> 0 -> 0, actionability >= 4 has always been 0,
and events 1, 103 and 228 each LOST a relevance point. So part of the quadrant's
reachability was bought by UNDER-SCORING RELEVANCE rather than by lifting strategic
potential. Knock-on: priority.py needs relevance >= 5, or >= 4 with sp >= 3, so
immediate_priority is now as starved as horizon_signal used to be — the same defect
moved to the other end of the scale.

WORK — prompts/classify_item.md only:
1. Rewrite the relevance 4 and 5 anchors so real items can reach them. A 5 should mean
   something a real week contains: a breaking change to something in the stack, a
   security issue with a live exploit path, a deprecation with a dated cutoff. A 4 must
   not require the item to be about the user's exact current file.
2. Do the same for actionability, which has never exceeded 3 in any run. Define 4 and 5
   concretely — a documented migration path, a patch to apply, a config to change.
3. Protect task 012's decoupling EXPLICITLY. State in the prompt that raising relevance
   for stack-adjacent items must not pull strategic_potential up with it: they read
   different evidence. Task 012's test asserting the old stack-conditioned wording
   cannot return MUST stay green.
4. Mirror into backend/app/enrichment/fallback.py; keep the mirror-pinning test green.

HARD CONSTRAINTS
- priority.py UNTOUCHABLE (D-014). If immediate_priority is still starved afterwards,
  that is a FINDING to report, not a licence to change thresholds.
- Do NOT revert or dilute task 012's strategic_potential reframe. If relevance and
  strategic_potential genuinely cannot both be fixed, STOP and report — do not trade
  one for the other on your own judgement.
- No new axes, no renaming, no re-ranging, no change to the hype inversion.
- Sample only. Full-corpus re-enrichment is NOT authorised.

MEASURE: re-run THE SAME 45 items, verify identity before spending, and APPEND to
docs/m8-calibration-notes.md — prior runs stay on the record. Report per-axis
distributions before/after, both task 012 gates, and r as a DIAGNOSTIC only.

COST GATE: ~$1.60 approved for one 45-item sample. If it overruns, record the actual
figure as a D-NNN entry rather than absorbing it (as D-055 did).

ACCEPTANCE
- >= 1 item at relevance >= 4 AND >= 1 at actionability >= 4, both defensible by hand.
- Task 012's gates HOLD: quadrant occupancy >= 1, sp >= rel + 2 count >= 3. Losing
  either means the trade went the wrong way — report, do not ship.
- r will likely RISE. That is expected and fine (D-057). Report it; it is not a gate.
- No inflation: means before/after, 10-item hand spot-check with misses named.
- Suite green — re-verify the baseline yourself (D-022).

STOP CONDITION: one sample run. If the criteria are unmet, STOP and report with the
numbers. Do not iterate. Two tasks have now hit stop conditions on this prompt file; a
third unmet run means the prompt is not the remaining lever and the next move is
Christo's.

Check the highest D-NNN in docs/DECISIONS.md before appending — concurrent sessions have
collided before. Merge into HANDOFF.md rather than overwriting other sessions' entries.
```
