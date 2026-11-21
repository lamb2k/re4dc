# Lane eng-e1i: the HUD and the last manager template (2026-11-20)

**Status: finished, unaudited.** Hand-back: `E:\RE4DC-Lanes\eng-e1i\HANDBACK.md`. Emulator results are **Flycast**
(standard slots, function checks). No timing claim, no model run; the pacer and the timing rows are untouched.

| Brief item | Result |
|---|---|
| 1. Ammo digits | Cause: the PS2 digit pictures (16 x 32, glyph at rows 5..28) drawn over their whole canvas, the capture's digits frozen at "10", widget rotation read as radians, padded pictures' coordinates not scaled, the wrong draw order. Fixed in the bake (`bake/hud_fix.py`) and the renderer (SERVICES.md 45); the digits are live (the magazine split once a tick). Check `s/hudcheck.py` (lane folder): fight 23 stills PASS (10, 9, 7, 5, 4, 9, ... read right), village and hill 36 PASS; control (the old 0..1 cut) 23 of 23 WRONG |
| 2. Lens | No screen copy: every HUD unit in the capture's RAM has trans_type 0. The dark, off-centre lens was the rotation (sphere light turned away) and the shrunk gauge frame. After the fix the lens matches the old game's still. HUDOLD keeps the old reading |
| 3. cObj manager template | `!*/* cManager<*>::* c*Mgr::memClear*` in allowed_original.txt: default FAIL 2 (wep02 createBack 416 B, cObjMgr::memClear 12 B); cManager<cObj> on the engine pool (mgr_pool.cpp): default 0 PASS, SENDABLE 0 PASS. Control `MGR_EXTRA=-DE1_MGR_ORIG_COBJ=1` FAIL 2. Other allowed units: only game/dmg's cManager<cDmg> create / destroy / log and cDmgMgr::memClear (FIGHT, BOSS), already offenders |
| 4. Laser dot still | fight tick 280: the dot on the Ganado's face (lane folder ev/laser). Size and colours stay eng-e1h's: the reference still has no laser |
| 5. Pool refusals fail the scene | selector.c: non-zero or missing `E1 POOL` line fails an E1 scene. Control POOLCTL: FIGHT FAILED "pool refused: full 0, bad frees 1", LEON OK on the same disc |
| 6. Docs | SERVICES.md 45-47, bench/NATIVE.md (the hud_fix step), this note |

## Link check, SERVICE functions per image

| Image | origin/engine 699132559 | this lane |
|---|---:|---:|
| default | 0 by the old list, 2 by the new list (control build) | 0 PASS |
| default SENDABLE=1 | 0 by the old list | 0 PASS |
| FIGHT=1 | 109 (eng-e1h hand-back) | 109 |
| BOSS=1 | 59 (eng-e1h hand-back) | 58 |

## Shared files touched

`render/native_layers.inc`, `render/native_scene.h` (the bench's HUD also draws in degrees and the source's order;
the bench has no live digits), `core/draw_e1.c`, `core/main.cpp`, `core/e1_core.h`, `services/draw.cpp`,
`services/model/mgr_pool.cpp`, `loader/selector.c`, `game/allowed_original.txt`, `tools/engine/build_console_disc.sh`
(defaults LKG, HILL_PAK, FIGHT_PAK: the packs after hud_fix.py in `E:\RE4DC-Lanes\eng-e1i\packs`).

## Run-time lab arms

- HUDOLD (boot file): the renderer's old reading (radians, every parent, deepest level first, frozen digits, blend 0).
- POOLCTL (boot file): a refused double free, the selector's control.

## Not done / not covered

- The EMPTY sign and the no-weapon player states for the digits.
- The packs must be re-made with `hud_fix.py` whenever a pack is re-baked (native_pack.py, hill_pack.py and the fight's
  pack_trim do not call it yet).
- Hill: a thin dark line crosses the bullet icon (a widget not identified).
