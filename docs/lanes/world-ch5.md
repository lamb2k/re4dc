# Lane world-ch5: chapter 5 (the island) and the Disc 3 arm

Owner: lane world-ch5 (Claude), 2026-11-02. Branch `lane/world-ch5` from origin/t15/int 15ed29fe.
User 11-02: build the remainder of the discs today, chapters 4 and 5 in parallel; warp and play-through testing come later.
Number labels: sizes are measured file sizes; no Flycast or console timing in this file yet.

## What landed on the branch

| Commit | What |
|---|---|
| 0941df76 | Merge origin/codex/island18 (44 commits: ch5found16 / island18 foundations, final16, stress16b, U-3, Krauser, r327, r300 diagnostics). 11 conflicts, both sides kept, each island18 addition behind its default-off knob |
| 5cd70341 | Merge fix: native_motion.cpp lost the MOTION_RESERVE_PACK `#endif` |
| faff5647 | Disc 3 arm: DISC3_MODULES, AICA_SHARED_BGM1 gate, island5/build-disc3.sh, discsets d3-content.sh / disc3_fixture.py / mkdisc3.py, rr/rr-disc3.sh, rr-cycle hook, recipe RR_DISC3=0 |
| (next) | em16 module guard for DISC3_MODULES, Disc 3 em prune + village/castle pack prune, island5/disc3-lane.sh, this doc |

**Knob-off identity (Disc 1 and Disc 2 unchanged):** at 5cd70341 + the AICA_SHARED_BGM1 gate, Disc 1 rP image f6f938e6 and
Disc 2 d2rP image 845f373d plus all 15 / 23 overlays are byte-identical to rr15ed29f (the 15ed29fe release cycle). Without
the gate the merge changed the release image (re4dc_audio_arq +400 B: island18 c0819831 ran under AICA_SPILL).

## Disc 3 arm design

- **Hand-off:** no Disc 1 / Disc 2 change. Their programs already carry DISC_SET=1; game.cpp StageInit needs disc 3 once
  pG->chapter >= 14. r22a ends chapter 4-4 (`SceSetChapterEnd(CHAPTER_4_4)`), the chapter-end save follows, and loading
  r300 on Disc 2 holds on "insert disc 3". The player boots Disc 3 in GDEMU and loads the save (no hot swap, I-002).
- **Program:** `island5/build-disc3.sh` = release CH2 (DISC_SET=1) + D3CARRY (the program-wide CH4REC fixes: NO_GC cast
  path, Ashley PS2, cap-4 Novistador / defer rules, SS pool top, statue lights, PS2 mist, haze cut, registry dying / run
  share / blend table, NATIVE_BUMP_FLAT) + D3REC (ROUTE_CH3 STAGE_OVL ROUTE_MOVIES, DISC3_MODULES, PS2_ENEMY_ST3=23,
  ALIVE_CAP=4 + PARK, island PRIM budgets, AICA_SPILL + AICA_SHARED_BGM1, AICA_STR_ENT_MAX=56, ARENA_KOS_BYTES=53248,
  MOTION_LARGE_CLIPS, ROUTE_FINAL, NMR_PRELOAD_SKIP, RESIDENT_SHARED_R327). Build wc5d15ed29fd3rP: image e565cfa9,
  missing 0, _end 8c3d1b74.
- **DISC3_MODULES=1** (new, default 0): DISC2=1's stage-1 module drop (+ em16) for heap 4, with the dc/disc.id identity.
- **Data:** `discsets/d3-content.sh` composes the island content tree `/root/re4data/private/island-d3-20261102`
  (5075 files, 852 MB, SHA256SUMS 5cc3d65388b35977): ch5regen-20261018 (33 rooms) + island18 resident, r333 route
  streams, r300 / r30f / r317 / U-3 sound, U-3 large motion, Krauser hot set, r317 QTE movies, pack tex-ch5e.
  `disc3_fixture.py` lays it over the Disc 1 candidate tree (island-owned files win; pack = Disc 1 pack + island keys, minus
  672 village/castle-only keys, 9.4 MB). `mkdisc3.py` prunes village (309 files, 525 MB) and castle r200-r22b (51, 19.6 MB)
  rooms, 22 unused enemy / partner archives (84 MB), keeps r22c, writes dc/disc.id `disc=3`.
