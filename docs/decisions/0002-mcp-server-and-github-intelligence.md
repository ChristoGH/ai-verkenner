# ADR 0002 — Read-only MCP server surface; GitHub intelligence stays curated

## Status

Accepted — 2026-06-18. Extends [ADR 0001](0001-graph-vector-visual-stack.md). Touches the
[`../../CLAUDE.md`](../../CLAUDE.md) exclusions (see Decision); CLAUDE.md is updated in the same
change set that implements the MCP milestone.

## Date

2026-06-18

## Context

Two output ambitions emerged once the graph/vector stack ([ADR 0001](0001-graph-vector-visual-stack.md))
gave AI Verkenner a real corpus of enriched items, entities, and convergences:

1. **Agentic consumption.** The most modern way to consume this intelligence is not only a
   dashboard or a newsletter, but a programmatic surface other agents can call — "ask my radar"
   instead of re-searching the open web. MCP is the natural protocol; the data already lives in
   SQLite + Qdrant + Neo4j by milestone M7.
2. **GitHub as an early signal.** Code ships before blog posts, so watched GitHub activity (new
   repos, star-velocity, advisories) is often the *earliest* indicator of a forming trend. The
   project already ingests `github_releases`. The question is whether broadening GitHub coverage
   crosses the "no broad crawler" line.

Both brush against current `CLAUDE.md` exclusions: a "plugin framework" and "Slack/Teams/email
integrations" are excluded, and a "broad web crawler / browser automation" is excluded. We need to
state precisely what is in and what stays out.

## Decision

**1. Adopt a read-only MCP server as a distribution surface (Phase-1.5 milestone M8.5).** It
exposes the existing intelligence — search, weak signals, entity dossiers, digests — as MCP tools
and resources over the SQLite/Qdrant/Neo4j stores. It is:

- **Read-only** in Phase 1: no tool may write, post, trigger ingestion, or mutate state.
- **Local**: served on the user's machine alongside the backend; no external exposure.
- **A thin projection**, not a new pipeline: it reads the same stores the dashboard reads.

This is explicitly *not* the excluded "plugin framework" (we are not building an extensibility/
plugin system) and *not* a third-party messaging integration (Slack/Teams/email remain excluded).

**2. Broaden GitHub coverage, but only as curated source types via the GitHub API.** Add
`github_star_velocity`, `github_new_repos`, `github_advisories`, and `github_changes` as
`source_type`s driven by *watched* orgs / users / topics declared in `sources.yaml`. Rate-limited,
fail-safe per source, every item keeps its URL.

This stays inside the **curated-pipeline invariant** and does **not** authorise a broad GitHub
crawler, scraping, or browser automation — those remain excluded. "Watched list in `sources.yaml`
+ official API" is the line; "discover and fetch arbitrary repos" is over it.

## Alternatives

- **No MCP; dashboard + newsletter only.** Simpler, but forgoes the agentic surface that is a
  core part of the envisioned value and is nearly free once the stores exist. Rejected.
- **A read/write MCP (let agents post, re-rank, trigger runs).** More powerful, but adds auth,
  safety, and mutation-consistency problems disproportionate to a personal Phase-1 tool. Deferred;
  Phase 1 is read-only by decision.
- **GitHub via a generic crawler / scraping trending pages.** Higher coverage, but violates the
  curated-pipeline invariant and adds legal/operational risk. Rejected in favour of the API +
  watched-list model.
- **Skip GitHub-intelligence, keep only releases.** Loses the earliest signal source and the
  best convergence feeder. Rejected.

## Consequences

**Easier:** the user's other agents can query the radar directly; GitHub gives earlier convergence
signals and richer graph edges (`repo↔org↔concept`); the published outputs (Weak Signal of the
Week, Noise Report) gain a high-signal feed.

**Harder / new cost:** an MCP server is another surface to keep in sync with the store schemas (kept
small and read-only to contain this); GitHub API rate limits and token handling (handle per-source,
fail safe); more source types to validate in the registry.

**Required follow-on (same change set as implementation):**

- Update [`../../CLAUDE.md`](../../CLAUDE.md): note the read-only MCP surface and the curated
  GitHub source types as sanctioned by this ADR; explicitly **keep** excluded: plugin framework,
  Slack/Teams/email integrations, broad crawler, browser automation, auth, multi-user, billing.
- Reflect the new source types in `sources/sources.yaml` and the source-registry validation.
- Keep the read-only guarantee covered by a test on the MCP surface.

Operationalised in [`../PHASE_1_PLAN.md`](../PHASE_1_PLAN.md) (GitHub in M3/M5; post generator
M7.5; MCP server M8.5) and detailed in [`../SIGNATURE_OUTPUTS.md`](../SIGNATURE_OUTPUTS.md).
