# Lane world-ch32 (chapter 3-2 on Disc 2, Test 27 or later)

Branch `lane/world-ch32` (origin), merged with t15/int (99ef42358, then the emleon03..09 and sky census fixes).
Disc 1 is unchanged except a default-off PS2_ENEMY_CASTLE bit; Disc 1 links no st2_1.

## Chapter 3-2 rooms and events
Route (worldch32/route-32.txt): r204 -> r205 -> r204 -> r209 -> r20a -> r20b, ending with r20b s00 (End of Chapter 3-2).
r22c (the optional shooting range, st2_4) is not on the 3-2 route and is left out.

| Room | Place | Enemies | Events | Data (cw32) | rr 1102-1442-d4ef6d18 (Flycast, 60 s warps) |
|---|---|---|---|---|---|
| r204 | 3-1 end / 3-2 hub | em14 | s00 | cgca26 | all PASS |
| r205 | pendulum pit | em2d | area-3 cut (the PS2 drops it) | 21 PS2 objects, 4 pictures | enters; em2d now loads (no heap 4 refusal); room set-up stalls (FPS 0.1 at frame ~186), so TEXCHK has no coverage. OPEN |
| r209 | Zealot hall | em1a | s00 at door 4 | 24 objects + BIN pairs 20/22/24, 12 pictures, 4 motions | TEXCHK, CAST-GC, LEON-GC, VRAM PASS; cap peak 4; GC-ASSET checkpoint not covered |
| r209 s00 | door 4 opened (etcdoor) | - | s00 movie + 2nd battle | - | ran, no HALT |
| r20a | Novistador room | em23 em2d | - | 23 objects + pair 21, 6 pictures, 2 motions | PASS except GC-ASSET: 1 unreviewed texture 72be589c-3bbd0657 |
| r20b | 3-2 end, merchant | em18 em22 | s00 | 22 objects + pair 1f, 4 pictures | TEXCHK etc PASS; GC-ASSET checkpoint not covered |

Disc 2 rows of that cycle:
- PASS: build + disc_lint, census 11/11 ran, CAST-GC, LEON-GC 11/11, VRAM no-contig 0, HALT/FAULT 0, cap 4, KOS 48 KiB
  (min headroom 30264), GDEMU race.
- FAIL: TEXCHK 10/11 (r205); GC-ASSET (r209 / r20b checkpoints not covered, r20a 72be589c).
- Disc 1 rows: all PASS (36/38 overall).

## Data sets (Disc 2 only)
- `cw32-20261102` rev 2: st2 .dar only, 38 picture keys. The 48 keys cgca26 already ships are not repeated. 6 keys are
  also in world-ch334's cgca34 (reports/tex-shared-cgca34.txt, for the merge dedupe).
- `pmcw32-20261102`: PS2 motion. re4-assets-private manifest commit 0f5049d.
- Recipe: `D2_DATA="cgca26,pmcgca26,cpic26,cpic26b,cpic26c,cw32,pmcw32"`; t11-fix DATA rows cw32 / pmcw32.
- Generator: tools/d367/worldch32/gen-all.sh (ROOMS / CEM / SNDEM / SPECS / PRIOR_TEX from env); binpairs.py.

## Spawn unit
PS2_CH3_ENEMY covers 3-2 as one knob: the r20b waves (bit 0x02, existing) and the r205 area-3 cut (bit 0x10, this lane).
r209 0x9E is verified the same as GC (PS2-ENEMY-CODE-DIFF-20261015); r20a has no Normal change. Cap 4 on top.

## Gates wired
rr-jobs.sh disc2_jobs: d2cg / d2gca jobs for r205 r209 r209s00 r20a r20b (warps in worldch32/warps).

## CH-FIXES-CARRY status (3-2 rooms)
- Rows 1/2 (PS2 assets, motion): cw32/pmcw32; GC-ASSET open (above).
- Row 3 (CAST-GC/LEON-GC): PASS.
- Row 5 (spawn, cap): PS2_CH3_ENEMY 0x02|0x10, hold-only; cap PASS.
- Row 6 (PCCULL): GAP. No 3-2 room has a cell: the log says "not this package" for every room.
- Row 8 (KOS): d2kos PASS (door/fight segments are the 3-1 ones).
- Row 10 (R4TC sidecar): GAP. The castle tree has no ps2-world.r4tc for r205 r209 r20a r20b.
- Row 15 (resident lists): vram/resident r205/r209/r20a/r20b.tsv exist; evicted 0; dynamic 0.9-1.3 MB after preload
  (late uploads) to trim.
- Row 17 (TEXCHK): r209 r20a r20b PASS, r205 open.

## Open
1. The r205 stall at room set-up. A/B bases (ctl, and cw32 without r205.dar) via castlegca26/ctl-disc2.sh; paused for
   the Test 26 release check.
2. GC-ASSET: r20a texture 72be589c-3bbd0657; r209 / r20b checkpoints not covered in the 60 s window.
3. PCCULL cells and R4TC sidecars for the 3-2 rooms.
