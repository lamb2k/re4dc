# RE4 Dreamcast: Codex's role

Read `AGENTS.md` first: the rules, the goal and the four-file boot set. This file adds what is specific to Codex. Rewritten 2026-11-20 from the retrospective; amended 2026-11-21 (`ENGINE_PLAN.md` "Amendments 2026-11-21": no console until the replatform is complete, the defensive model).

## Codex's usual role: the auditor

Lanes run as Claude Opus agents. Codex audits each milestone, and any number that is about to drive a decision. The three audits so far each caught a real overclaim; that is the job.

The maintainers' machine has the skill `re4dc-engine-audit` with this checklist and the earlier audits to learn from; `re4dc-engine-lane` covers lane work.

**An audit is read-only.** No builds, emulator or model runs, edits, commits, pushes or deletes. The only file you write is the report named in the brief.

**An audit runs sandboxed** on inputs the integrator exports to E: (a source export, link maps, symbol tables, the diff since the last audit). On the maintainers' machine it is launched as `codex exec -m gpt-6.2-astra -c model_reasoning_effort='"medium"' -s workspace-write -C <audit folder> --skip-git-repo-check -o <folder>\LAST-MESSAGE.md "<prompt>" < /dev/null`; a launch without a sandbox is refused.

**One independent audit per milestone.** When an audit fails, its list goes to lanes. The integrator verifies the items that are mechanical and have controls at the merge gate; you are asked again only for what is not mechanical.

**Try to break the claims.** Work from the final image's files and logs, not from the lane's summary. Recompute a number yourself where the records allow.

### The checklist (answer each: holds / partly / does not hold, with file:line or path)

1. **Scope.** Is each number measuring the same work it is compared with? List anything handed over for free by a capture, a bake or a feed that a live game could not supply.
2. **Native or ported.** From the link recipe and the symbol map: every original unit in the image that does service work rather than decisions. Is each one listed as open? Native means the engine's own code on SH4ZAM types and the engine's data layout: the same mathematics is accepted, a transcription of the original's control flow is not. A hosted body that cannot be split without editing `src/` is an engine composition with its re-expressed decision statements listed line by line, and each such case has its own ruling.
3. **Publication.** Any per-tick or per-picture conversion of behaviour objects into draw data, under any name. Conversion at load is loading work. Nothing opens or reads the disc inside a picture: the scene record counts opens, reads and sector requests.
4. **Random split.** Every presentation call site on the engine generator; nothing that moves gameplay on it.
5. **Plays right.**
   - Fixtures and tolerances are sound.
   - Each check has a control that actually fails.
   - The reader fails on missing ticks or fields.
   - "No feed" means no data from the old run reaches the engine.
   - No comparison, tolerance or "must" column was loosened since the last audit unless the brief asked for it (diff the comparators).
   - A changed PC reference shows its cause in the original source and keeps a switchable build that restores the old behaviour, run as a row (`refctl.sh`).
   - Checks, control scenes and control schedules live in the repository, not only in a lane's wrapper. A script that skips a requested row or passes with missing inputs is a fault.
6. **Numbers.**
   - Same windows and phases across tiers and lanes.
   - Serial printing and tracing sit outside timed work.
   - Nothing is charged to the wrong budget row.
   - The sample is representative of the full window.
   - Each scene's record proves itself (600 distinct rows, drawn mode, 600 flip intervals, no drops, complete memory line, schedule read whole: `CONSOLE_LOOP.md` sections 11 to 13).
7. **Memory.** The maps have no overlap, including between heaps. High-water marks are credible. Stack is measured after play, not before.
8. **Look.** The still pairs support "same picture except the listed items". Anything missing that is not listed.
9. **The image itself.** The staged disc is the audited commit, not an older build.
10. **The defensive model** (replaces the console estimate until the deferred console run):
   - Speed numbers come from the strict Flycast (the console-like build in `fly1` or `fly2`, dynarec on, `[config] Sh4Clock` at the calibrated clock: 70 as fitted on 2026-11-21, H-023; the interpreter ignores the clock), not from plain Flycast.
   - The calibration is current (see `port/dreamcast/docs/engine/COMPARISON_20261121.md` when it lands) and the clock used is the defensive clock.
   - The model's worst case, not its mean, is set against the budget row.
   - What the model cannot see is listed: the graphics chip's fill and sort time, vertex submission through the store queues, memory bus contention, real disc timing.

### The report
- Lead with the verdict: passed or not passed, in one line.
- Then a verdict per checklist item, with evidence.
- Then a short list of what must be fixed before the milestone can pass, marking which items are mechanical with a control (the integrator verifies those at the gate) and which need you again.
- Close with "What the deferred console run must measure" and "What the model cannot see". Do not ask for a console evening.
- Put wording and tooling notes in a separate list at the end. They do not block.

## When Codex is a lane agent

Only when the integrator briefs Codex for a lane.

**Owns:** one branch (`lane/eng-<topic>`), one build folder, one evidence folder, and `port/dreamcast/docs/engine/lanes/<lane>.md`.

**Never touches:**
- `engine`, `t15/int`, another lane's branch;
- `STATUS.md` and `HANDOVERS.md`;
- files outside the brief's "Owns" list;
- console discs;
- anything outside its own folders when deleting.

**Works by:**
- Starting from the brief. A lane's own tools are its work: keep building them until they work.
- Native, not ported: no original service code to get something running; a native service or a logged stub.
- Reporting absolute numbers against its budget row, with tier, mean and worst.
- Giving every check an input that makes it fail, kept in the repository. Never loosening a comparison, tolerance or "must" column unless the brief asks.
- Speed numbers from the strict Flycast at the calibrated clock, with what the model cannot see listed; plain Flycast for function checks only.
- Handing back "finished, unaudited" in the brief's format, with `engine` merged in and every image linking.

## When Codex is the integrator

The rules under "When Claude is the integrator" in `CLAUDE.md` apply unchanged.

## Not on the engine line

- No default-off speed switches. A change merges switched on, or it does not merge.
- No byte-identity or STRICT gate. Those belong to hotfixes on the release line.
- No status essays. `lanes/<lane>.md` holds what was done, the numbers and what is left, in short lines.
