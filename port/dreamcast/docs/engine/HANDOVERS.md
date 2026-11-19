# Engine line hand-overs

One numbered entry per milestone or blocking question. Newest first. Format: commit, image hashes, numbers with tiers, evidence path, what was not done.

## H-001 (2026-11-19): plan proposed, owner decisions needed

- **From:** Claude (self-assessment session). **To:** the owner.
- **Commit:** this branch, `docs/reassess-20261119`, from `t15/int` a5aca9cf9. Docs only. No image.
- **What it is:** [ENGINE_PLAN.md](../ENGINE_PLAN.md), [LANES.md](LANES.md), rewritten `AGENTS.md` and `CLAUDE.md`, new `CODEX.md`.
- **Numbers:** all from the console session of 2026-11-11 and the A/B of 2026-11-12 (Test 27.1). Nothing new was measured.
- **Decisions needed:**
  1. Confirm the goal and the bar: 30 fps as the floor at the benchmark scenes; "plays right and looks right", not bit-exact.
  2. Approve the engine line: a new renderer proven on a bench image first, then in the game, instead of more switches in the legacy image.
  3. Retire knob-off identity and STRICT as gates on the engine line. They stay for hotfixes on the release line.
  4. Freeze speed work on the legacy drawing path.
  5. Book the M0 console session.
  6. Order of the room work while the renderer is rebuilt.
  7. Who audits each milestone.
- **Not done:** no code, no build, no console run. The contributor documents (`CONTRIBUTING-PORT.md`, the kit) still describe the release line and are correct for it; they change when the first engine-line release ships. Three front-page lines still point at the old `CLAUDE.md` content (`README.md` line 463, `port/dreamcast/README.md` lines 54 and 120); they are updated when this branch is approved and merged.
