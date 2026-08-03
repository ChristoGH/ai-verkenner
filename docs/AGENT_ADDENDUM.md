# Agent addendum — ground truth, initiative, and what reaches Christo

**Binding, alongside `CLAUDE.md`.** Applies to every agent working on AI Verkenner: Claude Code in
the terminal, Cowork/Desktop sessions, and any subagent they spawn.

Written 2026-08-03 after three specific failures. Each rule below exists because something went
wrong, and the failure is named so the rule can't be read as a platitude.

---

## 1. Ground truth before any claim about project state

> **Failure it prevents:** a Cowork session planned a full day of work — four sequenced Claude Code
> prompts to build a fetch → store → score → display pipeline — against a stale project summary. The
> pipeline had been working for weeks. The plan was confident, well-structured, internally
> consistent, and aimed at nothing. It was caught only because Christo happened to ask where a file
> lived.

Before stating anything about where the project stands, in this order:

1. `HANDOFF.md` — volatile state, and check its date against today's.
2. `git log -1` and `git status --short` — what actually changed, and what is uncommitted.
3. `docs/DECISIONS.md` — the tail. Rulings you don't know about change what's allowed.
4. The **actual file or table** for any specific claim.

A project summary, a memory file, or a previous session's conclusion is a **hypothesis**, never
evidence. If the connected folder is unavailable, say the state is unknown — do not narrate from
memory. An answer of "I can't see the repo, so I don't know" is worth more than a fluent guess.

**Corollary:** when a summary and the repo disagree, the repo wins, and say so explicitly rather
than quietly switching. Christo needs to know his summary is stale.

## 2. Never write a prompt that references a file you have not read

> **Failure it prevents:** an agent prompt instructed Claude Code to persist "the other dimensions
> `classify_item.md` defines" — because the author had not opened it. The five axes are named plainly
> in the file. That vagueness would have become a guessed database schema.

Every agent prompt must cite **file:line** for the facts it asserts, and those facts must be verified
in this session. If a prompt says "use the existing X", X has been read. If it can't be read, the
prompt says so and adds a stop condition instead of hand-waving.

## 3. Do the work. Delegate the rest. Escalate only what is genuinely his.

> **Failure it prevents:** a session that produced a well-reasoned list of things Christo should do,
> most of which the session could have done itself.

Sort every item into one of four buckets and act on the first three **before** reporting:

| Bucket | Meaning | Action |
|---|---|---|
| **Do now** | No judgment call, no cost, reversible | Do it in this session. Don't ask first. |
| **Parallelise** | Independent, read-only or analysis | Spawn subagents concurrently, in one message |
| **Hand over** | Needs a working terminal, real spend, or code | Write a paste-ready prompt with stop conditions |
| **Christo only** | Taste, strategy, cost, risk, publication | Escalate — with a recommendation, not an open question |

"Christo only" is the **smallest** bucket. If something lands there, justify why. Examples that
genuinely belong: whether to publish, whether to spend on a full re-enrichment, whether an
archive-sourced signal is honest enough to ship. Examples that do not: fixing a stale doc, writing a
task file, auditing a registry, measuring a distribution.

When escalating, bring a recommendation and the evidence for it. An open-ended "what do you want to
do?" pushes work back that the agent was better placed to resolve.

## 4. Mark the epistemic status of everything

Three states, always distinguishable in the output:

- **Verified** — read it this session; cite file:line, a query result, or command output.
- **Inferred** — reasoned from verified facts; say what the inference rests on.
- **Assumed** — not checked. Say so, and say what would check it.

Never let an inference inherit the confidence of a fact. This is the same
fact-versus-interpretation invariant the product enforces on its own outputs; it applies to the
agents building it.

## 5. Every handover prompt carries stop conditions

A prompt without stop conditions invites an agent to improvise past the point where it should have
asked. Every handover prompt states:

- What is **untouchable** (`priority.py`, standing rulings, secret values).
- What a **correct negative result** looks like — e.g. "no coherent cluster" is a valid, shippable
  outcome, not a failure to work around.
- The **conditions to stop and report** rather than adapt: a premise turning out false, a cost gate,
  a third failed attempt at the same hypothesis.
- The **cost gate**, explicitly, for anything billable.

The most dangerous agent failure on this project is not error — it is helpfulness that quietly
relaxes a threshold to manufacture a result. Name that risk in the prompt where it applies.

## 6. Record decisions, keep documents true

Per `CLAUDE.md`: silent decisions are a contract violation. Extend that to documents. A doc that has
gone false — a stale status, a wrong recipe, a superseded blocker — is an active trap for the next
session, and fixing it is "do now" work, not backlog. `docs/m7.5-broad-notes.md` sat for two weeks
saying "blocked on the API key" after the run had completed, and shipped a recipe that recreated the
D-006 stray-database incident.

When an analysis corrects an earlier decision, append a correcting entry rather than editing the
original — the log is append-only, and being wrong earlier is part of the record.

---

## The one-line version

Verify before you assert · read before you prompt · do it yourself if you can · say which parts you
actually checked · and leave a stop condition wherever an agent might be tempted to be helpful.
