# Engine line hand-overs

One numbered entry per milestone or blocking question. Newest first. Format: commit, image hashes, numbers with tiers, evidence path, what was not done.

## H-004 (2026-11-19): guideline check (owner asked "Are we still operating under the right guidelines")

- **Holding:** lane limits, tiers on every number, no input sent to windows, Codex builds and Claude audits, SD card / GitHub / SH4ZAM boundaries.
- **Drift and fix:**
  1. Model-only rounds: M1 round 3 is the last before a console run.
  2. Briefs caused 4 of 5 lane stops: an integrator brief checklist goes in LANES.md section 7.
  3. M1 thresholds disagreed: one table in ENGINE_PLAN.md section 4.
  4. Mid-milestone audit: an exception is written into LANES.md section 5.
  5. Bookkeeping: OPT-TRACK.md and these hand-overs brought up to date.

## H-003 (2026-11-19): M1 round 2 audit

- **From:** independent auditor (Claude). **To:** the integrator.
- **Commit audited:** lane/eng-bench 0b6f207ca.
- **Finding:** the claimed MODELLED -51.7% (cross) and -45.6% (hay-fork) are not like for like. Like for like: -3 to -5.5 ms (18-30%) and -8 to -10.5 ms (22-28%).
- **Evidence:** E:\RE4DC-Lanes\eng-bench\AUDIT-M1-R2.md.
- **Action:** round 3 steered (STEER-004): the whole drawing path at runtime from logic outputs, a fair one-tick baseline, compact whole-room bakes, 20+ timed pictures.

## H-002 (2026-11-19): plan approved

- **From:** the owner. **To:** the integrator.
- **Words:** "get to work", then, asked to confirm, "Yes, all 10 as recommended". All ten recommended answers in H-001 stand.
- **Added the same day:** "the engine needs to leverage sh4zam or improve upon it if there are shortcomings" (ENGINE_PLAN.md section 3, AGENTS.md).
- **Console:** "Later, prepare it and wait". The lab disc is prepared; it goes on the SD card when the owner says the card is in.
- **Next:** `engine` branch from this commit; lanes lab33 (M0) and eng-bench (M1).

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
