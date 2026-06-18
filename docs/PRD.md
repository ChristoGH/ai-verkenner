# AI Verkenner — Product Requirements Document

## Problem

Anyone working in or near AI is drowning. Labs, framework maintainers, tool vendors, and
researchers all ship constantly, across dozens of feeds, blogs, changelogs, and preprint
servers. Reading even a fraction is a part-time job, and the cost of *missing* the right thing —
a breaking change in a tool you depend on, a security advisory, an early signal of where the
field is heading — is high. Generic news aggregators make this worse: they optimise for clicks
and volume, surface hype, and have no idea what *you* work on.

The unmet need is not "more news". It is **triage**: a trusted scout that reads the curated set
of sources that matter to you, separates signal from noise, and tells you the few things worth
your attention today — and what to do about each.

## Users

The primary user is a **technically literate AI practitioner** — an engineer, researcher,
founder, or product lead — who:

- depends on specific tools and frameworks (and is exposed when they change),
- wants to track a defined set of labs, projects, and researchers,
- cares about early signals, not just headlines,
- has little time and low tolerance for noise.

The MVP is explicitly **single-user and personal**. Multi-user is out of scope.

## Desired experience

The user opens AI Verkenner and, in under a minute, knows where they stand. The ideal output
reads like a briefing from a sharp assistant:

> *"Here are 7 developments since yesterday. **Two affect you now**: a breaking change in a
> framework you use, and a security advisory in your stack. **One is a weak signal** worth
> watching — an early research direction that could matter in six months. The other four are
> noise; I've demoted them. Here's what I'd do about the first two."*

Each item is a card that separates **what happened** (source fact, with the link) from **why it
matters** (interpretation), states **how it connects to your work**, and gives a **recommended
action**. The user can react — useful / not useful / save / ignore — and those reactions sharpen
future ranking. Once a week, the same intelligence is rolled up into a decision-oriented digest.

## MVP features

- **Curated source registry** — a maintained `sources.yaml` of trusted origins (RSS/Atom,
  GitHub releases, arXiv queries), each with a trust level and an enable switch.
- **Fail-safe ingestion** — fetch every enabled source; one broken source never breaks the run.
- **Deduplicated storage** — raw items persisted in SQLite, de-duplicated.
- **LLM enrichment** — classification, the five scores (relevance, novelty, actionability,
  strategic_potential, hype — *hype inverted*), summary, why-it-matters, connection-to-work,
  recommended action, and a derived priority class.
- **Core Radar dashboard** — a ranked feed of enriched item cards.
- **Horizon Scanner** — surfacing of weak signals (the low-relevance / high-future quadrant).
- **Early Warning** — prominent treatment of immediate-priority items.
- **Feedback actions** — useful / not useful / save / ignore, feeding ranking.
- **Weekly digest** — a decision-oriented periodic briefing.

## Non-goals (MVP)

- No broad web crawling or scraping beyond the curated registry.
- No multi-user, accounts, or auth.
- No vector database, graph database, Redis, Postgres, or Kubernetes.
- No third-party delivery integrations (Slack, Teams, email).
- No browser automation, billing, or plugin framework.
- Not a social feed, not a chat assistant, not a general news reader.

## Success criteria

- The user can open the dashboard and, in **under a minute**, identify what (if anything)
  needs action today.
- **Precision over recall**: when AI Verkenner flags something as immediate priority, it is
  genuinely worth acting on. False urgency is the cardinal sin.
- **No missed urgent items** from sources in the registry (security advisories / breaking
  changes in the user's own stack reliably surface as immediate_priority).
- **Every surfaced item keeps its source link** and cleanly separates fact from interpretation.
- The weekly digest is something the user actually reads to the end because it drives decisions,
  not because it lists links.
