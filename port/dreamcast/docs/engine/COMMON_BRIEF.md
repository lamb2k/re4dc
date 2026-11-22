# Common part of every RE4DC engine lane brief (2026-11-21, from H-014 to H-024)

Your own brief names the lane, branch, goal, items and files you own. This file holds what is the same for every lane.
Where the two disagree, your own brief wins.

## Read first
In your worktree (`/root/work/lanes/<lane>`, WSL `Ubuntu-24.04`, root): `AGENTS.md`, `CLAUDE.md` ("When Claude is a lane
agent"), `port/dreamcast/docs/ENGINE_PLAN.md` (the Amendments of 2026-11-21 first, then sections 3, 4, 7 to 9),
`port/dreamcast/docs/engine/LANES.md`, `docs/engine/HANDOVERS.md` H-016 to H-024, and the skills
`C:\Game Dev\Emulators\.claude\skills\re4dc-engine-lane\SKILL.md` and `re4dc-test-rig\SKILL.md`.

## What this work is
The replatform: RE4 as a Dreamcast native port of the whole game, playing like the GameCube version at 30 fps. The
engine owns the loop, memory, loading, renderer and services; the original AI, player, event and script code is
hosted for decisions; no original service code in the engine image. No console is used until the replatform is
complete: speed is judged on the calibrated emulator tier (below), never on plain Flycast.

## Many lanes run at once (the owner, 2026-11-21: "Run as many as possible with an integration lane as long as they aren't redundant")
- Your brief lists the files and the question you own. Do not work outside them. If you find you need a change in
  another lane's area, write it in your hand-back as a request; do not make it.
- Only the integration lane merges into `engine`. Never merge another lane's branch. Pull `origin/engine` (merge it)
  before your final checks and whenever your brief says.
- If you discover your work duplicates another lane's (see the lanes table in `docs/engine/STATUS.md` on
  `origin/engine`), stop that part and say so.

## Rules
- No timing claim from plain Flycast. Speed numbers come only from the calibrated tier: the console-like build
  (slots `fly1`, `fly2`) with `Dynarec.Enabled = yes` and `[config] Sh4Clock = 70`, labelled "MODELLED (console-build
  dynarec at 70 MHz, calibrated on the old port)". Judge a budget row on the worst picture, not the mean, and list
  what the model cannot see (graphics chip fill and sort, store-queue submission, bus contention, disc timing).
- Native, not ported: the engine's own code on SH4ZAM types and the engine's data layout; the same mathematics is
  fine, a transcription of the original's control flow is not. `src/` is not edited. No publication layer (no per-tick
  conversion of game objects into draw data). No default-off switch; a comparison arm is a run-time lab arm (a boot
  file read before play), listed in the hand-back.
- Never loosen a comparison, tolerance or "must" column. If a result cannot meet its bound, report the numbers and
  stop. A change to the PC reference needs its cause shown in the original source and a switchable build that
  restores the old behaviour (`hostref/svc/refctl.sh`).
- Every check ships with an input that makes it fail; run it and record how it failed. Checks, control scenes and
  schedules live in the repository, never only in your own wrapper.
- Effects are added one at a time on a budget (the owner, 2026-11-21); do not bring over effect drawing unless your
  brief names the effect.
- The old port (`origin/t15/int`) is a measuring stick and a source of parts: never tuned, profiled or fixed.
- Status at hand-back is "finished, unaudited". No new scope.

## Working habits (added 2026-11-21, from the F-Zero line's experience)
- Hand back before you lose the thread: after about 250 tool calls, or when you notice yourself repeating a run,
  finish the item in hand, push, and hand back with what remains. A second lane continues from a clean brief.
- A speed arm never carries a look change, and a look arm never carries a speed change: one variable per arm.
- Never report a picture as "the same" or "improved" without the count of differing pixels against the base still
  (and the still where the arms differ most).
- A speed claim needs a matched pair in the same session: the base re-run beside the change, same slot, same
  settings, same scenes; never a base quoted from an earlier run or another lane.
- Anything baked (a pack, a table, converted data) carries a receipt: the hashes of its inputs and scripts and the
  hash of its output. Using baked data whose receipt does not match its inputs is a fault.

## Existing suites that must still end as they must
`hostref/svc/svc_controls.sh <out>` (79 rows), `hostref/svc/camcheck.sh <out>` (21), `hostref/svc/refctl.sh <out>` (12),
`tools/plays_right/controls.sh <out>` (18), `tools/plays_right/outcome_controls.py <out>` (35), `hostref/svc/aim_check.sh
<out>`; on a Flycast serial log: `tools/plays_right/shot_engine.py <serial> <out>`, `tools/plays_right/hill_engine.py
<serial> <out>`, `CAMENGINE_NAMES="LEON=LEONT,HILL=HILLT" hostref/svc/camengine.sh <out> <serial>`. Counts may grow when
a merged lane adds rows; none may turn to WRONG.

