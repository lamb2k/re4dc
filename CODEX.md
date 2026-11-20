# RE4 Dreamcast: Codex's role

Read `AGENTS.md` first: the eight rules, the goal and the four-file boot set. This file adds what is specific to Codex. Rewritten 2026-11-20 from the retrospective.

## Codex's usual role: the auditor

Lanes run as Claude Opus agents. Codex audits each milestone, and any number that is about to drive a decision. The three audits so far each caught a real overclaim; that is the job.

The maintainers' machine has the skill `re4dc-engine-audit` with this checklist and the earlier audits to learn from; `re4dc-engine-lane` covers lane work.

**An audit is read-only.** No builds, emulator or model runs, edits, commits, pushes or deletes. The only file you write is the report named in the brief.

**Try to break the claims.** Work from the final image's files and logs, not from the lane's summary. Recompute a number yourself where the records allow.

### The checklist (answer each: holds / partly / does not hold, with file:line or path)

1. **Scope.** Is each number measuring the same work it is compared with? List anything handed over for free by a capture, a bake or a feed that a live game could not supply.
2. **Native or ported.** From the link recipe and the symbol map: every original unit in the image that does service work rather than decisions. Is each one listed as open?
3. **Publication.** Any per-tick or per-picture conversion of behaviour objects into draw data, under any name.
4. **Random split.** Every presentation call site on the engine generator; nothing that moves gameplay on it.
5. **Plays right.**
   - Fixtures and tolerances are sound.
   - Each check has a control that actually fails.
   - The reader fails on missing ticks or fields.
   - "No feed" means no data from the old run reaches the engine.
6. **Numbers.**
   - Same windows and phases across tiers and lanes.
   - Serial printing and tracing sit outside timed work.
   - Nothing is charged to the wrong budget row.
   - The sample is representative of the full window.
7. **Memory.** The maps have no overlap, including between heaps. High-water marks are credible. Stack is measured after play, not before.
8. **Look.** The still pairs support "same picture except the listed items". Anything missing that is not listed.
9. **The image itself.** The staged disc is the audited commit, not an older build.
10. **Console estimate.** The modelled figure times the model's known error, against the budget row.

### The report
- Lead with the verdict: passed or not passed, in one line.
- Then a verdict per checklist item, with evidence.
- Then a short list of what must be fixed before the milestone can pass on the console.
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
- Giving every check an input that makes it fail.
- Handing back "finished, unaudited" in the brief's format, with `engine` merged in and every image linking.

## When Codex is the integrator

The rules under "When Claude is the integrator" in `CLAUDE.md` apply unchanged.

## Not on the engine line

- No default-off speed switches. A change merges switched on, or it does not merge.
- No byte-identity or STRICT gate. Those belong to hotfixes on the release line.
- No status essays. `lanes/<lane>.md` holds what was done, the numbers and what is left, in short lines.
