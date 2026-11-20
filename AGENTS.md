# RE4 Dreamcast: agent rules

Applies to every agent, Claude or Codex. Rewritten 2026-11-20 from the retrospective (`port/dreamcast/docs/engine/RETRO_20261120.md`). Earlier text is history in `port/dreamcast/docs/history/` and is not instruction.

**State:** read `port/dreamcast/docs/engine/STATUS.md`. If it says lanes are stopped or the plan is waiting on the owner, do not start a lane.

## The eight rules (each one cost us time when it was broken)

1. **Done means audited and run on the console.** Until then work is "finished, unaudited", and that is the only status you report.
2. **One milestone at a time, at most two lanes.** New scope goes to the backlog in `ENGINE_PLAN.md` section 7, not into a new lane.
3. **The console decides.** Label every number console, MODELLED, Flycast or estimate. One model-only speed round per milestone, then the console. If the console is unavailable, do work that does not depend on timing.
4. **Native, not ported.** No original service code in the engine image (drawing, skeleton, collision, cloth, effects, routes, camera, input, math, managers). Use the native service or a logged stub. The link check enforces it.
5. **No publication layer.** Engine state is draw state. Nothing converts a behaviour object into draw data each tick or picture.
6. **Plays right by outcome.** Same kills, damage, waves, triggers, doors, room clears and cutscenes, no stuck events, positions within tolerance. Never tick-exact matching with the old game.
7. **Every check ships with an input that makes it fail.** A check that cannot fail is not evidence.
8. **Evidence, not summaries.** Before merging or reporting, re-run the controls and read the files. An agent's summary is a claim.

## Outside contributors start here

The rest of this file is the maintainers' working rules. It names folders on their machine that you do not have and do not need.

- **Public, in this repository:** all port code, build recipes, tools, the toolchain script and Dockerfile, and the documents. Start with `port/dreamcast/CONTRIBUTING-PORT.md`.
- **From the test release:** the disc (GDEMU zip) and the Build-Assets zip. `bash port/dreamcast/contrib.sh` downloads both and gives you a bootable disc.
- **A pull request against the release line** (`t15/int`) is a fix. It needs the change behind a build knob whose default is 0, the same program bytes with the knob off, and no change to collision, events, game state or AI. See "Send a patch" in `CONTRIBUTING-PORT.md`.
- **Speed work goes to the engine line**, not the release line. Read `port/dreamcast/docs/ENGINE_PLAN.md` first and open an issue before writing code.
- Never commit game data, disc images or extracted files.

## Read these four files, in this order

1. `AGENTS.md` (this file).
2. `port/dreamcast/docs/ENGINE_PLAN.md`: goal, budget, architecture, the path (section 7), gates (section 8), workflow (section 9).
3. `port/dreamcast/docs/engine/STATUS.md`: milestone state, numbers, running lanes, what waits on the owner.
4. `port/dreamcast/docs/engine/HANDOVERS.md`: the newest numbered hand-over.

Then your role file (`CLAUDE.md` or `CODEX.md`) and `port/dreamcast/docs/engine/LANES.md`.

Everything else under `port/dreamcast/docs` is history or reference. Read a history file for a specific past result. Do not take work orders from it.

## Goal

- All of the game in a new native Dreamcast engine, playable on a real console, from PS2 assets.
- **30 fps is the floor:** at most two 60 Hz fields between presented pictures, judged on the worst interval.
- **Correct means it plays right and looks right.** Bit-exact results are not a goal.
- **Never changed:** behaviour (collision results, event order, game state, AI decisions), enemy cap 4, no GameCube assets.

## How the engine is built

- **The engine is the program; the original game supplies decisions.** The engine owns the main loop, memory map, loading, renderer and every service. Original AI, player, event and script code is hosted on it and calls thin setters.
- **Random numbers are split.** The original generator serves behaviour only. Effects, cloth, eye and camera sway, voices and rumble use an engine generator. Aim sway moves shots, so it is behaviour.
- **Budget first.** Every lane reports against its row in `ENGINE_PLAN.md` section 4 (behaviour 2, services 9, publication 0, drawing 14, system 3.5 ms), in absolute ms, mean and worst. Never as a percentage of the old game.
- **Content built for this console.** The graphics chip has headroom and the CPU does not. Baked visibility, distance levels and caps, each approved by the owner from still pairs.
- **Simple fixes first.** Remove repeated work, fix data layout, batch, convert offline. Add SH-4 assembly only where the console profile shows the cost.
- **SH4ZAM is the math and kernel base.** Improve it in its own style where it falls short. Posting to `gyrovorbis/sh4zam` needs the owner's OK.
- **A change merges switched on, or it does not merge.** No default-off speed switches.
- **The old port is frozen.** Hotfixes only on the release line. Do not improve, re-measure or re-profile it.

## Roles

| Role | Who | Does | Never does |
|---|---|---|---|
| **Owner** | the user | Sets goal and bar; approves the plan, look steps and releases; boots the console | |
| **Integrator** | the Claude session that resumes | Writes briefs and steers; checks and merges lanes into `engine`; keeps `STATUS.md` and `HANDOVERS.md`; builds the console disc and runs console sessions; reports to the owner | Lane work while lanes run; merging on a summary; starting a lane for a new idea |
| **Lane agent** | Claude Opus agents | One lane, one branch, one build folder; hands back "finished, unaudited" in the template | Merging; other lanes' files; `STATUS.md`; console discs; deleting outside its own folders |
| **Auditor** | Codex | One independent audit per milestone, and of any number about to drive a decision | Reviewing each change; blocking on wording |

## Gates

Per milestone, once, on the final image. Full table: `ENGINE_PLAN.md` section 8.

- Frame floor on the console. Plays right by outcome. Determinism of one build against itself. Looks right. Memory with no overlap. No disc reads in play. The link check.
- Knob-off identity and STRICT gate only hotfixes on the release line.

## Hand-overs

Numbered, in `port/dreamcast/docs/engine/HANDOVERS.md`. One per milestone, audit or owner decision. Commit, image hashes, numbers with tiers, evidence path, what was not done. Owner decisions are recorded in the owner's words. A message with no reply is not agreement.

## Repository rules

- `lamb2k/re4dc` is public. Every push is a publication. Push to `origin` only.
- Stage only files you own. Never reset, clean or overwrite another agent's work.
- Private sources, derived assets, discs and captures stay outside Git.
- Releases follow the owner's release rules (scope based, one download, QA disc, images, live notes). The integrator ships them.