- **Size:** 502,781 of 504,000 data sectors (99.76 %), 5672 files, 1,020.8 MB. disc_lint loader + standard PASS.
  Built at /root/probe/lanes/world-ch5/cand-15ed29f/disc3/gdemu (ext4; for the play-through test).
- **rr:** `rr/rr-disc3.sh` mirrors rr-disc2.sh (program, tree, master, census twin d3c, GC-ASSET twin d3a);
  recipe.conf RR_DISC3=0 until the gates pass. rr-jobs.sh has no disc3_jobs yet (room list = the table below), and rr.sh /
  t16-package.sh do not put disc3/ in the game zip yet.
- **Lane build outside rr:** `island5/disc3-lane.sh <rr work> <lane home>` (read-only on the rr candidate).

## Room / event table (route from ISLAND-ROUTE-20261016.md; status = last measured, ch5found16 round 7, Flycast, cap 4)

| Ch | Room | Events | Enters | CAST-GC (10-17) | Notes |
|---|---|---|---|---|---|
| 5-1 | r300 | s00 landing (from r22a rope) | yes | PASS (r300 LEON frame-180 fallback, island18 H-009) | |
| 5-1 | r301 | waves (PS2 bit 1) | yes | FAIL em1e GC | |
| 5-1 | r303 r304 r306 r308 | r304 s00 | yes | PASS | |
| 5-1 | r305 | 7 kills | yes | FAIL em1e GC | door to r22c |
| 5-1 | r307 | | yes | PASS | VRAM tight (76 KB free) |
| 5-1 | r30b r30c | r30b s00 -> r310; r30c s00 ends 5-1 (0xE) | yes | FAIL em1f GC | |
| 5-2 | r30e r309 r30a | r30a s00/s10 lift -> r316 | yes | PASS* | |
| 5-2 | r310 | r310 s00 | yes | PASS | tex_rej 12.5 KB (island18 res1: 0 refusals) |
| 5-2 | r311 r30d r312 r30f r315 | r30f bulldozer | yes | r311 / r30f FAIL em1f, r315 FAIL em1e | r30f heap 4 low 294 KB |
| 5-2 | r316 | s00 ends 5-2 (0xF) | yes | PASS* | |
| 5-3 | r317 | s00-s15 Krauser knife QTE | yes | CAST FAIL (wounded GC overlay) | |
| 5-3 | r318 r31a | laser corridor, lift | yes | PASS | |
| 5-3 | r31b | s00 U-3 | yes | CAST FAIL (U-3 texBlend) | MOTION_LARGE_CLIPS |
| 5-3 | r31d | | yes | FAIL em1e | door to r22c |
| 5-3 | r31c | s00-s02 Krauser, ends 5-3 (0x10) | yes | Krauser invisible (no NMRS rows) | em39 fits only with the hot set |
| 5-4 | r320 | s00/s01 Mike | yes | FAIL em1d | heap 4 low 103 KB; gatling = documented cap exception |
| 5-4 | r321 r325 r326 r329 | movies | yes | PASS | |
| 5-4 | r327 | camp (PS2 bit 2) | yes | FAIL em1d | kept gatling Ganado = cap exception |
| 5-4 | r330 | s00 ends 5-4 (0x11) -> r331 | yes | FAIL em1f | |
| final | r331 r332 r333 | Saddler, jet ski | not on Disc 3 yet | | data in island18-final-*; Disc 3 has 1,219 sectors left |

## Gates

