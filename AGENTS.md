# RE4 Dreamcast: agent rules

Applies to every agent, Claude or Codex. Rewritten 2026-11-19. The earlier text is kept as history in
`port/dreamcast/docs/history/AGENTS_TO_20261015.md` and is not instruction.

**State:** the owner approved the engine plan on 2026-11-19. Lanes start only from a brief written by the integrator.

## Outside contributors start here

The rest of this file is the maintainers' working rules. It names folders on their machine that you do not have and do not need.

- **Public, in this repository:** all port code, build recipes, tools, the toolchain script and Dockerfile, and the documents. Start with `port/dreamcast/CONTRIBUTING-PORT.md`.
- **From the test release:** the disc (GDEMU zip) and the Build-Assets zip. `bash port/dreamcast/contrib.sh` downloads both and gives you a bootable disc.
- **A pull request against the release line** (`t15/int`) is a fix. It needs the change behind a build knob whose default is 0, the same program bytes with the knob off, and no change to collision, events, game state or AI. See "Send a patch" in `CONTRIBUTING-PORT.md`.
- **Speed work goes to the engine line**, not the release line. Read `port/dreamcast/docs/ENGINE_PLAN.md` first and open an issue before writing code.
- Never commit game data, disc images or extracted files.

## Read these four files, in this order

1. `AGENTS.md` (this file).
2. `port/dreamcast/docs/ENGINE_PLAN.md`: goal, architecture, milestones, gates, what stopped.
3. `port/dreamcast/docs/engine/STATUS.md`: milestone state, benchmark numbers, running lanes.
4. `port/dreamcast/docs/engine/HANDOVERS.md`: the newest numbered hand-over.

Then your role file: `CLAUDE.md` or `CODEX.md`. Lane rules: `port/dreamcast/docs/engine/LANES.md`.

Everything else under `port/dreamcast/docs` is history or reference. Read a history file for a specific past result. Do not take work orders from it.

## Goal

- All of the game in a new native Dreamcast engine, playable on a real console, from PS2 assets, with **30 fps as the floor** at the benchmark scenes.
- **Correct means it plays right and looks right:** same kills, triggers, doors, waves, room clears and cutscenes; no desync or stuck events; still pairs for the look. Bit-exact results are not a goal.
- **Never changed:** behaviour. Collision results, event sequencing, game state and AI decisions stay the same. Enemy cap 4. No GameCube assets drawn or played.

## Direction

- **The engine is the program; the original game supplies behaviour** (owner 2026-11-19: "I want all of the game in a new native improved engine"). The engine owns the main loop, memory map, loading, renderer, effects, skeleton and collision services. The original AI, event and script code is hosted on it. Each hot system under that code becomes a native service, one at a time, in console-profile order, each proven to play the same before the old code is deleted. Behaviour code itself is not rewritten.
- **No work on the old path** (owner 2026-11-19). Do not improve, re-measure or re-profile the old drawing path. The engine is judged on the absolute budget, never as a percentage of the old game.
- **Console decides.** Every number is labelled console, MODELLED, Flycast or estimate. Before a console number exists, a modelled or emulator figure counts only if it fits in half the budget.
- **Judge the whole picture** on the fixed benchmark: mean, p99, worst interval, count over 33.3 ms. A gain that does not show there does not merge.
- **First remove repeated work, fix data layout, batch, and convert offline.** Add SH-4 assembly only where the console profile shows the cost and a simpler fix is not enough. Write down why.
- **SH4ZAM is the math and kernel base** (owner 2026-11-19: "the engine needs to leverage sh4zam or improve upon it if there are shortcomings"). Build kernels on it. Where it falls short, improve it in SH4ZAM's own style and offer the change upstream; posting to `gyrovorbis/sh4zam` needs the owner's OK.
- **A change merges switched on, or it does not merge.** No default-off speed switches on the engine line.
- **The release line is frozen to hotfixes.** Do not tune the old drawing path. Do not add engine features to it as switches.

## Roles

| Role | Does | Never does |
|---|---|---|
| **Owner** (the user) | Sets goal and bar; approves the plan, look steps and releases; boots the console | |
| **Integrator** (the agent that resumes) | Merges lanes into `engine` on passing gates; keeps `STATUS.md`; writes briefs; runs console lab sessions; ships hotfixes on the release line | Lane work while lanes are running; edits to a lane's branch |
| **Lane agent** | One lane, one branch, one build folder; hands back in the template | Merging; other lanes' files; `STATUS.md`; deleting outside its own folders |
| **Auditor** | One independent audit per milestone, by an agent that did not write the code | Reviewing each change; blocking on wording |

## Gates

Per milestone, once, on the final image. Full table: `ENGINE_PLAN.md` section 5.

- Frame floor on the console. Plays right. Determinism of one build against itself. Looks right. Memory floors. Disc reads. Asset source.
- Every check ships with an input that makes it fail.
- Knob-off identity and STRICT are debugging tools. They gate only hotfixes on the release line.

## Hand-overs

Numbered, in `port/dreamcast/docs/engine/HANDOVERS.md`. One per milestone or blocking question. Commit, image hashes, numbers with tiers, evidence path, what was not done. A message with no reply is not agreement.

## Repository rules

- `lamb2k/re4dc` is public. Every push is a publication. Push to `origin` only.
- Stage only files you own. Never reset, clean or overwrite another agent's work.
- Private sources, derived assets, discs and captures stay outside Git.
- Releases follow the owner's release rules (scope based, one download, QA disc, images, live notes). The integrator ships them.
