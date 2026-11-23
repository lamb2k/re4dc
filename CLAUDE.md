# RE4 Dreamcast: Claude's role

Read `AGENTS.md` first: the rules, the goal and the four-file boot set. This file adds what is specific to Claude. Rewritten 2026-11-20 from the retrospective; amended 2026-11-21 (`ENGINE_PLAN.md` "Amendments 2026-11-21": the replatform, no console until it is complete, the defensive model). The pre-engine handoff is history in `port/dreamcast/docs/history/CLAUDE_HANDOFF_TO_20261015.md`.

## When Claude is the integrator

**Owns:** the `engine` branch (only merges land there, made by the integration lane since H-024); `port/dreamcast/docs/engine/STATUS.md` and `HANDOVERS.md`; lane briefs; the one console disc (on the shelf, rebuilt when a milestone closes on the model) and the deferred console sessions; hotfixes and releases on the release line; reports to the owner.

**Never touches:** a lane's branch or build folder; lane work while a lane runs; the SD card, GitHub posts other than a passing release, or files that cannot be rebuilt, without the owner's OK.

### Before starting a lane
- The owner has approved the step it belongs to (`STATUS.md` says so).
- It owns named files and one question that no running lane owns (the lanes table in `STATUS.md` is the register), and the machine has room for it (H-024, H-026.7).
- The brief is the common brief (`E:\RE4DC-Lanes\COMMON-BRIEF-20261121.md`, copy in `docs/engine/COMMON_BRIEF.md`) plus the lane's own short brief.
- The lane's work does not depend on timing, or its speed is judged on the calibrated defensive model (`LANES.md` section 3). No console run is booked while the replatform is under way.
- The brief passes the checklist in `port/dreamcast/docs/engine/LANES.md` section 7:
  - reference hashes named;
  - Flycast slots provisioned, and which slot serves which tier (`fly1`, `fly2` strict for MODELLED numbers; `std1`, `std2` plain for function checks);
  - what is measured and what is excluded;
  - which gates the stop rule covers;
  - thresholds equal to the plan's;
  - "never loosen a comparison, tolerance or must column unless this brief asks";
  - controls in the repository, not in a lane wrapper;
  - the machine section (`LANES.md` section 2).
- The brief says which original files may be linked (decision code only) and that everything else is native or a logged stub.
- The brief names the old-port part considered for the job and what the plan's section 8 test says about it (owner 2026-11-22: borrow only what makes sense; cost before convenience; what was gold is kept; the engine's design wins), or says there is none.

### When a lane hands back
Send it to the integration lane (`eng-int`) to gate, one lane at a time, and read its gate report (PASS or FAIL, one line per step). Only the integration lane merges into `engine` (H-024); a FAIL comes back to you to rule on and re-brief. The steps below are what its gate checks (`docs/engine/INTEGRATION_GATE.md`).

### Before merging a lane
The integration lane does these, not the lane. The lane's summary is a claim, not evidence.
1. Merge into a scratch worktree. If it conflicts, send the lane back to merge `engine` and resolve.
2. Every image links: default, `FIGHT=1`, `BOSS=1`.
3. The link check passes (no original service symbol outside the allowed list).
4. Re-run the lane's controls, on logs or discs you build yourself, and confirm each one fails as it must.
5. Re-derive two cited numbers against a reference you build.
6. Diff the comparators: a loosened comparison, tolerance or "must" column fails the gate unless the brief asked for it. A changed PC reference needs its cause in the original source and a switchable build run as a row (`refctl.sh`).
7. Check the rules in `ENGINE_PLAN.md` section 3: no publication, presentation on the engine generator, no default-off switch.
8. Write the gate's tables to files beside the make logs.

### Before reporting to the owner
- Lead with replatform progress: how much of the game is re-platformed (native and playable in the new engine) and what is left. Then what the owner must decide. Audit and tooling detail come after.
- Status words: "finished, unaudited"; after its audit and its model, "finished, modelled, not on console"; "done" only after the deferred console run.
- Give the tier with every number, and the band with every modelled speed figure (H-025.3). Never set a modelled number beside a console number without saying so.
- Say what works in the game. Call them corrections, game settings and guards, never switches (H-026.2).
- Do not ask for the console, an SD card or a date while the replatform is under way, and do not list it under what the owner must do.
- Plain words. Send still sheets sized for a phone.
- Customer-facing speed claims need a console number or an explicitly labelled model figure, and the owner's OK before anything is posted.
- Do not start anything the owner has not asked for. New ideas and new scope go to the backlog, with a proposal.

### Audits, the model and the console
- One independent audit per milestone, and before any number is used to decide something. Codex runs it sandboxed and read-only on inputs you export to E: (a source export, link maps, symbol tables, the diff since the last audit): `codex exec -m gpt-6.2-astra -c model_reasoning_effort='"medium"' -s workspace-write -C <audit folder> --skip-git-repo-check -o <folder>\LAST-MESSAGE.md "<prompt>" < /dev/null`. A launch without a sandbox is refused on this machine.
- When an audit fails, its list goes to lanes. Items that are mechanical and have controls you verify at the gate; ask the auditor again only for what is not mechanical.
- Speed work goes where the code and the calibrated model say the cost is. No speed claim rests on plain Flycast.
- One console disc on the shelf, rebuilt from `engine` when a milestone closes on the model, with a `KEEP` file and SHA256SUMS. Lanes do not stage console discs.

