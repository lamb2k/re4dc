# Lane eng-look1: Leon's handgun (and what the muzzle flash lacks)

Status: **finished, unaudited**. Brief: `E:\RE4DC-Lanes\eng-look1\BRIEF.md`. Evidence: `E:\RE4DC-Lanes\eng-look1`.

## The cause

The engine drew no live weapon at all. The pistol the owner saw in the village's first pictures is not Leon's gun: it
is placement 209 (mesh 190, 184 x 290 x 72 mm, centred at -7763 1587 2272) of the r101 PS2 world package
(`dc/native/r101/ps2-world.r4pw`), which every pack built from r101 carries in its whole-room bake. The old port's
STATIC_OBJ_BAKE (lane crowd12, 2026-10-15) baked the room's static objects into that package, and with them the held
cObjRuger (kind 1, id 0x21) at the pose it had in the bake capture: in Leon's hand at the village warp start
(origin/t15/int `port/dreamcast/game/model_bridge.cpp`, sobake `kTable`: `{0x101,1,0x21,0x5f72f97e,209}`). The old port
draws that copy only while the live gun's model and part matrices are bit-identical to the baked pose
(PS2_PLACE_GATE) and otherwise draws the gun live through the original model pass (`ModelTrans`: be_flag 1, 2 and 4).
The engine draws every world placement and had no weapon model in its catalogue (`core/draw_e1.c` line 5: "Not drawn in
E1: ... the handgun model (not in the pack)"), so the copy stood fixed in the world: in the hand for the first pictures
(Leon stands still at the start), then floating by the barn door (the fight's stills from tick 440 on).

## What changed

| File | What |
|---|---|
| `engine/bake/weapon_model.py` (new) | The PS2 handgun models (em/wep02 archive slots 6 and 7, the Punisher and its upgrade; pictures of slot 5, PS2 packages only) into a pack's model catalogue in the catalogue's format; each part's role word tagged `0x5745SSAA` (file slot, archive slot). Bind = minus the rest position, as the skeleton service makes it. No format change; `--verify` lists the entries; `hud_fix.verify` re-run on the output |
| `engine/services/weapon.cpp`, `weapon_view.h`, `weapon_draw.inc` (new) | Each picture: the player's weapon objects (`cPlWep::m_pWep`, `pObj2`), the hosted gate (be_flag 1, 2, 4; in an event 0x800), the archive slot of the model data, the native skeleton table (pointers); a visible weapon drawn through the E1 actor pass on its own palette, lit by its own model record. At pack open: the catalogue mapped, the world copy retired (index, centre and size checked). E1 WEP lines (report; trace, run-length), WEPSTILL facts in stills runs, the NOWEP control |
| `engine/services/actor_e1.inc` | The pass returns whether it could draw; the weapon pass after Leon's opaque call; the pack-open hook |
| `engine/services/draw.cpp` | The weapon's trace choice before play, its record after each picture |
| `engine/host/e1_svc_mem.cpp` | One line: the E1 WEP report beside E1 PUB (outside the owned list) |
| `engine/loader/selector.c` | An e1 scene fails when the weapon's drawn count differs from its visible count, drawn-hidden is not 0, or the line is missing (outside the owned list; the brief asks for the selector rule) |
| `tools/engine/wepcheck.py` (new) | The still check |
| `tools/engine/build_console_disc.sh` | The packs with the weapon models (defaults); control scenes CNOWEP, CNOWEPH, CNOWEPF, CNWLS, CNWHS, CNWFS |

Packs (private, not in git): `E:\RE4DC-Lanes\eng-look1\packs\lkg-wep\CROSS.PAK`, `hill2-wep.pak`, `fight-wep.pak`
(eng-e1i's packs plus the two weapon models; the village and fight packs already held both pictures, the hill pack gains
two textures and two headers).

RESULTS: see the hand-back (`E:\RE4DC-Lanes\eng-look1\HANDBACK.md`).
