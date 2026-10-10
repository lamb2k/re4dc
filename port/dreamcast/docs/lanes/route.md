# Lane route (coordinator): make r106 playable

Rules: port/dreamcast/docs/D367_WORKSTREAMS.md. Branch lane/route, tree /root/work/lanes/route, evidence /root/probe/lanes/route.

## Goal
The play build continues past r103: r103 -> r106 (chapter 1-1 end), following R4_FIRST_STAGE_GAP_AUDIT.md "Full stage-1 route".

## State and next step
2026-10-01 (evening): r104, the chapter 1-2 arrival, is landed (750aa52f, QTE icons f16f2aec). The QTE pass leads to
gameplay, and the miss leads to Continue.

Next, in stage_route.py order:
1. Done: chapter 1-1 -> 1-2 (r106 -> save -> r104), see below.
2. r107: in game (2026-10-02, below); the r104 -> r107 door walk next.
3. r105.

The history of the r106 bring-up is below.

## Progress 2026-10-01

- **em29 (bats) and em2e (crawlers) are in the image** (ebde74a5). Changes:
  - `new (em) cEmXX;` off the GC (value-init zeroed the subArc);
  - em29's slot scan uses `EmMgr.workAt` (sparse slots);
  - wired by `assets.sh discover r106 --wire` (MODULES, MODULE(27, em29), MODULE(38, em2e), the ENEMY_DEMAND
    audit list).

  The play recipe + DBG_WARP=1 builds (out-r1). It has the same 4 UNRESOLVED stubs as r21k pw8w. The image is
  +16,192 B (text +15,872, data +160, bss +160), so heap 4 is ~16 KB smaller in every room.
- **Room container.** The GC debug disc's St1/r106.das (3,880,960 B, sha 8cc9473e..) is the same source as the
  mirrors (r103.das byte-identical to frontier iso-src). `le_mirror.py <src> <dst> --native-rooms` converts it
  (62 report entries, none incomplete): r106.dar 8,791,072 B, r106.arc 4,910,112 B. That is too big to load:
  r103's uncompacted 4.8 MB .dar failed until W8b compacted it to 1.45 MB.
  Next:
  - a compact-room contract for r106 in prepare_native_ui.py ROOM_CONTRACTS;
  - release the GC scenery BINs the PS2 world replaces (room_smd.py release);
  - measure the loaded size.

  Output (rebuildable, private): /root/probe/lanes/route/mirror-r106. Source: /root/probe/lanes/route/iso-src.
- **Event r106s00.** The PS2 movie archive (BIO4MOV.AFS) has r106s00.sfd + .evd, and a movie for all 46 stage-1
  events. The route-movie path (ROUTE_MOVIES, tools/convert_route_movies.py) can present it, skipping the
  4,268,192 B evd. Needs: add r106s00 to the converter's names, a call site in src/st1/r106.cpp (as r100/r101),
  and staging.
- **Build note.** `make` breaks on the store path's space ("Game Dev"). Pass ASSETS=/root/probe/lanes/play-actor-bundle
  (a symlink to re4-assets-private/play-actor-bundle-20260928).

## Progress 2026-10-01 (room size)

- **r106 room container fits like r103's.** The resident archive (heap 4) goes from 4,910,112 to 1,611,200 B (r103 1,455,456;
  r100 1,918,528). The container .dar is 5,492,160 B. Recipe (private outputs, rebuildable, under /root/probe/lanes/route):
  ```
  echo st1/r106.arc > r106-tex.manifest
  python3 tools/prepare_native_ui.py iso-src r106-tex.manifest tex-r106          # 127 native images
  python3 tools/prepare_native_ui.py --compact-room iso-src/st1/r106.das --compact-room-mips     --textures tex-r106 --output w-r106c                                          # 4,910,112 -> 3,879,136, 117 identities
  python3 tools/convert_room_bins.py pkg-r106/MAINSCENARIO.re4mesh --owner 0xff --smd iso-src/st1/r106.das     --lod --lod-min-gain 0.4 --lod-max-levels 4 --lod-eps 24,48,96,192,384 --lod-share --class-auto --color prelit
  python3 tools/room_smd.py release w-r106c/r106.{dar,arc} pkg-r106/MAINSCENARIO.re4mesh.json rel-r106/st1/r106.{dar,arc}
  ```
  All 87 scenery BINs released; check passes (other slots unchanged). sha256: package 67c20da2.., r106.dar c55fdfc0..,
  r106.arc dd005831...
  - `prepare_native_ui.py`: ROOM_CONTRACTS r106 = 55 slots, SMD#4, EFF#7/#42, ITM#9, model TPLs #47/#49/#51 (r101's layout).
  - `convert_room_bins.py --color prelit` (new CLI option; default `oct` unchanged): r106 has more than 16 CLR0 values,
    which the oct palette can't hold. Under PS2_WORLD_ROOMS=2 this package is the release identity and the
    open-failure fallback only (the PS2 world opens first and the scenery package is skipped).
- **Runtime:** one shared room list, `re4dc_ps2_world_room()` (native_static.cpp), now r100/r101/r103/r106, used by
  the =2 preload and native_ps2_world.cpp's covers(). Default image unchanged (PS2_WORLD_ROOMS defaults 0). out-r2
  builds with the play recipe + DBG_WARP=1, the same UNRESOLVED list as out-r1.
- **Lighting:** the r106 PS2 world package comes from the ps2rooms lane, relaunched 2026-10-01 on the user's PS2-pattern
  lighting decision (prelit, 0 runtime ms, enhanced for DC). Until it delivers, staging uses its authored package
  (ps2rooms-20260930/out/r106).
