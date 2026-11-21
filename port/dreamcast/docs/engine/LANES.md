# Engine line: lane rules

Binding for every agent on the engine line. Plan: [../ENGINE_PLAN.md](../ENGINE_PLAN.md) (read its "Amendments 2026-11-21" first: the replatform, no console until it is complete, the defensive model). Each rule comes from a mistake listed at the end.

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
- **A lane reports "finished, unaudited".** After its audit and its model a milestone is "finished, modelled, not on console"; "done" only after the console run, which is deferred until the replatform is complete (not waived).
- **Lanes do not stage console discs.** The integrator keeps one engine disc on the shelf, rebuilt from `engine` when a milestone closes on the model.
- PC-only lanes may not start an emulator.
- Lanes run as Claude Opus agents; Codex audits each milestone.
- A lane uses its own build folder and its own evidence folder. It deletes only inside them, by literal path.
- Processes are stopped by pid, never by name.
- A staged disc that is queued for the console gets a `KEEP` file in its folder. The hourly cleanup deletes disc images (`track0*`, `disc.gdi`) untouched for 6 hours unless the folder or a parent has one.
- Flycast runs only from fixed slot folders that the integrator provisions once per lane (`std1`, `std2` the plain build for function checks; `fly1`, `fly2` the strict build for modelled numbers; see the lane's SLOTS.txt). Copying configs and data inside a slot is fine; a copy of flycast.exe at any other path is not. At most two running. Never take window focus or send input to a window. GDB off unless needed.
- No lane waits on the console while the replatform is under way: speed is judged on the calibrated model (section 3). A question only the console can answer goes in the hand-back for the deferred console run.

**Machine rules** (H-014, H-015; the machine is shared and stalled once on a full C:):
- Build objects in RAM (`/dev/shm`). One image build at a time. Delete build folders once checked (WSL's swap file on C: grows with what sits there).
- Check C: and E: free from Windows before every build and disc stage. Stop and tell the integrator at C: 31 GB or E: 15 GB.
- A `sleep` keeper per lane while it works. A timeout on every WSL call. WSL work from script files.
- Test discs are deleted after their runs, with a note.
- A lane that changes a slot's `emu.cfg` (clock, dynarec) keeps the original beside it, restores it before hand-back, and never changes a slot another lane is using.
- A lane taking a "strict" or "plain" number first prints the slot's `Dynarec.Enabled` and `Sh4Clock` values into its log.
- No `fstrim` or compaction by lanes. The nightly backup job is `C:\Game Dev\Emulators\_private_tools\wsl-backup\wsl-backup.sh` (one bundle per repository).

## 3. Measuring

- **Tiers:** every number is labelled with one of:

  | Tier | What it is |
  |---|---|
  | **console** | Real Dreamcast, GDEMU. Deferred until the replatform is complete |
  | **MODELLED (strict Flycast, calibrated)** | The interpreter build (`Dynarec.Enabled = no`; slots `fly1`, `fly2`) at the calibrated `[config] Sh4Clock` (MHz, default 200; upstream since v2.2, ours v2.7-14-g12bb43652). Judges speed until the deferred console run |
  | **MODELLED (PC hardware model)** | The PC hardware model, with the images' own per-picture counters (it has under-read the console by 1.3 to 2 times) |
  | **Flycast** | The plain build (slots `std1`, `std2`). Function checks only; no speed claim |
  | **estimate** | No run behind it |

- **The defensive model** (owner 2026-11-21, H-021) replaces "the console decides" until the deferred console run:
  - The clock is calibrated on the old port: its five benchmark scenes have real console means from Test 27.1 (village cross 56 ms, bell fight 53 to 60 ms, farm entry 44 to 58 ms, farm hay-fork view 96 ms, farm quiet view 34 ms). The lowest clock any scene needs is the defensive clock; the spread across scenes says how far one factor can be trusted. The first calibration: see `COMPARISON_20261121.md` in this folder when it lands.
  - A figure passes its budget row on the model's worst case, not its mean.
  - Cost is also read from the code: the images' own per-picture counters and the PC hardware model.
  - With every modelled number, list what the model cannot see: the graphics chip's fill and sort time, vertex submission through the store queues, memory bus contention, real disc timing.
  - Speed work goes where the code and the model say the cost is, and is judged on the calibrated model. No speed claim rests on plain Flycast.
- **The benchmark is fixed:** village cross, bell fight, farm entry, farm hay-fork view, farm quiet view, lake fight, castle hall. Same presets, cap 4.
- **Report the whole picture:** mean, p99, worst interval and count over 33.3 ms, over 600 pictures, against the lane's budget row. The floor is at most two fields between presented pictures.
- **One model-only round per milestone.** After it, the next step is the console. (Superseded 2026-11-21 by the defensive model above.)
- **A/B on console is one image:** two arms switched at run time in the same boot, in A/B/A order. Never two builds, never two sessions.
- **Before a console number exists,** a modelled or emulator figure counts only if it fits in half the budget. (Ruling 2026-11-21: this holds for uncalibrated figures, that is plain Flycast and the PC hardware model before it is re-fitted. A calibrated strict-Flycast figure is judged on its worst case against the full row, less a margin equal to the calibration's spread across the benchmark scenes; it must fit the row at the defensive clock, which is already the slowest clock any scene needs.)
- **A new measuring tool needs a control** that makes it read wrong on purpose, before its numbers are used.
- **Speed is the game's own tick and picture counters,** never the display's refresh.

- **Go native.** The new path is measured against the budget, not against the old game. No lane tunes, profiles or improves the old drawing path.
- **The old port is a measuring stick** (owner 2026-11-21, H-019). It may be measured as a baseline beside the engine: same scenes, same tier, same measure, with what each side draws and runs stated. It is never tuned, profiled or fixed, and nothing chases exact agreement between the two. Customer-facing speed claims need a console number or an explicitly labelled model figure, and the owner's OK before anything is posted.
- The lessons from our other ports are part of every brief:
  - the console decides in the end; until the deferred console run, the calibrated model does, because an uncalibrated model under-reads the console by 1.3 to 2x;
  - remove repeated work first, with change flags per picture;
  - no disc reads in play;
  - the engine image links no original game code;
  - every check ships with an input that fails it.

## 3b. Native, not ported (owner 2026-11-19)

- A lane that hosts a character never links original service code (effects, skeleton, collision, cloth, routes, managers) to get it running. It uses the native service or a logged stub and lists the stub.
- Presentation code never draws from the original generator.
- **Native means** the engine's own code on SH4ZAM types and the engine's data layout. The same mathematics is accepted; a transcription of the original's control flow is not (H-016.1).
- **A hosted body that cannot be split** without editing `src/` becomes an engine composition, with its re-expressed decision statements listed line by line (H-017.10). Each such case needs its own ruling.
- **Decisions stay hosted** because that keeps play identical, and they are cheap (under 1 ms a picture in Flycast). A decision function goes native only where the model shows it is hot, and then the outcome check must show play unchanged.
- **No per-tick conversion** of behaviour objects into draw data. Conversion at load is loading work. Nothing opens or reads the disc inside a picture; the scene record counts opens, reads and sector requests (H-016.2, H-018).

## 4. Gates

- Gates are per milestone and are listed in the plan, section 8. They run once, on the final image.
- A lane's own merge gate is the smallest set that proves its change: it builds, it boots, the benchmark does not get worse, and its own check passes and can fail.
- Every check ships with an input that makes it fail.
- A failing gate gets two distinct hypotheses tested. Then the blocker is written as a hand-over. No tolerance is loosened to pass.
- That rule is for milestone and merge gates. A lane's own tools (capture, bake, checkers) are its work: keep building them until they work. Hand back early only for the brief's stop rule or a blocker outside the lane's own files.
- Byte identity with a previous build is not a gate on the engine line.
- **Never loosen.** A loosened comparison, tolerance or "must" column is a gate failure unless the brief asked for it (H-016.10). The gate diffs the comparators.
- **Changing the PC reference** needs the cause shown in the original source and a switchable build that restores the old behaviour, run as a row (H-016.8, H-017.8; `port/dreamcast/engine/hostref/svc/refctl.sh`).
- **Checks live in the repository.** Checks, control scenes and control schedules are in the repository (the CONTROLS lists in `port/dreamcast/tools/engine/build_console_disc.sh`, `port/dreamcast/tools/engine/hudcheck.py` and the like), never only in a lane's wrapper (H-017.11). A script that skips a requested row or passes with missing inputs is a fault.
- **A scene is OK only if its record proves itself:** 600 distinct rows, drawn mode, 600 flip intervals, no drops, a complete memory line, the schedule read whole. [CONSOLE_LOOP.md](CONSOLE_LOOP.md) sections 11 to 13 describe it.
- **The integrator's merge gate:** the link check passes (no original service symbol outside the allowed list), the lane's controls re-run on logs or discs the integrator builds itself, every image links, cited numbers are re-derived against a reference the integrator builds, the comparators are diffed, and the plan's section 3 rules hold. The gate writes its tables to files beside the make logs (H-016.7). A lane's summary is not evidence.
- **Plays right is checked by outcome** (a scripted player on the engine and the reference: kills, damage, waves, triggers, time to clear), not tick for tick against the old game.

## 5. Audits and hand-overs

- **One independent audit per milestone,** by the agent that did not write the code. It reads the final image's evidence and tries to break the claims.
- No review round per change. Tooling and wording findings do not block a merge.
- Exception: a lane number that is about to drive a decision (a stop, a milestone call, a plan change) gets an independent check first.
- **When an audit fails,** its list goes to lanes. Items that are mechanical and have controls are verified by the integrator at the gate; the auditor is asked again only for what is not mechanical (H-018).
- **An audit runs sandboxed and read-only** on inputs exported to E: (a source export, link maps, symbol tables, the diff since the last audit): `codex exec -m gpt-6.2-astra -c model_reasoning_effort='"medium"' -s workspace-write -C <audit folder> --skip-git-repo-check -o <folder>\LAST-MESSAGE.md "<prompt>" < /dev/null`. A launch without a sandbox is refused on this machine.
- The auditor's closing section is "what the deferred console run must measure" and "what the model cannot see", not a request for a console evening.
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
- the lane's thresholds match ENGINE_PLAN.md;
- the step is approved by the owner, belongs to the current milestone, and fewer than two lanes are running;
- the work does not depend on timing, or its speed is judged on the calibrated model (no console run is booked while the replatform is under way);
- which Flycast slot serves which tier;
- "never loosen" and "controls in the repository" are in the brief;
- the machine section is in the brief.

```
Lane: eng-<topic>            Branch: lane/eng-<topic> from engine <sha>
Milestone: M<n>              Kind: PC-only | emulator | console lab
Goal: <one line, as a change to the benchmark picture or a named risk>
Already ruled out: <closed results, with their tiers>
Read first: <files>
Owns: <files and folders>    Never touches: <files and folders>
Original code allowed: <decision files only>; everything else native or a logged stub (list the stubs)
Tiers and slots: fly1/fly2 strict Flycast at Sh4Clock <MHz> for MODELLED numbers;
           std1/std2 plain Flycast for function checks only
Merge gate: <checks, each with its failing control>
Never loosen: no comparison, tolerance or "must" column is loosened unless this brief says so
Controls: in the repository (<script or list>), never only in a lane wrapper
Machine: objects in /dev/shm; one image build at a time; C: and E: free checked from Windows
           before every build and disc stage (stop at C: 31 GB or E: 15 GB); a sleep keeper;
           a timeout on every WSL call; WSL work from script files; test discs deleted after
           their runs with a note; no fstrim or compaction
Stop rule: <when to hand back without a result>
Hand back: status "finished, unaudited"; engine merged in and every image linking;
           table (scene, mean, p99, worst, over-budget count, tier), commit, image hash,
           evidence path, what the model cannot see, what was not done
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
| C: fell to 2.6 GB free and the WSL disk stalled for seven hours (11-20) | Section 2, machine rules |
| A lane widened every boundary-log field to 0.01 (11-21) | Section 4, never loosen |
| The PC reference was wrong and the engine right; reference changes landed without kept controls (11-21) | Section 4, reference changes |
| Control scenes built from a lane's wrapper; a script passed with an empty table (11-20, 11-21) | Section 4, checks live in the repository |
| A module and 158 motion-key files read from disc at the first spawn, in play (11-21) | Section 3b, no disc reads inside a picture |
| Four paper audits in one night, each a shorter list (11-21) | Section 5, mechanical items at the gate |
