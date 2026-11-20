# Engine line: lane rules

Binding for every agent on the engine line. Plan: [../ENGINE_PLAN.md](../ENGINE_PLAN.md). Each rule comes from a mistake listed at the end.

## 1. Lines and branches

| Branch | Purpose | Who merges |
|---|---|---|
| `engine` | Integration line for the engine plan | The integrator only |
| `lane/eng-<topic>` | One lane's work | Its owner pushes; the integrator merges |
| `t15/int` | Release line, frozen to hotfixes | The integrator, under the release rules |

- A lane pulls `engine` into its branch. It never merges another lane's branch.
- A change merges **switched on**, or it does not merge. The engine line has no default-off speed switches. Run-time lab arms for console A/B are the one exception, and they are listed in `STATUS.md`.
- One bug or area has one owner lane.

## 2. Lane limits

- **One milestone at a time, at most two lanes** (plan version 3, after the 2026-11-20 retrospective). New scope goes to the backlog in `ENGINE_PLAN.md` section 7, not into a new lane. The machine is shared with other projects.
- **A lane reports "finished, unaudited".** Done means audited and run on the console.
- **Lanes do not stage console discs.** The integrator rebuilds one engine disc from `engine` for each console session.
- PC-only lanes may not start an emulator.
- Lanes run as Claude Opus agents; Codex audits each milestone.
- A lane uses its own build folder and its own evidence folder. It deletes only inside them, by literal path.
- Processes are stopped by pid, never by name.
- A staged disc that is queued for the console gets a `KEEP` file in its folder. The hourly cleanup deletes disc images (`track0*`, `disc.gdi`) untouched for 6 hours unless the folder or a parent has one.
- Flycast runs only from fixed slot folders that the integrator provisions once per lane (`fly1`, `fly2` console-like; `std1`, `std2` standard harness; see the lane's SLOTS.txt). Copying configs and data inside a slot is fine; a copy of flycast.exe at any other path is not. GDB off unless needed.
- A lane that waits on the console does not chain into model-only work. It hands back and stops.

## 3. Measuring

- **Tiers:** every number is labelled console, MODELLED, Flycast or estimate.
- **The benchmark is fixed:** village cross, bell fight, farm entry, farm hay-fork view, farm quiet view, lake fight, castle hall. Same presets, cap 4.
- **Report the whole picture:** mean, p99, worst interval and count over 33.3 ms, over 600 pictures, against the lane's budget row. The floor is at most two fields between presented pictures.
- **One model-only round per milestone.** After it, the next step is the console.
- **A/B on console is one image:** two arms switched at run time in the same boot, in A/B/A order. Never two builds, never two sessions.
- **Before a console number exists,** a modelled or emulator figure counts only if it fits in half the budget.
- **A new measuring tool needs a control** that makes it read wrong on purpose, before its numbers are used.
- **Speed is the game's own tick and picture counters,** never the display's refresh.

- **Go native.** The new path is measured against the budget, not against the old game. No lane re-times, re-profiles or improves the old drawing path. The lessons from our other ports are part of every brief:
  - the console decides, and models under-read it by 1.3 to 2x;
  - remove repeated work first, with change flags per picture;
  - no disc reads in play;
  - the engine image links no original game code;
  - every check ships with an input that fails it.

## 3b. Native, not ported (owner 2026-11-19)

- A lane that hosts a character never links original service code (effects, skeleton, collision, cloth, routes, managers) to get it running. It uses the native service or a logged stub and lists the stub.
- Presentation code never draws from the original generator.

## 4. Gates

- Gates are per milestone and are listed in the plan, section 8. They run once, on the final image.
- A lane's own merge gate is the smallest set that proves its change: it builds, it boots, the benchmark does not get worse, and its own check passes and can fail.
- Every check ships with an input that makes it fail.
- A failing gate gets two distinct hypotheses tested. Then the blocker is written as a hand-over. No tolerance is loosened to pass.
- That rule is for milestone and merge gates. A lane's own tools (capture, bake, checkers) are its work: keep building them until they work. Hand back early only for the brief's stop rule, a console need, or a blocker outside the lane's own files.
- Byte identity with a previous build is not a gate on the engine line.
- **The integrator's merge gate:** the link check passes (no original service symbol outside the allowed list), the lane's controls re-run, every image links, and the plan's section 3 rules hold. A lane's summary is not evidence.
- **Plays right is checked by outcome** (a scripted player on the engine and the reference: kills, damage, waves, triggers, time to clear), not tick for tick against the old game.

## 5. Audits and hand-overs

- **One independent audit per milestone,** by the agent that did not write the code. It reads the final image's evidence and tries to break the claims.
- No review round per change. Tooling and wording findings do not block a merge.
- Exception: a lane number that is about to drive a decision (a stop, a milestone call, a plan change) gets an independent check first.
- **Hand-overs are numbered** (`H-001`, `H-002`, ...) in [HANDOVERS.md](HANDOVERS.md). One per milestone or per blocking question. Each has: commit, image hashes, numbers with tiers, evidence path, what was not done.
- A message with no reply is not agreement.

## 6. Documents

- The boot set is four files: `AGENTS.md`, `port/dreamcast/docs/ENGINE_PLAN.md`, `port/dreamcast/docs/engine/STATUS.md`, `port/dreamcast/docs/engine/HANDOVERS.md`.
- `STATUS.md` stays under 80 lines and only the integrator edits it.
- A lane writes only `port/dreamcast/docs/engine/lanes/<lane>.md`.
- Old checkpoint notes are history. They are not instructions.

## 7. Brief template

Integrator checklist before a brief goes out:
- every reference hash named;
- slots and folders provisioned;
- the baseline's scope defined (which phases, ticks per picture, what is excluded);
- the stop rule says which gates it covers;
- the lane's thresholds match ENGINE_PLAN.md.

```
Lane: eng-<topic>            Branch: lane/eng-<topic> from engine <sha>
Milestone: M<n>              Kind: PC-only | emulator | console lab
Goal: <one line, as a change to the benchmark picture or a named risk>
Already ruled out: <closed results, with their console numbers>
Read first: <files>
Owns: <files and folders>    Never touches: <files and folders>
Merge gate: <checks, each with its failing control>
Stop rule: <when to hand back without a result>
Hand back: table (scene, mean, p99, worst, over-budget count, tier), commit, image hash,
           evidence path, what was not done
```

## 8. The mistakes these rules come from

| Mistake | Rule |
|---|---|
| 17 speed lanes in 8 days, one console-confirmed gain at one view | Section 3, fixed benchmark and whole picture |
| About 31 console discs staged, 4 read | Section 2, a waiting lane stops; section 3, one image per A/B |
| The model saw 28% memory stall where the console had 53% | Section 3, half-budget margin |
| 32 landed switches sat off for 20 days | Section 1, merges switched on |
| A measuring disc waited on identity and STRICT gates | Section 4, smallest merge gate |
| A combined disc's switches were never read one at a time, 4.5 hours apart | Section 3, one image, A/B/A |
| A capture was taken in the wrong room and reported as a fight | Section 3, tool controls |
| A cleanup deleted a harness folder another lane was using | Section 2, own folders only |
| Reviewer estimates of 2 to 14 ms that the console did not confirm | Section 5, audit evidence, not ideas |
| Rule files a month behind the owner's direction | Section 6, four-file boot set |
| eng-bench handed back after two tries at its own capture tool, reading it as a gate (11-19) | Section 4, gate rule scope |
| The lab disc lost three files to the hourly cleanup while it waited for the console (11-19) | Section 2, `KEEP` on queued discs |
