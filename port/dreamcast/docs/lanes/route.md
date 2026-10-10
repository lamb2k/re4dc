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

## Numbers (image, build, evidence)

## Ready to land
