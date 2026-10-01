# Task 009 (M7.5 — Post generator) — X + LinkedIn + Medium drafts

**Status: M7.5 — IN PROGRESS** (implemented on `feat/m7.5-post-generator`; ends at the review gate)

Turn a weekly `Digest` into human-approved, publishable **drafts** — the **Weak Signal of the Week**
and the **Noise Report** — projected to **X**, **LinkedIn**, and **Medium**. See
[`docs/SIGNATURE_OUTPUTS.md`](../docs/SIGNATURE_OUTPUTS.md) §1–3 (X and LinkedIn are now the two
explicit public publishing surfaces) and [`docs/PHASE_1_PLAN.md`](../docs/PHASE_1_PLAN.md) §5 (M7.5).

**Draft-only, human-in-the-loop.** No auto-posting, no social API calls, no browser automation — ever
— in this slice. Publishing to X and LinkedIn is a deliberate human action (paste / assisted-confirm),
not an automated one.

## Goal

From one already-generated `Digest`, emit publishable drafts (markdown) for each surface, preserving
every source URL, separating source **FACT** from **INTERPRETATION**, respecting the hype inversion,
and carrying a header that marks each file a **DRAFT for human review**.

## Scope

- `app/posts/` — a pure `DigestData -> drafts` generator (no LLM, no network):
  - **X (Twitter):** one strong hook post (≤ 280 chars) — the convergence in one line + an evidence
    link + a pointer to the image — plus an optional short thread carrying the facts + all URLs.
  - **LinkedIn:** 1 hook line + 3 tight bullets + a CTA + an image slot. Scroll-stopping.
  - **Medium:** the convergence narrative (cluster + timeline + why it matters) + evidence links
    (every source URL) + a short methodology footnote.
  - Two pieces per run: **Weak Signal of the Week** (from the digest's weak-signals/convergence) and
    the **Noise Report** (from the inverted-hype demotions — loudest-but-emptiest).
- A **static convergence-cluster image** exported server-side when `matplotlib`+`networkx` are present
  (optional `[posts]` extra), else a **clearly-marked placeholder** + a one-line "screenshot the
  Cosmograph Network view" instruction. No headless WebGL renderer.
- Draft files written under `outputs/posts/` (git-ignored) and returned as text.
- **Vault output (create-only):** with `--vault-dir <path>` (default from `VAULT_DIR`), also write each
  draft as a **new** note into `<vault>/00-Inbox/` with frontmatter (`type: post-draft`,
  `tags: [post-draft, ai-verkenner]`, `created`) and a `[[AI Verkenner]]` backlink. Only ever CREATE;
  never modify or delete existing vault files.
- CLI: `python -m app.cli posts --digest <id|latest> [--vault-dir <path>] [--days N]`.

## Non-goals

- No posting / social API / OAuth / browser automation (excluded by `CLAUDE.md`).
- No scheduling, no MCP (M8.5), no new sources, no ranking/priority/graph changes. The priority rule
  is not re-derived — `app/scoring/priority.py` stays the single source of truth.

## Acceptance criteria

- X draft ≤ 280 chars (the hook) with the hook + an evidence link.
- LinkedIn draft has a hook + exactly 3 bullets + a CTA.
- Medium draft has a narrative + evidence links + a methodology footnote.
- The Noise Report lists the hype ≥ `DIGEST_HIGH_HYPE` / archive items (loudest-but-emptiest first).
- The convergence case produces a real **Weak Signal of the Week**; the thin/no-convergence case
  degrades gracefully — **no false "converging" claim**.
- Every draft preserves source URLs and separates FACT from INTERPRETATION.
- The vault writer creates notes in a temp dir and never deletes; a test asserts **no social-posting
  code path exists**.

## Files likely to change

`backend/app/posts/`, `backend/app/digests/generator.py` (extract reusable `build_digest_data`),
`backend/app/digests/sections.py` (expose the noise items, not just the count),
`backend/app/core/config.py` (`VAULT_DIR`), `backend/app/cli.py`, `backend/tests/`, `.env.example`,
`.gitignore` (`outputs/`), `backend/pyproject.toml` (`[posts]` extra), docs.

## Test plan

- Offline + deterministic against two fixture `DigestData`s (thin + synthetic-convergence): the
  per-surface shape assertions above; URLs preserved; fact≠interpretation; graceful degrade; vault
  writer creates-only in a temp dir; a scan asserts no posting/network code path in `app/posts/`.

## Agent constraints

- Draft-only; never post. Preserve source links; respect the hype inversion; keep FACT and
  INTERPRETATION separate. Reuse ranking / priority (do not re-derive). One slice; stop at the review
  gate.
