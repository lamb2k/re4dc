# Lane items: PS2 pickups, medals and breakable debris for test 12 (2026-10-14)

User direction 2026-10-14: test 12 ships the complete PS2 world on the disc 1 route (17 rooms: r100 r101 r102 r103 r104
r105 r106 r107 r108 r109 r10a r10b r11a r11b r117 r118 r119). A GameCube model drawn where a PS2 version exists is a
bug. GameCube logic stays: pickup, collision and break code are unchanged; this lane changes disc data plus one
default-0 render knob.

Worktree /root/probe/lanes-20261014/items/tree, branch lane/items from lane/t11 eb4e8813. Work dir
/root/probe/lanes-20261014/items/work (out/<room>, lib, fixtures in ../fix). Library rows:
re4-assets-private\ps2lib\items and ps2lib\breakables plus INDEX.tsv (owner_lane items). Disc data:
re4-assets-private\items-20261014 (<room>i/<room>.dar, core/core.das, sscmn/, tex-items.pak, SHA256SUMS). Evidence
C:\Flycast-Evidence\re4-dreamcast\items-20261014. Full notes: C:\Game Dev\Emulators\PS2-ITEMS-20261014.md.

## Classes and where their models live

| Class | Model source | Key |
|---|---|---|
| Pickups (obj19 cItemObj, shoot-down items, items enemies carry) | room archive ITM block (cItmSys::DataLoad: id table + bin/tpl pairs) | item id |
| Pick-up zoom models (itemZoom) | ss/cmn/itmXX.bin/.tpl | item id |
| Blue medal / etc emitems (Et1a cEmItem) | ETM et1a00.bin: already PS2 (lane objs / p2b), not touched here | ETM name |
| Breakable debris (Efm effect models, record Id 0xFC..0xFF, obj04/05/09) | efm table of an EFF: room EFF, ETM .eff members, core.das entry 1 | efm id |

Mapping (17 rooms): ITM ids identical GC/PS2 in every room (304 placements, 40 models); 18 zoom models 1:1; Efm 109
placements, 99 converted. No PS2 model (ps2_source=NONE): r101 0x02, r106 0x5a, r10a 0x7b, r10b 0x7b/0x7c, r119
0x14/0x16/0x17, r11a et10 0x0f, core 0x3e.

## Tool: tools/ps2_items.py

    ps2_items.py convert --lib <ps2lib> --commit <sha>        one pass per class over all route rooms + core + SS/cmn
    ps2_items.py pack --dar <in .dar> --room rNNN --lib <lib> --out <new .dar> [--json report]
    ps2_items.py pack-core --das <core.das> --lib <lib> --out <new>
    ps2_items.py pack-ss --src <dir with GC itmXX.bin/.tpl> --lib <lib> --out <dir>
    ps2_items.py census --dar <staged .dar> --room rNNN --lib <lib>   offline GC-fallback count (exit 1 on any GC slot)
    ps2_items.py verify --dar <dar>                                   texture_package.cpp NTR checks
    ps2_items.py gate --lib <lib> --rooms r100,... --result PASS:<run>   records a gate in INDEX.tsv (lane items rows)
    ps2_items_tex.py (Windows Python)                         <lib>/<class>/tex/<key>.re4tex from the PS2 pictures

- Geometry: ps2_objects.rebuild (lane objs' converter). itm01/02/0e and ae/b0..b4 re-quantised one shift lower (PS2
  positions just past s16 at the GC shift). Where the PS2 rebuild does not fit the GC slot and the PS2 mesh equals
  the GC mesh triangle for triangle, the GC bytes are kept (`gc-identical`; 12 models); their pictures still swap.
- Pictures: the PS2 TPL image of the same index, transposed back when interlace bit 0 is clear (PS2 UVs = GC UVs).
  Identity = the PS2 picture as GC CMPR (fmt 14) through native_ui.cpp image_key; ITM R4NREF records get the new
  key, resident Efm images get the CMPR texels. The displayed texture is the <key>.re4tex (VQ565 / 1555 / 4444 by
  alpha class, ps2_room_r4im rules) in tex.pak. CI4/CI8 identity is not usable: R4NREF refuses fmt 8/9.
- Packing is in place: payload size, entry offsets and NTR/ESQ tables are unchanged; heap 4 is the control's.
- Items dars are packed on lane objs' dars (objs-20261014/<room>o, r119c). If objs regenerates its dars, re-run pack.
- core.das: lane fx12 also rewrites core.das EFF #1 textures. Apply `pack-core` on the final core.das at landing (it
  refuses a model slot that no longer holds the GC bytes and a picture whose header is no longer the GC size/format;
  a resident picture with the GC header is overwritten, so check fx12's core EFF picture keys against ours first).

## Knobs and data sets

- `EFM_PS2_CUT` (effects30.mk, default 0): trans.cpp ModelRender returns before drawing an Efm model listed in
  eff_sys.cpp kEfmPs2Cut (the NONE rows). Render only: obj04/05/09 work, records, Rnd() and moves unchanged.
  Log `efm ps2 cut: room= id= total=`.
- `ITEMS_CENSUS` (effects30.mk, default 0): `itemcen:` lines per registered ITM / Efm model; gate
  `python3 tools/d367/items_census.py <ps2lib> <run-output.txt>` -> ITEMS-CENSUS PASS (0 GC fallbacks).
- t11-fix.py data sets: `items-<room>` (one dar, replaces objs-<room> / r119c) and `items` (17 dars + core.das + SS/cmn
  + tex-items.pak = tex-t11.pak + 71 packages; list it after the test 11 data so its tex.pak wins).

## Gates

See PS2-ITEMS-20261014.md "Results" for the run table (knob-off identity, warp STRICT + decision_cmp per room, H2 +
s30, TEX_CHECK=2, ITEMS-CENSUS, VRAM, look sheets).

## Results (2026-10-15, data ps2_items-v2@421b7251, code ed79dd0c)

- Knob-off identity: itemstP (ed79dd0c) vs t11htP IDENTITY PASS.
- 17 rooms (h2, objs sq101 / w102..w11b, p2b w119), check arm itemsmW: TEXCHK=2 PASS, ITEMS-CENSUS PASS (0 GC), no
  "no contiguous block", 0 pair missing, 0 upload FAILED, halt / missing / fault / LEONGC / overrun 0.
- STRICT + decision_cmp vs lane objs' objstT controls: MUST-IDENTICAL in all 17 rooms (2401-2402 ticks; h2 4702 with
  s30 340/340; r108 1100 ticks: both arms hit the 600 s deadline). ed79dd0c re-traced h2 / sq101 / wi119 / wi11a:
  MUST-IDENTICAL.
- v1 failed TEXCHK on one material pair (core efm25): fixed by v2 (masks + pair packages).
- Not exercised in a run: an Efm cut firing (no warp breaks anything), SS/cmn pick-up zoom models; both covered by
  offline look sheets (sheets/offline-look3.png: GC | ours | PS2 BIN direct).
