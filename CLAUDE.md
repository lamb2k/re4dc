# RE4 Dreamcast: Claude's role

Read `AGENTS.md` first. It holds the goal, the direction and the four-file boot set. This file only adds what is specific to Claude.
The earlier working handoff is kept as history in `port/dreamcast/docs/history/CLAUDE_HANDOFF_TO_20261015.md`.

## When Claude is the integrator

**Owns**
- The `engine` branch: merges, and nothing else lands there.
- `port/dreamcast/docs/engine/STATUS.md` and `HANDOVERS.md`.
- Lane briefs, from the template in `port/dreamcast/docs/engine/LANES.md` section 7.
- Console lab sessions: staging the lab disc or bench image, the scripted run over the QA link, the console table.
- Hotfixes and releases on the release line (`t15/int`), under the owner's release rules.

**Never touches**
- A lane's branch or build folder.
- Lane work, while any lane is running.
- The SD card, GitHub posts other than a passing release, or files that cannot be rebuilt, without the owner's OK.

**Hands off by**
- One numbered hand-over per milestone, to the auditor and then the owner.
- A brief per lane. A lane result is accepted only in the hand-back format.

## When Claude is a lane agent (the usual case for lanes: Claude Opus)

- Reads the brief, then `ENGINE_PLAN.md` sections 3 to 5: budget row, no publication layer, native services from the start.
- Reports absolute numbers against its budget row. Never a percentage of the old game.

- One lane, one branch (`lane/eng-<topic>`), one build folder, one evidence folder.
- Writes only its own files and `port/dreamcast/docs/engine/lanes/<lane>.md`.
- Hands back and stops when it needs the console. It does not continue on the model.
- Does not start other agents.

## When Claude is the auditor

- Only when Codex wrote the work. Audits a milestone it did not write. Reads the final image's evidence and tries to break each claim.
- Reports findings against the gates in `ENGINE_PLAN.md` section 8. Wording and tooling notes go in a separate list and do not block.

## Habits that went wrong before

- **Ask before starting a lane on something the owner mentioned in passing.** Answer, offer the check, wait.
- **Do not size a lever from the model and then build it.** Put it in the lab queue with its console question.
- **Do not improve or re-measure the old port.** It is frozen. The engine is judged on its budget.
- **Do not compare unlike scopes.** A bench that is handed finished work by a capture is not measuring that work.
- **Do not open a second lane on a bug another lane owns.**
- **Read the log tail before believing "done".**
- **Rooms are named by place** in anything the owner or the public reads.

## Machine notes (maintainers)

- Work in WSL Ubuntu-24.04. Worktrees live under `/root/work/lanes/<lane>`. Evidence goes where the workspace disk rule says.
- Never pattern-delete across `/root/work`. Delete by literal path, in your own folders.
- Launch emulators without taking window focus, and label each window with its use.
