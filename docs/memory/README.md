# docs/memory — module maps for AI Verkenner

One file per module/subsystem (e.g. `core.md`, `api.md`, `ui.md`). Each map
tells an agent what it needs to know BEFORE opening source files:

- what the module is responsible for (and explicitly not responsible for)
- the key files and entry points
- data shapes / tables / contracts it owns
- invariants and gotchas
- pointers to relevant decisions in `docs/DECISIONS.md`

Rules:
- Maps are synced to the code at end-of-session, scoped to the diff
  (commit message: `memory: sync to <sha>`).
- A map that contradicts the code is a bug — fix the map in the same commit.
- Keep each map under ~100 lines; link to the decision log instead of
  restating rationale.
