# Lane eng-e1h: close E1 for its audit (2026-11-20)

**Status: finished, unaudited.** Hand-back: `E:\RE4DC-Lanes\eng-e1h\HANDBACK.md`. PC numbers are re4ref (hostref);
emulator numbers are **Flycast** (standard harness slots, function checks). No timing claim; no model run; the pacer and
the timing rows are untouched.

| Brief item | Result |
|---|---|
| 1. The six service functions left in the default image | default and SENDABLE=1 link 0 (was 6); FIGHT 116 -> 109, BOSS 65 -> 59 as a side effect. cEm and cLight tables on the engine pool, the laser sight drawn by the renderer from engine setters |
| 2. Controls that pass with no rows | svc_controls.sh, controls.sh, outcome_controls.py, svc5_units.sh fail closed (exit 2); each control exits 2; full runs 77 / 18 / 28 rows, all as they must |
| 3. Shot and hit | the reference fires from a real magazine and reads the rumble table in order; `shot-ganado`: Leon's shot damages Ganado 0x14 on the PC reference and the native build (outcome PASS, control FAIL on damage); the fight image's shots on Flycast (see the hand-back) |
| 4. Dying Ganado skinning | cause: em10ScaleCompress writes the part records after the world pass; native `skel_compress_y`; kill / clear PASS, control FAIL at 241 / 204 |
| 5. HUD compositing | each widget's own blend (blend_type from the capture's shape bits); still pair in the hand-back |
| 6. Docs | SERVICES.md sections 41-44, PLAYS_RIGHT.md "Shots, the magazine and controls that fail closed", this note |

## Link check, SERVICE functions per image

| Image | origin/engine b387c10f7 | this lane |
|---|---:|---:|
| default | 6 | 0 (PASS) |
| FIGHT=1 | 116 | 109 |
| BOSS=1 | 65 | 59 |
| default SENDABLE=1 | 6 | 0 (PASS) |

Gone from the default image: cManager<cEm>::createBack and cEmMgr::memClear (pl_sub), cManager<cLight>::destroy and
::log (pl_npc), drawPoint and Draw_line3d_local_222 (objWep). From FIGHT / BOSS also em_set's cManager<cEm>::create and
countActiveWork (the pool) and, in FIGHT, em10ScaleCompress (item 4). Control: `MGR_EXTRA=-DE1_MGR_ORIG_CREATEBACK=1`
FAILs on pl_sub's createBack (416 B).

## What changed where

- `services/model/pool.h`, `services/model/mgr_pool.cpp`, `hostref/svc/pooltest.cpp` (SERVICES.md 41).
- `services/laser.cpp`, `services/e1_laser.h`, `core/draw_e1.c` (e1_laser_pass), `host/e1_stubs.cpp`,
  `game/Makefile` WEAKEN_game/objWep (SERVICES.md 42).
- `services/input/vib_table.h`, `core/loader.cpp`, `hostref/host_glue.cpp` (SERVICES.md 43).
- `hostref/host_stubs.cpp` (the magazine), `host/e1_stubs.cpp` (the same rules), `hostref/svc/aimcheck.cpp`, `svc.mk`,
  `aim_check.sh`, `tools/plays_right/fixtures/shot-ganado.txt` (PLAYS_RIGHT.md).
- `services/skeleton/skel.{h,cpp}` (skel_compress_y), `services/skeleton/em_compress.cpp`, `game/Makefile`
  WEAKEN_em10/em10, `hostref/svc/svc.mk` weak6/, `svc5_dump.cpp` control nocompress (SERVICES.md 44).
- `render/native_layers.inc` (per-widget blend), `core/draw_e1.c` (HUDOLD boot file).
- `hostref/svc/svc_controls.sh`, `svc5_units.sh`, `tools/plays_right/controls.sh`, `outcome_controls.py` (fail closed).
- `core/frame.cpp`: the E1 LASER and E1 POOL report lines.

## Run-time lab arms and boot files added

- `HUDOLD` (E1 images): every HUD widget with blend 0, the look before this lane (the HUD control and the "before"
  still of the pair, from the same image).

## Not done / not covered

See the hand-back's "Not done".