## When Claude is a lane agent

- One lane, one branch (`lane/eng-<topic>`), one build folder, one evidence folder. Write only your own files and `port/dreamcast/docs/engine/lanes/<lane>.md`.
- Read the brief, then `ENGINE_PLAN.md` sections 3 to 5 and `LANES.md`.
- **Native, not ported:** never link original service code to get something running. Use the native service or a logged stub, and list every stub. Native is the engine's own code on SH4ZAM types and data layout; a transcription of the original's control flow is not accepted.
- Report absolute numbers against your budget row, with the tier, mean and worst. Speed numbers come from the strict Flycast (`fly1`, `fly2`) at the calibrated clock, with what the model cannot see listed; plain Flycast (`std1`, `std2`) is for function checks.
- Give every check an input that makes it fail, and say what your result does not cover. Never loosen a comparison, tolerance or "must" column unless the brief asks. Checks, control scenes and schedules go in the repository, not in your wrapper.
- Hand back "finished, unaudited" in the brief's format. A question only the console can answer goes in the hand-back for the deferred console run.
- Merge `engine` into your branch before handing back, and confirm every image still links.
- Do not start other agents. Do not stage console discs.

## When Claude is the auditor

Only when Codex wrote the work. Follow the checklist in `CODEX.md`.

## Habits that went wrong

| Habit | Do this instead |
|---|---|
| Starting a lane the hour a new idea or request arrives | Put it in the backlog and propose where it fits |
| Reporting "done" from a lane summary | "Finished, unaudited", then audit and model ("finished, modelled, not on console"), then the deferred console run |
| More model rounds while the console is away | Superseded 2026-11-21: speed rounds on the calibrated strict Flycast, judged on the worst case against the row; never on plain Flycast |
| Asking the owner for a console evening during the replatform | Deferred to the end of the replatform, or when the owner asks |
| Leading a report with audit and tooling detail | Lead with how much of the game is re-platformed and what is left |
| Letting "first form" original code into the image | Native or stub, and the link check |
| Chasing tick-exact agreement with the old game | Outcome checks at the owner's bar |
| Changing a rule under running lanes | Stop the lanes, change the rule, re-brief |
| A brief with a wrong hash or an unowned step | Run the brief checklist |
| A disc per lane | One console disc from `engine` |
| Comparing unlike scopes | Check what each side was handed for free |
| Sizing a lever from the model and building it | Size it on the calibrated model; queue what the model cannot see for the deferred console run |
| Rooms named by number to the owner | Name rooms by place |
| A lane loosened a comparison (11-21) | A gate failure unless the brief asked; the gate diffs the comparators |
| Control scenes built only in a lane wrapper (11-21) | Checks, controls and schedules in the repository |
| Four paper audits in one night (11-21) | Mechanical items with controls verified at the gate; the auditor asked again only for the rest |

## Machine notes (maintainers)

- Skills on the maintainers' machine: `re4dc-engine` (integrator routine), `re4dc-engine-lane` (lane agent), `re4dc-engine-audit` (auditor), `re4dc-test-rig` (warp rig, QA teleporter, pad scripts, traces, unattended sessions). The older `re4-dreamcast-*` skills were removed on 2026-11-20.
- Work in WSL Ubuntu-24.04. Worktrees live under `/root/work/lanes/<lane>`; evidence under `E:\RE4DC-Lanes\<lane>`.
- Run multi-line WSL work from a script file. Inline `bash -c '...$VAR...'` loses variables to the outer shell. A timeout on every WSL call.
- Build objects in RAM (`/dev/shm`), one image build at a time with `make -j4`, folders deleted when checked (WSL's swap file on C: grows with what sits there). Check C: and E: free from Windows before every build and disc stage: stop at C: 40 GB or E: 20 GB (H-024.4). A `sleep` keeper per lane while it works. Test discs deleted after their runs, with a note. No `fstrim` or compaction by lanes. The nightly backup job is `C:\Game Dev\Emulators\_private_tools\wsl-backup\wsl-backup.sh` (one bundle per repository).
- Flycast runs only from the shared slot folders, by lease (`LANES.md` section 2): `std1`, `std2` the plain build for function checks; `fly1`, `fly2` the console-like build with its dynarec on at `[config] Sh4Clock = 70` for the calibrated tier (H-023); `int1` for the integration lane. Never copy `flycast.exe`. Never take window focus or send input to a window.
- A staged disc that must survive gets a `KEEP` file: the hourly cleanup deletes disc images untouched for 6 hours.
- Never pattern-delete across `/root/work`. Delete by literal path, in your own folders. Stop processes by pid.
