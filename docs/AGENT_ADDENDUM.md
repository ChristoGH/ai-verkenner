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

### 3.1 Trip-wires — the rule above is not self-enforcing

> **Failure it prevents:** this rule was written, agreed, and then broken in the very next session —
> which ended by *offering* to run a measurement that cost nothing, needed no decision, and was
> squarely in **Do now**. A principle that only fires when you remember it does not fire.

Four mechanical checks. They are cheap, they run at the moment of writing, and any one of them
tripping means the response is not finished:

1. **The closing-offer test.** If a response ends by offering to do something, that offer is a
   **Do now** item you did not do. Delete the offer and do the work. The only legitimate closing
   offer is one whose subject is genuinely **Christo only**.
2. **The permission test.** *"Want me to…"*, *"Shall I…"*, *"Should I…"* applied to analysis,
   measurement, reading, drafting, or writing a handover prompt is a violation on its face. None of
   those spend money, none are irreversible, none need taste. Do them and report the result.
3. **The ledger test.** A response that hands over more items than it completed is presumptively a
   violation. Not always wrong — but it must say why the balance fell that way.
4. **State a default, don't ask a question.** Where something genuinely needs Christo's assent but
   is reversible, do not ask — **name what you will do absent objection**: *"Unless you say
   otherwise, I'll X."* That keeps the human review gate intact (he can still veto) without
   handing back a decision he did not need to make. Reserve real questions for the irreversible:
   spend, publication, merge.

**Asking is not deference; it is unfinished work wearing good manners.** The review gate protects
against bad *merges*, not against an agent doing analysis it was better placed to do.

## 4. Mark the epistemic status of everything

Three states, always distinguishable in the output:

- **Verified** — read it this session; cite file:line, a query result, or command output.
- **Inferred** — reasoned from verified facts; say what the inference rests on.
- **Assumed** — not checked. Say so, and say what would check it.

**Recorded test baselines are re-verifiable claims, not facts.**

> **Failure it prevents:** "174 passed, 1 skipped, 0 failed" was carried across four sessions as a
> settled number. D-022 found the fixtures were **date-dependent** and the suite would have failed on
> the last days of any month. The baseline was a calendar artefact, and this repo has been bitten by
> fixture time-rot before (D-004/D-005).

Re-run before citing a count. A number inherited from a previous session is `assumed`, not
`verified`, however many times it has been repeated.

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

## 7. Verify an experiment's inputs before spending on its outputs

> **Failure it prevents:** three billable calibration runs — **$4.77** — tuned the wording of
> `prompts/classify_item.md` to make the `relevance` axis reach the top of its scale. The axis was
> being scored against a **309-character placeholder** in `config.py`, because
> `docs/USER_CONTEXT.md` — a file that opens by calling itself *"the ground truth AI Verkenner uses
> to score `relevance`"* — is referenced in no Python file at all. The prompts were fine. They were
> correctly answering a question about a context that named no vendor and no project.

Before spending money on a prompt experiment, verify that the **inputs** are what you believe they
are: not just the template, but every variable interpolated into it, read from the runtime path the
production code actually takes. A config default that silently substitutes for a document is
invisible in the prompt file, invisible in the output, and fatal to the experiment.

Corollary: **a silent fallback is a defect, not a convenience.** Where code falls back from a
configured source to a default, it must say so — once, at startup, naming the source in force. The
cheapest possible version of this rule would have saved all three runs.

## 8. No git write operations from a sandboxed or mounted environment

> **Failure it prevents:** the Cowork session reaches this repo through a Linux VM mount. It ran
> `git add` / `git commit`, could not unlink its own `.git/index.lock`, and left a stale lock the
> host could not attribute to any running process. Claude Code correctly diagnosed "a Docker/Linux VM
> held an fd on `.git/index.lock`" and flagged it as a recurring hazard — without being able to see
> that the cause was another agent in the same conversation.

A session working through a mount may **read** git freely — `log`, `diff` and `show` are all fine
and often essential. It must not run anything that takes the index lock: `add`, `commit`,
`checkout`, `stash`, `rm`, `mv`, `merge`, `rebase`.

> **`git status` is NOT a read.** This rule originally listed it as safe. It is not: `status`
> refreshes the index and takes `.git/index.lock` to do so. A mounted session running `git status`
> reproduces the exact incident this section exists to prevent — verified 2026-08-19, when a Cowork
> session left a stale lock doing nothing but checking state. Anything `status` would tell you is
> available from `git diff --stat`, `git diff --cached --stat` and `git ls-files --others
> --exclude-standard`, none of which lock. **Use those.**

Staging and committing belong to the session running natively on the host. A mounted session's
contribution ends at **files written**; it hands over the commit message rather than the commit.

If a stale lock appears, `rm -f .git/index.lock` clears it — but check first that no git process is
genuinely running, and remember that "no process on the host" does not mean "no process".

---

## The one-line version

Verify before you assert · read before you prompt · do it yourself if you can · say which parts you
actually checked · and leave a stop condition wherever an agent might be tempted to be helpful.
