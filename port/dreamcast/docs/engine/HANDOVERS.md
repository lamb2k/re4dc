# Engine line hand-overs

One numbered entry per milestone or blocking question. Newest first. Format: commit, image hashes, numbers with tiers, evidence path, what was not done.

## H-007 (2026-11-19): E0 bench audit (Codex)

- **From:** the auditor (Codex). **To:** the integrator.
- **Commit audited:** lane/eng-e0 renderer e28d7f2c2, hand-back 46cb02609. Report: E:\RE4DC-Lanes\eng-e0\AUDIT-E0.md.
- **Holds:** the speedup is real (cross 45.4 to 14.2 ms mean MODELLED, hay-fork 99.7 to 16.1). The timed path does every drawing step at run time; no captured pick lists, pre-projected corners or shadow packets.
- **Does not hold or only partly:**
  - Console entry: 25 of 25 cross pictures over 7 ms MODELLED. Estimated console mean 18.5 to 28.4 ms against the 14 ms row.
  - A clipping error: a multi-bone part can skip near-plane clipping.
  - Baked visibility is validated only on the recorded route, reuses a cell's mask at any camera height, and at 7,260 bytes a camera cell cannot scale to a whole room.
  - Look: mean absolute error 9.89 (cross) and 7.72 (farm) levels; lighting, flames and the weapon differ, beyond hair and HUD.
  - Memory accounting is incomplete; texture copies stay in main RAM.
  - The hand-back said every cross picture was over 14 ms; the files show 14 of 25.
- **Action:** lane eng-e0b fixes these (not a speed round). Content changes still wait for the owner.

## H-006 (2026-11-19): plan version 2, the F-Zero X approach; lanes move to Claude Opus

- **From:** the owner. **To:** the integrator.
- **Words:** "Write a plan for the right path forward - we should take the same approach as the fzero session can you ask it how it won", then "Update instructions and switch to opus to get this work done".
- **What the F-Zero coordinator said (11-19, all emulator numbers, no hardware run yet):** about 37 ms of its gain came from no longer hosting the original simulation (22.1 ms) and the publication layer that converts original state into draw data (17.3 ms); changing what is drawn bought the last 5 to 8 ms. It says RE4 is probably missing a whole-frame budget with hosted-original rows, owner-approved content changes, a worst-interval floor gate, and an early console run of the bench.
- **Changed:** ENGINE_PLAN.md rewritten as version 2 (budget rows, no publication layer, host only decisions, content for this console, milestones E0 to E4). AGENTS.md, CLAUDE.md, CODEX.md and LANES.md updated: lanes run as Claude Opus agents, Codex audits each milestone, one model-only round per milestone, lane limits two build plus two PC-only.
- **Waiting on the owner:** approval of E0 to E4 and the budget rows; the content look calls; the SD card.

## H-005 (2026-11-19): scope widened to the whole game in a native engine

- **From:** the owner. **To:** the integrator.
- **Words:** "I don't want to pile on improvement for old work - ensure we are following the guidance and lessons learned to go native." Then: "I want all of the game in a new native improved engine", choosing "Engine owns everything, original behaviour hosted on it".
- **Meaning:** the engine is the program (main loop, memory map, loading, renderer, effects, skeleton, collision services). The original AI, event and script code is hosted on it. Hot systems become native services one at a time, in console-profile order, each proven to play the same. Behaviour code is not rewritten.
- **Changed:** ENGINE_PLAN.md sections 1, 3, 4, 6 and 8; AGENTS.md goal and direction. M2 is now the engine shell; M3 is native services round 1; M5 is the rest of the game.
- **Lanes:** eng-bench continues (renderer, absolute budget). disc2-play handed back its chapter 3-1 play-through work. New PC-only lane eng-shell-map: the service boundary between behaviour code and the engine.

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
