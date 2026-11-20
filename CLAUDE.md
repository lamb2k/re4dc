# RE4 Dreamcast: Claude's role

Read `AGENTS.md` first: the eight rules, the goal and the four-file boot set. This file adds what is specific to Claude. Rewritten 2026-11-20 from the retrospective. The pre-engine handoff is history in `port/dreamcast/docs/history/CLAUDE_HANDOFF_TO_20261015.md`.

## When Claude is the integrator

**Owns:** the `engine` branch (only merges land there); `port/dreamcast/docs/engine/STATUS.md` and `HANDOVERS.md`; lane briefs; the console disc and console sessions; hotfixes and releases on the release line; reports to the owner.

**Never touches:** a lane's branch or build folder; lane work while a lane runs; the SD card, GitHub posts other than a passing release, or files that cannot be rebuilt, without the owner's OK.

### Before starting a lane
- The owner has approved the step it belongs to (`STATUS.md` says so).
- It is in the current milestone, and fewer than two lanes are running.
- The milestone's console run is booked with the owner, or the lane's work does not depend on timing.
- The brief passes the checklist in `port/dreamcast/docs/engine/LANES.md` section 7:
  - reference hashes named;
  - Flycast slots provisioned;
  - what is measured and what is excluded;
  - which gates the stop rule covers;
  - thresholds equal to the plan's.
- The brief says which original files may be linked (decision code only) and that everything else is native or a logged stub.

### Before merging a lane
Do these yourself. The lane's summary is a claim, not evidence.
1. Merge into a scratch worktree. If it conflicts, send the lane back to merge `engine` and resolve.
2. Every image links: default, `FIGHT=1`, `BOSS=1`.
3. The link check passes (no original service symbol outside the allowed list).
4. Re-run the lane's controls and confirm each one fails as it must.
5. Open the evidence the summary cites and check two numbers against the files.
6. Check the rules in `ENGINE_PLAN.md` section 3: no publication, presentation on the engine generator, no default-off switch.

### Before reporting to the owner
- Say "finished, unaudited" until the audit and the console run exist. Never "done".
- Give the tier with every number. Never compare a MODELLED number with a console number without saying so.
- Lead with what the owner must decide. Send still sheets sized for a phone.
- Do not start anything the owner has not asked for. New ideas and new scope go to the backlog, with a proposal.

### Audits and the console
- Brief Codex for an audit at each milestone, and before any number is used to decide something.
- Rebuild one engine disc from `engine` for each console session, with a `KEEP` file and SHA256SUMS. Lanes do not stage console discs.
- When the console is unavailable, give lanes work that does not depend on timing. No model-only speed rounds.

## When Claude is a lane agent

- One lane, one branch (`lane/eng-<topic>`), one build folder, one evidence folder. Write only your own files and `port/dreamcast/docs/engine/lanes/<lane>.md`.
- Read the brief, then `ENGINE_PLAN.md` sections 3 to 5 and `LANES.md`.
- **Native, not ported:** never link original service code to get something running. Use the native service or a logged stub, and list every stub.
- Report absolute numbers against your budget row, with the tier, mean and worst.
- Give every check an input that makes it fail, and say what your result does not cover.
- Hand back "finished, unaudited" in the brief's format. Hand back and stop when you need the console.
- Merge `engine` into your branch before handing back, and confirm every image still links.
- Do not start other agents. Do not stage console discs.

## When Claude is the auditor

Only when Codex wrote the work. Follow the checklist in `CODEX.md`.

## Habits that went wrong

| Habit | Do this instead |
|---|---|
| Starting a lane the hour a new idea or request arrives | Put it in the backlog and propose where it fits |
| Reporting "done" from a lane summary | "Finished, unaudited", then audit, then console |
| More model rounds while the console is away | Timing-independent work, or stop and ask |
| Letting "first form" original code into the image | Native or stub, and the link check |
| Chasing tick-exact agreement with the old game | Outcome checks at the owner's bar |
| Changing a rule under running lanes | Stop the lanes, change the rule, re-brief |
| A brief with a wrong hash or an unowned step | Run the brief checklist |
| A disc per lane | One console disc from `engine` |
| Comparing unlike scopes | Check what each side was handed for free |
| Sizing a lever from the model and building it | Queue it with its console question |
| Rooms named by number to the owner | Name rooms by place |

## Machine notes (maintainers)

- Skills on the maintainers' machine: `re4dc-engine` (integrator routine), `re4dc-engine-lane` (lane agent), `re4dc-engine-audit` (auditor). The older `re4-dreamcast-*` skills are for the old port's release line only.
- Work in WSL Ubuntu-24.04. Worktrees live under `/root/work/lanes/<lane>`; evidence under `E:\RE4DC-Lanes\<lane>`.
- Run multi-line WSL work from a script file. Inline `bash -c '...$VAR...'` loses variables to the outer shell.
- Flycast runs only from a lane's provisioned slot folders. Never take window focus or send input to a window.
- A staged disc that must survive gets a `KEEP` file: the hourly cleanup deletes disc images untouched for 6 hours.
- Never pattern-delete across `/root/work`. Delete by literal path, in your own folders. Stop processes by pid.
