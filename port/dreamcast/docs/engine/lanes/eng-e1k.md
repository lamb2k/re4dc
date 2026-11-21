# Lane eng-e1k: the shot against the reference, a strict reader, a record that proves itself (2026-11-21)

**Status: finished, unaudited.** Hand-back: `E:\RE4DC-Lanes\eng-e1k\HANDBACK.md`. PC numbers are re4ref (hostref); engine
numbers are **Flycast** (standard harness slot std2, function checks). No timing claim, no model run; the pacer and what
the field counter counts are unchanged (its record is stricter).

| Brief item (H-016) | Result | Control and how it failed |
|---|---|---|
| 1. outcome.py false passes (H-016.5) | missing-sample, R lines required when the H line declares a room, a present but unrecorded position or angle is malformed, yaw within `ang_deg` (1 degree) for Leon and every actor. No existing fixture needed a fix | seven new rows in outcome_controls.py (35, 37 with the engine log); each new FAIL input passed the old reader (`ev\item1\old-reader.txt`) |
| 2. the shot on the engine against the PC reference (H-016.3) | native `GetWepTargetList2` in every image (the default stub gone; FIGHT 108, BOSS 57 service functions). The FIGHT=1 image plays the fixture file `shot-ganado.txt` (boot file SHOT.TXT). One reference fix: em10's presentation draws split as in the engine. Engine against reference: the same hit (0x14, tick 162, 800 to 500), positions and yaws bit for bit over 321 ticks | SHOTNP (press removed): FAIL damage; SHOTDMG (100 more life taken): FAIL damage amounts; SHOTLATE (hit held 30 ticks): FAIL damage at 192 against 162. PC: aimchk both lists on every shot, the grow control FAILs the list |
| 3. the scene record (H-016.6) | run-kind line, 600 distinct rows, presented mode for drawing images, 600 intervals, zero queue drops (a full queue refuses and counts), after-play memory line with a stack guard | ROWDUP, NOFLIP, QDROP, STACKX each FAILED with its reason; LEON, FIGHT, BOSS OK; the traced SHOT scene OK as "not a timing run" |
| 4. docs | PLAYS_RIGHT.md last section, CONSOLE_LOOP.md section 11, this note | - |

## What the engine is given in the shot scene

The fixture file, verbatim, and nothing from the reference's run (`engine/fight/shot_e2.cpp`): room and enemy list (must
be r101 and list 0), Leon's placement, weapon (must be 2 0), the seed, the resume, `god`, the four list entries created
by the original EmSetFromList2 after the enemy table's move of tick 1, and the pad lines. Any other key refuses the scene.
Where the fixture says nothing the engine starts where re4ref does: no room script, scenario task or room-entry spawn,
no difficulty points, no warp flags. The scene is always traced.

## Link check, SERVICE functions per image

| Image | origin/engine 736751764 | this lane |
|---|---:|---:|
| default | 0 (PASS) | 0 (PASS) |
| FIGHT=1 | 109 | 108 |
| BOSS=1 | 58 | 57 |
| default SENDABLE=1 | 0 (PASS) | 0 (PASS) |

Gone from FIGHT / BOSS: em_sub's GetWepTargetList2 (weakened; the native body linked).

## Stubs, original units, shared files, lab arms

- Stub removed: `host/e1_stubs.cpp` GetWepTargetList2. No stub added. No original unit added.
- Shared files touched: `core/draw_e1.c` (the release queue's drop, the drawn and stills facts, NOFLIP and QDROP),
  `core/main.cpp` not touched, `loader/selector.c` (the record's checks; `E2 SHOT REFUSED` as a refusal),
  `loader/cl_send.c` (the same refusal), `game/Makefile` (one WEAKEN line), `tools/engine/build_console_disc.sh` (the
  SHOT scenes, only when named), `hostref/Makefile` (PRESENT_EM10), `hostref/svc/{aimcheck.cpp, svc.mk, aim_check.sh}`.
- Run-time controls (boot files, never defaults): SHOTDMG, SHOTLATE (fight image, shot scene only), ROWDUP, NOFLIP, QDROP,
  STACKX (E1 images). No lab arm added.

## Not done

- The default image's native target list is exercised on the engine only in the FIGHT image (30 shots, 25 of them an
  empty list by computation) and on the PC; no default-image scene fires a shot (LEON and HILL: 0 shots).
- Video memory has no per-tick sample (before and after play only).
