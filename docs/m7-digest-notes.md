# M7 — Feedback + GraphRAG digest: smoke notes

Acceptance-gate evidence for **M7** (`tasks/007-feedback-actions.md`, `tasks/008-weekly-digest.md`),
run on real data. Per the agreed plan this was a **cheap partial smoke** (~$3–5, not the full
broad-corpus run): isolated stores on non-conflicting ports (so the unrelated
`za-corruption-neo4j-1` container was left untouched), a small 4-publisher slice, a **persistent**
dev corpus at `data/dev_corpus.db` (gitignored) so future smokes are free.

## Configuration

| Knob | Value |
|---|---|
| Stores | `m7smoke` compose project — Qdrant `localhost:6335`, Neo4j `bolt://localhost:7688` (isolated) |
| Corpus DB | `data/dev_corpus.db` (persistent, gitignored) |
| Sources | 4 independent feeds: Ars Technica AI, The Register, VentureBeat AI, arXiv cs.CL |
| Window | `SOURCE_MAX_AGE_DAYS=7`, `SOURCE_MAX_ITEMS=8`, `ARXIV_MAX_RESULTS=8` |
| Embedder | `BAAI/bge-small-en-v1.5` (real, 384-dim) |
| Enrichment / digest LLM | `claude-opus-4-8` |

Pipeline: `python -m app.cli run` → `python -m app.cli digest --days 7`.

**Run:** `fetched=24 new=24 embedded=24 enriched_events=24 projected_events=24 sources=4`
(VentureBeat had nothing inside the 7-day window). Recency cap bounded the feeds (Ars 20→8, Reg
50→8). **22 of 24 events were enriched by real Opus**; the last 2 fell back (see the credit finding).

## ⚠️ Headline finding: the Anthropic API account is out of credits

Mid-run the API began returning `400 … "Your credit balance is too low to access the Anthropic
API."` This is an **account/billing** issue, not a code defect — and it exercised the
degrade-don't-crash invariant under a *real* failure:

- **Enrichment** degraded per-item to the rule-based fallback (2 of 24 events); the run still
  completed and persisted every record. The 2 fallback items are honestly labelled in the digest
  ("_Why:_ No LLM interpretation available (rule-based fallback)").
- **Digest composition** (the single Opus call) also hit the limit and **degraded to the
  deterministic fallback render** (`method=fallback`), so the digest still generated.

**Consequence for this gate:** the *LLM-composed narrative* digest could not be validated — what was
produced is the structured fallback render. Add credits to validate the composed prose (and the
broad M8 run).

## Q1 — Does it read as decisions, not links? ✅ at the item level; ⚠️ not yet as a composed narrative

Where real Opus enrichment ran, the item-level output is genuinely decision-oriented and **clearly
steered by `docs/USER_CONTEXT.md`**:

- *"Anthropic pauses token-based billing for its Claude Agent SDK"* → **Action:** "Check whether your
  cloud LLM layer depends on the Claude Agent SDK; model the proposed token-billing scenario to
  gauge cost exposure and keep a fallback provider in mind." — a real decision tied to the user's
  stack.
- *"LedgerAgent: Structured State for Policy-Adherent Tool-Calling Agents"* (arXiv) → **Action:**
  "note the pre-call constraint-check pattern as a candidate design for any tool-calling agent
  component in AI Verkenner." — connects research to *this* project.

Every bullet keeps its source link and separates FACT (summary) from INTERPRETATION (why / action),
with hype shown inverted. What is **not** yet shown is the LLM's cross-item *synthesis* (the "week in
a glance" narrative) — that is the composition call that the credit limit blocked. The fallback
render is honest and structured but per-item, not synthesised.

## Q2 — Is the weak-signals section the cross-publisher convergence? ⚠️ correct selection, but convergence did not fire on this thin slice

The weak-signals section correctly drew **only from the horizon/archive quadrant** — but **no
cross-publisher convergence fired**, so it fell back to ranking the quadrant by hype-aware salience
(the documented degrade). Every weak-signal item is single-source ("Sources: The Register" / "Ars
Technica AI"), because across only 4 feeds in one week the stories did not overlap on a shared entity
(London Hydro breach, Windows 26H2, a Brazil alert, Taiwan drones — all distinct). This is expected
and matches the plan: **full cross-publisher weak-signal strength is to be re-confirmed on M8's broad
corpus** (M6.5 already proved convergence fires there — NVIDIA/Anthropic across independent
publishers). The mechanism is wired (`graphrag=True` — Qdrant retrieve + Neo4j expand both ran); it
just needs a corpus with overlap.

A related observation: with no convergence, the weak-signals lane is "low-relevance quadrant by
salience," which surfaced mostly off-topic Register security/IT news — i.e. the section only earns
its keep once convergence is present. Good motivation for the M8 broad run.

## Q3 — Is the noise count honest? ✅ yes

**21 of 24** items were filtered as noise (archive OR hype ≥ 4) — and that is *correct*, not a bug:
a generic 4-publisher news slice is mostly off-stack for a RAG / knowledge-graph engineer (Windows
updates, data breaches, space-junk, drones all scored low-relevance → archive). The 3 surfaced in
the body are exactly the on-stack ones (the agents paper, the Anthropic SDK billing change, an
essay-scoring framework). The hype filter also worked: *"Dangerous AI models are coming no matter
what"* scored hype 4/5 and was demoted as noise while still appearing under the Risks security lens.

A wording nuance worth tightening later: in the no-convergence case the Weak-signals and Risks lenses
deliberately resurface quadrant items, so "excluded from the body" slightly understates where noise
items still appear. (Fixed one inaccuracy already: the exec summary no longer claims weak signals are
"converging" when they are the salience fallback.)

## Section routing (source-fact grounded) — ✅ working

arXiv → Research radar; the Anthropic Agent-SDK item → Tool changes; breaches / rogue-alert / phishing
→ Risks; high-strategic-low-hype → Opportunities (empty this slice). All ten sections rendered.

## Verdict

The M7 machinery is **wired and proven end-to-end on real data**: feedback ranking + the GraphRAG
digest (retrieve + expand + compose-or-fallback) generate over a real, persistent, mostly-Opus-
enriched corpus, with honest noise accounting and correct degrade behaviour under two genuine
failures. **Two things are explicitly deferred to a credited M8 broad run:** (1) the LLM-*composed*
narrative digest (blocked by the credit limit), and (2) cross-publisher weak-signal convergence
(needs a corpus with publisher overlap). Both are configuration/credit/corpus matters, not code.

## Teardown

Isolated `m7smoke` stores torn down after the run; `za-corruption-neo4j-1` untouched throughout.
`data/dev_corpus.db` kept (gitignored) so the next smoke is free — re-generate a digest any time with
the stores up and `python -m app.cli digest`.