## Building
- `export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367; . port/dreamcast/kos-env.sh`; images in
  `port/dreamcast/engine/game` with `make -j4 OUT=/dev/shm/<lane>/<image>` (plus `FIGHT=1`, `BOSS=1`, `SENDABLE=1`); link
  check `python3 port/dreamcast/tools/engine/check_link.py <e1.map> [--list]`. PC reference (hostref):
  `RE4_TREE=/root/re4data/private/release-trees/test24-608abf36`, targets `all native odump aimchk`; make `build` in the
  worktree a symlink to `/dev/shm/<lane>/build` and never `git add` it.
- Test discs: the repository's `tools/engine/build_console_disc.sh` (at most 8 scenes a disc; control scenes in its
  CONTROLS lists). Runner used by earlier lanes: `E:\RE4DC-Lanes\eng-e1p\s\fly.py <slot> <gdi folder> <seconds> <out>`
  and `cdisc.sh` there. Private packs: `E:\RE4DC-Lanes\eng-e1i\packs` (the disc script's defaults). Never commit packs,
  stills or discs.

## Machine
- Build objects in RAM (`/dev/shm/<lane>`), one image build at a time, each folder deleted when its check is done.
  The machine is shared with two other projects and several RE4 lanes: `make -j4` at most.
- Check `(Get-PSDrive C).Free/1GB` and `(Get-PSDrive E).Free/1GB` from Windows before every build and disc stage. C:
  under 40 GB or E: under 20 GB: stop, delete your own intermediates, push, say so in your hand-back.
- Keep one background `wsl -d Ubuntu-24.04 -u root -- sleep 14400` open while you work; stop it by pid at hand-back.
- A `timeout` on every WSL call. WSL work from script files under `E:\RE4DC-Lanes\<lane>\s\` (`tr -d '\r' < file >
  /tmp/x.sh; bash /tmp/x.sh`); inline `bash -c "...$VAR..."` loses variables; in Git Bash use forward slashes in paths
  that hold a variable. No `fstrim`, no compaction. If a WSL command hangs or `dmesg` shows `hv_storvsc` errors, stop
  and report. If told to pause for a WSL shutdown: commit, push, stop your keeper, no WSL call until told.
- Discs, stills and evidence go to `E:\RE4DC-Lanes\<lane>\`; each test disc (1.1 GB) is deleted right after its run
  with a note. Never pattern-delete under `/root/work`; delete by literal path inside your own folders only.
- **Flycast slots are shared by lease.** Slots: `E:\RE4DC-Lanes\eng-e1d\std1`, `std2` (plain build: function checks)
  and `fly1`, `fly2` (console-like build: the calibrated tier). Before using a slot, create
  `<slot>\LEASE.txt` holding your lane name and the time; if the file exists and is under two hours old, use another
  slot of the same kind or wait and retry every few minutes (do other work meanwhile); delete your lease the moment
  your run ends. A lease covers only a Flycast process of yours that is running: no reserving a slot ahead of a
  run, and no holding it between runs. The integration lane has priority: if `WANTED-eng-int.txt` appears in a slot
  you hold, finish the run in progress, release, and do not retake that slot until eng-int's lease has come and gone.
  Never stop a `flycast.exe` you did not start. Never copy `flycast.exe`. Never take window focus or
  send input to any window. If you change a slot's `emu.cfg` (dynarec, clock), keep the original beside it, restore
  it before you release the lease, and write the slot's `Dynarec.Enabled` and `Sh4Clock` values into your run's log.
- Git: public repository, no game data; add files by name; no blob over 300 KB; push only your own branch to
  `origin`. End commit messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not touch
  `docs/engine/STATUS.md`, `HANDOVERS.md`, branch `engine`, the console disc folder or the SD card.

## Hand back
`E:\RE4DC-Lanes\<lane>\HANDBACK.md` and a final message: status "finished, unaudited"; per item: finished or not,
the evidence path, the control and how it failed; numbers with their tier; link-check service functions per image
before and after if you changed an image; files touched outside your owned list (there should be none); requests
for other lanes; the branch head; what was not done; what you could not verify. Keep
`E:\RE4DC-Lanes\<lane>\STATUS.md` current as you go. Before handing back: merge `origin/engine`; if you changed an
image, confirm default, `FIGHT=1`, `BOSS=1` and `SENDABLE=1` link.

## Borrow what works (owner, 2026-11-22, H-032)
"we should be borrowing things that work fine at a mechanical level from the old build pre re architecture." Before writing new engine plumbing, check `docs/engine/SALVAGE_20261121.md` (REUSE / ADAPT rows) and the old port's own Dreamcast code (release line, read only): disc and loader, door and room-change memory guards, video-memory residency, sound, movies, memory card, crash screen, proven kernels. Lift what works and adapt only what the new architecture needs; say in the hand-back what you lifted and from where. Original game service code stays out (link check); the old drawing path as a whole is not tuned.