- **r106s00 route movie** (chapter 1-1's end): r106.cpp presents it through RouteMoviePlay(0x10600) like r101's events (ROUTE_CUTSCENES.md row); r106.o gets the route-movies header; convert_route_movies.py names it. Converted into the shared movie folder (/root/probe/d367-agents/cutscenes/movies-288x192-full/r106s00, index merged, not replaced): 288x192, 1,738 frames, 58.0 s, seq 12,184,020 B (sha 1e5e3b02..). out-r4 builds (play recipe + DBG_WARP=1), same UNRESOLVED list.
- **r106 reached in game through the r103 door (2026-10-01).** Image: route-build.sh r6 (play recipe + PACE_MODE=fast
  DBG_WARP=1 PC_SAMPLER=1 ARENA_FIT_KOS_BYTES=180224; ELF 8832fa42), fixture tour/route-rel-r103-r106-walk-pw.json (preset
  r103-r106-door --door; r106 PS2 world = the ps2rooms authored package), run scenarios/route-r106w1 (240 s, HALT 0, MISSING 0):
  - Door taken at vbl 1602, r106 entered vbl 1649; room identities ok (117, archive 1,611,200 B); PS2 world opens
    (1,038,208 B, heap 4 5,445,600 -> 4,407,296 free); scenery package skipped; route movie 10600 owns the event
    (3,932,160 B em12 reservation released). Ran to frame 3,360 (deadline) with no HALT.
  - Open: VRAM free at entry 69,760 B (r103's room set still resident: no r106 VQ overlay yet); 156 of 212 source-OT
    model parts rejected (to check against r103); the closet event (area 2) not walked yet.
  - The direct warp start (preset r106-entry, scenarios route-r106e1/e2/e3) does NOT work: every disc open fails after
    the first r106.dar read (KOS heap and the disc layout are fine: a KOS-style Joliet walk finds every file; +32 KB
    KOS heap changes nothing). The door route does not hit it, so the warp-only path is parked; use the door walk.
  - Fixture maker fix: door views pass warp.py options (route-r103-r106-walk = r103-r106-door --door); the first
    r103-r106-door fixture had no door actions (single-use name kept).
- Next: r106 PS2 world from ps2rooms' `--color-light ps2` bake (TEV x4), r106 VQ overlay, the closet event + r106s00
  movie run, heap-4 / hw ms measurement.

## Progress 2026-10-01 (r106 sound, landing)

- **Landed** lane/route on dreamcast-port as f66e8c5b (gate: candidate 016ece9a vs control f367d83a, play recipe,
  kite fight 180 s identical progress, HALT 0 / MISSING 0 both; door walk HALT 0).
- **r106 sound.** r106's banks were GC (not AICA): the room and foot blocks "did not fit" and played nothing.
  `aica_banks.py --fixed-route title,r100,r101,r103` (new): the existing route is planned alone and frozen (caps and
  layout, so every r100-r103 bank stays byte-identical; checked: headers of em12/em26/core/pl00 equal the disc's), and
  r106 only lowers its own banks to fit the frozen arena (1,004,192 B): ROOM 11,025 Hz, FOOT / em29 / em2a / em2e
  8,000 Hz; em12 stays 11,025 (planning r106 into the route instead would have dropped r100's em12 to 8,000).
  `aica_banks.py build --mirror <mirror-w4q + w8b r103 + rel-r106> --out aica-r106 --route title,r100,r101,r103,r106
  --fixed-route title,r100,r101,r103`; staged: st1/r106.dar, em/em29.drs, em/em2e.drs (fixtures *-snd).
  Door walk route-r106w2 (image r8 22708c23): ROOM / FOOT / em12 / em29 / em2e prebuilt, em2a runtime conversion, HALT 0.
- **Direct start still fails** with the AICA banks (route-r106e5), so sound was not the cause. Open.
- **Direct start: cause and fix (IO_SERIAL).** dvd.cpp now logs errno: every open after the first r106.dar read
  failed with ENOENT (route-r106e6, image r9 7012393a): KOS's directory lookup itself fails. The room archive is read
  into a 32-byte aligned heap-4 buffer, so KOS iso9660 streams it (cdrom_stream_start over the rest of the file),
  while the main thread opens the HUD/player texture packages (room/texture_package.cpp, plain fs_open). Through the
  door those textures are already resident, so nothing opens concurrently. The codebase already avoids KOS
  streaming against concurrent opens elsewhere (room_storage.cpp's unaligned bounce, the AICA stream reader).
  IO_SERIAL=1 (new, default 0; on in build-r21.sh): texture-package opens wait (thd_pass) while DVDReadAsyncPrio has a
  file open on another thread. Direct start route-r106e8 (image r10 8b35b37a, IO_SERIAL=1): room identities ok, PS2
  world open, movie owns the event, placed at vbl 981, frames to 1200+ (the runner's capacity guard ended it), one
  texture `open failed` left (b8420096: a texture not on the disc, also in the door walk). Gate pending (kite fight vs
  control c8): PASSED route-kiter11 (image r11 006016f9, IO_SERIAL on in the recipe) == route-kitec8: frame 2100 at
  the same position, vbl 10399 both, spills 4 / upload FAILED 12 / HALT 0 both. Landed with this commit.

## Progress 2026-10-01 (chapter 1-1 end, r106 textures)

- **End of chapter 1-1 draws.** Warp preset r106-closet (AEV area 2, trigger 0x88) runs the r106s00 event. The movie
  plays 1738/1738 frames, then the "End of Chapter 1-1" results screen draws (Leon picture, hit ratio / kills / deaths,
  Next Chapter 1-2) with the Save? prompt (route-r106c4, image r11, fixture route-rel-r106-closet-snd3, frame at 94 s).
- **Chapter pictures.** SS/eng/chap01.dat's 14 pictures were not on the disc (`open failed` x14 at the screen). They are
  built from the GC original in chap-gc (chap-src/ss/eng holds chap01-07 for the later chapters):
  ```
  echo ss/eng/chap01.dat > chap-tex.manifest
  python3 tools/prepare_native_ui.py chap-gc chap-tex.manifest tex-chap01                 # 25 images, 0 errors
  python3 tools/vq_native_ui.py --textures tex-chap01 --log chap01-loads.log --output tex-chap01-vq \
      --model-min-bytes 8192 --pvrtex /root/work/kos-re4dc-d336/utils/pvrtex/pvrtex       # 4 images VQ, 2,359,296 -> 303,104 B
  ```
- **em2a picture.** r106 loads 8fb0fccf-d75e4a3f (128x128 CMPR; the "b8420096" above was a misread of this load), which
  r100-r103 never did. It lives in em/em2a.drs, found with the new tools/d367/route/find-texture-source.py.
  - Build: `prepare_native_ui.py /root/re4data em2a-tex.manifest tex-em2a` (manifest em/em2a.drs; 2 images).
  - route-r106c5 (fixture *-closet-snd4): open failed 0, upload FAILED 0, HALT 0. Door walk route-r106w4 (fixture
    r103-r106-walk-snd4): r106 entered at vbl 1444, open failed 0, upload FAILED 0, HALT 0.
- **Trap: the kite base disc's own pad script.** The base disc carries dc/padscript.txt (58 entries, source clock).
  - The fixture maker popped it from `replace`, which leaves the disc's copy in place. Every route run before *-snd3
    also played the kite script; its B+Up turned the save screen into "Exit?" in route-r106c3.
  - New views put it in `remove`.
  - The landed IO_SERIAL gate is unaffected: candidate and control both ran it.
- **Fixture maker.** Texture sets (TEXSETS chap01, em2a) are named in a view's rooms list. Views *-snd4 (closet, entry,
  door walk) are the r106 play set.

## Progress 2026-10-01 (r104: chapter 1-2 arrival)

- **Room package.** r104 (ps2rooms --color-light ps2 bake) plus em13, the chapter 1-2 Ganados (not on the kite disc):
  - em13 joins the EM10_SHARED group (em10g = em12+em15+em13). Built alone, its own em10.cpp cost heap 4 266 KB.
  - Its bank is prebuilt; its EM0 equals em12's. aica_banks.py now writes a bank once per key and walks `room_paths`.
  - room_smd compaction needs `header_grow=32`: r104's 46-slot header ended flush with the payload ("layout differs").
- **Leon without the jacket (pl08).** title.cpp keeps costume 0 (pl00) only in r120/r100/r101/r103/r106. Every
  later room loads em/pl08.drs.
  - The GC file is 1,057,792 B, larger than the 846,656 B player area (route-r104a: read REJECTED).
  - prepare_enemy_motions.py textures-only cuts it to 869,728 B. The build needs `PLAYER_RESIDENT_BYTES=869728`.
  - Its PL bank equals pl00's, so it is resident in aica_banks.py. As a room bank it overflowed the arena.
  - Kite gate r15 vs c9 (step1 fdc151ea):
    - identical position at frame 2100;
    - spills 4, upload FAILED 12, HALT 0 on both;
    - heap 4 free −23,072 B.
- **Module alias pass for every module.** gen_modules.py's 2.95-mangled `asm("...")` alias block ran only for per-link
  modules. em13 then linked `setPtr__7cEmWrapsSci` to a silent stub and halted. With the pass, missing stubs went from
  4 to 1 (memset only).
- **PS2 world.** r104 is added to `re4dc_ps2_world_room` (native_static.cpp). Without it the world draws grey
  (route-r104b2: HALT 0, missing 0, 29.9 fps, Leon pl08 draws, no world).
- **Route movies and the QTE (the PS2 pattern).** r104s00 (4856 pictures) ends on a QTE at its cancel cut 0x1E.
  - The PS2 evd cameras put cut k at picture Σ_{j<k}(maxFrame_j+1): cut 0x1E starts at picture 4795 and lasts 60
    frames. r104s00c is that cut alone, played after a skip.
  - `RouteMoviePlayQte` (route_movie_bridge.cpp):
    1. Plays the movie up to picture 4795 (`re4dc_movie_play_until`).
    2. Runs the cut as game frames, Event func mode 1 at NowCut 0x1E. The ActBtn prompt draws over the stepped movie
       picture (`re4dc_movie_step`, `re4dc_ui_movie_background`).
    3. A pass (Room_flg[0] bit 31, `r104_succeedAction`) plays s01. A miss plays s02, then DiedemoExec.
  - s10 and s20 play as plain route movies. No evd is read while the movies own the events, so the ARAM pre-reads are
    skipped.
  - ActBtn flags 0x42 fail a press of both pairs. Test pad scripts press one pair, A+B (0300) or L+R (0060); r104
    picks the pair by Rnd. The bridge reports fixture state `qte=1` for the press to wait on.
- **Result, image r17 (fixtures route-rel-r104-qte-{ab,lr}-pw, preset r104-arrival, 300 s):**
  - route-r104-qte-ab: s00 hands off at picture 4795. The QTE passes 9 frames into the cut (Room_flg[0] 80000000).
    s01 plays 565/565, then gameplay resumes in r104 with the PS2 world drawn and Leon in pl08 (shot t0240).
  - route-r104-qte-lr: r104 picked A+B, so the L+R press misses. The cut runs 60/60 frames while the movie plays to
    4856/4856. s02 plays 25/25, then the Continue Yes/No screen (shot t0240).
  - Both runs: HALT 0, missing 0, s00 cadence dropped 0 / late 0.
- **The prompt over the movie.** route-run.sh takes `PERIOD=<s>` for the screenshot period. The test knob
  `ROUTE_QTE_FRAMES=600` holds the cut for 20 s so a timed shot can catch it. Without the knob, the cut lasts 2 s and
  three 5 s-period runs all missed it.
  - route-r104-qte-hold1 (r18): "DODGE" drew without the button icons. The cut set Disp_flg = all bits but 0x1000.
    Disp_flg bits hide when set: IdSys draws no ID units under 0x2000 and skips OT type 0x13 (the cockpit's action
    icons) under 0x10000.
  - The fix uses the source's event-UI mask (sce_com.cpp): all bits but 0x1000 | 0x2000 | 0x10000.
  - route-r104-qte-hold2 (r19): A+B and DODGE draw over the s00 picture, as on the GC, with no HUD.
- **Landed.**
  - 750aa52f (lane 99a82a6c). Landing image l18, from a clean objdir:
    - kitel18 vs kitec9: identical position at frame 2100 (610,0,-4346); spills 4, upload FAILED 12, HALT 0;
      heap 4 free −23,072 B (pl08).
    - route-r104-qte-ab-l18: the QTE passes, s01 plays 565/565.
  - f16f2aec (lane f97e5431, the icons). Landing image l20: route-r104-qte-ab-l20 passes 3 frames into the cut; s01 plays 565/565; HALT 0.

## Progress 2026-10-01 (night: chapter 1-1 -> 1-2 on the landed image)

- **The play path r106 -> r104 works** on the landed image l20: route-r106-r104-ch2, fixture
  route-rel-r106-r104-chapter2-pw, preset r106-closet, every r106 and r104 set staged. HALT 0, missing 0. The sequence:
  1. The closet event; r106s00 plays 1738/1738.
  2. The chapter 1-1 results, then Save? Yes.
  3. The save screen: slot 01, "Save? Yes" (pad script Left + A), then the VMU write (card-vmu syswrite rc=0).
  4. Chapter 1-2: DOORDEMO, then r104 is entered (pl08 read, the r104 PS2 world opens: 677,216 B).
  5. r104s00 plays to the QTE handoff.
  6. The script's lone A is not the A+B pair, so the QTE misses: s02, then the Continue screen. That is the expected
     miss branch.
- **Pad script (`pad-chapter-save`).** The first try (route-r106-r104-ch1, A only) looped in the save screen. A on a slot
  opens "Save? Yes/No" with No selected (card state 2/6), and A there returns to the list (2/1). The script now gates
  its presses on card=2/1 and card=2/6.
- **Observations, not blockers:**
  - At the chapter end, r104's PS2 world is opened while still in r106, with heap 4 down: `PS2MESH open failed ...
    heap=-1`. The room's own entry retires the attempt and opens it.
  - VRAM free at the r104 entry is 223,488 B (drift −2.29 MB): the native UI cache holds the results and save screen
    pictures. It evicts on demand.
  - The s00 movie dropped 23 pictures (max gap 42 fields) on this path; a warp start drops 0.

## Progress 2026-10-02 (r107: the path after r104)

`assets.sh discover r107` lists:
- em12, em27 (the lake fish) and em2a, from the ESL;
- no evd events, so no movies;
- the room container, not prepared.

- **Room container.**
  - le_mirror rejected `st1/r107.arc#15`, AEV scenario entry type 14. Type 14 is "stoop" (sce_at.cpp
    `sceAtFunc_stoop`: PlSetCrouch) and reads no payload. It is now qualified only with an all-zero payload, like
    types 0/2/6/7/20.
  - prepare_native_ui gets the r107 contract: 27 slots, r103's owner layout (SMD#4, EFF#7, ITM#9), no model slots.
  - Resident archive: 4,398,848 → 1,323,968 B (r103 1,455,456). 207 scenery BINs released; container 5,370,944 B.
    Recipe as r104's: iso-src-r107, mirror-r107, tex-r107 (166 images), w-r107c, pkg-r107, rel-r107.
- **em27.** `assets.sh discover r107 --fix --wire` fixed the value-init and slot-math lint errors and wired
  Makefile MODULES, the ENEMY_DEMAND audit list and modules.cpp MODULE(16, em27). Pictures: tex-em27 (manifest
  em/em27.drs).
- **Cross-REL import (trap).** r107.cpp (st1_1) calls `cEm27::setWaterHeight` on its fish.
  - A module's partial link keeps only its entry points and state global, so the call bound to the image's
    missing-symbol stub: route-r107a (image r21) halted with `RE4DC MISSING: __ZN5cEm2714setWaterHeightEf`.
  - On the GC, OSLink binds the import by module id. gen_modules.py now has `CROSS_REL_EXPORTS = {"em27": [...]}`.
  - An nm scan of every module object finds this as the only cross-REL import in the image (scratchpad
    k143.py: module U symbols defined in another module).
- **Sound.** aica-r107 plans r106 and r107 together against the frozen title..r103 layout, because em2a's bank is one
  disc file shared by both rooms. Every shared bank comes out identical to aica-r106 (em12, em2a, em29, em2e, r106.dar,
  r100-r103, core, pl00). r107 adds st1/r107.dar and em/em27.drs.
- **Runtime.** r107 is in `re4dc_ps2_world_room`, and warp preset `r107-entry` puts Leon at r104 door 0's destination:
  (29683, −13, −28512), angle 2.286 (stage_route.py).
- **Missing material pair.** route-r107a/b log `pair missing 06a93b5a-bea302c6 color=2d1f80f9 mask=10592447`, built by
  `pairs_from_log.py ... --file st1/r107.das ...` into pairs-r107 (fixture texture set `pairs-r107`).
- **route-r107b** (image r22, fixture r107-entry-a): HALT 0, missing 0.
  - Room identities ok (85); the PS2 world opens (945,728 B).
  - The world, Leon (pl08) and the HUD draw (shot t0091).
  - PACE (Flycast proxy): about 15 drawn fps at speed ~97-100, draw_us 43-45 ms. r107 is heavier than r104 (29.9);
    not measured on the hw model yet.
- **route-r107c** (r22, fixture r107-entry-b with pairs-r107): open failed 0, upload FAILED 0, HALT 0.
- **Kite gate r22 vs c9 / l18:** identical position at frame 2100 (610,0,-4346); spills 4, upload FAILED 12, HALT 0;
  heap 4 free 8,178,432 (l18 8,194,816: −16,384 B, em27 joins the image).

## Progress 2026-10-02 (r104 -> r107 walk, r105: chapter 1-2's end)

- **r104 -> r107 door walk.**
  - route-r104-r107-w1 (preset r104-r107-door): the emblem gate says "It won't open". r104.cpp keeps door 0x97 disabled
    until `door_unlock[0]` bit 0x00400000 is set (r104_checkDoor107KeyUse, the combined emblem 0xA6 used).
  - Preset r104-r107-door-unlocked adds `unlock 0 0x00400000`. route-r104-r107-w2 (r22): door demo, r107 entered, the
    PS2 world opens, HALT 0.
- **r105 room.** Same recipe as r107: r107's 27-slot contract.
  - Resident archive 1,399,936 B, 110 scenery BINs released.
  - aica-r105 plans r106 + r107 + r105 against the frozen layout; every shared bank equals aica-r107's.
  - r105 is in `re4dc_ps2_world_room`. Warp preset `r105-entry` is r107 door 1's destination (72778, −2238, −37465,
    −1.226).
  - pairs-r105 holds 8b7f9449 and 6378dfee (route-r105a).
  - route-r105a (r23): HALT 0, about 26 drawn fps.
- **r105 route movies.** r105s00 (1667 pictures, chapter 1-2's end) and r105s10 (1107, Ashley's rescue) were converted
  with `convert_route_movies.py r105s00 r105s10`.
  - r105.cpp presents both through RouteMoviePlay (0x10500 / 0x10510), with Evt_R105S00/S10_Func as the begin/end
    funcs, and skips the ARAM pre-reads.
  - s00's evd flag 0x10 (StatusFlag 0x400, the fade 30 frames before the end) becomes `FadeSetW(2, 0x2D)` after the
    movie, as r106.
  - s10's lasting side effect, window 5 SetBreakModel at cut 0x14 frame 2, is a picture tick at 891. The cut->picture
    sums equal both movies' picture counts (1107, 1667).
  - r105.o gets the route-movies header (Makefile ROUTE_MOVIE_GAME).
- **Reaching r105's event (test rig).**
  - R105Main arms area 8 only once the key item is picked up (`item_flags[0]` bit 0x20000000). Warp gains a test-only
    `items <idx> <mask>` line (DBG_WARP builds).
  - The warp `--dump` now prints each area's check flag, angle and range, and an xz4 area's box.
  - Area 8: check 01 (front point), box x 7225..7935, z 4840..6137, floor 6020 + 1484.
  - At the box centre Leon is pushed east out of the box (x ~7942) and nothing fires (r105e1/e3/e5). Preset
    r105-event-west (7400, 6020, 5500, angle 0) fires it: route-r105e6 (r26) plays r105s00 1667/1667, then the chapter
    1-2 "Save?" prompt.
  - The chapter 1-2 results pictures were missing (15 loads). tex-chap02 comes from the GC disc's SS/eng/chap02.dat
    (chap-src's copy has no handler), 25 images; 3 are shared with chap01.
- **Chapter 1-2 end -> save -> chapter 1-3 (route-r105e7, r26, view r105-event-f).** r105s00 1667/1667, the chapter
  1-2 results pictures (chap01 + chap02 staged; open failed 0), "Save?" -> Yes -> slot, `card-vmu: op=syswrite rc=0`,
  then chapter 1-3 opens with r105s10 1107/1107 (Ashley's rescue, cadence 29.97, dropped 0) and gameplay in r105.
  HALT 0, MISSING 0. Gameplay after s10 runs ~11 drawn fps / 74% game speed (Flycast, draw ~75 ms) with 3
  `native UI: upload FAILED vram=0` (VRAM free 115 KB during s10): the next r105 item, with r107's ~15 fps.
- Not yet proven: the emblem halves (r104 -> r107) and r105's key item picked up in play; the warp rig sets
  `door_unlock` / `item_flags`. A user play disc is the check (memory: user play over scripts).

## Progress 2026-10-09/10 (r10b: chapter 1-3's end, behind ROUTE_CH13)

r10b (the lake: Leon's boat pl0f, Del Lago em2f, the em27 fish) plays to `SceSetChapterEnd(CHAPTER_1_3, 6)`; door 6
to r11b shows "Coming Soon". All of it is behind ROUTE_CH13=1 (default 0: the image is byte-identical apart from
__DATE__/__TIME__). Lane tree /root/probe/lanes-20261009/r10b, evidence D:/Flycast-Evidence/re4-dreamcast/r10b-20261009.

- **Route movies.** r10bs00/s10/s20/s20c/s21/s22 through RouteMoviePlay; the s20 QTE through RouteMoviePlayQte
  (ExecActBtn; routeEndEvent). Full route (fixture f6, warp aid): boarding, s10, the QTE passes with 17 presses, s22,
  the chapter 1-3 results and "Save?", then "Coming Soon". HALT 0, MISSING 0, no allocation failure.
- **pl0f / em2f are room overlays (ROUTE_OVL=1, default with ROUTE_CH13=1).** gen_modules.py `<mod>:ovl` (the
  SUBSCREEN_OVL mechanism); tools/link.sh now takes a list of overlay sections, links overlay i at 0x8E000000 +
  i * 4 MiB, proves each one separately (a second link with only that overlay 1 MiB higher: the rest of the image,
  other overlays included, must not change) and writes `<mod>.ovl` (sscrn.ovl, pl0f.ovl 43,060 B / 309 relocations,
  em2f.ovl 16,472 B / 70). platform/modules.cpp: the table entry is empty until the game links the module; the bind
  reads /cd/dc/<mod>.ovl into heap 4 (checks size + FNV hashes, relocates, flushes the caches); the unlink and
  gameRoomMemInit (before heap 4 is rebuilt) fill the code with `trapa #0xFF`, free it and empty the entry. A link
  with no loadable overlay stops in re4dc_missing (never a stub); missing.txt is empty. Staging: route-build.sh copies
  the .ovl files to the program dir, build.sh / stage.sh copy every *.ovl; a harness fixture adds
  `dc/pl0f.ovl` + `dc/em2f.ovl` (lane tool addovl.py). Log: `route overlay: pl0f load 1 41760 B (309 relocs) ...`.
- **Image and heap 4.** Trace arm r10bT2 vs the 19f62e62 control tiB: .text 2,574,884 vs 2,576,836, total 4,037,952
  vs 4,039,744; `_end` 8c3ebafc vs 8c3eb8bc (same 4 KiB page, so the arena is unchanged). H2: the r100 s30 movie
  340/340 with heap_before 57,504 = control 57,504; New Game heaps identical (7,941,952 / 1,010,528).
- **espgen45 (the lake water): RE4DC_WATER45_LEAN + RE4DC_WATER45_GRID_SKIP (Makefile, ROUTE_CH13 block).** GX is a stub
  on the Dreamcast, so the generator never drew anything; the PS2 world draws the lake. Logic reads only the plane
  (GetWaterHeight / GetWaterCrossPos use mat / inv / nx / ny). LEAN drops the normal / bump / display-list buffers;
  GRID_SKIP drops the height field too (hA / hB / pos, ~571 KB) and its per-frame update: Move00 keeps the plane
  header (Status_flg[0] 0x200, mat, inv) and returns. The grid update takes no RNG; the init's fRand1_1 draws (the
  shared RNG) are kept, same count and order. AddWaterPower skips a grid-less 0x45 water. Proof: STRICT pair on r10b,
  grid on (r10bTg) vs off (r10bTs), fixture f6 through boarding, s10, the QTE and the chapter end:
  decision_cmp all MUST fields identical except `st` for 6 ticks at the last, ungated post-QTE press (entry 45),
  which lands on a different game tick because the grid-on arm spends longer in the s00 movie (heap loan): input skew,
  not logic (rng, player, enemies, effects identical throughout). heap 4 free at r10b frame 1400: 1,051,520 B.
- **em27 fish NaN (RE4DC_EM27_SLOT_FIX, ROUTE_CH13 block).** em27ObaHitCk walked the enemy slots with raw slot math
  (`pArray + size * i`); with the sparse enemy backing an unbacked slot reads as 0xFF filler, `be_flag` 0xFFFFFFFF
  passes the alive test and the filler position (NaN) is pushed into the fish (`OBA e=6 ... epos=-nan,0,-nan`).
  The fix walks `EmMgr.workAt(i)` and skips null slots (as em27JumpCk and em21 already do). After: 11,820 fish
  position samples on the route, 0 NaN. hw dock 127.9 -> 61.3 ms drawn. The default image's r107 fish use the same
  scan: whether to enable the fix outside ROUTE_CH13 is a coordinator decision (it changes r107 logic).
- **Disc.** Removed (never read by the play route, each with a code reason, disc-audit.json): em10/11/1f/20/22/25/2b/2c/2d
  .drs (modules not linked), st1/r100/r101/r103/r120 .das (native rooms read .dar), st1/r120.dar/.arc (New Game skips
  r120: nativeSkipOpeningRoom; New Game+ needs game_cnt != 0, incremented only in r333 (stage 3), so it is
  unreachable on this disc), le_mirror_report.json. pl0f.drs is rel-stripped (le_mirror --compact-static-rel).
  Next disc-space lever: bio4bgm / bio4evt.sbb (332 MB, the old sound reads; stub them later), no change now.
- **hw ms first (hwproject SH-4 model, cost arm, drawn / skipped ms per frame), then Flycast (PACE draw ms over
  300-frame windows, p50 / p99 / max, vsync off).** Before = r10bC (lean + PRIM_CAP_R10B, no fish fix, grid on); after
  = r10bO (the landed state: fish fix, grid skip, overlays). Evidence hwmodel-r10b-r10bC-* / hwmodel-r10b-r10bO-*.

  | view (window) | hw before | hw after | Flycast before | Flycast after |
  |---|---|---|---|---|
  | dock, quiet (500:579) | 127.9 / 94.9 | 61.3 / 14.7 | 94.4 / 94.4 / 94.4 (5.8 fps) | 32.9 / 33.3 / 33.3 (29.9 fps) |
  | lake (800:879) | 63.3 / 21.9 | 60.2 / 14.4 | 101.2 / 101.4 / 101.4 (5.6 fps) | 39.9 / 47.1 / 47.1 (22.5 fps) |
  | boss pass (4100:4179) | 42.6 / 19.6 | 39.5 / 16.5 | 29.2 / 43.0 / 43.0 | 26.7 / 68.8 / 68.8 |

  Boss window proof: fixture fb (f6 without the kill; boarding presses are state-gated, so the trace and cost arms
  reach the same ticks); the trace arm's LP log puts em2f surfaced (y -245) 1.9 m from Leon at frame 4139 (Leon in
  the water after being thrown off; the camera then faces the water: no screenshot shows the boss). The earlier
  "boss" window (700:779, 132.2 -> 60.8 ms) was a warp with Leon standing on the water, not a boss view.
  Headroom at r10b (route f6, frame 1400): heap 4 free 1,051,520 B (the two overlays hold 59,680 B), VRAM free
  203,520 B, AICA largest free 1,004,192 B.

## Progress 2026-10-10 (r11b: chapter 2-1's start, behind ROUTE_CH21)

r11b (the lake shore: Leon lands from the boat, the wolf (em22) ambush) plays from the r10b door 6 transition that
follows the chapter 1-3 end save. Its three exits to rooms not on the disc (r11a, r10c, r10d) show "Coming Soon".
Everything is behind ROUTE_CH21=1 (needs ROUTE_OVL=1, so ROUTE_CH13=1; default 0: byte-identical apart from
__DATE__/__TIME__, both the play and the default recipe, overlays identical). Lane tree
/root/probe/lanes-20261010/r11b, evidence D:/Flycast-Evidence/re4-dreamcast/r11b-20261010.

- **em22 is a room overlay** (MODULES `em22:ovl`, overlay slot 3 at 0x8E000000 + 2 * 4 MiB; platform/modules.cpp
  g_route_ovl gains em22 under RE4DC_ROUTE_CH21 through ROUTE_OVL_SLOT / ROUTE_OVL_ID). em22.ovl 27,236 B;
  log `route overlay: em22 load 1 26496 B (169 relocs)` when the ambush spawns the wolves. em22.cpp lint fixes
  (off-GC only): `new (em) cEm22;` (value-init zeroes subArc), em22EmWork through EmMgr.workAt, em22DoorOpenCk
  skips null doors (the sparse enemy backing; same trap as the em27 fish).
- **r11bs00 through RouteMoviePlay** (id 0x11b00, ROUTE_MOVIE_SND_EVENT, end function Evt_R11BS00_Func; else the
  source evd). 1484/1484 pictures, dropped 0.
- **Trap: chapter 2's enemy list.** etc/emleon01.esl was on the disc raw (big-endian: room read as 0x1b01), never
  read before r11b; EmSetFromList2 returned errEm and the boat's setPos hung in R11bInit. Stage the le_mirror'd
  copy. le_mirror's knob-conditional set now strips `:ovl`.
- **Assets.** prepare_native_ui ROOM_CONTRACTS r11b (33 slots, smd 4, effect 7, item 9, model slot 28); aica_banks
  ROOMS r11b (+ em22 / em27 / pl0f drs) and ROOM_BGM0 r11b [10]: with `--fixed-route title,r100,r101,r103` every bank
  is identical to r10b's except bio4midi.dat, which gains #10 prebuilt (r11b arena 797,312 of 1,004,192). Streams
  0:17 (the battle) and 1:36 (the ambush) added to aica_str.dat. em22.drs rel-stripped
  (le_mirror --compact-static-rel=em22). PS2 world built with --lod-uv-guard 0.002 (760,544 B, 60 textures).
- **Gates.** Knob-off identity PASS (3 bytes: the time stamp). Trace arms r11bT (1f7865d3) vs r11bB (base 67fda5c8):
  `_end` 8c3ebb5c vs 8c3ebafc (same 4 KiB page, +96 B text); missing 0, MISALIGN 0. H2 ACT_CAP=0 STRICT in
  1450..1569, 0..740 and 1218..6990, decision_cmp MUST-IDENTICAL (6991 ticks); s30 340/340, heap_before 57,504 =
  control. Bell STRICT frame + room, MUST-IDENTICAL (5101 ticks). New Game: intros 1971 / 2360, r100, s04.
  Route f6s: r10b to the chapter 1-3 results, save (card-vmu save rc=0, syswrite rc=0), door 6, r11b, s00, the
  radio call; HALT 0, MISSING 0. Doors: r11a / r10c / r10d "Coming Soon". Ambush a1: em22 loads, seven wolves,
  streams 1:36 + 0:17, SHAKE OFF QTE; HALT 0, no allocation failure.
- **Numbers (hw first: hwproject SH-4 model, cost arm r11bC = play flags + ROUTE_CH21=1 PC_SAMPLER=1 DBG_WARP=1,
  drawn / skipped ms; then Flycast PACE draw ms over 300-frame windows, p50 / p99 / max, vsync off, route runs).**

  | view (window) | hw drawn / skipped | Flycast p50 / p99 / max |
  |---|---|---|
  | quiet, the landing (e1 500:579) | 40.0 / 39.4 (1 drawn traced tick; RENDER 22.8) | 34.4 / 34.5 / 34.5 (28.5 fps) |
  | wolves (a1 700:779) | 81.6 / 26.3 (LOGIC 12.5, TRANS 8.3, RENDER 49.6) | 50.5 / 66.8 / 66.8 (13-14 fps) |

  Wolf window proof: the cost run's log has the em22 overlay load and seven em22 (id 22) set 7-15 m from Leon after
  the goto at frame 200; LOGIC is 12.5 ms in the window (0 in the quiet view). Headroom: heap 4 free 2,250,528 B
  after init, 1,106,976 B in the fight (largest 1,105,152; the two overlays hold 70,464 B); VRAM free 122,112 B in the
  fight (texture slots 448 as on r10b, rejects 0, missing 0); AICA largest free 1,004,192 B. Disc +31.5 MB
  (208 files, loose textures; ~42 MB were free on track03).
- **Next: r11a** (exit 1). Script is small (two player water effects, the water hit table; no events); enemies from
  the ESL: em12 (linked, heap 4 worst case 1,105,152 B: measure one run). Needs the room container
  (prepare_native_ui contract exists, 27 slots), the PS2 world, textures, its AICA bank entry (ROOMS r11a exists)
  and then ROUTE_CH21 coverage of its own exits.

## Progress 2026-10-10 (SBB_STUB: the GC stream banks leave the disc)

bgm/bio4bgm.sbb (139,395,072 B) and bgm/bio4evt.sbb (193,495,040 B) are off the play disc with SBB_STUB=1 (default
0: image byte-identical). Lane tree /root/probe/lanes-20261010/sbb, evidence D:/Flycast-Evidence/re4-dreamcast/sbb-20261010.

- **What the DC build did with them.** Only src/game/snd_str0.cpp Snd_str_init opens one (DVDOpen of
  FileTbl[StrFileTbl[blk]], file 1 = bio4bgm, file 0x5F = bio4evt), and src/game/snd.cpp SndStrReq refuses the
  request when that FileTbl entry is -1 (so simply leaving the files off would silence and stall every stream: the
  scenario waits on ready / stopped). Every read of them is snd_str2.cpp's DVDReadAsyncPrio(cb_dvd_read_end), which
  platform/audio_strm.cpp's link wrap skips (completion at the next audio frame, no disc access) in every build.
  Stream lengths, loop points, rates and the .sbb offsets come from SND_SHD / SND_RIT in bgm/bio4str.hed (loaded by
  snd.cpp, still staged); audio_aica.cpp keys aica_str.dat entries by SND_SHD[7] and never opens a .sbb; the end of
  a stream is detected from the emulated voice address (re4dc_strm_advance), not from the file. Nothing read the
  payload; the logic sees only the entry number and DVDFileInfo, which the stub keeps (retail sizes, no open).
  io_probe.cpp (IO_PROBE test builds) still names them; aica_banks.py reads them from the source mirror.
- **Change.** platform/dvd.cpp fileSize(): under RE4DC_SBB_STUB the two paths return the retail size without an
  fs_open; Makefile SBB_STUB ?= 0 sets it on dvd.o only. No new staged file (no header file is needed).
- **Gates (ACT_CAP=0, arms at ab21e8ab: sbbT = play flags + ROUTE_CH21=1 + traces + SBB_STUB=1 on discs without
  the banks; sbbB = the same with SBB_STUB=0 and the banks).** Knob-off identity: sbbQ (play flags, knob off) vs
  sbbO (the same flags from a clean ab21e8ab worktree): objcopy images differ in 2 bytes (the time stamp), the four
  overlays identical, `_end` 8c3e231c both (also with the knob on). missing.txt empty on all five arms; MISALIGN 0
  in every run. H2 (g-h2, 480 s): STRICT 1450..1569, 0..740, 1218..6990 and whole room 0100 (6810 ticks, om too);
  decision_cmp MUST-IDENTICAL (6992 ticks); s30 340/340 both, heap 57504 -> 79200 both; radio call voice 1:141 and
  calls 10003 / 10020 shown 1465 / 571 both. Bell (g-bell, 300 s): STRICT frame 0..5100 and room 0101, MUST-IDENTICAL
  (5101 ticks). r10b (f6s, 600 s): stream 0:4 starts, room 010b STRICT, MUST-IDENTICAL (5482 ticks). r11b ambush
  (a1, 150 s): em22 load, streams 1:36 then 0:17, room 011b STRICT, MUST-IDENTICAL (1951 ticks). Stream event
  sequences (ready / start / stopped / closed, ids, voices, rates) identical to the control in every pair; the aica
  times differ by a few ms (the audio thread is wall-timed). New Game (sbbP play ELF, banks removed, 420 s): intros
  1971 / 2360, s40 1175, streams 1:3 and 1:140 play; HALT 0, MISSING 0, "SND: File Not Found" 0 everywhere.
- **Disc.** Staged payload 1,010,718,720 B -> 677,828,608 B on the same fixture: **332,890,112 B (162,544 sectors)
  freed on track 3**. No hw ms arm: the change only skips two file opens (boot / first stream); no per-frame code.

## Progress 2026-10-10 (r11a: the lake shore path, chapter 2-1, behind ROUTE_CH21)

r11a plays from r11b door 0. Its door 0 (to r119) shows "Coming Soon"; door 1 leads back to r11b. **No game code
changed**: the existing ROUTE_CH21 image already covers it. route_end.cpp counts a room as built when
dc/native/r11a/ps2-world.r4pw is on the disc, r11a is in the PS2 world registry, and em12 is linked. The only repo
change is aica_banks.py: ROOMS r11a gains em/em24.drs and ROOM_BGM0 gains r11a [10]. Lane tree
/root/probe/lanes-20261010/r11a, evidence D:/Flycast-Evidence/re4-dreamcast/r11a-20261010.

- **Room container** (recipe as r106; byte-identical to the world-coverage lane's 10-03 outputs): GC st1/r11a.das
  (sha 631355a9..) -> le_mirror -> tex-r11a (164 images) -> compact w-r11ac (4,489,984 -> 3,243,744, 95 identities)
  -> pkg-r11a (convert_room_bins --color prelit, 1,138,976 B) -> room_smd release. 183 scenery BINs released; resident
  archive 1,422,816 B; container 5,475,136 B (ROOM_CONTRACTS r11a, 27 slots, already present).
- **PS2 world.** ps2_room_r4im.py r11a (ps2rooms inputs, `--color-light ps2 --lod-uv-guard 0.002`): 735,296 B
  re4mesh, 18,376 B r4pw, 37 textures (551,424 B VRAM), 242 placements.
- **Sound.** `aica_banks.py build --route title,r100,r101,r103,r104,r107,r102,r108,r109,r10a,r10b,r11b,r11a
  --fixed-route title,r100,r101,r103 --weapons` over r11b's AICA mirror plus the released r11a.dar. Every other
  output (bio4midi.dat with #10, every .drs and .dar) is byte-identical to aica-r11b. Only st1/r11a.dar is new: ROOM
  171,104 B at 8,000 Hz, FOOT 142,200 at 8,000, em12 601,288 at 11,025, em24 34,040 at 8,000; arena 948,672 of
  1,004,192. em24 is read at room entry, as in r108 / r10a. Without it, route-r11a-x1a logged "blk 9 (34040 bytes)
  does not fit the room arena". r11a needs no stream that is not already in aica_str.dat.
- **Enemies.** The ESL (etc/emleon01.esl, list 1) has 11 em12 entries in r11a, all alive at entry: types 0/1/3/4
  around the huts (21,760..70,090, 93,000..110,050) and at the r119 door (-53,060..-33,470, 67,540..75,950).
  route-r11a-e4a: the `kill 0x12` rig found a live Ganado at (-53004, 7345, 69840). route-r11a-e5a (Leon at the r119
  door cluster, `alert`): two Ganados attack, one with a torch (shot t0036).
- **Gates** (image r11aS = play flags + ROUTE_CH21=1 SBB_STUB=1 DBG_WARP=1 on 3b87488f, ELF 594a3a87; play twin r11aP
  0f5ede82; both .sbb banks left off the staged discs):
  - The ELF sources are those of 3b87488f, so knob-off identity, H2 / bell STRICT and s30 are 3b87488f's own gates.
    missing.txt is empty and MISALIGN is 0 in every run.
  - route-r11a-w2S: r11b warp, walk through door 0, r11a entered, walk to door 0, "door to r119 (not on this disc):
    Coming Soon"; HALT 0, MISSING 0.
  - route-r11a-b1a: r11a door 1 -> r11b entered (#2).
  - route-r11a-f6sS: r10b -> s00/s10/s20 QTE/s22 -> chapter 1-3 save (card-vmu rc=0) -> door 6 -> r11b s00 1484/1484;
    HALT 0.
  - route-r11a-ngS2 (play ELF, padscript-newgame): r120s00 1971/1971, s01 2360/2360, r100, s40 1175/1175; heaps
    7,941,952 / 1,010,528 (= r11b's ngP).
  - No allocation failure in any run.
  - Two problems are r11b's, not r11a's; they are in r11b's own runs too: one `package rejected: open failed` for
    18d0fd82-2c9a9309 (256x256) in r11b before door 0 (also route-r11b-d0a), and `stream sbb=9900000 (1:148) not in
    aica_str.dat` on r11b entry.
- **Numbers.** hw ms come first: the hwproject SH-4 model on cost arm r11aC (play flags + ROUTE_CH21=1 PC_SAMPLER=1
  DBG_WARP=1), drawn / skipped ms per tick, 6 traced ticks each. Then Flycast PACE draw ms over 300-frame windows
  (frame >= 900), p50 / max, vsync off.

  | view (window) | hw drawn / skipped | Flycast p50 / max |
  |---|---|---|
  | quiet, the r11b door (e1 500:579) | 58.8 / 39.0 (LOGIC 27.5, TRANS 5.4, RENDER 17.5) | 36.2 / 36.5 (22.2 fps, speed 100) |
  | Ganados at the r119 door (e5 700:779) | 68.1 / 37.0 (LOGIC 27.3, TRANS 5.3, RENDER 24.1) | 42.1 / 44.4 (15-16.7 fps) |

  LOGIC is high even in the quiet view because of the lake water generator: **Espgen42_Move00 13.3 hw ms +
  PSVECNormalize 4.5** per drawn tick (functions.tsv, q). That is the same height-grid update that
  WATER45_GRID_SKIP removed from r10b's espgen45 (r10b dock 127.9 -> 61.3). The next r11a item is an espgen42
  equivalent, which needs its own logic-reader audit and a STRICT pair. Headroom: heap 4 free 780,640 B quiet
  (largest 779,840), 812,448 in the fight (largest 744,288); VRAM free 318,208 quiet, 264,960 in the fight, 91,904
  when entered from r11b (r11b's set resident; rejects 0, missing 0); AICA arena 948,672 of 1,004,192.
- **Disc.** +11.3 MB over r11b (harness image 1,025,087,488 -> 1,036,402,688 B). Without SBB_STUB this is about 1 MB
  over track 3; with SBB_STUB=1 (3b87488f) about 332 MB stay free.
- **Next: r119** (r11a door 0; then r118 -> r117, the chapter 2-1 end): done, see "r119" below.

## Progress 2026-10-10 (r119: El Gigante, chapter 2-1, behind ROUTE_CH21)

r119 (the village square: El Gigante, the dog, the parasite) plays from r11a door 0 through its four events to the
giant's death; its exits to rooms not on the disc (door 0 r118, door 6 r10e) show "Coming Soon", door 1 returns to
r11a. Everything is behind ROUTE_CH21=1 (default 0: knob-off images byte-identical). Lane tree
/root/probe/lanes-20261010/r119, evidence D:/Flycast-Evidence/re4-dreamcast/r119-20261010.

- **em2b is a room overlay** (MODULES `em2b:ovl`, the fourth route overlay at 0x8E000000 + 3 * 4 MiB; modules.cpp
  g_route_ovl[4], MODULE(30, em2b)). em2b.ovl 66,064 B; log `route overlay: em2b load 1 64864 B (284 relocs)`
  when R119's fight sets the giant. em2b.cpp lint fixes (off-GC only): `new (em) cEm2b;` and the six enemy slot
  scans through EmMgr.workAt with null slots skipped (sparse enemy backing).
- **Events through RouteMoviePlay** (src/st1/r119.cpp; each call falls back to its source event when its movie is
  not on the disc (RE4DC_MOVIE_UNHANDLED); the ARAM pre-reads and the loads into the giant's block are skipped when
  s00's movie is on the disc): s00 0x11900 (entrance, Evt_R119S00_Func begin / end), s10 0x11910
  (the dog, Evt_R119S10_Func), s20 0x11920 (death, Evt_R119S20_Func), s30 0x11930 (the parasite). s30's source
  call is EvtReadExec(.., 0xA0): new flag ROUTE_MOVIE_SCE_TRUE (ROUTE_CH21 builds) starts it with SceEventStart(1)
  (enemies stay out of event mode) and runs EvtReadExec's camera Comeback; 0x20 = ROUTE_MOVIE_KEEP_POSE. Movies
  (convert_route_movies.py, 288x192): s00 1928, s10 446, s20 782, s30 140 pictures; all played to the end.
- **Heap 4 (measured first).** r119 after init: 3,854,656 B free in two cells, the largest 2,770,912 B. em2b's GC
  body is 4,792,224 B (4,689,664 rel-stripped), so it cannot load as is. prepare_enemy_motions.py now takes em2b in
  SMALL (textures) and MOTION_SMALL (motion), with the consumer audit in the tool: every FCV goes to MotionSetCore
  (directly, em2bBlendMotSet, MotSetObj16, the player's grab motions); the one other read is ARC(0xE2)'s header
  (resident). Prepared body 2,258,208 B: textures 1,048,576 B out (29 TPLs to native packages), 89 clips
  (1,417,280 B) to motion leases (dc/mot/*.fcv, no hot set), 29 clips over the 32 KB lease slot (1,269,984 B) stay
  resident. In the fight (route-r119-fb census, frame 900): heap 4 1,096,896 B free in 7 cells, largest 578,656;
  the s10 movie opened at 1,048,032 free and s20 at 641,120; no allocation failure in any run.
- **Assets.** Room container as r11a (GC st1/r119.das sha f04e1f81..; ROOM_CONTRACTS r119 33 slots, model TPL#31
  = the SetTree tree): tex-r119 144 images, compact 4,255,552 -> 3,068,128, pkg 1,048,256 B, release 43 BINs,
  resident archive 1,306,176 B, container 4,307,616 B. PS2 world ps2_room_r4im --color-light ps2 --lod-uv-guard
  0.002: 1,058,272 B re4mesh, 35 textures. em2b textures (41) + r119 (VQ by vq_native_ui from the run logs:
  em2b 4,046,848 -> 557,056 B VRAM, the giant's two 512x512 bodies 524,288 -> 67,584 each); one material pair
  (41387140-38190dc7). AICA: ROOMS r119 (em2b, em21), ROOM_BGM0 r119 [3]; every other bank byte-identical to
  r11a's; r119 arena 612,256 of 1,004,192. aica_str.dat + stream 0:5 (the battle, 3,145,728 B).
- **Warp rig:** `kill <id> <frame> <room> <kind>` registers that weapon kind (test builds only). The giant loses hp
  only on the parasite or to kind 0xD (em2b's rocket launcher case sets hp 0), so the route run kills it with
  `kill 0x2b 2200 0x119 0xd` after `trg 0` (DebugTrg(0): the parasite event). The climb / slash QTE is not
  exercised by the rig.
- **Gates** (arms on d74b8ec8: T = trace flags + ROUTE_CH21=1 SBB_STUB=1, B = the same from a clean d74b8ec8;
  C cost / P play twin; SBB off every disc). Knob-off identity: default recipe and play flags 0 bytes different
  (one earlier play pair differed by 1 byte: dbgslot_bridge's `__TIME__` stamp); overlays identical, `_end` equal.
  CH21 `_end` 8c3ebb7c vs 8c3ebadc (same 4 KiB page: the trace image is page-tight, so r119.cpp has no helper
  function; an earlier version crossed a page and cost s30 8 KB of heap_before). missing.txt empty on every arm;
  MISALIGN 0 in every run. H2 (ACT_CAP=0): STRICT 1450..1569, 0..740, 1218..6992, decision_cmp MUST-IDENTICAL
  (6985 ticks, om info only as before); s30 340/340 heap_before 57,504 both. Bell STRICT frame (5090) + room,
  MUST-IDENTICAL. Evidence route-r119-{h2,bell}{T,B}4; route-r119-{g3,g4,g5,w2,b1,f6s}C2 (05450fc9 base), g3C3 / ngP3 (d74b8ec8). New Game (P): 1971 / 2360, r100, s40 1175. f6s: r10b -> QTE ->
  chapter 1-3 save (rc=0) -> r11b s00 1484/1484. Route g3/g4/g5 (C): r11a door 0 -> r119, s00, the dog s10, the
  parasite s30, the kill, s20, then door 0 "door to r118 (not on this disc): Coming Soon", door 6 r10e, door 1 ->
  r11a. HALT 0, MISSING 0, upload FAILED 0, pair missing 0.
- **Numbers.** hw ms first (hwproject SH-4 model, cost arm r119C, drawn / skipped ms per tick), then Flycast PACE draw
  ms over 300-frame windows (p50 / max of the windows, vsync off).

  | view (window) | hw drawn / skipped | Flycast p50 / max |
  |---|---|---|
  | quiet, the r11a door (q 500:579) | 112.0 / 7.3 (LOGIC 5.4, TRANS 4.0, RENDER 91.7: models(other) 59.3, world 16.8) | 72.1 / 75.0 (12.5 fps) |
  | El Gigante (b 900:979) | 90.6 / 11.7 (LOGIC 7.0, TRANS 5.5, RENDER 65.5: models(other) 32.6, world 10.7) | 62.6 / 69.4 (12.6-13.8 fps) |

  Boss window proof: the same fixture's Flycast run (route-r119-fb) logs the giant at (120668, 2306, 10028) at frame
  980 and Leon at (124231, 2309, 11585) at frame 900 (3.9 m); shot t0124 shows it over Leon. The quiet view's RENDER
  is the source-drawn room models (the huts, roofs, gate and the three SetTree trees): RENDER/models(other) 59 ms is
  the next r119 perf item. Headroom: heap 4 above; VRAM free 93,440..192,256 B in the fight (missing 0); AICA arena
  612,256 of 1,004,192.
- **Next: r118** (r119 door 0; then r117, the chapter 2-1 end).

## Progress 2026-10-10 (WATER42_GRID_SKIP: espgen42 without its height grid, r10a + r11a)

espgen42 (the room lake water) skips its height grid and per-frame update with WATER42_GRID_SKIP=1, the default
inside the ROUTE_CH13 block (the default image, ROUTE_CH13=0, is byte-identical apart from the build stamp). Same
pattern as r10b's WATER45_GRID_SKIP. Lane tree /root/probe/lanes-20261010/fix21, evidence
D:/Flycast-Evidence/re4-dreamcast/fix21-20261010.

- **What logic reads (src/game/Espgen42.cpp).** g_pWater is file-static; nothing outside the file reads
  Espgen42Work (grep: only espgen45.cpp shares the layout). The entry points the game calls (GetWaterHeight,
  GetWaterCrossPos, AddWaterPower; 30 callers: player, weapons, enemies, objects, effects) read only the plane:
  Status_flg[0] 0x200 (set in Move00 before anything else), mat, inv, nx, ny and the 45 unit's flag. AddWaterPower is
  the only writer of the grid (hA / hB) and nothing reads it back except Move00 and the GX draw (TransSub: pos / nrm
  as vertex arrays, bump as an indirect texture, dl as the display list; GX is a stub here and the PS2 world draws the
  lake). RNG: Move00 takes none; SetWaterWork draws fRand1_1 once per grid point ((nx + 1) x (ny + 1), for the initial
  pos.y). The debug branch (Debug_flg + B) writes hB only.
- **Change.** Under RE4DC_WATER42_GRID_SKIP: SetWaterWork keeps the plane (mat / inv / nx / ny / size / rate), leaves
  hA / hB / pos / nrm / bump / dl NULL (no allocation, no display list) and makes the same fRand1_1 calls in the same
  order; Move00 sets Status_flg[0] 0x200, keeps the noise-texture check, then returns; AddWaterPower returns on a
  grid-less 0x42 water; Trans queues no draw. Makefile: `WATER42_GRID_SKIP ?= 1` in the ROUTE_CH13 block
  (Espgen42.o only).
- **Where espgen42 runs.** A scan of every effect sequence record in GC disc 1 (st1/*.das, evd, em drs: le_mirror's
  sequence observer, Kind 1 and Espgen_id 0x42) finds two rooms: r10a (120 x 120 grid, cell 530) and r11a
  (128 x 128, cell 600), both centred at (45151, -9200, 98120). None in r100 / r101 / r103 or any event. (0x45 is in
  r102, r107, r10b-r10e, r112, r11b and two st2 events.) The heap-4 census confirms it: Espgen42.cpp holds
  1,125,984 B in r11a (6 blocks) and 990,368 B in r10a with the grid, nothing without.
- **Gates (arms at d3fe14d8 + this change, play flags + ROUTE_CH21=1 SBB_STUB=1, both .sbb banks off the discs; trace
  arms f21T0 = WATER42_GRID_SKIP=0 vs f21T1 = default, LOGIC_TRACE=1 GAME_DECISION_TRACE=1 PACE_MODE=off).**
  - Knob-off identity: f21C0 (knob 0) vs f21O (the same flags from a clean d3fe14d8 worktree): objcopy images differ in
    2 bytes (the time stamp), all four overlays identical, `_end` 8c3e991c both; the default recipe (ROUTE_CH13=0)
    f21D vs f21DO: 3 time-stamp bytes. Knob on: image -128 B, `_end` 8c3e989c (same 4 KiB page). missing.txt empty on
    every arm; MISALIGN 0 in every run.
  - r11a STRICT (frame and room 011a, decision_cmp MUST-IDENTICAL): e1 quiet 2402 ticks, e5 Ganados at the r119 door
    2186 ticks (info sq only), lk lake view 1944 ticks. r10a STRICT (entry warp, 2925 ticks).
  - H2 (ACT_CAP=0): STRICT 1450..1569, 0..740, 1218..6992; whole room DISCRETE with om only in the call window (476
    ticks from 741, as r21w/x/y); decision_cmp MUST-IDENTICAL (6993 ticks). s30 340/340, heap_before 65,696 >= 57,504
    (control). Bell: STRICT frame 0..5099 and room 0101, MUST-IDENTICAL (5100 ticks).
  - New Game (play ELF f21P): intros 1971 / 2360, r100, s40 1175; HALT 0. r11b ambush (a1): em22 load, streams 1:36 +
    0:17. r11b door 0 -> r11a -> r119 door "Coming Soon" (w2). r10b -> s00 / s10 / the s20 QTE / s22 -> chapter 1-3 save
    (card-vmu rc=0) -> door 6 -> r11b s00 1484/1484 (f6r on the cost arm f21C1: the trace arms run the QTE movie
    slower and miss presses, 10 of 17, as the sbb lane's trace run did). HALT 0, MISSING 0, no allocation failure in
    any run.
  - Look: GX never drew the lake on the Dreamcast, so the image cannot change; screenshot pairs (lk, e1, e5, r10a at
    60 / 120 s) show the same scene (pose differences only: the shots are wall-timed and the after arm runs faster).
  - Heap 4: +1.13 MB free in r11a (census free 772,448 -> 1,906,624 at frame 900), +1.0 MB in r10a (550,656 ->
    1,549,184).
- **Numbers (hw ms first: hwproject SH-4 model, cost arms f21C0 / f21C1 = play flags + ROUTE_CH21=1 SBB_STUB=1
  DBG_WARP=1 PC_SAMPLER=1, 12 traced ticks; then Flycast PACE draw ms over 300-frame windows from frame 900, p50 / p99
  / max, vsync off).**

  | view (window) | hw before drawn / skipped | hw after | Flycast before | Flycast after |
  |---|---|---|---|---|
  | r11a quiet (e1 500:579) | 58.8 / 39.1 (LOGIC 29.3) | 41.2 drawn work + 26.1 pace wait (LOGIC 16.4) | 36.2 / 36.7 / 36.7 (22.2 fps) | 27.2 / 27.3 / 27.3 (29.9 fps, capped) |
  | r11a Ganados (e5 700:779) | 68.1 / 37.1 (LOGIC 34.3) | 49.3 / 20.4 (LOGIC 14.1) | 42.1 / 45.0 / 45.0 (15-16 fps) | 35.1 / 38.6 / 38.6 (27-30 fps) |

  Function rows (quiet, drawn tick): Espgen42_Move00 13.26 -> 0 (gone), PSVECNormalize 4.55 -> 0.25. After the change
  the quiet view runs under the 30 fps cap, so its drawn tick carries the pace wait and the drawn / skipped split of
  the model is not meaningful there (all 12 ticks are drawn; 9 with the wait, 3 at 42.9 without). Evidence
  hwmodel-fix21-f21C0-e1 / -e5, hwmodel-fix21-f21C1-e1 / -e5; Flycast route-f21-e1C0 / e1C1 / e5C0 / e5C1.

## Progress 2026-10-10 (r10b / r11b material pair 18d0fd82-2c9a9309 on the disc)

`native UI: package rejected: open failed` for 18d0fd82-2c9a9309 (256x256) followed by `pair missing ...
color=71edfaa9-5e1dd270 mask=a1c67505-45451a25`: a material-pair package (a model part with a separate mask image draws
from one package keyed by prepare_native_ui.material_pair_identity) that no staged texture set built. The two source
images are images 0 and 1 of the room model TPL in both lake rooms: st1/r11b.arc #28 (ROOM_CONTRACTS r11b model slot
28) and st1/r10b.arc #27 (find-texture-source.py). The first request is in r10b, after s00 (route-f21-f6rC1), then
again in r11b before door 0. Data only, no code. Lane fix21, evidence D:/Flycast-Evidence/re4-dreamcast/fix21-20261010.

- **Package.** `tools/d367/pairs_from_log.py --iso <GC disc 1> --file st1/r11b.das --log <a run log with the pair
  line> --output pairs` (131,216 B, ARGB4444), then the model-texture VQ rule the asset pipeline applies to pairs
  (vq_native_ui.py --model-min-bytes 16384 over a one-line synthetic load log): 18,432 B VRAM (package 18,576 B; a noisy
  ground-dirt decal, PSNR 23.9 dB, previews identical by eye). Private output /root/probe/lanes/route/pairs-r11b (with
  the raw16 pairs report).
- **Staging.** Lane r11b tools/mkfix.py r11b() now adds pairs-r11b to the r11b texture set, so the r11b / r11a play
  fixtures (and pack-fixture.sh packs of them) carry it; a chapter 1-3-only disc needs it too (r10b requests it).
  Pack check: pack-fixture.sh of the r10b -> r11b fixture holds the key byte for byte. Caveat for play discs:
  pack-fixture.sh builds the pack from the staged loose dc/tex files only, and its output replaces any dc/tex.pak the
  input fixture already carries (the 10-09 catalog pack d87983e1 in the r10b / r11b fixtures): merge the catalog pack's
  packages in before packing, or the pack loses them.
- **Runs (image 079650ba = f21C1 / f21T1; both .sbb banks off).** route-f21-f6rN (r10b -> s00 / s10 / QTE / s22 ->
  save -> door 6 -> r11b s00, the radio call): 18d0fd82 loads in r10b and r11b, `open failed` only for the known early
  PS2 world open at the chapter end (retried); route-f21-w2N (r11b -> r11a -> r119 door) and route-f21-a1N (the
  ambush): open failed 0. HALT 0, MISSING 0, MISALIGN 0, no allocation failure. The image is item 1's; H2 / bell /
  New Game discs carry no r10b / r11b room textures, so their gates are 079650ba's.

## Progress 2026-10-10 (stream 1:148, the r11b radio call voice, in aica_str.dat)

`aica: stream sbb=9900000 not in aica_str.dat, silent` on r11b entry: bio4str.hed block 1 request 148 (SND_SHD
offset 0x9900000, 22.0 s stereo one-shot at 32 kHz), requested right after the Ope radio 1:3, i.e. the voice of the
r11b radio call. Lane fix21, evidence D:/Flycast-Evidence/re4-dreamcast/fix21-20261010.

- **Change.** tools/aica_banks.py: CH21_STREAMS = ROUTE_STREAMS + CALL_VOICE_STREAMS + 0:4 (r10b) + 0:17, 1:36 (r11b)
  + 1:148, selectable as `--streams ch21` (STREAM_PRESETS). It names the list the r11b lane passed by hand (14
  streams) and appends 1:148, so every earlier entry and its data bytes are unchanged: only the 2 KB header grows by
  one entry. `aica_banks.py streams --mirror <LE mirror with the .sbb> --out DIR --streams 0:2,...,1:36` reproduces
  the r11b file byte for byte (15,800,320 B, sha 0a9dfd80..); `--streams ch21` gives 16,504,832 B (sha c49229aa..):
  bytes [2048, 15,800,320) identical, entries 0..13 identical, entry 14 = {0x9900000, 32000, 0x940100, 2, 704000 (A),
  0, 0xF11800, 0}. Staged by lane r11b tools/mkfix.py r11b() (rooms/str-r11b-ch21). test_aica_banks.py: 12 tests OK.
- **Runs (image 079650ba; both .sbb banks off).** route-f21-f6rN (r10b -> chapter 1-3 save -> door 6 -> r11b s00, the
  radio call): `stream 1:148 ready / start ... stopped` 21.8 s after its start, right after 1:3; no "not in
  aica_str.dat" for it. H2 with the 14-stream vs the 15-stream file (route-f21-h2o / h2nn, ACT_CAP=0): STRICT 1450..1569,
  0..740, 1218..6991 and the whole room, MUST-IDENTICAL (6992 ticks); the stream event sequences (start / stopped,
  ids) identical; s30 340/340. Bell (bello / bellnn): STRICT frame and room, MUST-IDENTICAL (5100 ticks). New Game
  (play ELF f21P, 15-stream file): intros 1971 / 2360, s40 1175, 1:3 and 1:140 play. r11b -> r11a (w2N) and the ambush
  (a1N): HALT 0. HALT 0, MISSING 0, MISALIGN 0, no allocation failure in every run.
- **Still silent (not this change):** 0:29 (sbb 0x3480000, 60 s one-shot music) requested on the chapter 1-3 results /
  save screen in r10b (route-f21-f6rC1, also the r11a lane's f6sS); `sbb=000000` (0:0) in r10b after the QTE and in the
  r101 bell warp (also before SBB_STUB).

## Progress 2026-10-10 (PVR_READY_STRICT: no scene into a busy TA bank, issue 9)

The issue 9 diagnosis (r108 -> r109 bridge door hang on a console; C:/Game Dev/Emulators/issue9-diagnosis-20261010.md)
found a latent KOS defect on the way. Lane tree /root/probe/lanes-20261010/kosfix, evidence
D:/Flycast-Evidence/re4-dreamcast/kosfix-20261010.

- **Defect.** The pinned KOS (/root/work/kos-re4dc-d367, toolchain, not in the repo) pvr_scene.c
  pvr_start_ta_rendering() (static, inlined into pvr_list_begin at a scene's first list) ignores pvr_wait_ready()'s
  100 ms timeout: the next scene's TA input is appended to the bank whose previous scene was never handed to a render
  (no TA list init). When that render starts, pvr_begin_queued_render() writes the background plane at the TA's
  current vertex position (inside the new scene) and pvr_sync_reg_buffer() re-inits the TA under the half-written
  scene: a corrupted render (an ISP lockup on hardware) or a scene whose list-done events never all arrive. With one
  bank the same function also ignores pvr_wait_render_done()'s timeout (TA input into the bank being rendered), as
  does pvr_set_presort_mode() (WORLD_AUTOSORT: the tile matrix being rendered). pvr_present_wait() returns after one
  100 ms wait; present_fence() then halts ("completion fence failed"), so a render that is only slow stops the game.
- **Fix, PVR_READY_STRICT=1 (default 0, needs PVR_PIPELINE=2).** No toolchain edit: link wraps
  (`-Wl,--wrap=pvr_list_begin -Wl,--wrap=pvr_set_presort_mode`) acquire the TA bank before KOS's own waits run (ta_busy
  clear, plus render_busy clear with one bank), and present_fence() retries pvr_present_wait(); every wait goes on in
  100 ms slices up to 10 s, then the stop screen names it. No TA / ISP reset. Every expired slice is counted; with
  PVR_LATCH=1 the ring gets K (TA bank) / Q (render done) / Y (present fence) and the stop screen a row
  `rdy K<n> Q<n> Y<n> first <ui frame> last <ui frame>`. Checked and unchanged (they never proceed into a busy bank):
  pvr_render_lists (render only with render_busy / render_completed clear and all lists in), the async decision
  (applied only at render-done), the fast-wake and latch chains (KOS's handler runs first), pvr_scene_finish's blank
  lists, pvr_set_vbuf_doublebuf (refuses while busy), re4dc_ui_ta_single_bank and the single-bank stream_open (fence
  first, halt on failure), the gpu::quiesce callers (after present_fence; halt or skip the VRAM change). Comment
  block: platform/native_ui.cpp namespace pvr_ready. Test aid: dc/crashtest.txt `pvrwait`.
- **Gates** (arms from route-build.sh with the 10-10 test flags + ROUTE_CH21=1 SBB_STUB=1, ACT_CAP=0; kfC control
  traced from a clean worktree of the same HEAD, kfT = kfC + PVR_LATCH=1 PVR_READY_STRICT=1):
  - knob-off identity: kfQ (patched tree, play flags, knobs off) vs kfO (clean tree): objcopy images differ only in
    the __TIME__ string, four overlays identical, `_end` 8c3e231c both. Fresh objdirs; missing.txt empty on every arm.
  - H2 (480 s): STRICT 1450..1569, 0..740, 1218..6990; whole room DISCRETE float drift only (om 476, as every gate
    since 19f62e62); decision_cmp MUST-IDENTICAL (6993 ticks). s30 in the H2 runs: 340/340 shown, heap 57504 -> 79200
    in both arms (= control).
  - bell (300 s): STRICT 0..5100 and room 0101, MUST-IDENTICAL (5100 ticks).
  - MISALIGN 0 in every run; HALT 0 and MISSING 0 except the forced test.
  - New Game (kfP play image, 420 s): r120s00 1971/1971, r120s01 2360/2360, r100 s40 1175/1175.
  - r108 -> r109 bridge door (i9b fixture): DOORDEMO START / END, room enter 109.
  - r10a -> r10b door (r10b w1 walk) entered; r10b chapter 1-3 end (f6s, 600 s): s00 / s10 / s20 QTE / s21 played,
    the save, room 10b #2. The f6s trace is identical through the first visit and the QTE, then shifts after the
    wall-timed chapter end (room 10b #2 at vbl 18015 vs 18022; Status_flg 18 ticks; control vs control repeat is
    identical): the wall-timed event class, not a logic change; H2 and bell are the STRICT gates.
  - forced failure (crashtest pvrwait, route-kf-missT2 shots/t0113/frames/fb1.png): `rdy K3 Q0 Y0 first 582 last 584`.
- **Numbers** (hwproject SH-4 model drawn / skipped hw ms, stride 7; kfH strict+latch vs kfHc control, untraced):
  r101 square (hw22e e-sq, 1330:1409, 6 traced drawn ticks): 71.55 / 26.09 vs 70.91 / 25.60; r100 house fight
  (e-fight, 2300:2379, 1 drawn + 11 skipped ticks): 69.89 / 68.01 vs 69.60 / 67.60. Both inside the model's sampling
  noise (the bucket split moves by more than the total). Flycast PACE draw ms per 300-tick window from tick 1500
  (p50 / p99 / max, fps): square 52.4 / 60.4 / 60.4, 14.3 vs 53.3 / 61.3 / 61.3, 14.4; fight 39.3 / 40.9 / 40.9,
  21.8 vs 39.2 / 41.1 / 41.1, 21.9. As expected: the waits only run long on hardware.
- **Recipe.** Next console test build: PVR_READY_STRICT=1 PVR_LATCH=1 (checklist top). The play recipe waits for a
  console result.
## Progress 2026-10-10 (r10b lake water: WATER45_NATIVE, default 1 in the ROUTE_CH13 block)

The r10b lake drew as a flat pale grey sheet. Two causes: nothing draws the water (espgen45's surface is a GX
screen-copy draw, a stub on the Dreamcast; the PS2 world package has no lake surface mesh: SMD_000 is the lake bed),
so the fog-coloured background shows; and the room's GameCube mist / backdrop sheets (owner 0xd0: sst 0x02 tex f2,
sst 0x04 f6 / cb / 1d, sst 0x06 ff) plus est 0x23's white square paint over it. The PS2 release (SLUS-211.34 r10b
EFF, the source of truth for the look) has none of those sheets (est 0x23's colour is 0,0,0,0), draws its lake as flat
planes and retunes the haze (2100 mm, (180,185,175,30), R 5000). Lane lake, evidence
D:/Flycast-Evidence/re4-dreamcast/lake-20261010.

- **Water (espgen45.cpp re4dc_water45_draw, native_ui.cpp re4dc_water45_quad).** The plane (mat) over the grid and
  the GX path's border (15 grid sizes, or the grid with flag bit 0) as 16 x 16 cells spaced t|t| around the eye, each
  corner's factor = lerp(TEV col, 1, fog) (native_static.cpp re4dc_fog_amount: the PVR's loaded fog table), drawn as a
  PVR multiply (DESTCOLOR, ZERO), TR, Gouraud, GEQUAL, no Z write; fully fogged and behind-camera cells are skipped.
  Queued in OT layer 0x10 like Espgen45_TransSub: from Espgen45_Trans and, on a drawn coarse image, from the
  logic-only EspgenTrans (trans.cpp re4dc_espgen_draw_pass). Drawing it during Trans instead put the quads into the
  wrong PVR frame (every other image without water). Corners are two rolling rows on the stack (no bss: `_end` equal).
- **Sprites (esp_sub.cpp, EFFECT_SPRITES).** r10b room sheets f2 / f6 / cb / 1d / ff (owner 0xd0) and est 0x23's
  square (owner 0x01, id 0, tex 0) are not drawn; kPs2Haze gains r10b (every 1, PS2 colour, R 5000, scale
  2100 / 1731.4); a sprite wholly under the surface seen from above is not drawn (the GC water writes Z first).
- **Material pair 18d0fd82** (also 3594d8f5): rooms.toml [material_pairs] + pairs_from_log.py ROUTE_FILES st1/r10b.das,
  so the asset pipeline builds it. Staging unchanged from 3594d8f5 (dc/tex/1/18d0fd82-2c9a9309.re4tex, VQ, into the pack).
- **Gates.** Knob-off identity at 6516c62b: default recipe, play flags with ROUTE_CH13=0, and ROUTE_CH13=1
  WATER45_NATIVE=0 vs HEAD ROUTE_CH13=1: 3 bytes each (the time stamp). missing.txt empty, MISALIGN 0, HALT 0.
  Trace arms lkCT (85b7832e + warp aid) vs lkLT2 (+ this change), `_end` 8c3ebb3c both, text +3,584 B. H2 (g-h2, 480 s)
  MUST-IDENTICAL frame (6986 ticks, every info row ok) and room 0100, s30 340/340 heap_before 57,504 = control. Bell
  (g-bell, 300 s) MUST-IDENTICAL frame + room 0101 (5091 ticks; sq info only). r10b f6 (boarding, s10, the QTE, s21):
  in-room ticks 166..3967 identical in every field but `st` at 803..842, Status_flg[0] 0x40000000 / 0x20000000 /
  0x4000 (pad action / fire bits) one tick out of phase: the retrace-clocked pad script's presses landing one tick
  later (two control runs are identical; raw words logged by a probe build); rng, player, enemies, decisions and
  movies identical; QTE presses 10 vs 11 (wall-timed input).
- **Cost (hw first; cost arms lkCC / lkLC, play flags + PC_SAMPLER).** Lake view 800:879: drawn 61.10 -> 51.60 hw ms
  (RENDER/effects 10.31 -> 1.16, the water +1.5 in RENDER/other), skipped 14.45 -> 14.40; Flycast p50 / p99 / max
  50 / 51 / 51 -> 43 / 48 / 48. Boss pass 4100:4179 (fixture fb): Flycast 35 / 37 / 37 -> 33 / 34 / 34; its hw pair is
  not like for like (the pad script's phase moves the camera: lkLC draws the boss and Leon, lkCC the mist), hw
  39.62 vs 69.18 drawn with 17.97 of it PACE/WAIT. Screens: route-lk-f6v21b (before) vs route-lk-f6v32 (after)
  t0082 (dock) and t0145 (from the boat).

## Progress 2026-10-10 (LINK_TIGHT + LINK_OVL_HELPERS: heap margin for the CH21 images, lane r118)

The CH21 trace image was page-tight: s30 heap_before sat exactly at the control (57,504), and any image growth risked
the r100 s30 movie cliff. Two link-only knobs, default 1 in the ROUTE_CH21 block (no effect elsewhere):
- **LINK_TIGHT.** KOS shlelf.xc has ten empty .sub0..9 sections, each `ALIGN(0x2000)`, so .init and everything after
  it (rodata, data, bss, `_end`, the KOS heap) moves to the next 8 KiB boundary: 0..8 KiB of padding, and an 8 KiB
  jump whenever .text crosses one. The Makefile links with a copy of the script without that block
  (`$(OBJDIR)/shlelf-tight.ld`, awk; the rule fails if the KOS layout changes).
- **LINK_OVL_HELPERS.** Image code that only one room overlay reaches moves into that overlay: tools/link.sh links
  once per overlay with that overlay discarded (`--print-gc-sections`), tools/ovl_helpers.py renames the .text
  sections that only the discard link drops into `<ovl>.h<n>` (COMDAT members skipped) and the overlay scripts KEEP
  them; obj/ovlh/moves.tsv lists them. 31 sections, 4,724 B (pl0f 43,060 -> 45,576, em2f 16,472 -> 16,800, em2b
  66,064 -> 68,140, em22 unchanged). The sub screen overlay is left alone (19.7 KB of Sscrn-only code; lifetime risk).
- **MOVIE_FENCE_RETRY** (timing only, same block): a route movie retries a not-ready render fence before a picture
  upload (up to 3 more times, logged as "route movie upload fence"). One intermediate image layout ended r119 s30 at
  its first picture (terminal=3, uploaded=0, `re4dc_ui_movie_upload_begin` false) deterministically; the cause is
  layout/timing dependent (two other layouts play it 140/140) and was not reproduced again.
- **`_end`.** Trace 8c3ebb7c -> 8c3e9adc (final image, all three r118-lane changes), play 8c3e233c -> 8c3df73c, cost
  8c3e993c -> 8c3e85bc. Trace arena slack ("left to KOS" - 147,520) 1,160 -> 2,376 B; s30 heap_before 57,504 ->
  65,696 (+8,192).
- **Gates (final image l4, bc2593cd + this + ACTOR_EXACT_FAST + r118).** Knob-off identity: default recipe and play
  flags without ROUTE_CH21 differ from bc2593cd in the time stamp only (3 / 4 bytes), overlays equal; missing.txt
  empty; MISALIGN 0, HALT 0. H2 (480 s) STRICT 1450..1569, 0..740, 1218..; room DISCRETE with om at 741 as before;
  MUST-IDENTICAL (6986 ticks); s30 340/340 heap_before 65,696 >= 57,504. Bell (300 s) STRICT frame + room 0101,
  MUST-IDENTICAL (sq info only). New Game: 12000 1971/1971, 12001 2360/2360, s40 1175/1175. r10b f6 -> QTE -> save
  -> r11b s00 1484/1484 (same QTE outcome as the control). r119 g3: s00 / s10 / s30 / s20 all terminal=1 (s30
  140/140). r11a -> r11b.

## Progress 2026-10-10 (ACTOR_EXACT_FAST: r119's exact-lit trees, lane r118)

r119's quiet-view RENDER/models(other) was the actor path's exact per-vertex lighting: 92% of
evaluate_prepared_source_lighting came from pass_lights_exact <- re4dc_actor_submit <- ModelRender. Census: cEmTree
(id 0x49, 3 parts) 4,835 exact-lit vertices a frame under up to eight flickering torch lights (more than three
significant lights, so no fold, and the bake key changes every frame: a bake gave nothing), cEmTorch 314.
- **ACTOR_EXACT_FAST=1** (render only, default 1 with ROUTE_CH21): pass_lights_exact computes each light's constants
  once outside the vertex loop and the distance with fsrra; same lights, order, ambient start, clamps, material and
  tev scale (float rounding only).
- **hw ms (cost arms l1C -> l3C, drawn).** Quiet q 500:579: 109.3 -> 93.8 (-15.5). Boss b 900:979 (El Gigante,
  proven in the r119 doc): 88.0 -> 89.5 (noise; the boss's own body dominates, few exact vertices). Flycast PACE
  300-frame windows p50 / max: quiet 72 / 74 -> 69.5 / 73; boss pass window 78 -> 74, after it 61-62 both.
- **Gates.** As LINK_TIGHT (same final image l4): H2 + bell STRICT, MUST-IDENTICAL; play-throughs pass.
- **Next for r119 perf.** The boss itself (em2b, GC-drawn: models(other) ~33 ms) needs a native draw path; the
  quiet view's remaining cost is the source-drawn huts / roofs / gate.

## Numbers (image, build, evidence)

## Ready to land
