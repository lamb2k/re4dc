# RE4 Dreamcast: agent rules

Applies to every agent, Claude or Codex. Rewritten 2026-11-20 from the retrospective (`port/dreamcast/docs/engine/RETRO_20261120.md`); amended 2026-11-21 with the owner's directions of that day (`ENGINE_PLAN.md` "Amendments 2026-11-21"). Earlier text is history in `port/dreamcast/docs/history/` and is not instruction.

**What this is: the replatform.** We are re-platforming RE4 as a Dreamcast native port of the whole game (owner 2026-11-21: "Remember re-platform for Dreamcast native port."). Progress is how much of the game is re-platformed (native and playable in the new engine) and what is left. A finished milestone is a part, not the replatform.

**State:** read `port/dreamcast/docs/engine/STATUS.md`. If it says lanes are stopped or the plan is waiting on the owner, do not start a lane.

## The rules (each one cost us time when it was broken)

1. **Done means audited, modelled and run on the console.** Status words: "finished, unaudited"; after its audit and its model, "finished, modelled, not on console"; "done" only after the console run. That run is deferred until the replatform is complete, not waived.
2. **As many lanes as are not redundant, one integration lane.** (Owner 2026-11-21: "Run as many as possible with an integration lane as long as they aren't redundant"; this replaces "at most two lanes".) Each lane owns named files and one question; no two lanes own the same files or the same fault; only the integration lane merges into `engine` (`E:\RE4DC-Lanes\eng-int\GATE.md`). New scope still goes to the backlog in `ENGINE_PLAN.md` section 7 unless the integrator briefs it as a lane with its own files.
3. **The defensive model decides until the deferred console run.** Label every number: console; MODELLED (strict Flycast, calibrated); MODELLED (PC hardware model); Flycast (plain, function checks only); estimate. A figure passes its budget row on the model's worst case, not its mean, and lists what the model cannot see. No speed claim rests on plain Flycast. Nobody asks the owner for a console evening, an SD card or a date while plan steps 2 to 5 are under way. Details: `LANES.md` section 3.
4. **Native, not ported.** No original service code in the engine image (drawing, skeleton, collision, cloth, effects, routes, camera, input, math, managers). Use the native service or a logged stub. The link check enforces it. Native means the engine's own code on SH4ZAM types and the engine's data layout: the same mathematics is accepted, a transcription of the original's control flow is not.
5. **No publication layer.** Engine state is draw state. Nothing converts a behaviour object into draw data each tick or picture. Conversion at load is loading work. Nothing opens or reads the disc inside a picture.
6. **Plays right by outcome.** Same kills, damage, waves, triggers, doors, room clears and cutscenes, no stuck events, positions within tolerance. Never tick-exact matching with the old game.
7. **Every check ships with an input that makes it fail.** A check that cannot fail is not evidence.
8. **Evidence, not summaries.** Before merging or reporting, re-run the controls and read the files. An agent's summary is a claim.
9. **Never loosen a check.** A loosened comparison, tolerance or "must" column is a gate failure unless the brief asked for it.
10. **Checks live in the repository.** Checks, control scenes and control schedules are in the repository (for example the CONTROLS lists in `port/dreamcast/tools/engine/build_console_disc.sh`, `port/dreamcast/tools/engine/hudcheck.py`), never only in a lane's wrapper. A script that skips a requested row or passes with missing inputs is a fault.
11. **The PC reference changes only with its cause shown** in the original source, and with a switchable build that restores the old behaviour, run as a row (`port/dreamcast/engine/hostref/svc/refctl.sh`).
12. **A scene is OK only if its record proves itself:** 600 distinct rows, drawn mode, 600 flip intervals, no drops, a complete memory line, the schedule read whole, and disc opens, reads and sector requests in play counted (`port/dreamcast/docs/engine/CONSOLE_LOOP.md` sections 11 to 13).

## Outside contributors start here

The rest of this file is the maintainers' working rules. It names folders on their machine that you do not have and do not need.

- **Public, in this repository:** all port code, build recipes, tools, the toolchain script and Dockerfile, and the documents. Start with `port/dreamcast/CONTRIBUTING-PORT.md`.
- **From the test release:** the disc (GDEMU zip) and the Build-Assets zip. `bash port/dreamcast/contrib.sh` downloads both and gives you a bootable disc.
- **A pull request against the release line** (`t15/int`) is a fix. It needs the change behind a build knob whose default is 0, the same program bytes with the knob off, and no change to collision, events, game state or AI. See "Send a patch" in `CONTRIBUTING-PORT.md`.
- **Speed work goes to the engine line**, not the release line. Read `port/dreamcast/docs/ENGINE_PLAN.md` first and open an issue before writing code.
- Never commit game data, disc images or extracted files.

## Read these four files, in this order

1. `AGENTS.md` (this file).
2. `port/dreamcast/docs/ENGINE_PLAN.md`: "The plan as of 2026-11-21" first, then the amendments of 2026-11-21, then goal, budget, architecture, the path (section 7), gates (section 8), workflow (section 9).
3. `port/dreamcast/docs/engine/STATUS.md`: milestone state, numbers, running lanes, what waits on the owner.
4. `port/dreamcast/docs/engine/HANDOVERS.md`: the newest numbered hand-over.

Then your role file (`CLAUDE.md` or `CODEX.md`) and `port/dreamcast/docs/engine/LANES.md`.

