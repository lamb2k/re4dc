# Lane world-ch32 (chapter 3-2 on Disc 2, Test 27 or later)

Branch `lane/world-ch32` from origin/t15/int 15ed29fe5. Disc 1 program and data unchanged by this lane.

## Chapter 3-2 rooms and events (GC/PS2 data, CASTLE-ROUTE-20261015 round 8, CH3-FOUNDATIONS-20261016)

Route: r204 -> r205 -> r204 (part 1) -> r209 -> r20a -> r20b; ends with r20b s00 (End of Chapter 3-2). r22c (shooting
range, stage st2_4, linked by no knob) is optional and left out.

| Room | Place | Enemies (module) | Events | Data (this lane) | Earlier first pass (Flycast) | Status |
|---|---|---|---|---|---|---|
| r204 | Chapter 3-1 end / 3-2 hub | em14 | r204 s00 | in cgca26 (castle-gca-26) | PASS | data done |
| r205 | Novistador cave hall | em2d | - | cw32: 21 PS2 objects, 4 pictures | all PASS; heap 4 refused em2d.drs (h2-02) | data done, not run |
| r209 | Zealot hall, 2nd battle | em1a | r209 s00 (door 4, r209_2ndBattle) | cw32: 24 PS2 objects + 3 BIN pairs, 12 pictures, 4 PS2 motions | model FAIL (em1a GC; fixed by cgca26 em1a) | data done, not run |
| r20a | Novistador room | em23, em2d | - | cw32: 23 PS2 objects + 1 BIN pair, 6 pictures, 2 PS2 motions | all PASS | data done, not run |
| r20b | Chapter 3-2 end (merchant) | em18, em22 | r20b s00 | cw32: 22 PS2 objects + 1 BIN pair, 4 pictures | all PASS, s00 + skip -> End of Chapter 3-2 | data done, not run |

## Data sets (Disc 2 only; not yet on D2_DATA)
- `/root/re4data/private/cw32-20261102` (116 files sealed): st2/r205 r209 r20a r20b .dar/.arc, em/em2d em23 em18 em22 .drs,
  79 PS2 picture keys, provenance.tsv (776 rows, 133 ps2).
- `/root/re4data/private/pmcw32-20261102` (21 files): PS2 motion (VERIFY PASS for all 8 files).
- Generator: `tools/d367/worldch32/gen-all.sh <Disc 2 tex.pak> <Disc 1 tree> 20261102` (castlegca26 method; ROOMS / CEM /
  SNDEM / SPECS from env). Inputs used: pak rr 1102-0559-352687ac d2/fx/tex.pak, Disc 1 tree castle-gca-26-scratch/d1tree.
  BIN pairs from `worldch32/binpairs.py` (GC index = PS2 index in every 3-2 room; r205 has no room BINs).
- Sound: 302 samples, 269 PS2, 33 GC kept (snd28 store rows; listed in reports/snd-map).
- Enemy models: em2d 1 member PS2 (2801 -> 2265 tris), em22 1 member; em23 and em18 0 members converted (no PS2 BIN match:
  GC-ASSET will show whether they need the cast path or allowlist rows).
- Proposed recipe line (after the gate): `D2_DATA="cgca26,pmcgca26,cpic26,cpic26b,cpic26c,cw32,pmcw32"`, plus the store
  copies in re4-assets-private and its manifest.

## Not done (blocked)
- C: had 19 GB free (floor 40 GB): no rr Disc 2 cycle, no Flycast runs, no disc build.
- CH-FIXES-CARRY.md not written yet (lane world-ch31).
- Gate rooms: the Disc 2 GC-ASSET / CAST-GC census covers r200-r208; add r205 r209 r20a r20b.
- PS2 spawn port for 3-2 as one knob: PS2_CH3_ENEMY already carries r20b (bit 0x02); r209 "small (verify 0x9E)", r205 /
  r20a no Normal change. Needs the r209 check before a 3-2 knob.
- em2d does not fit heap 4 in r205 (needs em2d motion streaming: design item).
- Warp presets / route file: earlier cx32 warps in castle18; none written for Disc 2 yet.
