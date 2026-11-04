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

## rr cycle 1103-1811-e5635d31 (lane tools; Flycast 60 s warps; Disc 2 census 12/12 rooms)
Run from a lane copy of /root/rr/bin with this branch's rr-jobs.sh / rr-judge.py / rr-disc2.sh (the installed bin lists
only the 3-1 rooms). Evidence E:\RE4DC-Lanes\world-ch334\rr\1103-1811-e5635d31. Disc cache on E: (RE4DC_DISCCACHE) when
RR_EBASE is on E: (hard links cannot cross drives: cycle 1103-1322 failed on that).

| Room | CAST-GC | LEON-GC | TEXCHK | VRAM no-contig | HALT/FAULT | cap peak | GC-ASSET (d2gca) |
|---|---|---|---|---|---|---|---|
| r20c | PASS | PASS | PASS | 0 | none | 0 | 0 unreviewed |
| r20f | PASS | PASS | PASS | 0 | none | 0 | 0 unreviewed |
| r206 | PASS | PASS | FAIL (no coverage) | 0 | none | 0 | 0 unreviewed (stalled) |
| r20d | FAIL: em19 drawn GC (4200 parts, no PS2 cast plan / registry) | PASS | PASS | 0 | none | 2 | 0 unreviewed |
| r20e | PASS | PASS | FAIL: 3 keys open failed (3f0e6e6e-095478dd, b8a23b61-838818fa, f8da1db6-59ba93ae, 512x256 fmt 6; on no store, not on disc) | 0 | none | 0 | 0 unreviewed |

Disc-wide rows: build + disc_lint PASS; KOS 48 KiB PASS (min headroom 31480; door/fight segments are the 3-1 ones);
GDEMU race PASS; Disc 1 rows PASS. GC-ASSET FAIL is r203 only (3-1: 72be589c-3bbd0657 + GC model rows), not this lane.

- r206 stalls at room set-up: FPS 0.3 from frame ~183, KOS free falling 116984 -> 101984, no refusals (same shape as
  the 3-2 r205 stall). TEXCHK and GC-ASSET have no real coverage there.
- Size: Disc 2 data_sectors 454695 (was 454689 before 3-3/3-4); cgca34 mostly replaces castle-content files in place.
  Limit: disc_lint.py HD_END = LBA 549150 (end of the GD-ROM high-density area; track 3 starts at LBA 45000), so about
  504150 data sectors; mkdisc2.py reports it as limit 504000. Headroom ~49300 sectors (~96 MB). Fits; no split needed.
- 8 cgca34 tex keys are not on the disc (PRIOR_TEX / pack drops; 26 of 34 staged files identical): to check against r20e.

## CH-FIXES-CARRY status (3-3 / 3-4 rooms)
- 1/2 PS2 assets + motion: cgca34 / pmcgca34 staged; d2gca 0 unreviewed for all 5 rooms (r206 window stalled).
- 3 CAST-GC: OPEN r20d em19 (Zealot) drawn GC. LEON-GC PASS.
- 5 spawn/cap: PS2_CH3_ENEMY hold-only; peaks <= 4.
- 6 PCCULL: GAP, every room "cell=-1" (no cell).
- 8 KOS: PASS on the 3-1 segments; no 3-3/3-4 door segment yet.
- 9 sky: interiors, no rows needed.
- 10 R4TC: GAP, no ps2-world.r4tc for these rooms.
- 11 lighting: on program-wide. 12/13/14 effects/fire/sound: from cgca34 (banks PS2); effect census PASS.
- 15 VRAM residency: evicted 0, no-contig 0; resident lists not made.
- 17 TEXCHK: OPEN r20e (3 keys), r206 (stall).

## Gate closure, rr cycle 1103-2136-a1882cf5 (Disc 2: all rows of the 3-3 / 3-4 rooms PASS)
Disc 2 census 12/12: CAST-GC PASS, LEON-GC 12/12, TEXCHK 12/12, VRAM no-contig 0, HALT/FAULT 0, cap peaks <= 4, KOS 48 KiB
PASS (min 29816), GDEMU PASS; d2gca 0 unreviewed rows in r20c r20f r206 r20d r20e. Disc 2 GC-ASSET FAIL is r203 (3-1) only.
Disc 2 data_sectors 454735 (limit: disc_lint.py HD_END LBA 549150, track 3 at LBA 45000, about 504150 data sectors).
- r20d CAST-GC: em19 rows (emleon03 114..119) carry flag 0x4000 without 0x200000 = mot[38] BIN 0x217 + mot[40] TPL 0x219,
  a role zealot-em19-07p lacks, so registry_bind refused them (NMRS plan=G declined). ps2_cast.py zealot-em19-07q (07p +
  acc2-b 0x211|0x220 + acc5-b 0x217|0x219, the em1a-07q pattern); masks 13/16/20/22; model_registry.py --package-room 20d
  --source-normal-length --wide-identity --pool --roles5 (flags proven: castle18 reg-r208-v2 e28cd7a3 rebuilt byte for byte).
  Data set r20dem19 (dc/native/r20d/registry.re4nmr a95a8850, 120768 B). After: NMRS id=19 plan=R native=1050 declined=0.
  The partner package (Ashley pl01-no/nc, castle21 4a0825ce) is unchanged.