Everything else under `port/dreamcast/docs` is history or reference. Read a history file for a specific past result. Do not take work orders from it.

## Goal

- All of the game in a new native Dreamcast engine, playable on a real console, from PS2 assets.
- **30 fps is the floor:** at most two 60 Hz fields between presented pictures, judged on the worst interval.
- **Correct means it plays right and looks right.** Bit-exact results are not a goal.
- **The look (owner 2026-11-21):** "i want the raw stenghts of the syustem to stand out on a ps3 3d asseet foundation with native dreamcast code" (read: on a PS2 3D asset foundation). The PS2 version sets the shapes; the Dreamcast's own strengths are what the picture is built to show: the graphics chip's per-pixel hidden-surface removal and sorted transparency, modifier-volume shadows, 8 MB of video memory with compressed mip-mapped textures, a sharp 480p VGA picture, per-vertex highlights and bump mapping, and the SH-4's vector maths through SH4ZAM. The art may be reworked for it; no GameCube assets.
- **The player's test:** it plays like the GameCube version and runs as fast, at 30 fps (owner 2026-11-21: "People that have played the GameCube version shouldn't have to think about game play choices it should just run as fast.").
- **Never changed:** behaviour (collision results, event order, game state, AI decisions), enemy cap 4, no GameCube assets.
- **Known departures from the GameCube version** (a short list, kept short): the enemy cap of 4 (owner 2026-10-17; revisited when the model shows headroom, the owner's call); quick weapon select (owner 2026-11-21); one picture of input delay from the fixed-field pacer. The PS2 art may be reworked, retouched and repainted for this console (owner 2026-11-21); no GameCube assets.

## How the engine is built

- **The engine is the program; the original game supplies decisions.** The engine owns the main loop, memory map, loading, renderer and every service. Original AI, player, event and script code is hosted on it and calls thin setters. The decisions stay hosted because that keeps play identical, and they are cheap (under 1 ms a picture in Flycast); everything that does the heavy work is native. A decision function goes native only where the model shows it is hot, and then the outcome check must show play unchanged.
- **Random numbers are split.** The original generator serves behaviour only. Effects, cloth, eye and camera sway, voices and rumble use an engine generator. Aim sway moves shots, so it is behaviour.
- **Budget first.** Every lane reports against its row in `ENGINE_PLAN.md` section 4 (behaviour 2, services 9, publication 0, drawing 14, system 3.5 ms), in absolute ms, mean and worst. Never as a percentage of the old game.
- **Content built for this console.** The graphics chip has headroom and the CPU does not. Baked visibility, distance levels and caps, each approved by the owner from still pairs.
- **Simple fixes first.** Remove repeated work, fix data layout, batch, convert offline. Add SH-4 assembly only where the profile shows the cost (until the deferred console run: where the code and the calibrated model show it).
- **SH4ZAM is the math and kernel base.** Improve it in its own style where it falls short. Posting to `gyrovorbis/sh4zam` needs the owner's OK.
- **A change merges switched on, or it does not merge.** No default-off speed switches.
- **The old port is frozen and is a measuring stick.** Hotfixes only on the release line. Do not tune, profile or fix it. It may be measured as a baseline beside the engine: same scenes, same tier, same measure, with what each side draws and runs stated. Nothing chases exact agreement between the two (owner 2026-11-21: "We don't want to get stuck in the exact loop and we need a brand new architecture. But customers need to know how much faster the game will run.").
- **Customer-facing speed claims** need a console number or an explicitly labelled model figure, and the owner's OK before anything is posted.

## Roles

| Role | Who | Does | Never does |
|---|---|---|---|
| **Owner** | the user | Sets goal and bar; approves the plan, look steps (from stills) and releases; boots the console when the replatform is complete or when they ask | |
| **Integrator** | the Claude session that resumes | Writes briefs and steers; checks and merges lanes into `engine`; keeps `STATUS.md` and `HANDOVERS.md`; keeps the one console disc on the shelf (rebuilt when a milestone closes on the model) and runs the deferred console sessions; reports to the owner | Lane work while lanes run; merging on a summary; starting a lane for a new idea; asking the owner for the console while the replatform is under way |
| **Lane agent** | Claude Opus agents | One lane, one branch, one build folder; hands back "finished, unaudited" in the template | Merging; other lanes' files; `STATUS.md`; console discs; deleting outside its own folders |
| **Auditor** | Codex | One independent audit per milestone, and of any number about to drive a decision | Reviewing each change; blocking on wording |

## Gates

Per milestone, once, on the final image. Full table: `ENGINE_PLAN.md` section 8.

- Frame floor on the console (until the deferred console run: on the defensive model's worst case). Plays right by outcome. Determinism of one build against itself. Looks right. Memory with no overlap. No disc reads in play. The link check.
- Knob-off identity and STRICT gate only hotfixes on the release line.

## Hand-overs

Numbered, in `port/dreamcast/docs/engine/HANDOVERS.md`. One per milestone, audit or owner decision. Commit, image hashes, numbers with tiers, evidence path, what was not done. Owner decisions are recorded in the owner's words. A message with no reply is not agreement.

## Repository rules

- `lamb2k/re4dc` is public. Every push is a publication. Push to `origin` only.
- Stage only files you own. Never reset, clean or overwrite another agent's work.
- Private sources, derived assets, discs and captures stay outside Git.
- Releases follow the owner's release rules (scope based, one download, QA disc, images, live notes). The integrator ships them.