| Gate | State |
|---|---|
| Disc 1 / Disc 2 knob-off identity | PASS (above) |
| Disc 3 build, missing 0, disc_lint | PASS |
| Flycast warp runs, enter / clear / open per room | NOT RUN (user: testing later; C: had 24 GB free, under the 40 GB floor) |
| GC-ASSET / CAST-GC on Disc 3 | NOT RUN; expected FAIL: soldiers em1d / em1e / em1f on the GC path in 11 rooms, U-3, Krauser |
| TEXCHK, VRAM per room, KOS 48 KiB | NOT RUN on Disc 3 (round 7 / island18 numbers above are the last) |

## Blockers / open

1. Soldier cast (em1d / em1e / em1f) has no PS2 registry package: CAST-GC and GC-ASSET fail in 11 rooms. Needs the
   ps2cast converter run for the three soldier types (boss-check lane owns U-3 / Krauser / Saddler models).
2. Disc 3 space: 1,219 sectors left. The final chapter (r331-r333 rooms, worlds, em31, pl0e, movies) does not fit until the
   island's 3,816 loose 16-bit textures (147 MB) become VQ / PAL (CH-FIXES-CARRY row A1, lane assets-dc).
3. CH-FIXES-CARRY per-room data rows (interior cells, R4TC sidecars, PS2 sound / effect sets, resident lists for the
   rooms without one, PS2 motion stores) are not built for the island; program-wide rows ride D3CARRY.
4. rr-jobs disc3_jobs + packaging of disc3/ into the game zip are not written (rr infrastructure; coordinator call).
5. make_catalog.sh is called with PROVENANCE_D2=1 in rr-disc3.sh; Disc 3 provenance rows need checking.

## Round 2 (2026-11-02 afternoon, coordinator items 1-5; evidence on D:\RE4DC-Lanes\world-ch5, user "Use D: for now")

- **Soldiers (item 1):** the PS2 cast packages already exist (lane cast16: model-registry ps2-ch5-em1dp / em1dp2 / em1ep /
  em1fp, 16 island room registry.re4nmr packages in the island tree). They are bump bodies admitted only with
  NATIVE_BUMP_FLAT=1, which the 10-17 island arms lacked (the round-7 CAST-GC FAILs). Disc 3 now carries NATIVE_BUMP_FLAT=1
  (D3CARRY, as Disc 2). Proof = the d3cg census rows (queued).
- **CH-FIXES-CARRY island rows (item 2):** resident lists exist for all 33 rooms (vram/resident/r3*.tsv); Disc 3's
  resident.bin is now Disc 1's current resident.bin + those lists (disc3_fixture.py, water_resident.py pack), not the older
  island18 copy. Registry packages: 26 of 33 rooms (the rest have no soldier cast). Interior cells (row 6), R4TC sidecars
  (row 10), PS2 sound / effect sets (rows 12, 14) and PS2 motion stores (row 2): none built for the island yet.
- **rr integration (item 3):** rr-jobs.sh tier d3 / disc3_jobs (island5/rooms.tsv: 33 census rooms, 21 GC-ASSET rooms,
  KOS d3door r300 -> r301 and d3fight r30f), kos_squeeze.sh d3door / d3fight, t16-package.sh disc3/ in the game zip, rr.sh
  Disc 3 knob file + Build-Assets zip, provenance.py PROVENANCE_D3 / recipe D3_DATA. Job paths: t15/int 99ef4235's rr_gb kept.
- **Gates (item 4):** Disc 3 census twin built and its base mastered on D: (_discs/d3c, 5646 identical / 30 differing
  files, as expected for a twin). **GC-ASSET twin FAILS to build: catalog_index.py MAX_RECORDS 16320 ("catalog capacity")**:
  the Disc 3 catalog has more rows than the runtime index format holds. A format / quarantine decision for the
  gc_port23 owner. The 34 Flycast jobs (33 census rooms + KOS) are queued behind /root/probe/lane-rr.lock, 2 slots.
- **Routes (item 5):** island5/routes.txt: chapter 5-1..5-4 leg lists (start save -> end save, doors / event jumps).
  Per-room navplan goto paths still to generate.
