# Lane eng-e1o: the selector's last gaps, boot files before play, reference controls kept, results re-derived (2026-11-21)

**Status: finished, unaudited.** Hand-back: `E:\RE4DC-Lanes\eng-e1o\HANDBACK.md`. Answers HANDOVERS.md H-017.6 to H-017.9
(third E1 audit, sections 4 and 5). PC numbers are re4ref (hostref); engine numbers are **Flycast** (standard harness slot
std2, function checks). No timing claim; the pacer and what the field counter counts are unchanged.

| Brief item | Result | Control and how it failed |
|---|---|---|
| 1. Selector (H-017.6) | kind and mode from the schedule (`e1:<timing\|function>:<drawn\|headless>`), the image's run and headless lines must agree; camera ticks checked = the scene's ticks (every E1 scene); a complete numeric after-play memory line with the guard read from it, no headless sentinel on a drawn scene; strict numbers (rows, FIELDS, MEM, CAMREC, POOL, DONE, FILES) | ctlA: CCAM0 "camera record checked 0 of 640 ticks"; CMEMCUT "after-play memory line: no mallinfo"; CRUNFN "run kind: image says function, schedule says timing"; CNUMTXT "E1 FIELDS line: a field missing or not a number"; CHEADM "mode: image headless, schedule drawn"; CKIND "schedule: kind e1 (run and mode not said)"; LEON beside them OK |
| 2. Boot files before play (H-017.7) | every boot file read before the first picture (STACKX moved; the fight's FEED.BIN moved); `core/play_files.c` counts every file open in play (`E1 FILES`), the selector fails a timing scene where it is not 0. Found and fixed: the fight read its Ganado module and 158 motion-key files at the first spawn (159 opens on tick 1) | COPENX (a boot file looked up at picture 100) FAILED "files opened in play 1 (first /cd/OPENX)"; FIGHT before the fix FAILED "files opened in play 159"; every clean scene now 0 |
| 3. Reference controls (H-017.8) | `EM10_SPLIT=0`, `BSPLINE_ALIAS=i386`, `STAT_BYTES=0` each an old reference built in its own folder by `svc/refctl.sh`, its rows run, deleted; camcheck counts the trace exit; camengine builds its old reference, never skips a requested scene, requires the fixture's window | refctl 12 rows as they must (em10: +2 draws at 135, outcome FAIL at 151; BSpline: rail STUCK; routine bytes: FAIL at 2/2/3). Script controls: no tree exit 2; camcheck rail trace must FAIL exit 1; camengine refcut exit 2, missing control scenes exit 2, unbuildable old reference exit 2 |
| 4. Re-derived (H-017.9) | hill: Leon and Ashley every field 729/729 on the fixed reference, no feed; the eight float fixtures PASS | split-off reference: Ashley FAIL at 367; mathmuku FAIL |
| 5. Still sheet | `E:\RE4DC-Lanes\eng-e1o\ev\look\sheet-e1.jpg` (1400 x 2175), pairs `pair-hill-{200,240,280,320}.png`, engine stills `engine-*.png` (Flycast, run runC2) | - |
| 6. Docs | CONSOLE_LOOP.md section 12, PLAYS_RIGHT.md last section, SERVICES.md section 37 (one sentence), this note | - |

## Link check (final HEAD, this lane's builds)

| Image | SERVICE functions |
|---|---:|
| default | 0 (PASS) |
| FIGHT=1 | 114 (as before: step 3) |
| BOSS=1 | 57 (as before: step 3) |
| default SENDABLE=1 | 0 (PASS) |

## Stubs, original units, shared files, lab arms

- No stub added or removed. No original unit added.
- Shared files touched: `loader/selector.c` (not the PUB line's parse), `core/main.cpp` (`e1_lab_boot` call, CAMREC0 arm),
  `hostref/svc/camcheck.sh`, `loader/cl_send.c` (its fs_open wrapper becomes `cl_send_fs_open`, weak wrapper kept for the
  bench), `fight/route_fight.cpp` (FEED.BIN read with the route), `fight/fight_e2.cpp` (modules read at room load),
  `game/Makefile` (`--wrap=fs_open`), `docs/engine/SERVICES.md` (one sentence).
- Run-time controls added (boot files, read before play, never defaults): CAMREC0, MEMCUT, RUNFUNC, NUMTEXT, OPENX. Control
  builds (never defaults): hostref `EM10_SPLIT=0`, `BSPLINE_ALIAS=i386` (beside `STAT_BYTES=0`). Script self-controls:
  `CAMCHECK_RAIL_TRACE_MUST=FAIL`, `CAMENGINE_CONTROL=refcut`.

## Still sheet: what still differs from the old Dreamcast port (hill, ticks 200 to 320; Flycast both)

Copied from the hand-back (`E:\RE4DC-Lanes\eng-e1o\HANDBACK.md`, "Still sheet") by lane eng-e1p, at the fourth audit's
request; the sheet is `E:\RE4DC-Lanes\eng-e1o\ev\look\sheet-e1.jpg`.
- **Barrels:** the barrels right of Leon are not drawn (props are not in E1).
- **Ground light:** the bright light pool on the ground at Leon's feet is missing (an effect).
- **Leon's material:** the engine's Leon reads lighter and browner, with light arms, where the old port's is a dark
  navy outfit (the chapter-2 body chunks over the pl00 atlas; an owner look call).
- **Handgun on the hill:** the old port shows the raised handgun; on the engine's hill it is hard to see (in the village and
  fight stills it is drawn).
- **Camera framing:** the engine's picture is slightly wider (Ashley a little smaller); the camera state is not carried by
  the resume (known since eng-e1d).
- **Ashley's hair and foot shadows:** no clear difference visible at this size; not judged (no close still).
- **Engine-only (no old still in the named folders):** village tick 160, the hanging body next to the camera is drawn in a
  teal-green tint (material or light on a near character, visible now that the near plane draws it); fight tick 200, Leon
  is out of frame (the camera's view at that moment, not compared). The EMPTY sign is not in any still taken.

## Not done

- The PUB line's parse stays as it is (lane eng-e1n's); the bench's WINDOW values are shown, not judged, and keep `atof`.
- No old-port still exists for the village route or the fight in the folders named by the brief: those rows of the sheet
  are engine-only.
- `aim_check.sh` reports without musts and ends exit 0 even when its runs fail (seen when `make aimchk` had not been run);
  not changed here.
