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

- At most **two build lanes** at once, plus **one** lab or release lane.
- PC-only lanes (bakers, converters, host tests) do not count as build lanes, but may not start an emulator.
- A lane uses its own build folder and its own evidence folder. It deletes only inside them, by literal path.
- Processes are stopped by pid, never by name.
- A lane that waits on the console does not chain into model-only work. It hands back and stops.

## 3. Measuring

- **Tiers:** every number is labelled console, MODELLED, Flycast or estimate.
- **The benchmark is fixed:** village cross, bell fight, farm entry, farm hay-fork view, farm quiet view, lake fight, castle hall. Same presets, cap 4.
- **Report the whole picture:** mean, p99, worst interval and count over 33.3 ms, over 600 pictures. Never a subsystem number on its own.
- **A/B on console is one image:** two arms switched at run time in the same boot, in A/B/A order. Never two builds, never two sessions.
- **Before a console number exists,** a modelled or emulator figure counts only if it fits in half the budget.
- **A new measuring tool needs a control** that makes it read wrong on purpose, before its numbers are used.
- **Speed is the game's own tick and picture counters,** never the display's refresh.

## 4. Gates

- Gates are per milestone and are listed in the plan, section 5. They run once, on the final image.
- A lane's own merge gate is the smallest set that proves its change: it builds, it boots, the benchmark does not get worse, and its own check passes and can fail.
- Every check ships with an input that makes it fail.
- A failing gate gets two distinct hypotheses tested. Then the blocker is written as a hand-over. No tolerance is loosened to pass.
- Byte identity with a previous build is not a gate on the engine line.

## 5. Audits and hand-overs

- **One independent audit per milestone,** by the agent that did not write the code. It reads the final image's evidence and tries to break the claims.
- No review round per change. Tooling and wording findings do not block a merge.
- **Hand-overs are numbered** (`H-001`, `H-002`, ...) in [HANDOVERS.md](HANDOVERS.md). One per milestone or per blocking question. Each has: commit, image hashes, numbers with tiers, evidence path, what was not done.
- A message with no reply is not agreement.

## 6. Documents

- The boot set is four files: `AGENTS.md`, `port/dreamcast/docs/ENGINE_PLAN.md`, `port/dreamcast/docs/engine/STATUS.md`, `port/dreamcast/docs/engine/HANDOVERS.md`.
- `STATUS.md` stays under 80 lines and only the integrator edits it.
- A lane writes only `port/dreamcast/docs/engine/lanes/<lane>.md`.
- Old checkpoint notes are history. They are not instructions.

## 7. Brief template

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
