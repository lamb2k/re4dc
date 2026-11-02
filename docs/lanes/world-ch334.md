# Lane world-ch334 (chapters 3-3 and 3-4 on Disc 2)

Branch `lane/world-ch334` from origin/t15/int 15ed29fe5. Disc 1 program and data unchanged by this lane (every change is
a D2_DATA set, a Disc 2 gate list or a tool option that defaults off).

## Boundary (chapter-end events, src/st2)
- 3-2 ends at r20b s00 (`SceSetChapterEnd(CHAPTER_3_2)`, r20b.cpp). Chapter 3-3 starts there (warp `chapter 8`).
- 3-3 ends at r206 s00, Luis' death (`SceSetChapterEnd(CHAPTER_3_3)`, r206_die_event).
- 3-4 is Ashley's section (pl_type 1 in r20d / r20e) and ends at r206 s20, the reunion (`SceSetChapterEnd(CHAPTER_3_4)`,
  r206_gouryuu_event), then item_chk merges Ashley's items. Chapter 4-1 (r210 on) belongs to lane world-ch4.

## Rooms and events
| Room | Chapter | Place | Enemies (module) | Events | Data (cgca34) | Warp | Status |
|---|---|---|---|---|---|---|---|
| r20c | 3-3 | cage / Zealot hall | em11 em1b em25 | - | 12 PS2 objects + BIN 1f, 5 pictures, banks 57/61 PS2 | h-r20c | data done, not run |
| r20f | 3-3 | Zealot room | em14 em25 | - | 16 PS2 objects + BIN 1f, 6 pictures, banks 34/36 PS2 | i-r20f | data done, not run |
| r206 | 3-3 end, 3-4 end | Luis / reunion hall | em11 | s00 (Luis, end 3-3), s10 (snipe), s20 (reunion, end 3-4) | 13 PS2 objects + BIN 2f, 3 pictures, banks 37/38 PS2; BIN 32 and 34..3a + FCV 3c..3e kept GC | j-r206, n-r206s20 | data done, not run |
| r20d | 3-4 (also Leon in 3-3) | Ashley lantern hall | em11 em19 em25 | death trap demo | 11 PS2 objects + BIN 23 29, 6 pictures, banks 51/51 PS2 | l-r20d (Leon) | data done, not run |
| r20e | 3-4 | Ashley maze (armor) | em3c | Salazar crest | 8 PS2 objects (1 NONE), 2 pictures, banks 42/42 PS2 | m-r20e (Leon) | data done, not run |

Enemy archives: em11 8 members PS2 (3627 -> 3105 tris), em3c 3 members PS2, em25 0 (its BINs are the native cast's;
BIN 0x31 rebuilt larger than its slot, kept GC). em14 / em19 / em1b come from cgca26 already. Motion: em11 135 FCV
PS2-changed; em25 / em3c / the room archives already PS2-identical (VERIFY PASS each).

## Data sets (Disc 2 only)
- `/root/re4data/private/cgca34-20261102` (109 files, sealed), `/root/re4data/private/pmcgca34-20261102` (154 files);
  copies in re4-assets-private (manifest).
- Generator: `tools/d367/castlegca34/gen-all.sh <Disc 2 tex.pak> <Disc 1 tree> 20261102` (castlegca26 generalised:
  ROOMS / CEM / SET / SPECS from env). Inputs: castle-gca-26-scratch d2-1409ac5e-tex.pak and d1tree.
- `motion/ps2_motion_prepared.py --keep-gc` (new, default off): FCV / SEQ slots the PS2 archive dropped keep their GC
  member, verified unchanged (r206 56,57,58).
- Recipe: `D2_DATA="cgca26,pmcgca26,cpic26,cpic26b,cpic26c,cgca34,pmcgca34"`; t11-fix.py DATA rows; 12 kept GC samples
  in gc_port23/sound-kept-gc.tsv (owner world-ch334).

## Spawn logic and cap
PS2_CH3_ENEMY (one knob, all of chapter 3, already in CH4REC on the Disc 2 program): of these rooms only r20e has PS2
row differences (list 3); r20c r20f r206 r20d have none. ALIVE_CAP=4 + ALIVE_CAP_NOVIS=1 apply. No boss in 3-3 / 3-4.

## Gates (not run: C: had 18.6 GB free, floor 40 GB)
rr-jobs.sh disc2_jobs: the five rooms join the d2cg census (CAST-GC / LEON-GC / TEXCHK / VRAM / cap) and the d2gca
GC-ASSET lists. KOS squeeze, GDEMU and Disc 1 identity ride the same rr Disc 2 cycle.

## Open
- r206 GC leftovers: BIN 0x32 (converter refuses, PS2 positions outside s16) and BIN 0x34..0x3a (no PS2 entry). If the
  gate draws them they need allowlist rows or a converter fix.
- Ashley's section has no warp key for pl_type 1: the play-through reaches it from the r206 s00 save.
- Route 3-3 -> 3-4: r20b (end 3-2 save) -> r20c -> r20f -> r20d -> r206 (s00, end 3-3) -> Ashley: r20d -> r20e -> r20d
  -> r206 (s20, end 3-4). Door order from the GC/PS2 tables, to confirm in the play-through.