- r20e TEXCHK: the armor (em3c) registry package's 5 textures were not on Disc 2; and 4 cgca34 PS2 pictures lost to the base
  pack's bytes (castle_fixture drops loose keys the pack has). cpic34 = cpic27's pack + both (castlegca34/mkcpic34.py).
- r206: not a stall. The census warp landed on the Luis event (r206s00, 3030 frames, 101 s), past the 60 s window.
  j-r206 now sets rsf 0x206 bit 5 (r206_die_event done); o-r206s00 keeps the movie entry. r206 runs at ~17 fps (Flycast).
  For world-ch32: r205 may be worth the same check (is a movie / event running at the frame-186 "stall"?).

## CH-FIXES-CARRY rows (3-3 / 3-4), updated
- 1/2/3 PASS (above). 5 cap PASS. 8 KOS PASS (3-1 segments). 11-14 program-wide / cgca34.
- 6 PCCULL: OPEN. Cells are hand-authored (ps2world/interior: survey.py hull + eye boxes, build_cell.py, scan proof) and
  cull the outdoor world from inside a house; no castle room has one. These rooms draw unculled (allowed, logged).
- 10 R4TC: generated, not on disc. /root/re4data/private/trans34-20261103 (r206 239 parts, r20c 111, r20d 525, r20e 242,
  r20f 165; UNKNOWN parts draw as today). Disc 2 trclass.idx takes a room only after its tier 2 look gate.
- 15 resident: castle18/r20c r20f r206 (new) r20d r20e lists from the 2136 runs; res34 = res26pr2's Disc 2 resident.bin
  with those rooms replaced (every other room kept). On D2_DATA; its cycle did not run (C: 3 GB, lanelock refused).
- Stores cpic34 / castle34-em19 / res34 / trans34 are in /root/re4data/private; the copy to re4-assets-private + manifest
  is pending (C: full).

## 11-04: R4TC tier 2 look gate (CH-FIXES-CARRY row 10) and the Disc 1 GDEMU seed-1 fail
Arms: A = t15/int 83c26c8ee (rr 1104-0106, sidecars off: "trans: classes=unlisted"), B = 82dbd3206 (rr 1104-0214,
D2_DATA += trans34d2: "classes=ok"). Same Disc 2 census twin program; per room the census warp + `freeze 700` (r20f froze
at 958), fp_run --period 4, the last frozen shot of each arm, tr_pixdiff.py (no mask). Stills + heat maps:
re4-assets-private/trans34d2-20261104/look.
| Room | changed | verdict |
|---|---|---|
| r20c | 0.0 % | tier 2 PASS |
| r20f | 0.0 % | tier 2 PASS |
| r20d | 0.0 % | tier 2 PASS |
| r20e | 0.0 % | tier 2 PASS |
| r206 | 13.2 % | held: the torch-flicker lighting keeps changing in the frozen frame (two frozen shots of the same arm differ by ~10 %; heat on the flames, Leon, the lit dais, the HUD), so the gate cannot separate the sidecar; the pair looks identical by eye |
D2_DATA trans34d2 = the trans17 index + r20c r20f r20d r20e and their sidecars (r206 held; needs a flicker-free view or a
TRANS_POLICY_DEBUG mask still). Cycle B verdict: 38/39, the one fail a Disc 2 GC-ASSET r200 "layout" row (3a00a62f,
source geometry) seen because B's 60 s window reached a third r200 visit (A two); r200's sidecar and index entry are
unchanged between arms.
GDEMU (Disc 1, door103): seed 1 FAIL in 1103-2345 and 1104-0106, seeds 2 and 3 PASS (0 bad reads, r103 load 2.8 / 2.4 s).
Seed 1's read-log.err is empty and it has 0 bad reads: the guest ran ~782 ticks in the 60 s host window (seeds 2/3 reach
vbl 2478 by 41 s), so the door act (vbl ~1868) never came. Host throughput in the busy start of the cycle, not a disc read.
