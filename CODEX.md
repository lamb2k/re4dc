# RE4 Dreamcast: Codex's role

Read `AGENTS.md` first. It holds the goal, the direction and the four-file boot set. This file only adds what is specific to Codex.

## When Codex is a lane agent (the usual case)

**Owns**
- One lane: one branch (`lane/eng-<topic>`), one build folder, one evidence folder, named in its brief.
- `port/dreamcast/docs/engine/lanes/<lane>.md`.

**Never touches**
- `engine`, `t15/int`, or another lane's branch.
- `port/dreamcast/docs/engine/STATUS.md` and `HANDOVERS.md`.
- Files outside its brief's "Owns" list. If the work needs one, it asks in its hand-back.
- Anything outside its own folders when deleting.

**Works by**
- Starting from the brief. If the brief is unclear, it asks one blocking question and stops.
- Reporting the whole benchmark picture (mean, p99, worst interval, over-budget count, tier), never a subsystem number alone.
- Giving every check an input that makes it fail.
- Testing two distinct hypotheses on a failing gate, then writing the blocker. It does not loosen a tolerance.

**Hands off by**
- The hand-back in the brief template: table, commit, image hash, evidence path, what was not done.
- Pushing its branch to `origin`. It does not merge.

## When Codex is the auditor

- One independent audit per milestone, of code it did not write.
- It reads the final image's evidence against the gates in `ENGINE_PLAN.md` section 5 and tries to break each claim.
- It does not review each change, and it does not block on wording or tooling style.

## When Codex is the integrator

The rules under "When Claude is the integrator" in `CLAUDE.md` apply unchanged.

## Not on the engine line

- No default-off speed switches. A change merges switched on, or it does not merge.
- No byte-identity or STRICT gate. Those belong to hotfixes on the release line.
- No status essays. `lanes/<lane>.md` holds what was done, the numbers and what is left, in short lines.
