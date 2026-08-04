# M8 calibration notes — Task 012

> Two attempts, both on the record. **[Attempt 1](#attempt-1--tiebreaker--anchors)** (scope points
> 1–5) is below; **[attempt 2](#attempt-2--strategic_potential-reframed-on-the-problem-space)**
> (scope point 6, D-049) is at the end of this file. Attempt 1's raw output is
> `docs/m8-calibration.json`; attempt 2's is `docs/m8-calibration-attempt2.json`. Neither overwrites
> the other.

## Attempt 1 — tiebreaker + anchors

**Date:** 2026-08-04 · **Status: STOP CONDITION HIT.** The prompt rewrite is implemented and the
sample run is done. **`r(relevance, strategic_potential)` did not drop below 0.5**, so per the task
file's stop condition this reports the numbers rather than iterating.

- Script: [`backend/scripts/measure_calibration.py`](../backend/scripts/measure_calibration.py)
- Raw output: `docs/m8-calibration.json` (every item, before/after, token usage)
- Corpus: `data/dev_corpus.db`, 246 events, unmodified — the script opens it `mode=ro` and writes
  nothing back. No corpus item was re-enriched in place.

---

### 1. What changed

`prompts/classify_item.md`, per the five scope points in `tasks/012-enrichment-score-calibration.md`:

1. The blanket downward tiebreaker on `relevance` is gone. The only tiebreaker left is on `hype`
   ("assume noise until shown otherwise").
2. Every axis now carries anchors for all six values 0–5, with `4` and `5` defined explicitly and a
   standing instruction that the top of the scale is in use, not reserved.
3. An explicit decoupling section: score `strategic_potential` **first** and independently, and
   `relevance 0–1` with `strategic_potential 4–5` is stated as a correct answer, not an error.
4. One worked example of a low-relevance / high-strategic item, with the per-axis reasoning spelled
   out in scoring order.
5. The tiebreaker wording is mirrored into `backend/app/enrichment/fallback.py`; a test pins the
   mirror so the two cannot drift.

`backend/app/scoring/priority.py` was **not touched** (standing ruling, D-014). No axis was added,
renamed, or re-ranged. The hype inversion is unchanged.

### 2. Method

45 already-enriched Events, re-scored under the new prompt with the **classify prompt only** — the
summariser / weak-signal / graph prompts produce no scores and were skipped, which cut the run's
cost roughly fourfold. Template loading and the user-message block come from
`app.enrichment.prompts`, the same code path the enricher uses; only the provider call is made
directly, so per-call token usage could be recorded.

Sampling is deterministic (`seed=12`) and **stratified over the existing relevance distribution**:
1 item at rel 4, 11 at rel 3, 10 at rel 2, 12 at rel 1, 11 at rel 0.

> ⚠️ **Caveat on the stratification, and it matters for reading the r figure.** The corpus mean
> relevance is 1.2; a flat random draw of 40 would rarely contain a candidate for the
> "relevance ≥ 4 somewhere" criterion. Overweighting the top of the distribution fixes that, but it
> also **widens the relevance range, which raises r mechanically**: baseline r on this sample is
> **0.889**, against **0.842** corpus-wide. The before→after comparison below is internally
> consistent (same 45 items both times); the sample's r is not directly comparable to D-018's
> corpus-wide figure.

Model `claude-opus-4-8`, adaptive thinking, as configured in `backend/app/core/config.py`.
`USER_CONTEXT` was unset, so the default in `config.py` was used — the short paragraph, **not** the
richer `docs/USER_CONTEXT.md`. See §6.

### 3. Result — the headline numbers

| Measure | Before | After | Target |
|---|---|---|---|
| `r(relevance, strategic_potential)` | 0.889 | **0.749** | < 0.5 ❌ |
| items at `relevance ≤ 2 AND strategic_potential ≥ 4` | 0 | **0** | ≥ 1 ❌ |
| `horizon_signal` items | 0 | **0** | — |
| `relevance` reaches ≥ 4 | 1 | **0** | ≥ 1 ❌ |
| `actionability` reaches ≥ 4 | 0 | **0** | ≥ 1 ❌ |

Per-axis, before → after (mean, max):

| Axis | Mean | Max | After distribution |
|---|---|---|---|
| `relevance` | 1.53 → **1.42** | 4 → **3** | 0:6 · 1:19 · 2:15 · 3:5 |
| `novelty` | 2.42 → **1.96** | 4 → **3** | 0:1 · 1:15 · 2:14 · 3:15 |
| `actionability` | 1.02 → **0.91** | 3 → **3** | 0:14 · 1:22 · 2:8 · 3:1 |
| `strategic_potential` | 1.96 → **1.73** | 4 → **4** | 0:7 · 1:10 · 2:17 · 3:10 · 4:1 |
| `hype` | 1.93 → **1.69** | 5 → **5** | 0:1 · 1:26 · 2:9 · 3:5 · 4:3 · 5:1 |

**The decisive number is the gap, not the correlation.** `strategic_potential − relevance`:

| gap | −2 | −1 | 0 | +1 | +2 or more |
|---|---|---|---|---|---|
| before | 0 | 1 | 24 | 20 | **0** |
| after | 1 | 3 | 22 | 19 | **0** |

Mean gap **fell**, 0.42 → 0.31. Not one item in 45 reached `sp ≥ rel + 2`. The rewrite moved every
axis slightly *down* (22 of 45 items were unchanged on both axes; where they moved, 8 lost a point
of relevance against 5 gained, and 13 lost a point of strategic potential against 3 gained). The r
drop from 0.889 to 0.749 is mostly this mild compression, not decoupling.

### 4. Diagnosis — why it did not work

**The two axes are anchored to the same evidence, so "score them independently" cannot be obeyed.**
Read the `strategic_potential` anchors as written: a 3 is "a credible alternative to *something
already in the stack*"; a 4 is a shift "in an area *they build in*". Both are conditioned on
proximity to `user_context` — which is exactly what `relevance` measures. An item far from the
user's stack therefore scores low on **both by construction**, and the instruction to decouple them
is asking the model to override a definition it was also given. D-018 correctly identified the
tiebreaker as *a* cause; the deeper cause is that `strategic_potential` is defined relative to the
same anchor as `relevance`.

For the quadrant to be reachable, `strategic_potential` has to key on something other than nearness
to today's stack — something like *"would this change the shape of the problem the user works on,
even if it touches nothing they use today?"* That is a different axis definition, not a different
tiebreaker, and it is beyond what this task's scope authorises.

**A second, smaller factor: the corpus.** The 2026-07-14 → 07-21 window is dominated by
whole-publication feeds. Of the 45 sampled items, several are genuinely neither relevant nor
strategic to anyone building this stack — "Viking 1 landed on Mars 50 years ago", a UK government
ERP audit, a Dell firmware fix. A quadrant cannot be populated from items that do not belong in it.
This is the same defect D-017 records (19 of 266 corpus items off-topic, all from three site-wide
feeds) and Task 011 exists to fix. It does **not** explain the result on its own — the sample also
contains items that *should* land in the quadrant and did not (see event 54 below).

**Correction to D-018.** D-018 states "6 items would become `horizon_signal` immediately". Measured
against the corpus: `relevance ≤ 2 AND strategic_potential ≥ 4` matches **0 items**, not 6. All
seven items at `sp = 4` sit at `relevance ≥ 3` (six at 3, one at 4), so none is one step from the
quadrant on the *strategic* side — each would also have to lose relevance. The rest of D-018 stands
and was re-verified this session: r = 0.842 across 246, and exactly one item with `sp > rel + 1`.

### 5. Hand spot-check — 10 items

Acceptance asks whether calibration became inflation. **It did not — the drift is mildly
deflationary, and four of five axis means fell.** Below is every judgement, including the misses.

| Event | Item | New scores | Verdict |
|---|---|---|---|
| 246 | *Viking 1 landed on Mars 50 years ago* (The Register) | rel 0 · nov 1 · act 0 · sp 0 · hype 1 | ✅ Correct. Nothing AI, nothing in stack, no promotion. |
| 113 | *UK government ERP watchdog* (The Register) | rel 0 · sp 0 · act 0 · hype 2 | ✅ Correct, and evidence for D-017 — an off-topic item from a site-wide feed. |
| 46 | *plugin-legacy@8.2.1* (Vite Releases) | rel 1 · sp 0 (was 1) | ✅ Correct deflation. A patch changelog changes no direction; `sp 0` is better than the old 1. |
| 5 | *AI coding agents taught robots to install GPUs* (Ars) | rel 1 (was 2) · sp 2 · hype 2 (was 3) | ✅ Defensible. Robotics touches nothing in the stack; agentic self-improvement is adjacent, so `sp 2` reads right. |
| 213 | *FinSAgent: multi-agent RAG over SEC filings* (arXiv) | rel 3 · nov 3 · act 2 · sp 3 | ✅ Correct. Near-identical problem shape to Commission Intelligence. |
| 179 | *Nativ: run frontier open models locally on Mac* (HN) | rel 3 · sp 4 (was 3) | ✅ The one item that moved **up** and reached `sp 4` — local frontier inference genuinely reopens an architecture choice. `rel 3` is arguable (a Mac-local runner is not their server-side stack); at `rel 2` this would have been the quadrant item. Note the source content is an HN stub, so the model scored the title alone. |
| 228 | *New repo: memloom — local-first memory engine for AI agents* | rel 2 (was 4) · sp 3 (was 4) | ✅ on relevance — a day-old repo with a one-line description does not "affect something in production", so the old `rel 4` was the inflated score and losing it is right. ⚠️ `sp 3` is arguably a 4. |
| 1 | *Anthropic pauses token-based billing for Claude Agent SDK* (Ars) | rel 2 (was 3) · sp 2 (was 3) | ❌ **Under-scored.** `USER_CONTEXT` names the Claude Agent SDK as a strong relevance signal and the user builds on it; a billing change to it meets the new `rel 3` anchor ("touches a named part of the stack"). The anchors pushed a stack-relevant item down. |
| 38 | *How I tricked Claude into leaking your secrets* (Willison; `web_fetch` exfiltration) | rel 2 (was 3) · sp 3 (was 4) | ❌ **Under-scored on both.** The user runs Claude-SDK agents with tool access; an exfiltration vector in `web_fetch` is directly relevant and constrains agent architecture. This was one of the corpus's seven `sp 4` items and it lost the 4. |
| 54 | *Inkling: open-weights 975B MoE, Apache-2.0* (Willison) | rel 2 (was 3) · sp 3 (was 4) | ❌ **The clearest miss.** This is the textbook quadrant item: nothing to adopt today (`rel 1–2` is right) but frontier capability under a permissive licence changes what is buildable (`sp 4–5`). The new prompt moved it the *wrong way* — down to 3 — leaving it in `archive`. |

**Hype inversion: correct on every sampled item, at both ends.** `hype 5` went to sponsored Gartner
content; `hype 4` to corporate announcement posts (DeepMind, GitHub, an Ars opinion piece); `hype 0`
to a primary technical post by Simon Willison; arXiv preprints and the Vite changelog sat at 1. No
item had a high hype number attached to a substantive primary source, and hype moved only downward
(11 items by one point), never in a way that inverted the polarity.

### 6. Cost

| | |
|---|---|
| Calls | 45 (plus 2 smoke-test calls) |
| Tokens | 156,501 in / 23,126 out |
| Model | `claude-opus-4-8` @ $5.00 / $25.00 per MTok |
| **Cost** | **$1.36** (smoke test $0.06; **run total $1.42**) |

Full-corpus re-enrichment is **not** authorised and was not run. For scale: 246 events through the
classify prompt alone would be ≈ $7.50; through the full four-prompt enricher, ≈ $30.

### 7. Recommendation

The prompt hypothesis is **partly refuted**. Narrowing the tiebreaker and adding anchors did what it
said — the scores are better justified and no longer show a blanket downward pull — but it did not
decouple the axes, because the axis *definitions* share an anchor. Attempt 2 should therefore change
`strategic_potential`'s frame of reference, not its tiebreaker: define it against **the shape of the
problem the user works on** rather than against the contents of their current stack, and make the
worked example a case the current prompt demonstrably gets wrong (event 54, *Inkling*, is the ideal
regression fixture — it is in the corpus and its correct scoring is `rel 1–2 / sp 4–5`).

Two things should be settled before spending again:

1. **Is re-framing `strategic_potential`'s definition in scope?** Task 012's non-goals forbid
   changing the axes' *names, ranges, and the hype inversion* — they do not obviously forbid
   rewriting one axis's anchors, but this is a bigger change than "calibration" and is Christo's
   call.
2. **Run Task 011 first?** The three site-wide feeds put genuinely off-topic items in every sample.
   Measuring calibration on a cleaner corpus would be both cheaper and more honest.

A second sample run at the same size costs about $1.40 — cheap enough that the gate is the scope
question, not the money.

---

## Attempt 2 — `strategic_potential` reframed on the problem space

**Date:** 2026-08-04 · **Status: STOP CONDITION HIT AGAIN — the headline criterion is still unmet,
but the quadrant is reachable for the first time.** Per the task file's stop condition (`if r still
does not clear 0.5, STOP and report. Do not iterate a third time`), this reports and stops.

- Scope: **point 6 only** (authorised by [D-049](DECISIONS.md)). Attempt 1's points 1–5 are
  unchanged and stay.
- Script: unchanged — [`backend/scripts/measure_calibration.py`](../backend/scripts/measure_calibration.py)
- Raw output: `docs/m8-calibration-attempt2.json` (attempt 1's `m8-calibration.json` is untouched)
- **Same 45 items as attempt 1**, verified by comparing the sampler's output against attempt 1's
  recorded `event_id` list — identical, in the same order. Same seed (12), same strata, same corpus
  (`data/dev_corpus.db`, read-only, nothing written back), same model (`claude-opus-4-8`), same
  `USER_CONTEXT` (unset → the 309-character default in `config.py`, **not**
  [`docs/USER_CONTEXT.md`](USER_CONTEXT.md) — see attempt 1 §6).

### 1. What changed

`prompts/classify_item.md`, `strategic_potential` only:

- The axis is now scored against **the shape of the problem space** — agentic pipelines · retrieval
  and knowledge graphs · evaluation and traceability · trust-sensitive domains — with the question
  *"if this holds, does the problem itself look different in one to three years?"*
- All six anchors rewritten on that basis. The two attempt-1 anchors that made the axis a
  restatement of `relevance` — "a credible alternative to something already in the stack" (3) and a
  shift "in an area they build in" (4) — are **gone**, and a test asserts they cannot come back.
- The scoring-order section now states that the two axes read **different evidence**: `relevance`
  reads `user_context`; `strategic_potential` explicitly does not, and stack-distance is neither
  evidence for nor against it.
- `backend/app/enrichment/fallback.py` mirrors the frame in its comment and states why its flat
  `strategic_potential = 2` must **not** be derived from the stack-keyword hits it uses for
  `relevance` — that derivation is the collinearity itself.
- New test `test_strategic_potential_is_framed_on_the_problem_space_not_the_stack`.

No axis was added, renamed or re-ranged; the hype inversion is untouched; `priority.py` was not
opened.

### 2. Result

| Measure | Before | Attempt 1 | **Attempt 2** | Target |
|---|---|---|---|---|
| `r(relevance, strategic_potential)` | 0.889 | 0.749 | **0.693** | < 0.5 ❌ |
| items at `relevance ≤ 2 AND strategic_potential ≥ 4` | 0 | 0 | **2** | ≥ 1 ✅ |
| `horizon_signal` items | 0 | 0 | **2** | — (first time non-zero) |
| `relevance` reaches ≥ 4 | 1 | 0 | **0** | ≥ 1 ❌ |
| `actionability` reaches ≥ 4 | 0 | 0 | **0** | ≥ 1 ❌ |
| event 54 (*Inkling*) in the quadrant | — | no (`rel 2 / sp 3`) | **no (`rel 2 / sp 3`)** | yes ❌ |

**The gap distribution is where the change actually shows.** `strategic_potential − relevance`:

| gap | −1 | 0 | +1 | **+2** |
|---|---|---|---|---|
| before | 1 | 24 | 20 | **0** |
| attempt 1 | 4 | 22 | 19 | **0** |
| **attempt 2** | 8 | 15 | 18 | **4** |

Mean gap 0.42 → 0.31 → **0.40**. Attempt 1 produced *no* item with `sp ≥ rel + 2` in 45; attempt 2
produced four, two of which also clear `sp ≥ 4` and therefore land in the quadrant. The axes are
measurably less locked together even though `r` — a whole-sample summary dominated by the 33 items
still on or beside the diagonal — moved only 0.749 → 0.693.

Per-axis (mean, max), before → attempt 1 → attempt 2:

| Axis | Mean | Max | Attempt-2 distribution |
|---|---|---|---|
| `relevance` | 1.53 → 1.42 → **1.33** | 4 → 3 → **3** | 0:9 · 1:16 · 2:16 · 3:4 |
| `novelty` | 2.42 → 1.96 → **1.87** | 4 → 3 → **3** | 0:1 · 1:19 · 2:10 · 3:15 |
| `actionability` | 1.02 → 0.91 → **1.00** | 3 → 3 → **3** | 0:14 · 1:20 · 2:8 · 3:3 |
| `strategic_potential` | 1.96 → 1.73 → **1.73** | 4 → 4 → **4** | 0:11 · 1:6 · 2:14 · 3:12 · 4:2 |
| `hype` | 1.93 → 1.69 → **1.80** | 5 → 5 → **5** | 0:1 · 1:25 · 2:7 · 3:7 · 4:4 · 5:1 |

`strategic_potential`'s mean is unchanged from attempt 1 (1.73) while its *distribution* spread out —
0s rose 7 → 11 and 3s rose 10 → 12. The reframe **redistributed** the axis rather than inflating it:
items that are only one company's commercial news fell to 0–1, items that move a constraint in the
problem space rose to 3–4.

### 3. The two quadrant items, and the one that should have been there

| Event | Item | Attempt-2 scores | Reading |
|---|---|---|---|
| 38 | *How I tricked Claude into leaking your deepest, darkest secrets* (Willison — a data-exfiltration hole in `web_fetch`'s design) | rel 2 · nov 3 · act 2 · **sp 4** · hype 1 | Defensible. A new failure mode that anyone wiring tool-using agents to private data has to design around — the new `4` anchor almost verbatim. |
| 180 | *Frontier LLMs couldn't help Hugging Face fight off evil agents* (The Register) | rel 2 · nov 3 · act 2 · **sp 4** · hype 3 | Directionally right — defences failing against agentic attackers is an evaluation/trust constraint — but **scored from a one-line stub** ("Chinese open-weight model GLM 5.2 happily obliged"). The corpus stored no body text, so the model scored the headline. Treat this one as thin evidence. |
| **54** | *Inkling: open-weights 975B MoE, Apache-2.0* (Willison) | rel 2 · nov 2 · act 3 · **sp 3** · hype 1 | **The regression fixture missed again.** Frontier capability under a permissive licence is an access-and-cost barrier collapsing — the `4`/`5` anchors — and the model still reads it as a `3`. Unchanged from attempt 1 on the decisive axis. |

Event 54 is the honest verdict on this attempt: the frame moved several items the right way, but it
did not move *the* item the ruling named.

### 4. Hand spot-check — 10 items

Acceptance asks whether calibration became inflation. **It did not.** Relevance and novelty means
fell again, `strategic_potential`'s mean is flat, and the movement is redistribution. Every
judgement below, including the misses.

| Event | Item | Attempt-2 scores | Verdict |
|---|---|---|---|
| 38 | *Claude `web_fetch` exfiltration* (Willison) | rel 2 · **sp 4** | ✅ The clearest win. Attempt 1 had it at `sp 3`; the problem-space frame recognises a new agent failure mode. `rel 2` is arguably a 3 (the user runs Claude-SDK agents with tool access) — see the caveat below. |
| 180 | *Frontier LLMs vs evil agents* (The Register) | rel 2 · **sp 4** | ⚠️ Right direction, thin evidence — a stub item, headline-only. |
| 54 | *Inkling, open-weights 975B, Apache-2.0* | rel 2 · sp 3 | ❌ **Miss.** Should be `sp 4–5`. The frame did not reach the "capability arriving under a permissive licence" case. |
| 1 | *Anthropic pauses token-based billing for Claude Agent SDK* | rel 2 · nov 1 · act 1 · sp 1 · hype 2 | ✅ on `sp` — the new `0` anchor names "one company's commercial affairs", and a billing-schedule reversal is exactly that; `sp 3 → 1` is the frame working. ❌ on `rel`: the user builds on the Agent SDK and `rel 3` ("touches a named part of the stack") is the better read. |
| 103 | *Connecting AI agents to outside services explodes the risk radius* (The Register) | rel 2 · sp 2 | ❌ **Miss, and instructive.** Same subject as event 38 — agent tool-access risk — but scored two points lower, on a one-line stub. The reframe cannot compensate for missing body text. |
| 228 | *memloom — local-first memory engine for AI agents* (new repo) | rel 3 · nov 1 · sp 2 · hype 3 | ⚠️ Agent memory sits inside the problem space; `sp 2` reads low. Defensible only because it is a day-old repo with a one-line description and no evidence it works. |
| 179 | *Nativ: run frontier open models locally on Mac* (HN) | rel 3 · sp 3 | ⚠️ **Instability, worth recording.** Attempt 1 gave this `sp 4`; attempt 2 gives `sp 3`. Same item, same evidence, different run — the model's own variance is of the same size as some of the movements being measured. |
| 134 | *WorldCupArena: fine-grained evaluation of LMs and deep-research agents* (arXiv) | rel 2 · nov 3 · sp 3 | ✅ Evaluation methodology for agents is squarely in the named problem space; `sp 2 → 3` is the reframe doing what it says. |
| 161 | *FlashRT: agent harness for real-time multimodal deployment* (arXiv) | rel 1 · sp 3 | ✅ The decoupling shape: relevance **unchanged at 1** while `sp` rose 2 → 3. |
| 246 / 70 / 113 | *Viking 1 landed on Mars* · *How Gartner can help turn your AI vision…* · *UK government projects watchdog* | all rel 0 · sp 0 (Gartner hype 5) | ✅ The floor still holds. Off-topic items did not drift upward under a broader frame — the risk this reframe carried, and it did not materialise. |

**Caveat that cuts against the headline result.** Both quadrant items reach it partly through a
`relevance` of 2 that is arguably a 3 (event 38 in particular). The relevance anchors written in
attempt 1 have a measurable downward pull on stack-adjacent items — `relevance ≥ 4` went from 1 item
to 0, and events 1, 103 and 228 all lost relevance this run. **Some of the quadrant's reachability
was bought by under-scoring relevance rather than by lifting strategic potential**, and that is a
defect of its own, not a win to bank.

**Hype inversion: correct on every sampled item.** `hype 5` on sponsored Gartner content, `hype 4` on
corporate announcement posts, `hype 0–1` on primary technical sources and arXiv preprints. No
substantive primary source carried a high hype number.

### 5. Cost

| | |
|---|---|
| Calls | 45 (0 failures, 0 retries) |
| Tokens | 187,461 in / 27,297 out |
| Model | `claude-opus-4-8` @ $5.00 / $25.00 per MTok |
| **Cost** | **$1.62** |

**$1.62 against the ~$1.40 approved — 16% over.** Cause: the rewritten `strategic_potential` section
is ~700 tokens longer than attempt 1's and is resent with every call (45 × ~690 extra input tokens),
plus slightly longer adaptive-thinking output. Recorded rather than absorbed silently
([D-055](DECISIONS.md)). Running total across both attempts: **$3.04**.

Full-corpus re-enrichment remains **unauthorised** and was not run: ≈ $9 through the classify prompt
alone at this prompt length, ≈ $30 through the full four-prompt enricher.

### 6. Reading, and what is left

**What the reframe achieved.** The quadrant is **reachable** — the first non-zero `horizon_signal`
count this project has measured, and the first items ever produced at `sp ≥ rel + 2`. The axis is
no longer defined in terms of the user's stack, and its distribution spread in both directions
without inflating. On the product's own terms — *can a quiet, low-relevance item ever surface as a
weak signal?* — the answer moved from **no** to **yes**.

**What it did not achieve.** `r = 0.693`, well short of `< 0.5`; event 54 stayed out; and neither
`relevance` nor `actionability` reached 4 anywhere. Three of the five acceptance criteria are unmet.

**Why `r` may be the wrong instrument, stated as a question, not a licence.** With 45 items on
compressed 0–3/0–4 ranges, `r` is dominated by the 33 items that sit on or beside the diagonal —
mostly items that genuinely *are* both irrelevant and unstrategic (a Mars anniversary, a Gartner
ad, a Windows firmware fix). Those items correctly score low on both axes, and no prompt should
separate them; they nonetheless hold `r` up. The measure that tracks the product requirement is the
one that moved: **count of items at `sp ≥ rel + 2`** (0 → 4) and **quadrant occupancy** (0 → 2).
Whether to replace the acceptance metric is **Christo's call, not this session's** — the criterion
was not moved, and the run is reported against it as written.

**Three candidates for what remains, in the order the evidence supports them:**

1. **The `relevance` anchors now over-demote.** Attempt 1 rewrote them alongside everything else and
   they pull stack-adjacent items down (`rel ≥ 4`: 1 → 0). Fixing that would *raise* `r` while making
   both axes more truthful — the criterion and the goal point in opposite directions here.
2. **Corpus quality (Task 011).** Stub items — 103, 180, 179, 150 — are scored from headlines alone,
   and one of the two quadrant items is such a stub. Task 011 has since landed; a re-measure on a
   cleaner, fuller corpus is the cheapest next signal.
3. **Model variance.** Event 179 moved `sp 4 → 3` between runs on identical input. Single-run
   deltas of one point are inside the noise floor; only distributional shifts should be trusted.
