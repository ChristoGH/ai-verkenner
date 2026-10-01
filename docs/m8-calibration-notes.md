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

---

## Task 015 — `relevance` / `actionability` anchor recalibration

**Date:** 2026-08-04 · **Status: CRITERIA UNMET AND TASK 012'S GATES LOST — CHANGE REVERTED, NOT
SHIPPED.** Per the task file (*"losing either means the trade went the wrong way — report, do not
ship"*) the prompt is back at its attempt-2 state, which is the last state measured to hold the
gates. One sample run, hard stop, no iteration.

- Raw output: `docs/m8-calibration-task015.json` (prior runs untouched)
- **Same 45 items**, verified *before* spending: the sampler's `event_id` list was compared against
  both `m8-calibration.json` and `m8-calibration-attempt2.json` — identical, same order.
- Same seed (12), strata, corpus (read-only), model (`claude-opus-4-8`), and `USER_CONTEXT`.
- The attempted prompt is preserved verbatim in §5 below so it can be re-applied without redoing it.

### 1. What was changed (and has since been reverted)

Three edits to `prompts/classify_item.md`, plus the fallback mirror:

1. `relevance` **4** and **5** re-gated on evidence the *item* carries — "names a part of their stack
   **and** reports a concrete change to it: a release, a breaking change, a security advisory or CVE,
   a deprecation, a migration, or a change to pricing, rate limits or an API contract"; `5` = the
   same "on a clock". Plus an explicit note that the model is *not* expected to know what is
   deployed, and that 4/5 are **narrower** than 3 (to stop the mass drifting up).
2. `actionability` **4** and **5** re-gated on whether the item *supplies the specifics* — a version
   to upgrade to, a documented migration path, a config change, runnable published weights — with
   "a `4` does not require the action to be large".
3. A protection clause for Task 012: *"Raising `relevance` must never raise `strategic_potential` …
   score `strategic_potential` first … and do not revisit it."*
4. `fallback.py`: relevance cap 4 → 3, since keyword overlap can evidence "about the stack" but
   never "a change you must respond to".

### 2. Result — every criterion unmet, and both Task 012 gates lost

| Measure | Attempt 2 | **Task 015** | Gate |
|---|---|---|---|
| items at `relevance ≥ 4` | 0 | **0** | ≥ 1 ❌ |
| items at `actionability ≥ 4` | 0 | **0** | ≥ 1 ❌ |
| quadrant occupancy (`rel ≤ 2 AND sp ≥ 4`) | 2 | **0** | ≥ 1 ❌ **LOST** |
| items at `sp ≥ rel + 2` | 4 | **2** | ≥ 3 ❌ **LOST** |
| `r(relevance, strategic_potential)` *(diagnostic, not a gate)* | 0.693 | **0.608** | — |

Per-axis mean and max, attempt 2 → Task 015:

| Axis | Mean | Max | Task-015 distribution |
|---|---|---|---|
| `relevance` | 1.33 → **1.36** | 3 → **3** | 0:7 · 1:18 · 2:17 · 3:3 |
| `novelty` | 1.87 → **1.91** | 3 → **3** | 0:1 · 1:16 · 2:14 · 3:14 |
| `actionability` | 1.00 → **1.04** | 3 → **3** | 0:12 · 1:23 · 2:6 · 3:4 |
| `strategic_potential` | 1.73 → **1.64** | 4 → **3** | 0:10 · 1:8 · 2:15 · 3:12 |
| `hype` | 1.80 → **1.71** | 5 → **5** | 0:3 · 1:24 · 2:7 · 3:6 · 4:4 · 5:1 |

Movement vs attempt 2: `relevance` −1 on 3 items, +1 on 4, **unchanged on 38**.
`strategic_potential` **−1 on 9 items**, +1 on 5, unchanged on 31 — and its **max fell 4 → 3**,
which is what emptied the quadrant.

### 3. Diagnosis — the anchors were not the binding constraint; `USER_CONTEXT` is

**The rewritten anchors worked exactly as written, and correctly returned "no" on all 45 items.**

The new `relevance 4` requires the item to *name a part of the stack in `user_context`*. Here is the
`user_context` the model actually received, in full — 309 characters, from the default in
`config.py`:

> A solo engineer building AI Verkenner: a personal AI intelligence and early-warning system. Stack:
> Python, FastAPI, SQLite, Qdrant, Neo4j, React/TypeScript, local sentence-transformers embeddings,
> **and a cloud LLM**. Interests: LLM tooling, RAG, vector/graph databases, agentic systems, and AI
> developer tooling.

It names **no products** where it matters most. "A cloud LLM" is not "Anthropic" or "the Claude Agent
SDK". So:

- **ev1** — *"Anthropic pauses token-based billing for its Claude Agent SDK"* — is a pricing change
  to a service the user builds on, the `4` anchor almost verbatim. It scored **`relevance` 2**,
  because Anthropic is not a named part of the stack in `user_context`. The model was right.
- **ev46** — *`plugin-legacy@8.2.1`* (Vite) — is a released version with a changelog, the
  `actionability 4` anchor almost verbatim. It scored **`actionability` 2** (up from 0 — the anchor
  *did* fire partially), because Vite is not named either; `user_context` says "React/TypeScript".

Meanwhile [`docs/USER_CONTEXT.md`](USER_CONTEXT.md) — hand-maintained, and the file that calls itself
*"the ground truth AI Verkenner uses to score `relevance`"* — names Qdrant, Neo4j, FastAPI, React,
Cursor, Voyage embeddings, AKS/Knative, and lists **"Claude / Anthropic model + Agent SDK releases"**
under *strong relevance signals (elevate)*. **It is not wired into the runtime.** `USER_CONTEXT` is
unset in this environment, so `config.py` falls back to the 309-character paragraph.

**Consequence, and it is bigger than this task:** every `relevance` score this project has ever
measured — D-018's corpus baseline included — was computed against a stack description that omits
the user's most important named dependencies. Task 012 attempt 1 flagged the substitution in its §6
and nobody acted on it; this run shows it is not a footnote but the binding constraint on the top of
the scale.

**Why `strategic_potential` fell, stated with its uncertainty.** Nine items lost a point and the max
fell 4 → 3, which cost both gates. The most likely cause is edit 3: the protection clause's only
worked illustration shows `strategic_potential` **low** (*"can be `relevance 4–5` while being
`strategic_potential 0–1`"*), and "do not revisit it" adds a second downward nudge — an asymmetric
instruction where a symmetric one was intended. It **cannot be cleanly separated from run-to-run
variance** on a single run: attempt 2 recorded ev179 moving `sp 4 → 3` on identical input, so a
one-point drift is inside the noise floor. Nine down against five up with the max collapsing is
larger than pure noise, but the attribution is *inferred*, not measured.

### 4. Hand spot-check — 10 items (attempt 2 → Task 015)

**No inflation: `relevance` moved +0.03 and `actionability` +0.04 in the mean.** The problem is the
opposite — nothing moved where it needed to.

| Event | Item | a2 → 015 | Verdict |
|---|---|---|---|
| 1 | *Anthropic pauses Claude Agent SDK billing* | rel 2 → **2** | ❌ The headline miss. Should be a 4 under the new anchor; `user_context` never names Anthropic, so the gate cannot close. Not the anchor's fault. |
| 46 | *`plugin-legacy@8.2.1`* (Vite) | act 0 → **2**, hype 1 → **0** | ⚠️ The anchor half-fired: a bare changelog link moved 0 → 2, but not to 4, because Vite is not a named stack element. `hype 0` for a primary changelog is right. |
| 38 | *Claude `web_fetch` exfiltration* (Willison) | sp 4 → **3** | ❌ **Gate loss.** One of attempt 2's two quadrant items, and the clearest `sp 4` in the corpus. Losing it is the strongest evidence that edit 3 pushed `strategic_potential` down. |
| 180 | *Frontier LLMs vs evil agents* (The Register) | sp 4 → **3**, act 2 → **1** | ❌ **Gate loss**, the other quadrant item. Also a headline-only stub, so thin evidence either way. |
| 54 | *Inkling, open-weights 975B, Apache-2.0* | rel 2 → **3**, sp 3 → **3** | ⚠️ `rel 3` is the better read (it is a usable model release). But `sp` **still 3** — the regression fixture D-049 named has now missed in three consecutive runs. |
| 64 | *Kimi K3 / pelican benchmark* (Willison) | act 2 → **3**, sp 2 → **3** | ✅ Defensible both ways: a concrete benchmark to run, and open-weight frontier capability moves a real constraint. |
| 134 | *WorldCupArena: evaluation of LMs and agents* (arXiv) | rel 2 → **1**, sp 3 → **2** | ❌ Wrong direction. Evaluation methodology is squarely in the named problem space; attempt 2's `sp 3` was better. |
| 81 | *LLM cliché highlighter* (Willison) | sp 1 → **0**, hype 1 → **0** | ✅ A toy; `sp 0` is honest. `hype 0` correct for a primary post. |
| 94 | *nascheme/quixote* (a Python repo) | rel 1 → **2** | ⚠️ Python *is* named in `user_context`, so `2` is defensible — and it shows the anchors are reading the stack list literally, which is exactly the diagnosis. |
| 228 | *memloom — local-first agent memory* | rel 3 → **2**, nov 1 → **2** | ⚠️ Borderline. A day-old repo with a one-line description; `rel 2` is defensible, `rel 3` was too. |

**Hype inversion: correct on every sampled item, at both ends.** `hype 5` on sponsored Gartner
content; `4` on corporate announcement posts (DeepMind, GitHub, Ars opinion, a Register explainer);
`0` on primary sources (a Vite changelog, two Willison posts). No substantive primary source carried
a high hype number, and nothing inverted.

### 5. The attempted prompt text, preserved

Kept so this does not have to be re-derived if the `USER_CONTEXT` fix below makes it worth retrying.
A copy of the full attempted template is at
`…/scratchpad/classify_item.task015-attempt.md`; the three edits are quoted verbatim in §1 above,
and the anchor blocks were:

```
relevance
- `4` — names a part of their stack (a language, framework, database, model provider, library or
  service in `user_context`) **and** reports a concrete change to it: a release, a breaking change,
  a security advisory or CVE, a deprecation, a migration, or a change to pricing, rate limits or an
  API contract. The user has to decide what to do about it — that decision is what a `4` is.
- `5` — a `4` that is on a clock: an actively exploited vulnerability, a breaking change that has
  already shipped, or a dated cutoff. A `5` means today's work stops for this.

actionability
- `4` — the item supplies the specifics: a released version to upgrade to, a documented migration
  path, a patch or config change to apply, or published weights/code you could run as they stand.
- `5` — a `4` that is on a clock: a fix for an actively exploited vulnerability, a breaking change
  already shipped, or a dated deprecation deadline.
```

### 6. Cost

| | |
|---|---|
| Calls | 45 (0 failures, 0 retries) |
| Tokens | 215,181 in / 26,286 out |
| **Cost** | **$1.73** against ~$1.60 approved — **8% over**, recorded per the task's cost gate (D-063) |

Running total across all three runs on this prompt file: **$4.77**.

### 7. What this leaves

**Do not retry the anchors as they stand.** They are not the binding constraint, and a fourth run
against the same 309-character `USER_CONTEXT` would return the same "no" on the same items.

**The cheap, high-value experiment is one line of configuration, not another prompt rewrite:** point
`USER_CONTEXT` at [`docs/USER_CONTEXT.md`](USER_CONTEXT.md) — the file the repo already calls the
ground truth for `relevance` — and re-measure. Under that context, ev1 (Claude Agent SDK) and ev46
(Vite) both meet the attempted `4` anchors on their face, so the same prompt that scored zero 4s
here would be expected to produce several. That is a **config + measurement** task, not a prompting
one, and it should carry the fix for edit 3's asymmetry (illustrate `strategic_potential` moving in
**both** directions, and drop "do not revisit it").

**Second finding, independent of the above:** the regression fixture D-049 named — event 54,
*Inkling* — has now been missed in three consecutive runs (`sp 3` every time). Either the item is
genuinely a 3 and the fixture is wrong, or the `4`/`5` anchors do not reach the
"capability-under-a-permissive-licence" case. That is worth settling before it is cited again as a
target.

---

## Task 017 — `docs/USER_CONTEXT.md` wired in; prompts held constant

**One run, as authorised. Not iterated.** Raw output: `docs/m8-calibration-task017.json`.
The same 45 items, the same seed and model, and `prompts/classify_item.md` +
`enrichment/fallback.py` **byte-identical to their committed Task 012 attempt-2 state** (verified
`git status` clean on both before spending). The only variable moved is the `user_context` supplied
on each call. Corpus opened read-only; nothing written back.

### 1. Sample identity — verified BEFORE spending

The 45 `event_id`s were compared element-by-element against all three prior runs
(`m8-calibration.json`, `-attempt2.json`, `-task015.json`). **Exact match, in order, on all three.**
A comparison against a different sample costs the same and is worth nothing, so this was a gate, not
a formality.

### 2. Proof of input — what was actually sent

The report records the context verbatim (`measure_calibration.py` writes `settings.user_context`
into its output). Recorded: **2,331 characters**, first line `# USER_CONTEXT — who this radar is
for`, and containing `pgvector` · `Qdrant` · `Knative` · `tree-sitter` · `Agent SDK` · `Cursor` ·
`spaCy`. The stub is 309 characters and contains none of them. This is the check addendum §7 exists
to demand, and it is now in the run's own output rather than in a claim about it.

`docs/USER_CONTEXT.md` is **41 lines / 2,373 bytes / 2,332 characters** (the byte-character gap is
the multi-byte `—` and `·`); 2,331 after `.strip()`. **Nothing was trimmed and no boundary is
proposed** — at that size there is nothing to cut, and Task 017's scope item 3 is discharged by the
measurement rather than by an editorial judgement.

### 3. The prediction — CONFIRMED on the only limb this sample could test

**Stated before the run, with its own caveat measured first.** Of the 45 items, only **2** match the
predicted categories by title: ev1 and ev38, both Claude/Anthropic. **Zero** match
pgvector/Qdrant/Lakebase, **zero** tree-sitter, **zero** Knative/AKS/Cloud Run. (An apparent AKS hit
was `bre-AKS` inside "where the measurement breaks".) So three of the prediction's four limbs were
**untestable on this sample** — that is a fact about the sample, not a result.

| item | attempt 2 | task 017 | predicted? |
|---|---|---|---|
| ev1 — *Anthropic "pauses" token-based billing for its Claude Agent SDK* | `rel 2` | **`rel 4`** | ✅ rise |
| ev38 — *How I tricked Claude into leaking your deepest, darkest secrets* | `rel 2` | **`rel 3`** | ✅ rise |

**ev1 is the only item in the whole sample to reach `relevance 4`** — the criterion Task 015 could
not meet — and it is precisely the item predicted, for precisely the stated reason:
`docs/USER_CONTEXT.md` lists *"Claude / Anthropic model + Agent SDK releases"* verbatim under
**strong relevance signals (elevate)**, and two shipped projects (Commission Intelligence, MedVoice)
depend on the Claude SDK. D-062's diagnosis is confirmed by construction: the anchors were never the
binding constraint.

### 4. Results against every criterion

| Measure | Attempt 2 | **Task 017** | Gate | |
|---|---|---|---|---|
| `relevance >= 4` | 0 | **1** (ev1) | >= 1 | ✅ **MET** |
| quadrant occupancy (`rel<=2 & sp>=4`) | 2 | **0** | >= 1 | ❌ **LOST** |
| `sp >= rel + 2` count | 4 | **3** | >= 3 | ✅ holds, at the line |
| `actionability >= 4` | 0 | **0** | informational | — |
| `horizon_signal` items | 2 | **0** | — | follows the quadrant |
| `r(rel, sp)` *(diagnostic, D-057)* | 0.693 | **0.567** | not gated | fell |

`r` **fell** rather than rose. That was not predicted — the expectation was a rise — and it is
reported as the diagnostic D-057 made it, not claimed as a win.

### 5. ⚠️ The quadrant loss — what actually caused it

**The quadrant did not empty because `relevance` rose. It emptied because `strategic_potential`'s
ceiling fell.** Not one of the 45 items reached `sp >= 4`; the axis maximum went **4 → 3**.

| | attempt 2 | task 017 |
|---|---|---|
| items at `sp >= 4` | **2** (ev38, ev180) | **0** |
| `sp` distribution | `{0:11, 1:6, 2:14, 3:12, 4:2}` | `{0:9, 1:6, 2:19, 3:11}` |
| `sp` mean | 1.733 | 1.711 |

Both former quadrant items are accounted for individually: **ev180** (*Frontier LLMs couldn't help
Hugging Face fight off evil agents*) kept `rel 2` exactly and lost `sp 4 → 3`; **ev38** lost
`sp 4 → 3` as well. Neither left on a relevance rise alone.

**This matters because `strategic_potential` is the axis that, by design, does not read
`user_context`.** Task 012 attempt 2 framed it on the problem space specifically so it would not
restate `relevance`, and `test_strategic_potential_is_framed_on_the_problem_space_not_the_stack`
pins that. Two readings, and **one run cannot separate them**:

1. **Run-to-run variance.** The `sp >= 4` population was **2 of 45**. D-056 already recorded ev179
   moving `sp 4 → 3` between runs *on identical input*. A 2-item ceiling losing both items is well
   inside that documented ±1 noise.
2. **Contamination.** A longer, more concrete context could implicitly anchor the whole scoring pass
   downward on an axis meant to ignore it.

The honest statement is that **the quadrant gate is lost on this run, on a 2-item base, and the
cause is not separable from noise without a second run** — which the stop condition forbids and
which this session did not take. The mean barely moved (1.733 → 1.711), which is what argues for
reading (1); the ceiling moving at all is what keeps (2) open.

### 6. No inflation — per-axis means, before and after

| axis | stored | attempt 2 | **task 017** | Δ vs attempt 2 |
|---|---|---|---|---|
| relevance | 1.53 | 1.33 | **1.36** | **+0.02** |
| novelty | 2.42 | 1.87 | **1.93** | +0.07 |
| actionability | 1.02 | 1.00 | **0.96** | −0.04 |
| strategic_potential | 1.96 | 1.73 | **1.71** | −0.02 |
| hype *(inverted)* | 1.93 | 1.80 | **1.67** | −0.13 |

**Relevance moved by +0.02 on the mean: 6 items rose, 6 fell, 33 unchanged.** Wiring a richer
context **redistributed** relevance rather than lifting it — which is the correct signature. A
context that made everything more relevant would have been the failure mode to fear.

**Hype inversion verified unchanged** (0 = signal, 5 = noise): the Gartner advertorial (ev70) scored
**5** in both runs, Simon Willison's primary post (ev30) scored **1** in both. 0 items failed.

### 7. Hand spot-check — 10 items, MISSES NAMED

Every item that moved on `relevance` was read against its own text and against
`docs/USER_CONTEXT.md`. Six rose, six fell; all twelve are below, so this is the whole population of
movement, not a flattering selection.

**Correct (6):**

- **ev1** `rel 2→4` — Claude Agent SDK billing. Named verbatim in the strong-signal list; two
  shipped projects depend on that SDK. `sp` correctly stayed **1** — a pricing change is not a
  strategic shift, and the two axes moving independently here is the Task 012 decoupling working.
- **ev38** `rel 2→3` — Claude memory exfiltration. Security of a stack component.
- **ev161** `rel 1→2` — agent harness for multimodal pipelines. "agentic frameworks" is a named signal.
- **ev40** `rel 2→1` — OpenAI's GPT-Red. OpenAI is not this user's model vendor; `hype` also rose
  2→3, right for vendor safety-PR.
- **ev88** `rel 2→1` — email spam-filter salting. No stack contact.
- **ev134** `rel 2→1` — football-prediction benchmark. No stack contact.

**ev152** `rel 2→3` — *LLMs and Agentic AI Systems for Smart Grids* — looks wrong until you check
the document: **SmartSolar** (Sunsynk inverter / home-energy optimisation) is listed under active
work. The rise is defensible and is evidence the context is being read rather than pattern-matched.

**Misses (5) — named, not smoothed:**

- **ev228** `rel 3→2` — *memloom: local-first memory engine for AI agents*, from `topic:rag`. **The
  clearest miss.** "RAG techniques" is a named strong signal and agent memory is directly relevant to
  AI Verkenner and Commission Intelligence. This was the only item scored `rel 4` in the stored
  corpus and it fell to 2. (Its `hype 3→1` is more accurate, so the item did not simply sink.)
- **ev179** `rel 3→2`, `act 3→2` — *Nativ: run frontier open models locally on your Mac*. The
  document names embeddings (Voyage, sentence-transformers, OpenAI) but **not local LLM inference**,
  so the demotion is literal to the text. That reads as an **under-specified document**, not a
  wiring defect — a candidate line for Christo to add.
- **ev17** `rel 0→1` — health-board phishing exercise. **A control violation:** this was one of the
  no-stack-contact items predicted not to rise. The likely pull is *"MedVoice … healthcare
  compliance"*. Still bottom-of-scale, so nothing published depends on it.
- **ev49** `rel 0→1` — DeepMind/Isomorphic bioresilience. Nothing in the document touches bio.
  `hype 4` correctly marks it noisy.
- **ev81** `rel 2→1` — Simon Willison's LLM cliché highlighter. Arguable: the stub's "AI developer
  tooling" caught it, the real document's signal list does not. A hands-on tool from a primary source
  is plausibly something this radar should keep.

The three other controls held: ev246 (Mars) `0→0`, ev70 (Gartner) `0→0`, ev113 (UK ERP audit)
`0→0`, ev93 (wildfire satellites) `0→0`.

### 8. Cost — real API figures, under the gate

| | attempt 2 | **task 017** |
|---|---|---|
| input tokens / call | 4,166 | **5,097** |
| total tokens | 187,461 in / 27,297 out | **229,356 in / 26,392 out** |
| cost / item | $0.0360 | **$0.0402** |
| run total (45 items) | $1.6197 | **$1.8066** |

**+931 input tokens per call** — the real measured figure, against a ~575-token pre-run estimate;
markdown structure costs more per character than prose. **+$0.0042 per item (+11.5%)**, **+$0.42 per
100 items**. **$1.81 against a ~$2.00 gate — under, so no overrun entry is owed** (the D-055 / D-063
precedent applies to overruns; the figure is recorded here either way). 0 failed items.
Running total on this prompt file across four runs: **$6.58**. Full-corpus re-enrichment remains
**unauthorised and not run**; at this context size it would be ≈ $11 through the classify prompt
alone.

### 9. What this leaves

- **The wiring is done and proven at runtime**, not merely in tests: the source in force is named in
  the run's own output and by a startup log line.
- **`relevance >= 4` is reachable** and was reached by exactly the predicted item. **Task 015's
  premise is dead** — it proposed rewriting anchors that were never the constraint. Re-read it against
  this before running anything; D-062 already says not to run it as written.
- **Task 012's quadrant gate is lost on this run** and the cause is not separable from documented
  ±1 variance on a 2-item base. **This is the open question, and it is Christo's** — not another
  prompt edit. If it is worth settling, the cheapest instrument is a **repeat of this exact run with
  no changes at all** (~$1.81), which measures variance directly; a second *prompt* change would
  confound it again, which is the mistake this whole sequence exists to avoid.
- **Two document gaps found, not fixed** (its accuracy is Christo's — the file says so): local LLM
  inference is absent (ev179), and healthcare compliance pulls non-AI healthcare items (ev17).
