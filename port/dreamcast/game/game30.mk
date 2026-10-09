# Game-side CPU knobs (D367 game30). Included by the Makefile after the flag variables and
# object lists are defined. Every knob defaults to 0 and then contributes nothing: the
# reference image is byte-identical with or without this file.
#
# Bit-identical by construction or by proof (gate: the determinism trace, LOGIC_TRACE=1):
#   GAME_PS_ALIAS=1   the paired-single SDK entry points (PSMTX*/PSVEC*) are bound at link to
#                     the C bodies they forwarded to (platform/ps_alias.ld): the same machine
#                     code runs minus one call frame per call (~3,700 call sites).
#   GAME_SH4_MATH=1   (implies GAME_PS_ALIAS) hot PS entry points bound to hand-scheduled
#                     SH-4 bodies (platform/mtx_sh4.S) that execute the identical FP dataflow
#                     (tools/fpsym2.py --strict proof over the linked ELF).
#   GAME_ROOM_INDEX=1 cRoomData::getRoomSavePtr through a record-index table built once from
#                     the static stage tables instead of a ~70-entry scan per call (exhaustive
#                     host check over all 65,536 room ids).
#   GAME_ROT_CACHE=1  RotMatrix (Rz*Ry*Rx from Euler angles: 6 sinf/cosf) memoised on the exact
#                     angle bits in a 32-entry table; a hit returns the bits a call computes (pure
#                     function). Hit rate reported by GAME_TICK_LOG ("rotcache=hits/misses").
#   GAME_CPU=1        PS_ALIAS + SH4_MATH + ROOM_INDEX (ROT_CACHE stays separate until its hit
#                     rate is measured).
# Test instrumentation (never in a product image):
#   LOGIC_TRACE=1     one determinism record per frame-loop iteration (logic_trace.cpp).
#   GAME_TICK_LOG=N   one line per N frames with the mean/max time of every ProcessTickGet phase
#                     (TaskScheduler, EmMgr.move, Player, objTrans, ...) through re4dc_log: the
#                     serial console on real hardware (tick_log.cpp). Observation only.
#   LOGIC_TRACE_DELAY_US=N  (trace builds only) burn N us per frame in the trace hook: the
#                     timing-perturbation control arm that proves the fixture is insensitive to
#                     CPU speed before any A/B verdict is trusted.
# Build every arm in its own OBJDIR (flag changes do not rebuild existing objects).
GAME_CPU ?= 0
ifeq ($(GAME_CPU),1)
GAME_PS_ALIAS ?= 1
GAME_SH4_MATH ?= 1
GAME_ROOM_INDEX ?= 1
endif
GAME_PS_ALIAS ?= 0
GAME_SH4_MATH ?= 0
GAME_ROOM_INDEX ?= 0
GAME_ROT_CACHE ?= 0
LOGIC_TRACE ?= 0
GAME_TICK_LOG ?= 0
LOGIC_TRACE_DELAY_US ?= 0
# LOGIC_TRACE_MASK_RENDER=1 (trace builds only, opt-in): leave the render-only be_flag 0x08000000
# out of the hash (logic_trace.cpp; the frame pacing gates). Default 0: hashes unchanged.
LOGIC_TRACE_MASK_RENDER ?= 0
# LOGIC_TRACE_OBJ_FROM/TO=K (trace builds only, diagnostic; default 0 = off, hashes and image unchanged): one "LO"
# line per alive object for Frame_cnt FROM..TO (id, type, be_flag, Mot_state/frame, its own coord/parts hashes),
# so an om/of difference names the object.
LOGIC_TRACE_OBJ_FROM ?= 0
LOGIC_TRACE_OBJ_TO ?= 0
# LOGIC_TRACE_EM_FROM/TO=K (trace builds only, diagnostic, lane fm; default 0 = off, hashes and image unchanged): one
# "LE" line per alive enemy for Frame_cnt FROM..TO (the es inputs: be_flag, r_no bytes, id, type, Mot_state, hp;
# with Mot_frame, the pos bits, the unit's address and first word), so an es difference names the enemy and field.
LOGIC_TRACE_EM_FROM ?= 0
LOGIC_TRACE_EM_TO ?= 0

GAME30_LINK_INPUTS =
ifeq ($(GAME_SH4_MATH),1)
ifneq ($(GAME_PS_ALIAS),1)
$(error GAME_SH4_MATH=1 binds the PS* entry points and needs GAME_PS_ALIAS=1)
endif
PLATFORM_OBJS += $(OBJDIR)/platform/mtx_sh4.o
GAME30_LINK_INPUTS += platform/ps_alias_sh4.ld
$(OBJDIR)/platform/mtx.o: PLATFORM_CPPFLAGS += -DRE4DC_PS_ALIAS=1 -DRE4DC_SH4_MATH=1
$(OBJDIR)/platform/mtx_sh4.o: platform/mtx_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
else ifeq ($(GAME_PS_ALIAS),1)
GAME30_LINK_INPUTS += platform/ps_alias.ld
$(OBJDIR)/platform/mtx.o: PLATFORM_CPPFLAGS += -DRE4DC_PS_ALIAS=1
endif

ifeq ($(GAME_ROOM_INDEX),1)
$(OBJDIR)/src/game/roomdata.o: GAME_CPPFLAGS += -DRE4DC_ROOM_INDEX=1
endif

ifeq ($(GAME_ROT_CACHE),1)
$(OBJDIR)/src/game/math_sub.o: GAME_CPPFLAGS += -DRE4DC_ROT_CACHE=1
endif

# design-logic prototypes (bit-exact by construction; gate: LOGIC_TRACE STRICT):
#   GAME_PWC_DIAG=1  partsWorldCalc non-uniform-scale path: the two multiplies by a diagonal scale
#                    matrix run the concat kernel's own dataflow with the provably dead terms removed
#                    (diag a*s + 0, column 3 unchanged, NaN guard -> original path; model.cpp comment,
#                    host proof design-logic/proofs/pwc_diag_check.c). =2: check build, both paths,
#                    mismatches counted in the tick log ("pwcdiag=checks/mismatches").
#   GAME_ATCHK=1     EmAtCheck walks each actor list once per call (collidable bodies into an array,
#                    next-body prefetch) instead of three times.
#   GAME_MOTION_INDEX=1  re4dc_motion_acquire finds the clip record by binary search over the
#                    bind-validated, strictly increasing record offsets instead of a linear scan
#                    (platform residency layer only; returns the same record, so the same key table).
GAME_PWC_DIAG ?= 0
GAME_ATCHK ?= 0
GAME_MOTION_INDEX ?= 0
# Resource candidate, not a math/performance optimization. Explicit aggregate
# motion-key payload cap; 0 retains the original hot-resident policy. 262144 is
# the opening-memory-r1 candidate, pending normal-route/STRICT/I/O qualification.
# Hot payloads may be reloaded after unpinned eviction; archives/proxies remain.
MOTION_PRESSURE_BYTES ?= 0
ifneq ($(MOTION_PRESSURE_BYTES),0)
$(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -DRE4DC_MOTION_PRESSURE_BYTES=$(MOTION_PRESSURE_BYTES)
endif
# MOTION_OOM_EVICT=1 (native_motion.cpp, default 0): a motion key whose room-heap allocation fails evicts
# LRU unpinned keys and retries instead of halting (r100 after-ambush HALT, 2026-09-28). Logic-neutral.
MOTION_OOM_EVICT ?= 0
# MOVIE_HEAP_EVICT=1 (needs MOTION_OOM_EVICT=1, ROUTE_MOVIES=1; native_motion.cpp + native_movie.cpp, default 0):
# a route movie whose heap-4 staging does not fit evicts unpinned motion keys, least recently used first,
# and retries (r100 s30 after the ambush failed with 313 KB free in pieces of at most 148 KB). Logic-neutral:
# the keys reload from disc at their next use. First it lends the movie the model preparation cache (ui_bridge.cpp,
# 128 KB, rebuilt per frame; reallocated when the movie retires): LRU keys alone left 197 KB in holes of at most
# 40 KB when the route reached the cliff at another frame (route-hm1); a final failure logs heap 4's free map.
# The loan is explicit state in ui_bridge.cpp: while lent no model draw takes the cache back or latches its one
# attempt (a stepped movie's game frames keep drawing); the movie's retirement ends the loan and allocates again
# ("cache back (N B), K model draws asked during the loan"; 0 B is a failure line, retried at the next draw).
#   MOVIE_LOAN_TEST=1 (test only, default 0): each movie lends the cache at its first staging allocation (heap 4 had room).
MOVIE_HEAP_EVICT ?= 0
#   MOVIE_STAGE_ORDER=1 (default 0): a movie stages its large pieces up front, largest first (first fit decreasing),
#   and the player / decoder take them by size. r100 s30 with crash screen + PS2_WORLD_DYNAMIC + PS2_INTERIOR_ACTORS
#   failed (terminal=3) when the PCM and callback pieces split the lent model-cache hole and the second luma plane met
#   219,520 B free in holes of at most 47,808 B. Same pieces, same bytes; only the request order changes.
#   MOVIE_BALLAST_TEST=<bytes> (test only, default 0): holds that much heap 4 from r100 s30's open to its end (margin probe).
MOVIE_LOAN_TEST ?= 0
MOVIE_STAGE_ORDER ?= 0
MOVIE_BALLAST_TEST ?= 0
ifneq ($(MOVIE_HEAP_EVICT),0)
ifneq ($(MOTION_OOM_EVICT)$(ROUTE_MOVIES),11)
$(error MOVIE_HEAP_EVICT=1 needs MOTION_OOM_EVICT=1 ROUTE_MOVIES=1)
endif
$(OBJDIR)/platform/native_motion.o $(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_MOVIE_HEAP_EVICT=1
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_MOVIE_HEAP_EVICT=1
ifneq ($(MOVIE_LOAN_TEST),0)
$(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_MOVIE_LOAN_TEST=1
endif
ifneq ($(MOVIE_STAGE_ORDER),0)
$(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_MOVIE_STAGE_ORDER=1
endif
ifneq ($(MOVIE_BALLAST_TEST),0)
$(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_MOVIE_BALLAST_TEST=$(MOVIE_BALLAST_TEST)
endif
endif
ifneq ($(MOTION_OOM_EVICT),0)
$(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -DRE4DC_MOTION_OOM_EVICT=$(MOTION_OOM_EVICT)
endif
# GAME_WPAL_FAST=1 (trans.cpp, render only, exact, default 0): MakeWeightPalette keeps its 12 sums in
#                  registers and stores the palette entry transposed directly (same operations, same order;
#                  no per-entry memclr / PSMTXReorder call). =2 (check build): the reference loop re-runs
#                  and compares the palette words ("WPAL ... mismatch=" lines). =3: the loop in
#                  platform/wpal_sh4.S (same operations, two temps interleaved); =4: its check build.
# GAME_SK1_ASM=1 (trans.cpp, render only, exact, default 0): the off-PowerPC CalcSk1_x / CalcSk1_x2 source
#                skinning loops (morphed infos, Render() materialisation) in platform/sk1_sh4.S: same
#                operations, three components interleaved. =2 (check build): the C loop re-runs and
#                compares ("SK1 ... mismatch=" lines).
GAME_SK1_ASM ?= 0
ifneq ($(GAME_SK1_ASM),0)
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_SK1_ASM=$(GAME_SK1_ASM)
PLATFORM_OBJS += $(OBJDIR)/platform/sk1_sh4.o
$(OBJDIR)/platform/sk1_sh4.o: platform/sk1_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
endif
# SCREEN_320=1 (test builds; visible): render at 320x240 (KOS DM_320x240). Every screen mapping and clip
#              bound takes platform/include/re4dc_screen.h's size; the 640x480 2D UI is halved at its emit sites.
SCREEN_320 ?= 0
ifneq ($(SCREEN_320),0)
GAME_CPPFLAGS += -DRE4DC_SCREEN_W=320 -DRE4DC_SCREEN_H=240
PLATFORM_CPPFLAGS += -DRE4DC_SCREEN_W=320 -DRE4DC_SCREEN_H=240
endif
# ACTOR_STATS_LEAN=1 (native_actor_fast.cpp, exact, default 0): the actor statistics that only the
#                    NATIVE_ACTOR_LOG line reads compile to nothing (triangles stays: coarse_ganado reads it).
ACTOR_STATS_LEAN ?= 0
ifneq ($(ACTOR_STATS_LEAN),0)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_STATS_LEAN=1
endif
# SKIN_PALETTE_LAZY=1 (trans.cpp + native_actor_fast.cpp, render only, exact, default 0; needs
#                   NATIVE_ACTOR_SKIN_LAZY=1): ModelTrans registers a lazily skinned info with its palette copy
#                   reserved but not built; calcWeightMat + MakeWeightPalette run when a render consumer first reads
#                   it (prepare_frame / one_frame / re4dc_skin_materialize), same frame, same functions, same words.
#                   Owner-drawn and culled actors (Ganados, Leon) never build source palettes. =2 (check build): the
#                   eager palette is built and drawn, the lazy build compares ("SKLAZY ... bad= badw= stale=" lines).
SKIN_PALETTE_LAZY ?= 0
ifeq ($(filter $(SKIN_PALETTE_LAZY),0 1 2),)
$(error SKIN_PALETTE_LAZY must be 0, 1 or 2)
endif
ifneq ($(SKIN_PALETTE_LAZY),0)
ifneq ($(NATIVE_ACTOR_SKIN_LAZY),1)
$(error SKIN_PALETTE_LAZY needs NATIVE_ACTOR_SKIN_LAZY=1)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_SKIN_PALETTE_LAZY=$(SKIN_PALETTE_LAZY)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_SKIN_PALETTE_LAZY=$(SKIN_PALETTE_LAZY)
endif
# LEON_FACE_LAZY=1 (lane ln 2026-10-05; trans.cpp + model_bridge.cpp + shadow.cpp + mirror.cpp, render only, exact,
#                default 0; needs SKIN_PALETTE_LAZY=1): ModelTrans's CPU skin of Leon's morphed face info (be_flag 2)
#                keeps its arrays and morph but defers calcWeightMat + MakeWeightPalette + CalcSk1_x / CalcSk1_x2 to
#                the first render read of those arrays (a source draw of Leon, its shadow or mirror model): same frame,
#                same functions, same words. When the owner path draws Leon nothing reads them (~0.55 hw ms a tick).
LEON_FACE_LAZY ?= 0
ifeq ($(filter $(LEON_FACE_LAZY),0 1),)
$(error LEON_FACE_LAZY must be 0 or 1)
endif
ifneq ($(LEON_FACE_LAZY),0)
ifneq ($(SKIN_PALETTE_LAZY),1)
$(error LEON_FACE_LAZY needs SKIN_PALETTE_LAZY=1)
endif
LEON_FACE_LAZY_OBJS = $(OBJDIR)/src/game/trans.o $(OBJDIR)/src/game/shadow.o $(OBJDIR)/src/game/mirror.o $(OBJDIR)/model_bridge.o
$(LEON_FACE_LAZY_OBJS): GAME_CPPFLAGS += -DRE4DC_LEON_FACE_LAZY=1
endif
GAME_WPAL_FAST ?= 0
ifneq ($(GAME_WPAL_FAST),0)
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_WPAL_FAST=$(GAME_WPAL_FAST)
ifneq ($(filter 3 4,$(GAME_WPAL_FAST)),)
PLATFORM_OBJS += $(OBJDIR)/platform/wpal_sh4.o
$(OBJDIR)/platform/wpal_sh4.o: platform/wpal_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
endif
endif
# GAME_SINCOS=1 (design-logic P6, needs GAME_TRIG=1): RotMatrix and the SDK rotation builders take sin and
#                    cos of one angle from re4dc_sincosf (game30_trig.c: one |x| test and argument reduction,
#                    the same kernels): bit-identical by construction, all 2^32 inputs checked on the host
#                    (tools/game30/sincos_exhaustive.sh).
GAME_SINCOS ?= 0
ifneq ($(GAME_SINCOS),0)
ifneq ($(GAME_TRIG),1)
$(error GAME_SINCOS needs GAME_TRIG=1)
endif
$(OBJDIR)/game30_trig.o: KOS_CFLAGS += -DRE4DC_SINCOS=1
$(OBJDIR)/src/game/math_sub.o: GAME_CPPFLAGS += -DRE4DC_SINCOS=1
$(OBJDIR)/sdk/mtx.o: SDK_CFLAGS += -DRE4DC_SINCOS=1
endif
ifeq ($(GAME_MOTION_INDEX),1)
$(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -DRE4DC_MOTION_INDEX=1
endif
ifneq ($(GAME_PWC_DIAG),0)
$(OBJDIR)/src/game/model.o: GAME_CPPFLAGS += -DRE4DC_PWC_DIAG=$(GAME_PWC_DIAG)
endif
ifeq ($(GAME_PWC_DIAG),2)
$(OBJDIR)/tick_log.o: PLATFORM_CPPFLAGS += -DRE4DC_PWC_DIAG_LOG=1
endif
ifeq ($(GAME_ATCHK),1)
$(OBJDIR)/src/game/at_mod.o: GAME_CPPFLAGS += -DRE4DC_ATCHK=1
endif
# GAME_ATCHK_LIST=1 (needs GAME_ATCHK=1; square plan step 1): EmAtCheck keeps the EmMgr / ObjMgr alive
#                    lists in list order in an array, rebuilt when the list changed (cManager.h bumps a
#                    per-type generation on every list or work-array change), and tests each body's live
#                    collision flags from it with a deep prefetch. Same candidates, same order.
#                    =2: every cached use is checked against a list walk ("ATL" log line, mismatch count).
#                    A header knob: every object gets the define, so each inline list mutation bumps.
GAME_ATCHK_LIST ?= 0
ifneq ($(GAME_ATCHK_LIST),0)
ifneq ($(GAME_ATCHK),1)
$(error GAME_ATCHK_LIST needs GAME_ATCHK=1)
endif
GAME_CPPFLAGS += -DRE4DC_ATCHK_LIST=$(GAME_ATCHK_LIST)
PLATFORM_CPPFLAGS += -DRE4DC_ATCHK_LIST=$(GAME_ATCHK_LIST)
endif
# GAME_ATLIST_OVERFLOW=1: retain a failed alive-array build by the existing head
# and generation. Oversized lists still take the full source collision walk.
GAME_ATLIST_OVERFLOW ?= 0
ifneq ($(filter-out 0 1,$(GAME_ATLIST_OVERFLOW)),)
$(error GAME_ATLIST_OVERFLOW must be 0 or 1)
endif
ifneq ($(GAME_ATLIST_OVERFLOW),0)
ifeq ($(GAME_ATCHK_LIST),0)
$(error GAME_ATLIST_OVERFLOW needs GAME_ATCHK_LIST=1)
endif
$(OBJDIR)/src/game/at_mod.o: GAME_CPPFLAGS += -DRE4DC_ATLIST_OVERFLOW=$(GAME_ATLIST_OVERFLOW)
endif
# GAME_ATLIST_512=1: enlarge only the two ordered alive arrays from 320 to 512.
# Candidate capacity and overflow semantics are unchanged; SH-4 static cost +1536 B.
GAME_ATLIST_512 ?= 0
ifeq ($(filter $(GAME_ATLIST_512),0 1),)
$(error GAME_ATLIST_512 must be 0 or 1)
endif
ifneq ($(GAME_ATLIST_512),0)
ifeq ($(GAME_ATCHK_LIST),0)
$(error GAME_ATLIST_512 needs GAME_ATCHK_LIST=1)
endif
$(OBJDIR)/src/game/at_mod.o: GAME_CPPFLAGS += -DRE4DC_ATLIST_512=1
endif
# GAME_ATCHK_CACHE=1 (needs GAME_ATCHK_LIST=1; G, collision traversal; exact): EmAtCheck keeps each list's
#                    collected bodies while the list is unchanged and applies to them every body whose
#                    collidable test (cAtariInfo m_flag bit 0x200, m_radius2 != 0) changed: the two fields
#                    become wrappers that note such writes, and taking their address does not compile
#                    (atariInfo.h). A header knob: every object. =2 (check build): every reuse compared
#                    with a fresh collection ("ATC" lines).
GAME_ATCHK_CACHE ?= 0
ifneq ($(GAME_ATCHK_CACHE),0)
ifeq ($(GAME_ATCHK_LIST),0)
$(error GAME_ATCHK_CACHE needs GAME_ATCHK_LIST=1)
endif
GAME_CPPFLAGS += -DRE4DC_ATCHK_CACHE=$(GAME_ATCHK_CACHE)
PLATFORM_CPPFLAGS += -DRE4DC_ATCHK_CACHE=$(GAME_ATCHK_CACHE)
endif
# GAME_OBJHIT_LIST=1 (needs GAME_ATCHK_LIST=1; G, collision traversal; exact): ObjHitCheck (the camera's
#                    line against every live object) walks GAME_ATCHK_LIST's array of ObjMgr's alive list,
#                    the objects' header and id lines prefetched ahead, instead of chasing pNext.
#                    =2 (check build): the array compared with the live list at every call ("OHL" lines).
GAME_OBJHIT_LIST ?= 0
ifneq ($(GAME_OBJHIT_LIST),0)
ifeq ($(GAME_ATCHK_LIST),0)
$(error GAME_OBJHIT_LIST needs GAME_ATCHK_LIST=1)
endif
$(OBJDIR)/src/game/at_mod.o: GAME_CPPFLAGS += -DRE4DC_OBJHIT_LIST=$(GAME_OBJHIT_LIST)
endif
# GAME_LINE_LEAF=1 (G, collision traversal; exact): the scenery line queries' leaf loop (atari.cpp
#                  blkPolyLineCkCore) runs the polyBit dedup and At_poly_line_ck's first four tests (plane
#                  crossing, three edge sides) in platform/lnk_sh4.S with the same float operations on
#                  the same operands; only the polygons passing all four reach At_poly_line_ck. =2 (check
#                  build): every verdict compared with the tests in C and At_poly_line_ck ("LNK" lines).
GAME_LINE_LEAF ?= 0
ifneq ($(GAME_LINE_LEAF),0)
PLATFORM_OBJS += $(OBJDIR)/platform/lnk_sh4.o
$(OBJDIR)/platform/lnk_sh4.o: platform/lnk_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
$(OBJDIR)/src/game/atari.o: GAME_CPPFLAGS += -DRE4DC_LINE_LEAF=$(GAME_LINE_LEAF)
endif
# GAME_LINE_WALK=1 (G, collision traversal; exact): the scenery line queries' block walk (atari.cpp
#                  blkPolyLineCk: lineOverlap on every block of a chain, recursion into the overlapped
#                  nodes) in platform/lnw_sh4.S with lineOverlap's float operations on the same operands;
#                  the overlapped leaves then run blkPolyLineCkCore in the walk's order; hitCheck2 walks
#                  each piece first and ends a piece without an overlapped leaf there (no polyBit clear, no
#                  hit transform). =2 (check build): the recursive walk's leaves compared ("LNW" lines).
GAME_LINE_WALK ?= 0
ifneq ($(GAME_LINE_WALK),0)
PLATFORM_OBJS += $(OBJDIR)/platform/lnw_sh4.o
$(OBJDIR)/platform/lnw_sh4.o: platform/lnw_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
$(OBJDIR)/src/game/atari.o: GAME_CPPFLAGS += -DRE4DC_LINE_WALK=$(GAME_LINE_WALK)
endif
# GAME_LINE_PIECE=1 (G, collision traversal; exact; needs GAME_LINE_WALK=1 and GAME_FP_CONTRACT=off):
#                  hitCheck2's per-piece segment transform and walk setup in platform/lnw_sh4.S
#                  (re4dc_line_piece): the x and z rows of MTXMultVec's contract-off dataflow for both ends,
#                  mid / dir / |dir| as the C computes them, then the walk; only a piece with an overlapped
#                  leaf transforms both ends in full, as before. The piece loop steps a pointer. =2 (check
#                  build): the kernel's ends and leaves compared with PSMTXMultVec's and lineWalkPiece's
#                  ("LNP" lines).
GAME_LINE_PIECE ?= 0
ifneq ($(GAME_LINE_PIECE),0)
ifeq ($(GAME_LINE_WALK),0)
$(error GAME_LINE_PIECE=$(GAME_LINE_PIECE) needs GAME_LINE_WALK=1)
endif
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_LINE_PIECE mirrors the contract-off MTXMultVec dataflow: needs GAME_FP_CONTRACT=off)
endif
$(OBJDIR)/platform/lnw_sh4.o: KOS_CFLAGS += -DRE4DC_LINE_PIECE=1
$(OBJDIR)/src/game/atari.o: GAME_CPPFLAGS += -DRE4DC_LINE_PIECE=$(GAME_LINE_PIECE)
endif
# GAME_SPHERE_WALK=1 (G, collision traversal; exact; needs GAME_FP_CONTRACT=off): the swept-sphere queries'
#                   block walk (atari.cpp polySphereCk / blkPolySphereCk: hitCheckSphere on every block of a
#                   chain, recursion into the overlapped nodes) in platform/spw_sh4.S with hitCheckSphere's
#                   float operations on the same operands, resumable (a leaf's polygon test moves the sphere's
#                   end; the walk goes on against the moved end). Each piece is walked first with the x and z
#                   rows of both ends (MTXMultVec's contract-off dataflow); only a piece with an overlapped leaf
#                   clears polyBit and transforms both ends in full, as before. wallAdjust's two calls share
#                   one walk (the second replays the first's leaves when the first hit nothing). =2 (check
#                   build): the original loop on copies, a C walk per kernel step, the re-walks and
#                   PSMTXMultVec's x / z compared ("SPW" lines).
GAME_SPHERE_WALK ?= 0
ifneq ($(GAME_SPHERE_WALK),0)
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_SPHERE_WALK mirrors the contract-off MTXMultVec dataflow: needs GAME_FP_CONTRACT=off)
endif
PLATFORM_OBJS += $(OBJDIR)/platform/spw_sh4.o
$(OBJDIR)/platform/spw_sh4.o: platform/spw_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
$(OBJDIR)/src/game/atari.o: GAME_CPPFLAGS += -DRE4DC_SPHERE_WALK=$(GAME_SPHERE_WALK)
endif
# GAME_CUBE_MEMO=1 (G, camera line vs box bodies; exact): ComnHitCheck's box test (emLineCubeCrossCk: corners,
#                 six face normals normalized, per call) keeps each box's face normals and plane offsets in a
#                 table indexed by the body, keyed on the matrix, sizes and offset bits; a call runs only the
#                 two plane tests per face, and the original test when a face passes both (at_mod.cpp).
#                 =2 (check build): every call compared with emLineCubeCrossCk, every hit rebuilt ("CBM").
GAME_CUBE_MEMO ?= 0
ifneq ($(GAME_CUBE_MEMO),0)
$(OBJDIR)/src/game/at_mod.o: GAME_CPPFLAGS += -DRE4DC_CUBE_MEMO=$(GAME_CUBE_MEMO)
endif
# GAME_EM10_IDFIRST=1 (G, Ganado AI scan; exact): em10SomebodyDamageNowCk tests each slot's id range before
#                    be_flag (two plain loads, either failing skips the slot): fewer cache lines touched.
#                    =2 (check build): both orders compared ("EID" lines).
GAME_EM10_IDFIRST ?= 0
ifneq ($(GAME_EM10_IDFIRST),0)
$(OBJDIR)/mod/%/em10.o: GAME_CPPFLAGS += -DRE4DC_EM10_IDFIRST=$(GAME_EM10_IDFIRST)
endif
# GAME_LINE_YROW=1 (G, line queries; exact; needs GAME_LINE_PIECE=1): hitCheck2 takes a walked piece's ends'
#                 x / z rows from re4dc_line_piece and computes only the y rows (MTXMultVec's expression); the
#                 current end's transform is lb's until a hit is taken, the hit test's re-transform the one
#                 taken before the leaf tests (atari.cpp). =2 (check build): each compared with PSMTXMultVec
#                 ("LYR" lines).
GAME_LINE_YROW ?= 0
ifneq ($(GAME_LINE_YROW),0)
ifeq ($(GAME_LINE_PIECE),0)
$(error GAME_LINE_YROW needs GAME_LINE_PIECE=1)
endif
$(OBJDIR)/src/game/atari.o: GAME_CPPFLAGS += -DRE4DC_LINE_YROW=$(GAME_LINE_YROW)
endif
# GAME_ATRECT_FAR=1 (G, em-em collision; decision-exact): At_em_sphere_rect_ck returns 0 before building the
#                  box frame (RotRad, MultVec, PSMTXInverse) when the sphere's old and new positions both lie
#                  beyond the box's reach (offset + 2 x (sizes + radius)) plus a rounding margin on one side in
#                  x or z (at_mod.cpp arfFar): the original returns 0 there with no write. =2 (check build):
#                  the original always runs; rejected calls that hit are counted ("ARF" lines).
GAME_ATRECT_FAR ?= 0
ifneq ($(GAME_ATRECT_FAR),0)
$(OBJDIR)/src/game/at_mod.o: GAME_CPPFLAGS += -DRE4DC_ATRECT_FAR=$(GAME_ATRECT_FAR)
endif
# GAME_OBJHIT_IDFIRST=1 (G, camera line vs objects; exact; needs GAME_OBJHIT_LIST=1): ObjHitCheck tests each
#                      object's id before be_flag (1045 of 1240 objects/tick have id 2) and prefetches only the
#                      id lines from the array: one line per object instead of two (at_mod.cpp objHitOne).
#                      =2 (check build): both orders compared ("OID" lines).
GAME_OBJHIT_IDFIRST ?= 0
ifneq ($(GAME_OBJHIT_IDFIRST),0)
ifeq ($(GAME_OBJHIT_LIST),0)
$(error GAME_OBJHIT_IDFIRST needs GAME_OBJHIT_LIST=1)
endif
$(OBJDIR)/src/game/at_mod.o: GAME_CPPFLAGS += -DRE4DC_OBJHIT_IDFIRST=$(GAME_OBJHIT_IDFIRST)
endif
# GAME_EMHIT_LIST=1 (G, camera line vs characters; exact; needs GAME_ATCHK_LIST=1): EmHitCheck walks the
#                  alive-list array with the bodies' collision lines prefetched, and skips ComnHitCheck for a
#                  body without a box when the caller's flag has no bit 1 (it returns 0 there) (at_mod.cpp).
#                  =2 (check build): array vs list compared, skipped calls made and checked ("EHL" lines).
GAME_EMHIT_LIST ?= 0
ifneq ($(GAME_EMHIT_LIST),0)
ifeq ($(GAME_ATCHK_LIST),0)
$(error GAME_EMHIT_LIST needs GAME_ATCHK_LIST=1)
endif
$(OBJDIR)/src/game/at_mod.o: GAME_CPPFLAGS += -DRE4DC_EMHIT_LIST=$(GAME_EMHIT_LIST)
endif
# GAME_LINE_LEAF2=1 (G, collision traversal; exact; needs GAME_LINE_LEAF=1): the leaf kernel as platform/
#                   lnk2_sh4.S's re4dc_line_leaf2: lnk_sh4.S's passes software-pipelined (the polygon two
#                   ahead's vertex / normal lines prefetched during a plane test, the next edge's lines during
#                   an edge test), every float operation and compare kept. =2 (check build): lnk_sh4.S runs
#                   first on each chunk (polyBit put back); survivors and polyBit compared ("LK2" lines).
GAME_LINE_LEAF2 ?= 0
ifneq ($(GAME_LINE_LEAF2),0)
ifeq ($(GAME_LINE_LEAF),0)
$(error GAME_LINE_LEAF2 needs GAME_LINE_LEAF=1)
endif
PLATFORM_OBJS += $(OBJDIR)/platform/lnk2_sh4.o
$(OBJDIR)/platform/lnk2_sh4.o: platform/lnk2_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
$(OBJDIR)/src/game/atari.o: GAME_CPPFLAGS += -DRE4DC_LINE_LEAF2=$(GAME_LINE_LEAF2)
endif
# GAME_LINE_WALK_PF=1 (G, collision traversal; exact; needs GAME_LINE_WALK=1): the line walk and piece entry
#                     from platform/lnw2_sh4.S: lnw_sh4.S's with three prefetches added (the next block's
#                     `next` line, an overlapped node's child's `next` line, the root's lines at a piece's
#                     start). =2 (check build): lnw_sh4.S also runs; leaves and ends compared ("LWP" lines).
GAME_LINE_WALK_PF ?= 0
ifneq ($(GAME_LINE_WALK_PF),0)
ifeq ($(GAME_LINE_WALK),0)
$(error GAME_LINE_WALK_PF needs GAME_LINE_WALK=1)
endif
PLATFORM_OBJS += $(OBJDIR)/platform/lnw2_sh4.o
$(OBJDIR)/platform/lnw2_sh4.o: platform/lnw2_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
ifneq ($(GAME_LINE_PIECE),0)
$(OBJDIR)/platform/lnw2_sh4.o: KOS_CFLAGS += -DRE4DC_LINE_PIECE=1
endif
$(OBJDIR)/src/game/atari.o: GAME_CPPFLAGS += -DRE4DC_LINE_WALK_PF=$(GAME_LINE_WALK_PF)
endif
# GAME_LINE_TAIL=1 (G, collision traversal; exact; needs GAME_LINE_LEAF=1): a leaf kernel survivor (it passed
#                  At_poly_line_ck's plane and edge tests with the same operations) runs At_poly_line_tail
#                  (at_sub.cpp): At_poly_line_ck from t on, dp0 and a recomputed as there, the same decision
#                  trace note. =2 (check build): At_poly_line_ck also runs and is compared ("LTL" lines).
GAME_LINE_TAIL ?= 0
ifneq ($(GAME_LINE_TAIL),0)
ifeq ($(GAME_LINE_LEAF),0)
$(error GAME_LINE_TAIL needs GAME_LINE_LEAF=1)
endif
$(OBJDIR)/src/game/atari.o: GAME_CPPFLAGS += -DRE4DC_LINE_TAIL=$(GAME_LINE_TAIL)
$(OBJDIR)/src/game/at_sub.o: GAME_CPPFLAGS += -DRE4DC_LINE_TAIL=$(GAME_LINE_TAIL)
endif
# GAME_SCEAT_LIST=1 (G, trigger areas; exact): the per-frame area walks (sceAtCheck_main per caller type,
#                   sceAtDataLoopInit, sceAtItemFindCheck, sceAtCamCtrlCheck, SceAtCheckFieldInfo,
#                   SceAtCheckMoveScrAt, sceAtLink_check) take a list of the ordering table's records passing
#                   their checkType / type filter (table order), rebuilt when the table changes (every AddPrim /
#                   DelPrim / ClearOTagR in sce_at.cpp bumps a generation); a body that changes the table sends
#                   its walk back to the table (sce_at.cpp). =2 (check build): every list step compared with
#                   the table walk ("SAL" lines).
GAME_SCEAT_LIST ?= 0
ifneq ($(GAME_SCEAT_LIST),0)
$(OBJDIR)/src/game/sce_at.o: GAME_CPPFLAGS += -DRE4DC_SCEAT_LIST=$(GAME_SCEAT_LIST)
endif
# GAME_WORKAT_INLINE=1 (the 30 fps rethink; port overhead, exact; needs OBJECT_DEMAND=1 ENEMY_DEMAND=1):
#                    the demand-backed cObj / cEm managers' workAt (parts_bridge.cpp: two out-of-line
#                    calls per lookup, ~3,700 lookups per square tick from EfmDelete, GetEmPtrFromList,
#                    em10SomebodyDamageNowCk and the manager scans) inline for the common case: no pool
#                    frozen for the sub screen, the room's own array, an index in range: the slot table.
#                    Every other case takes the bridge as before. A header knob (include/cManager.h).
GAME_WORKAT_INLINE ?= 0
ifneq ($(GAME_WORKAT_INLINE),0)
ifneq ($(OBJECT_DEMAND)$(ENEMY_DEMAND),11)
$(error GAME_WORKAT_INLINE needs OBJECT_DEMAND=1 ENEMY_DEMAND=1)
endif
GAME_CPPFLAGS += -DRE4DC_WORKAT_INLINE=$(GAME_WORKAT_INLINE)
PLATFORM_CPPFLAGS += -DRE4DC_WORKAT_INLINE=$(GAME_WORKAT_INLINE)
endif
# GAME_ESP_OWNER=1 (square plan: active effects): live esp slots counted per owner (info.Core_pEm)
#                    bucket, so EspDelete with an owner returns at once when that owner has no live
#                    slot (include/esp.h). A header knob (ESP_INFO_SET): every game object gets it.
#                    =2: every early return is checked by the slot loop ("ESPOWN" log line).
GAME_ESP_OWNER ?= 0
ifneq ($(GAME_ESP_OWNER),0)
GAME_CPPFLAGS += -DRE4DC_ESP_OWNER=$(GAME_ESP_OWNER)
endif
# GAME_FX_SCAN=1 (30 fps rethink, lane fx; exact; needs GAME_ESP_OWNER=1): slot maps so the per-tick
#                effect pool loops (the source loops) step over runs of slots their tests cannot pass,
#                re-reading the map at every step: EspMove (live esp slots), EspDelete with an owner (the
#                owner bucket's live slots), EspgenMove / EspgenTrans / EspgenDelete (occupied controllers),
#                EfmDelete (slots holding obj 4 / 5 / 9, listed once per ObjMgr alive-list generation;
#                with GAME_ATCHK_LIST=1 and GAME_WORKAT_INLINE=1, else the source loop). A header knob
#                (include/esp.h). =2: every skipped slot is tested as the source loop would test it and
#                counted, with the maps checked against the pools every tick ("FXS" lines).
GAME_FX_SCAN ?= 0
ifneq ($(GAME_FX_SCAN),0)
ifeq ($(GAME_ESP_OWNER),0)
$(error GAME_FX_SCAN needs GAME_ESP_OWNER=1)
endif
GAME_CPPFLAGS += -DRE4DC_FX_SCAN=$(GAME_FX_SCAN)
PLATFORM_CPPFLAGS += -DRE4DC_FX_SCAN=$(GAME_FX_SCAN)
endif
# GAME_FX_MOVE=1 (30 fps rethink, lane fx; exact): the effect base update (cEsp::CommonMove with its
#                ColorUpdate, cEsp::AnmMove) and cEsp48::move read and write their float fields through
#                walking pointers (fmov.s @Rm+ / @-Rn, include/esp.h FXL / FXS): the same operations on
#                the same operands in the same order, fewer address adds. A header knob (esp.h). =2: the
#                source runs live and the new code on a copy of the effect, compared field for field
#                ("FXM" / "FX48" lines; FX48 also counts sinf argument repeats).
GAME_FX_MOVE ?= 0
ifneq ($(GAME_FX_MOVE),0)
GAME_CPPFLAGS += -DRE4DC_FX_MOVE=$(GAME_FX_MOVE)
PLATFORM_CPPFLAGS += -DRE4DC_FX_MOVE=$(GAME_FX_MOVE)
endif
# GAME_OB_SCAN=1 (30 fps rethink, lane ob; exact): per-tick bookkeeping scans. cDmgMgr::hitCheck tests
#                the live damage volumes from the alive list in slot order instead of all 20 slots, and
#                cDmgMgr::move skips the dieCheck calls that can no longer change a work (dmg.cpp);
#                GetEmPtrFromList searches EmMgr's alive list (one match = the answer, else the source
#                loop; em_set.cpp); IDSystem::move runs level pass 0 as the source and lists the deeper
#                units it steps over, so passes 1..m_levelMax walk that list instead of every slot
#                (id_sys.cpp). No static data at =1 (the image's data layout does not move). =2: the
#                source runs live beside each fast answer and every difference is counted ("OBS" lines).
GAME_OB_SCAN ?= 0
ifneq ($(GAME_OB_SCAN),0)
$(OBJDIR)/src/game/dmg.o: GAME_CPPFLAGS += -DRE4DC_OB_SCAN=$(GAME_OB_SCAN)
$(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_OB_SCAN=$(GAME_OB_SCAN)
$(OBJDIR)/src/game/id_sys.o: GAME_CPPFLAGS += -DRE4DC_OB_SCAN=$(GAME_OB_SCAN)
endif
# GAME_OB_MAT=1 (30 fps rethink, lane ob; exact): idSysMove03 keeps l_mat / mat when the unit's rotation,
#               position and group parent's matrix are unchanged (versions in IdUnit pad_D8; no static
#               data at =1). =2: the source matrices are built beside every call and compared ("OBM").
GAME_OB_MAT ?= 0
ifneq ($(GAME_OB_MAT),0)
$(OBJDIR)/src/game/id_sys.o: GAME_CPPFLAGS += -DRE4DC_OB_MAT=$(GAME_OB_MAT)
endif
# GAME_OB_PATH=1 (30 fps rethink, lane ob; exact): idSysMove00's path points (FuncPathCalc) computed with
#                the same de_Boor_Cox arithmetic in stack arrays instead of 3 + n + m heap blocks per call
#                (the heap lists end each call as they started; id_sys.cpp). =2: both run, compared ("OBP").
GAME_OB_PATH ?= 0
ifneq ($(GAME_OB_PATH),0)
$(OBJDIR)/src/game/id_sys.o: GAME_CPPFLAGS += -DRE4DC_OB_PATH=$(GAME_OB_PATH)
endif
# GAME_OB_NEAR=1 (30 fps rethink, lane ob; exact): getNearPoint's ten-nearest insertion as one test-and-shift
#                loop (the source's tests in the same order) instead of the two memmove calls GCC made of
#                the shift per inserted point (route_ck.cpp). =2: the source selection runs beside it and
#                its answer is used; differences counted ("OBN").
GAME_OB_NEAR ?= 0
ifneq ($(GAME_OB_NEAR),0)
$(OBJDIR)/src/game/route_ck.o: GAME_CPPFLAGS += -DRE4DC_OB_NEAR=$(GAME_OB_NEAR)
endif
# GAME_OB_DECODE=1 (30 fps rethink, lane ob; exact): the effect record reader (platform/native_effect.cpp,
#                  built at -O1) read every word through a 4-byte memcpy library call: an aligned word is
#                  read in place, and decode() expands an aligned record with the three mask words held
#                  in registers (the same 75 output words in the same order). =2: the source expansion
#                  runs beside it into a second buffer and its output is used; differences counted ("OBD").
GAME_OB_DECODE ?= 0
ifneq ($(GAME_OB_DECODE),0)
$(OBJDIR)/platform/native_effect.o: PLATFORM_CPPFLAGS += -DRE4DC_OB_DECODE=$(GAME_OB_DECODE)
endif
# GAME_ROTVEC_MEMO=1 (square plan: collision body positions; exact): RotVector (sub2.cpp) keeps yaw-only
#                    results in 256 one-line entries keyed by the input bits (RVM_BITS=n: 2^n entries);
#                    cAtariInfo::getPos repeats it for every candidate body on each EmAtCheck call.
#                    =2: every hit recomputed and compared ("RVM" log line).
GAME_ROTVEC_MEMO ?= 0
# GAME_ID_LISTS=1 (30 fps rethink, R headroom; exact): IDSystem::trans builds each unit's child lists once
#                 and unitTrans walks them instead of rescanning the pool per queued unit (0x80 units of
#                 0x138 bytes, ~38 queued per tick). =2: the lists run dry beside the live scans and every
#                 queued sequence is compared ("IDL" lines).
GAME_ID_LISTS ?= 0
ifneq ($(GAME_ID_LISTS),0)
$(OBJDIR)/src/game/id_sys.o: GAME_CPPFLAGS += -DRE4DC_ID_LISTS=$(GAME_ID_LISTS)
endif
# GAME_OT_MASK=1 (R headroom; exact): per-table bits "took an entry" / "took a model entry" since the
#                table's clear (trans_ot.cpp); ExecOt returns at once for an empty table and the model-asset
#                walk (model_asset_bridge.cpp) skips tables without models. =2: both ways, compared ("OTM").
GAME_OT_MASK ?= 0
ifneq ($(GAME_OT_MASK),0)
GAME_CPPFLAGS += -DRE4DC_OT_MASK=$(GAME_OT_MASK)
PLATFORM_CPPFLAGS += -DRE4DC_OT_MASK=$(GAME_OT_MASK)
endif
# UI_HEAP_LAZY=N (R headroom): the native frame stats' source_heap_free (OSCheckHeap, a whole-heap walk,
#                ~0.12 hw ms) refreshes every Nth frame; nothing in the image reads it.
UI_HEAP_LAZY ?= 0
ifneq ($(UI_HEAP_LAZY),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_UI_HEAP_LAZY=$(UI_HEAP_LAZY)
endif
# UI_PALETTE_SLOTS=N (R headroom; exact; with UI_HANDLES=1): the indexed-image handles' palette copies are
#                N slots given out on demand (LRU) instead of 16 fixed to handle index % 16 (the HUD's
#                indexed images evicted each other: 6 full resolves per tick in the r101 square).
UI_PALETTE_SLOTS ?= 0
ifneq ($(UI_PALETTE_SLOTS),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_UI_PALETTE_SLOTS=$(UI_PALETTE_SLOTS)
endif
# UI_QUAD_LEAN=1 (make-room F1, HUD; exact): re4dc_ui_submit tests the 16 coordinates for Inf / NaN on their
#                exponent bits (was a __unordsf2 call and a compare per coordinate: ~320 calls per drawn tick in
#                the r101 square); re4dc_draw_id_quad projects its corners with GXProject's own x / y
#                expressions inline (same -O1 -ffp-contract=off flags; no call, no unused depth); the texture
#                handles are two-way (slot and slot ^ 1: two image pairs evicted each other every frame, 4 full
#                resolves per drawn tick). =2 check build: both ways, verdicts, x / y and entries compared
#                ("UQL fin" / "UQL xy" / "UQL handle" lines); =3 is =2 with the handles folded onto 8 slots
#                (a stress check of both ways and the refill choice).
# Controller-aware presentation only; source input and timing are untouched.
# Copy prompt headers to platform/include before enabling; default-off build
# must be object-compared before promotion. Manual art is separately gated.
PAD_PROMPTS ?= 0
PAD_PROMPT_MANUAL_ART ?= 0
ifneq ($(PAD_PROMPTS),0)
GAME_CPPFLAGS += -DRE4DC_PAD_PROMPTS=1
PLATFORM_CPPFLAGS += -DRE4DC_PAD_PROMPTS=1
ifneq ($(PAD_PROMPT_MANUAL_ART),0)
GAME_CPPFLAGS += -DRE4DC_PAD_PROMPT_MANUAL_ART=1
PLATFORM_CPPFLAGS += -DRE4DC_PAD_PROMPT_MANUAL_ART=1
endif
endif
UI_QUAD_LEAN ?= 0
ifneq ($(UI_QUAD_LEAN),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_UI_QUAD_LEAN=$(UI_QUAD_LEAN)
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_UI_QUAD_LEAN=$(UI_QUAD_LEAN)
endif
# LINK_ORDER=<file> (G; exact, code placement only): an ld --section-ordering-file that puts the hot
#                    input sections first in .text (tools/d367/ordgen_c3.py from hwproject evidence: call
#                    chains clustered to the 8 KB direct-mapped I-cache, placed by density). The r101-square
#                    order is link-order/r101-square-c3-8k.ld: never-draw work -1.25 hw ms (I-miss 4.67 ->
#                    3.74), every tick drawn -0.94, logic trace STRICT. Regenerate it after code changes
#                    (tools/d367/ordcheck.py measures how stale an order is): link-order/
#                    r21y-house-fight-square-c3-8k.ld is the r21y code's order from the r100-h-quiet,
#                    r100-h-fight and perf-r101sq cost windows (perf-20261004 presets; drawn / skipped tick
#                    hw ms vs the square order: house -1.00 / -0.16, fight -0.96 / -0.17, square -1.23 /
#                    -0.27; H2 logic trace STRICT). The old order covered 47-57% of those windows' hw ms, the
#                    new one 87-88% (all the placeable code).
LINK_ORDER ?=
# LINK_ORDER_FILE: the file ld reads, LINK_ORDER itself or a knob's derived copy (GAME_ROT_FSCA).
LINK_ORDER_FILE = $(LINK_ORDER)
ifneq ($(LINK_ORDER),)
GAME_LDFLAGS += -Wl,--section-ordering-file,$(abspath $(LINK_ORDER_FILE))
endif
# PACE_TRANS_SKIP=mask (private test knob): presentation stages skipped for a dropped image
# (1 EspTrans 2 EspgenTrans 4 CtrlMgr.trans 8 ShadowTrans 16 ClothDraw 32 FilterTrans 64 TexRender
#  128 IdSys.trans 256 DrawOTag(MainOt[4]) 512 cMes.Trans 1024 Render() on a skipped iteration).
PACE_TRANS_SKIP ?= 0
ifneq ($(PACE_TRANS_SKIP),0)
$(OBJDIR)/src/game/trans.o $(OBJDIR)/src/game/main.o $(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/espgen.o: GAME_CPPFLAGS += -DRE4DC_PACE_TRANS_SKIP=$(PACE_TRANS_SKIP)
endif
# COARSE=1 (30 fps rethink step 2; needs PACE_CATCHUP=2 and the qualified PACE_TRANS_SKIP=4063): in-room
#          play images are drawn by coarse.cpp from gameplay records (camera-opaque collision pieces,
#          part skeletons, live effects). Trans() runs such a tick's presentation stages as for a
#          dropped image, but a drawn one keeps TexRender (the HUD's render textures); Render() runs
#          OTs 0 / TEX_RENDER1, then the coarse view in place of the world OTs ("COARSE" log line every
#          120 images). =2: + camera / stream state and a screen-point probe (what covers the view).
COARSE ?= 0
# ACTOR_SWAP=1 (benchmark, version A; needs COARSE=0 COARSE_LEON=1 COARSE_GANADO=1): the old renderer's
#              ModelRender draws Leon and the Ganados through the COARSE_LEON / COARSE_GANADO adapters (the
#              reduced meshes, native actor submission) instead of their source infos, so old and new
#              renderers are timed with the same character models (actor_swap.cpp). Presentation only.
ACTOR_SWAP ?= 0
ifneq ($(ACTOR_SWAP),0)
ifneq ($(COARSE),0)
$(error ACTOR_SWAP is the version A (COARSE=0) twin of the coarse actor adapters)
endif
ifneq ($(COARSE_LEON)$(COARSE_GANADO),11)
$(error ACTOR_SWAP needs COARSE_LEON=1 COARSE_GANADO=1)
endif
PLATFORM_OBJS += $(OBJDIR)/actor_swap.o
$(OBJDIR)/actor_swap.o: actor_swap.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -MMD -MP -c $< -o $@
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_SWAP=1
endif
# COARSE_GANADO_CAST=1 (needs COARSE_GANADO=1; render only): the Ganados draw the external cast's
#                      per-appearance meshes (coarse_ganado_cast.cpp replaces coarse_ganado.cpp in the link):
#                      COARSE_ACTOR_ASSET_DIR is then a private bundle with ganado_cast_runtime.h (four chunks
#                      per appearance in the source info order, the appearance's inverse bind, the source
#                      infos' signatures, the atlas key), made outside the repository from the cast packs.
#                      An actor draws the appearance its body and head signatures name; any cast hand pose
#                      draws that appearance's default hand. =2: check build, the 874 matcher runs beside
#                      each attempt ("GCAST" lines: both / cast only / 874 only / neither, role mismatches).
COARSE_GANADO_CAST ?= 0
COARSE_GANADO_SRC := coarse_ganado.cpp
ifneq ($(COARSE_GANADO_CAST),0)
ifneq ($(COARSE_GANADO),1)
$(error COARSE_GANADO_CAST needs COARSE_GANADO=1)
endif
COARSE_GANADO_SRC := coarse_ganado_cast.cpp $(COARSE_ACTOR_ASSET_DIR)/ganado_cast_runtime.h
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_COARSE_GANADO_CAST=$(COARSE_GANADO_CAST)
endif
# COARSE_PREGATE=1 (needs COARSE_GANADO_CAST; render only): an actor-level cull ahead of the cast Ganado adapter's
#                  skin work (coarse_ganado_cast.cpp): a visible chunk whose every drawable position is provably
#                  outside one of the actor path's culling planes (a screen edge or far) is skipped before its
#                  bones, palettes and submission (so it sends no TA header). The bound: per chunk and bone, a
#                  ball around the positions the bone moves, from the chunk's own positions and weights at first
#                  use (no mesh change). The palette (fog) gate stays the final arbiter of every kept chunk.
#                  =2: check build, nothing is skipped and each chunk the gate would skip must emit no triangle
#                  (the frame owner's model_output; "COARSE_PREGATE" lines count violations, which must be 0).
COARSE_PREGATE ?= 0
ifneq ($(COARSE_PREGATE),0)
ifeq ($(COARSE_GANADO_CAST),0)
$(error COARSE_PREGATE needs COARSE_GANADO_CAST)
endif
# Only cast chunks are crowd-classed with COARSE=1 (a declined Ganado is drawn as coarse segments), so a wholly
# culled cast actor cannot change another actor's crowd tier; with ACTOR_SWAP / COARSE=0 it could.
ifneq ($(COARSE),1)
$(error COARSE_PREGATE needs COARSE=1: with ACTOR_SWAP / COARSE=0 a culled actor would change declined Ganados' crowd tiers)
endif
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_COARSE_PREGATE=$(COARSE_PREGATE)
ifeq ($(COARSE_PREGATE),2)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_COARSE_PREGATE=2
endif
endif
# Private live-Ganado experiment. Limit affects mesh presentation only; ACT_CAP remains 0.
COARSE_GANADO ?= 0
COARSE_GANADO_LIMIT ?= -1
ifneq ($(COARSE_GANADO),0)
ifeq ($(COARSE_LEON),0)
$(error COARSE_GANADO requires COARSE_LEON=1 for the shared hooks)
endif
PLATFORM_OBJS += $(OBJDIR)/coarse_ganado.o
$(OBJDIR)/coarse.o $(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_COARSE_GANADO=1
# COARSE_FREEZE_AT=N (diagnostic, captures only): the CPU stops in frame N's actor pass (frame N-1 stays on screen)
COARSE_FREEZE_AT ?= 0
ifneq ($(COARSE_FREEZE_AT),0)
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_COARSE_FREEZE_AT=$(COARSE_FREEZE_AT)
endif
$(OBJDIR)/coarse_ganado.o: $(COARSE_GANADO_SRC) $(COARSE_ACTOR_ASSET_DIR)/ganado874_runtime.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -DRE4DC_COARSE_GANADO_LIMIT=$(COARSE_GANADO_LIMIT) -I$(COARSE_ACTOR_ASSET_DIR) -MMD -MP -c $< -o $@
endif
# Private 4K Leon proof through the existing actor path; generated assets stay outside Git.
COARSE_LEON ?= 0
ifneq ($(COARSE_LEON),0)
ifeq ($(COARSE)$(ACTOR_SWAP),00)
$(error COARSE_LEON requires COARSE (or ACTOR_SWAP=1, the version A benchmark))
endif
ifneq ($(NATIVE_ACTOR_FAST)$(NATIVE_ACTOR_SKIN_LAZY),11)
$(error COARSE_LEON requires NATIVE_ACTOR_FAST=1 NATIVE_ACTOR_SKIN_LAZY=1)
endif
ifndef COARSE_ACTOR_ASSET_DIR
$(error COARSE_ACTOR_ASSET_DIR must point at the private qualified asset)
endif
PLATFORM_OBJS += $(OBJDIR)/coarse_actor.o
$(OBJDIR)/coarse.o $(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_COARSE_LEON=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_COARSE_LEON=1
$(OBJDIR)/coarse_actor.o: coarse_actor.cpp $(COARSE_ACTOR_ASSET_DIR)/leon4k_runtime.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -I$(COARSE_ACTOR_ASSET_DIR) -MMD -MP -c $< -o $@
endif
# CHAR_DATA_BLOCK=1 (needs COARSE_LEON=1; layout only): the character adapters' data (every .rodata, .data and
#                   .bss input section of coarse_actor.o and coarse_ganado.o: the private meshes, palettes,
#                   weights and bind tables and the adapters' own state) is linked as one block after .data,
#                   padded so that what follows moves by whole 16 KiB (platform/char_data_block.ld). The game's
#                   .rodata and .data keep the addresses they have without character data, and its .bss the
#                   same operand-cache sets, whatever the cast's size. Costs up to 16 KiB of image (heap 4).
CHAR_DATA_BLOCK ?= 0
ifneq ($(CHAR_DATA_BLOCK),0)
ifneq ($(COARSE_LEON),1)
$(error CHAR_DATA_BLOCK needs COARSE_LEON=1)
endif
GAME_LDFLAGS += -Wl,-T,platform/char_data_block.ld
endif
# COARSE_SKIN_FTRV=1 (coarse actor adapters, render-only): palette matrices with FTRV (coarse_skin_sh4.S):
#                    T = root^-1 x part x bind^-1 for the bones the palettes use (two FTRV passes), each
#                    palette entry the weighted sum of its bones' T (three FTRVs; one-bone entries copied)
#                    instead of 2 PSMTXConcat per bone and the scalar weight loop. =2 check build: the C
#                    path runs too and COARSE_SKIN_CHK logs the largest difference.
COARSE_SKIN_FTRV ?= 0
ifneq ($(COARSE_SKIN_FTRV),0)
ifneq ($(COARSE_LEON),1)
$(error COARSE_SKIN_FTRV needs COARSE_LEON=1)
endif
PLATFORM_OBJS += $(OBJDIR)/coarse_skin_sh4.o
$(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_COARSE_SKIN_FTRV=$(COARSE_SKIN_FTRV)
$(OBJDIR)/coarse_skin_sh4.o: coarse_skin_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
endif
# COARSE_ONE_SUBMIT=1 (needs COARSE_LEON=1, NATIVE_ACTOR_DIRECT=1, NATIVE_ACTOR_UV16=0, TA_GUARD=0; render only): one
#                    submission per coarse actor. coarse_actor.cpp and coarse_ganado_cast.cpp hand the visible chunks
#                    to re4dc_actor_submit_chunks (platform/native_actor_fast.cpp) in groups whose palettes fit the
#                    adapter's buffer together (Leon 8 -> 3, a cast Ganado 4 -> 1); a group's chunks share one TA
#                    header. Each chunk keeps re4dc_actor_submit's steps, order and state effects; the TA stream
#                    loses only the repeated headers. =2: check build, every chunk also goes through
#                    re4dc_actor_submit first and both paths' TA words are compared ("C3CHK" lines: word, header and
#                    result mismatches must stay 0; the image draws each chunk twice).
COARSE_ONE_SUBMIT ?= 0
ifneq ($(COARSE_ONE_SUBMIT),0)
ifneq ($(COARSE_LEON),1)
$(error COARSE_ONE_SUBMIT needs COARSE_LEON=1)
endif
ifeq ($(COARSE_PREGATE),2)
$(error COARSE_ONE_SUBMIT: COARSE_PREGATE=2 counts output around each chunk's own submission (use 0 or 1))
endif
$(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_COARSE_ONE_SUBMIT=$(COARSE_ONE_SUBMIT)
$(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_COARSE_ONE_SUBMIT=$(COARSE_ONE_SUBMIT)
# native_ui.cpp's re4dc_model_direct_begin_reserved (the frame owner's hunk): without it the call would link to a silent stub.
ifeq ($(shell grep -c re4dc_model_direct_begin_reserved platform/native_ui.cpp),0)
$(error COARSE_ONE_SUBMIT needs native_ui.cpp's re4dc_model_direct_begin_reserved)
endif
endif
# COARSE_GATE_ONCE=1 (needs COARSE_ONE_SUBMIT, ACTOR_VTX_KERNEL, ACTOR_FOG_GATE=1; render only, exact): the coarse
#                   characters' gates decide the same and send the same words with less work. In
#                   re4dc_actor_submit_chunks the fog gate keeps a chunk whose first palette entry already proves it
#                   (its entry loop runs only otherwise).
#                   With COARSE_PREGATE=1 the cast Ganado pregate rebuilds its view constants only when the
#                   projection changes, builds one gate matrix per actor when the chunks' info matrices agree (word
#                   for word), evaluates only the undecided planes of a ball and its radius term only when the centre
#                   leaves one open, and takes the scale from the symmetric Gram. =2: check build, the previous paths
#                   run beside ("GATE1CHK" / "GATE1 PREGATE" lines; mismatches and proof_cull stay 0).
COARSE_GATE_ONCE ?= 0
ifneq ($(COARSE_GATE_ONCE),0)
ifeq ($(COARSE_ONE_SUBMIT),0)
$(error COARSE_GATE_ONCE needs COARSE_ONE_SUBMIT)
endif
ifeq ($(filter-out 0,$(ACTOR_VTX_KERNEL)),)
$(error COARSE_GATE_ONCE needs ACTOR_VTX_KERNEL (the kernel's fog gate loop))
endif
ifneq ($(ACTOR_FOG_GATE),1)
$(error COARSE_GATE_ONCE needs ACTOR_FOG_GATE=1)
endif
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_COARSE_GATE_ONCE=$(COARSE_GATE_ONCE)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_COARSE_GATE_ONCE=$(COARSE_GATE_ONCE)
endif
ifneq ($(COARSE),0)
ifneq ($(PACE_CATCHUP),2)
$(error COARSE needs PACE_CATCHUP=2 and PACE_TRANS_SKIP (the qualified mask 4063))
endif
ifeq ($(PACE_TRANS_SKIP),0)
$(error COARSE needs PACE_CATCHUP=2 and PACE_TRANS_SKIP (the qualified mask 4063))
endif
PLATFORM_OBJS += $(OBJDIR)/coarse.o
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_COARSE=$(COARSE)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_COARSE=$(COARSE)
$(OBJDIR)/coarse.o: coarse.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -DRE4DC_COARSE=$(COARSE) -MMD -MP -c $< -o $@
endif
# COARSE_NO_STD_SCENERY=1 (heap-4 reclaim, render-only; only with COARSE=1 and COARSE_WORLD set, below): in the
#   room the coarse world draws (coarse_world.h kRoom) native_static.cpp bind_mesh() neither opens nor binds the
#   room's scenery mesh package (r101 Standard: low/MAINSCENARIO.re4mesh, 599,328 B of heap 4). No coarse image
#   reads it: a coarse tick runs no ModelTrans and its Render() draws the coarse view in place of the world OTs.
#   Objects, collision and game state are unchanged (the bind returns nothing to the game). An image the coarse
#   path does not draw in that room (outside in-room play: door demo, death, continue) draws its scroll parts
#   through the generic path (a released part has no GX stream: nothing). "native mesh: no-std" log lines: the
#   heap-4 free where the package would have opened, and a census of its readers on coarse and other images.
COARSE_NO_STD_SCENERY ?= 0
ifneq ($(COARSE_NO_STD_SCENERY),0)
ifneq ($(COARSE_NO_STD_SCENERY),1)
$(error COARSE_NO_STD_SCENERY is 0 or 1)
endif
ifneq ($(COARSE),1)
$(error COARSE_NO_STD_SCENERY needs COARSE=1: coarse images draw every in-room image of the room)
endif
ifeq ($(filter-out 0,$(strip $(COARSE_WORLD))),)
$(error COARSE_NO_STD_SCENERY needs COARSE_WORLD: the coarse world draws the room in place of the scenery package)
endif
ifneq ($(NATIVE_STATIC),1)
$(error COARSE_NO_STD_SCENERY needs NATIVE_STATIC=1 (the scenery package it skips))
endif
ifneq ($(NATIVE_MESH),1)
$(error COARSE_NO_STD_SCENERY needs NATIVE_MESH=1 (the scenery package it skips))
endif
# Only the top-of-heap package layout (NATIVE_PKG_HIGH=1) is gated STRICT without the package: with the low layout
# every later source heap-4 allocation of the room would move down by the package's cell.
ifneq ($(NATIVE_PKG_HIGH),1)
$(error COARSE_NO_STD_SCENERY needs NATIVE_PKG_HIGH=1 (the only layout gated without the package))
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_NO_STD_SCENERY=1
$(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_NO_STD_SCENERY=1
endif
# COARSE_WORLD=bits (lane wd, test; needs COARSE=1): the coarse view's world beyond
#   the flat collision (coarse_world.cpp; data in the generated private coarse_world.h, textures staged with
#   EXTRA_TEXDIRS). 1: house shells (every house BIN of the room as its baked 128 VQ render shell, the
#   face light in the texture, in place of the collision polygons of its outer surfaces). 2: ground (the
#   floors under the source ground as 3.2 m cells coloured from it with a grey detail texture, in place of
#   those floors). 4: sky (the room's dome, unfogged, fading into the fog colour at the horizon; the PVR
#   background takes the fog colour, native_static FOG_BACKGROUND). 8: trees (the Standard impostor records
#   as their atlas quads in the punch-through list; needs TREE_IMPOSTOR=1).
#   Bits 16-128 read a layout-11 header (kWorldLayout = 11; the world agent's binary contract,
#   re4-assets-private world-agent-20260926 from-main\renderer-contract.md); with them off the build is as before.
#   16: R1 (+R6) mesh records (kMesh*, kSkipMesh): a mode byte per record (repeat, fog, cull or both sides,
#   16- or 32-bit UVs, an ARGB per strip vertex), drawn after the shells; reserved-mode (R2) records are
#   skipped and counted as rejects. 32: R7 backdrop segments (kBackdrop*, kSkipBackdrop): up to 16 textured
#   bands after the sky and before the ground, fading into the fog colour as the sky, world-fixed or following
#   the eye; with segments the sky dome writes no depth, so it never hides a band. 64: R3 world texture preload
#   (kWorldTex): the room-entry preload adds the listed keys in the data's room after its other passes, within
#   BUDGET.md revision 2's caps (16 new keys, 84,448 B of new VRAM per visit, at the packages' real sizes)
#   ("COARSE world tex" log line; needs TEX_RESIDENT=1). 128: K0: the coarse view does not walk piece 0
#   (its drawing only; collision is untouched) when the data covers every piece-0 polygon (kCover full); the
#   build fails on partial coverage or on a non-empty skip set whose bit is off. Any of bits 16-128 builds the
#   whole header through the data gate in coarse_world.cpp (static_asserts: ranges, sizes, layouts).
COARSE_WORLD ?= 0
ifneq ($(COARSE_WORLD),0)
ifeq ($(COARSE),0)
$(error COARSE_WORLD needs COARSE=1)
endif
PLATFORM_OBJS += $(OBJDIR)/coarse_world.o
$(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_COARSE_WORLD=$(COARSE_WORLD)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_COARSE_WORLD=$(COARSE_WORLD)
$(OBJDIR)/coarse_world.o: coarse_world.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -DRE4DC_COARSE=$(COARSE) -DRE4DC_COARSE_WORLD=$(COARSE_WORLD) -MMD -MP -c $< -o $@
ifneq ($(shell echo $$(( $(COARSE_WORLD) & 4 ))),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_FOG_BACKGROUND=1
endif
ifneq ($(shell echo $$(( $(COARSE_WORLD) & 8 ))),0)
ifneq ($(TREE_IMPOSTOR),1)
$(error COARSE_WORLD bit 8 (trees) needs TREE_IMPOSTOR=1 (the punch-through list, re4dc_model_pt_begin))
endif
endif
ifneq ($(shell echo $$(( $(COARSE_WORLD) & 64 ))),0)
ifneq ($(TEX_RESIDENT),1)
$(error COARSE_WORLD bit 64 (R3 world texture preload) needs TEX_RESIDENT=1 (the room-entry preload))
endif
endif
endif
ifneq ($(GAME_ROTVEC_MEMO),0)
$(OBJDIR)/src/game/sub2.o: GAME_CPPFLAGS += -DRE4DC_ROTVEC_MEMO=$(GAME_ROTVEC_MEMO) $(if $(RVM_BITS),-DRE4DC_RVM_BITS=$(RVM_BITS))
endif
# GAME_DECISION_TRACE=1 (test builds, with LOGIC_TRACE=1): per sample, hashes of the em-em collision
#                    results (pair order included), the scenery line tests, the area checks and the damage hit
#                    tests, in call order ("LX"), plus every alive enemy's position bits every 4th sample
#                    ("LP"): the decision-level comparison for last-bit FP changes.
GAME_DECISION_TRACE ?= 0
ifneq ($(GAME_DECISION_TRACE),0)
GAME_CPPFLAGS += -DRE4DC_DECISION_TRACE=$(GAME_DECISION_TRACE)
PLATFORM_CPPFLAGS += -DRE4DC_DECISION_TRACE=$(GAME_DECISION_TRACE)
endif
# GAME_SKEL_FTRV=1 (square plan: one gameplay matrix chain; last-bit FP policy, NOT exact): inside
#                    cEm10::move (the Ganados' whole update) partsWorldCalc runs each part's concat
#                    through FTRV from a table of this call's parent matrices (model.cpp).
#                    =2: check build, the FTRV pass runs in shadow and is compared with the live
#                    original ("SKELFTRV" log line; logic trace STRICT).
GAME_SKEL_FTRV ?= 0
ifneq ($(GAME_SKEL_FTRV),0)
GAME_CPPFLAGS += -DRE4DC_SKEL_FTRV=$(GAME_SKEL_FTRV)
endif
# GAME_PWC_KERNEL=1 (the 30 fps rethink, step 2; exact twin of GAME_SKEL_FTRV=1's live loop): the
#                    Ganados' part-world pass as one streaming SH-4 loop (platform/pwc_sh4.S: @Rn+ /
#                    @-Rn addressing, inverse scales once per distinct parent scale; the same FP operations
#                    on the same operands). =2: check build, the kernel pass runs first, then skelPass
#                    recomputes live and every mat / world / r_scale word is compared ("PWCK" log line).
#                    =3: every model's part-world pass on the kernel (Leon and objects move from the library
#                    path to FTRV: last-bit FP policy, decisions compared with GAME_DECISION_TRACE).
GAME_PWC_KERNEL ?= 0
ifneq ($(GAME_PWC_KERNEL),0)
ifneq ($(GAME_SKEL_FTRV),1)
$(error GAME_PWC_KERNEL needs GAME_SKEL_FTRV=1)
endif
PLATFORM_OBJS += $(OBJDIR)/platform/pwc_sh4.o
$(OBJDIR)/platform/pwc_sh4.o: platform/pwc_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
$(OBJDIR)/src/game/model.o: GAME_CPPFLAGS += -DRE4DC_PWC_KERNEL=$(GAME_PWC_KERNEL)
endif
# GAME_ROT_FSCA=1 (lane fm 2026-10-05; last-bit FP policy, NOT exact; needs GAME_PMC_KERNEL=1 and
#                    GAME_FP_CONTRACT=off): platform/pmc_fsca_sh4.S replaces pmc_sh4.S as re4dc_pmc_run and runs
#                    every part of cModel::partsMatCalc (no memo, no miss path) as one hand-scheduled SH-4 loop:
#                    the three angles' sin / cos from FSCA plus a residual correction (platform/include/
#                    re4dc_fsca.h; |x| < 2^-27 exact, |x| > 2 pi or NaN: the part through the C twin with
#                    re4dc_sincosf), then RotMatrix's products, the scale products, pos and the copy to mat as
#                    before, the next part's lines fetched with PREF meanwhile. Bit-identical to the C twin
#                    (platform/pmc_fsca.c). The local matrices (and so the skeleton the renderer reads) differ
#                    in the last bits. =2: check build, every part recomputed by the C twin (all 24 stored words
#                    must match) and with the exact sin / cos (differences counted; "ROTF" log lines). Host
#                    check of the sin / cos: tools/game30/trig_fsca_check.sh. With LINK_ORDER the kernel takes
#                    pmc_sh4.o's place in the order (ld reads a copy with that line renamed): left out of the
#                    order, it lands in the unordered tail and the ordered hot code after the slot moves 228
#                    bytes down. Regenerate the order (tools/d367/ordgen_c3.py) when landing it.
GAME_ROT_FSCA ?= 0
ifneq ($(GAME_ROT_FSCA),0)
ifneq ($(GAME_PMC_KERNEL),1)
$(error GAME_ROT_FSCA replaces the GAME_PMC_KERNEL loop: needs GAME_PMC_KERNEL=1)
endif
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_ROT_FSCA mirrors the contract-off RotMatrix / ScaleMatrix products: needs GAME_FP_CONTRACT=off)
endif
ifneq ($(LINK_ORDER),)
LINK_ORDER_FILE = $(OBJDIR)/link-order-rot-fsca.ld
$(OBJDIR)/link-order-rot-fsca.ld: $(LINK_ORDER)
	@mkdir -p $(dir $@)
	sed 's/\*pmc_sh4\.o(\.text)/*pmc_fsca_sh4.o(.text)/' $< > $@
$(TARGET): $(OBJDIR)/link-order-rot-fsca.ld
endif
$(OBJDIR)/platform/pmc_fsca.o: platform/pmc_fsca.c
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -w $(GAME_OPT) -O2 -ffp-contract=off $(GAME30_DECOMP_SAFE) -DRE4DC_ROT_FSCA=$(GAME_ROT_FSCA) -MMD -MP -c $< -o $@
$(OBJDIR)/platform/pmc_fsca_sh4.o: platform/pmc_fsca_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -DRE4DC_ROT_FSCA=$(GAME_ROT_FSCA) -c $< -o $@
endif
# GAME_PMC_KERNEL=1 (the 30 fps rethink, step 2; exact): cModel::partsMatCalc's parts whose rotation is in
#                    RotMatrix's memo (GAME_ROT_CACHE) as one streaming SH-4 loop (platform/pmc_sh4.S: the
#                    memo words, pos, the scale products and the copy to mat, stored with @-Rn); a memo miss
#                    takes the original four calls. Needs GAME_ROT_CACHE=1.
GAME_PMC_KERNEL ?= 0
ifneq ($(GAME_PMC_KERNEL),0)
ifneq ($(GAME_ROT_CACHE),1)
$(error GAME_PMC_KERNEL needs GAME_ROT_CACHE=1)
endif
ifeq ($(GAME_ROT_FSCA),0)
PLATFORM_OBJS += $(OBJDIR)/platform/pmc_sh4.o
else
PLATFORM_OBJS += $(OBJDIR)/platform/pmc_fsca.o $(OBJDIR)/platform/pmc_fsca_sh4.o
endif
$(OBJDIR)/platform/pmc_sh4.o: platform/pmc_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
$(OBJDIR)/src/game/model.o $(OBJDIR)/src/game/math_sub.o: GAME_CPPFLAGS += -DRE4DC_PMC_KERNEL=$(GAME_PMC_KERNEL)
endif
# GAME_HERMITE_FAST=1 (the 30 fps rethink, step 2; exact): HermiteInterpolation (motion.cpp, every key
#                    stream evaluation) as a restructured twin: the common key layouts (5, 0, 6, 10) decoded
#                    inline with the same conversions, the hermite blend inline (same expression), the axis
#                    stride from a table; the search, history and persistence of f0 / f1 / val / tan across
#                    axes unchanged. =2: check build, the original runs first on a copy of the history and
#                    every output word, history slot and return value is compared ("HERMF" log line).
GAME_HERMITE_FAST ?= 0
ifneq ($(GAME_HERMITE_FAST),0)
$(OBJDIR)/src/game/motion.o: GAME_CPPFLAGS += -DRE4DC_HERMITE_FAST=$(GAME_HERMITE_FAST)
endif
# ---- lane gskel (skeleton / animation / cloth / math library; arm prefix sk) ----
# GAME_LIGHT_LAZY=1 (G -> drawn frames; exact): cLightInfo::updateMatrix keeps its inputs in imat and
#                   marks the info; imat's only reader (lightHitCheckBBox: light selection for drawing)
#                   materializes it with the original arithmetic (lightInfo.cpp, light.cpp).
#                   =2: check build, the original also runs into a side table at every call and every
#                   materialization is compared word for word ("LLZ" log line).
GAME_LIGHT_LAZY ?= 0
ifneq ($(GAME_LIGHT_LAZY),0)
$(OBJDIR)/src/game/lightInfo.o $(OBJDIR)/src/game/light.o: GAME_CPPFLAGS += -DRE4DC_LIGHT_LAZY=$(GAME_LIGHT_LAZY)
endif
# GAME_FP_SCHED=1 (exact): GCC's pre-register-allocation scheduler (sched1, register-pressure aware) on
#                 this lane's FP code (motion, math_sub, IK, cloth, RotVector, the SDK matrix / quaternion /
#                 vector units, the trig file and the fdlibm cores). sched1 runs after combine and only
#                 orders instructions (independent chains interleave, e.g. sinf's and cosf's Horner
#                 polynomials), so every FP operation is the reference build's.
GAME_FP_SCHED ?= 0
SK_SCHED_FLAGS = -fschedule-insns -fsched-pressure
ifneq ($(GAME_FP_SCHED),0)
$(OBJDIR)/src/game/motion.o $(OBJDIR)/src/game/math_sub.o $(OBJDIR)/src/game/ik.o $(OBJDIR)/src/game/pendulum.o \
	$(OBJDIR)/src/game/pl_cloth.o $(OBJDIR)/src/game/sub2.o: GAME_CPPFLAGS += $(SK_SCHED_FLAGS)
$(OBJDIR)/platform/mtx.o: PLATFORM_CPPFLAGS += $(SK_SCHED_FLAGS)
$(OBJDIR)/sdk/mtx.o $(OBJDIR)/sdk/quat.o $(OBJDIR)/sdk/vec.o: SDK_CFLAGS += $(SK_SCHED_FLAGS)
$(OBJDIR)/game30_trig.o: KOS_CFLAGS += $(SK_SCHED_FLAGS)
$(OBJDIR)/fdlibm/%.o: KOS_CFLAGS += $(SK_SCHED_FLAGS)
endif
# GAME_HF_INLINE=1 (exact; with GAME_HERMITE_FAST): hfGet inline at its three sites in hermiteFast.
GAME_HF_INLINE ?= 0
ifneq ($(GAME_HF_INLINE),0)
$(OBJDIR)/src/game/motion.o: GAME_CPPFLAGS += -DRE4DC_HF_INLINE=$(GAME_HF_INLINE)
endif
# GAME_HF_PF=1 (exact; with GAME_HERMITE_FAST): PREFs of the next axis' key header (hermiteFast) and of the next
#              joint's first key header (MotionMoveCore): those demand loads missed on nearly every axis.
GAME_HF_PF ?= 0
ifneq ($(GAME_HF_PF),0)
ifeq ($(GAME_HERMITE_FAST),0)
$(error GAME_HF_PF needs GAME_HERMITE_FAST)
endif
$(OBJDIR)/src/game/motion.o: GAME_CPPFLAGS += -DRE4DC_HF_PF=$(GAME_HF_PF)
endif
# GAME_PWC_SCHED=1 (exact; with GAME_PWC_KERNEL): pwc_sh4.S's part-world loop rescheduled for the SH-4
#                  pipeline (r_scale first in the back bank, loads ahead of their fmuls, FTRV rows stored as
#                  they arrive); every FP operation and operand role is the original's.
# GAME_PWC_PF=1 (exact; with GAME_PWC_SCHED): each part prefetches the next part's lines at exact field
#                  addresses (flags, pList, mat / l_mat / pParent / world, scale / r_scale).
GAME_PWC_SCHED ?= 0
GAME_PWC_PF ?= 0
ifneq ($(GAME_PWC_SCHED),0)
ifeq ($(GAME_PWC_KERNEL),0)
$(error GAME_PWC_SCHED needs GAME_PWC_KERNEL)
endif
$(OBJDIR)/platform/pwc_sh4.o: KOS_CFLAGS += -DRE4DC_PWC_SCHED=$(GAME_PWC_SCHED)
endif
ifneq ($(GAME_PWC_PF),0)
ifeq ($(GAME_PWC_SCHED),0)
$(error GAME_PWC_PF needs GAME_PWC_SCHED)
endif
$(OBJDIR)/platform/pwc_sh4.o: KOS_CFLAGS += -DRE4DC_PWC_PF=$(GAME_PWC_PF)
endif
# GAME_TRIG_LEAN=1 (exact; acts with GAME_TRIG=1): game30_trig.c's sinf / cosf / re4dc_sincosf as leaf
#                  functions of the same operations (word moves through FPUL, large / non-finite arguments
#                  in separate functions, one kernel pick per quadrant); all 2^32 inputs checked on the host
#                  (tools/game30/trig_lean_exhaustive.sh).
GAME_TRIG_LEAN ?= 0
ifneq ($(GAME_TRIG_LEAN),0)
$(OBJDIR)/game30_trig.o: KOS_CFLAGS += -DRE4DC_TRIG_LEAN=$(GAME_TRIG_LEAN)
endif
# GAME_TRIG_FSCA=1 (lane fm 2026-10-05; last-bit FP policy, NOT exact; needs GAME_TRIG=1, GAME_TRIG_LEAN=1 and
#                  GAME_SINCOS=1): re4dc_sincosf (RotMatrix, PSMTXRotRad, PSMTXRotAxisRad) takes sin / cos from
#                  FSCA plus a residual correction (platform/include/re4dc_fsca.h): |x| <= 2 pi directly,
#                  |x| <= 2^7 pi/2 after the exact reduction; |x| < 2^-27, larger and non-finite arguments
#                  exact. sinf / cosf stay exact. =2: check build, the exact results beside every call,
#                  differences counted ("TRIGF" log lines). Host check: tools/game30/trig_fsca_check.sh.
#                  =1 with GAME_ROT_FSCA (the parts off the memo): RotMatrix also drops GAME_ROT_CACHE's memo and
#                  computes directly with the FSCA core inline (math_sub.cpp; the same words as through re4dc_sincosf;
#                  =2 keeps the memo path, whose misses go through the checked re4dc_sincosf).
GAME_TRIG_FSCA ?= 0
ifneq ($(GAME_TRIG_FSCA),0)
ifneq ($(GAME_TRIG_LEAN)$(GAME_SINCOS),11)
$(error GAME_TRIG_FSCA replaces the lean re4dc_sincosf: needs GAME_TRIG_LEAN=1 and GAME_SINCOS=1)
endif
$(OBJDIR)/game30_trig.o $(OBJDIR)/platform/pmc_fsca.o: KOS_CFLAGS += -DRE4DC_TRIG_FSCA=$(GAME_TRIG_FSCA)
ifeq ($(GAME_TRIG_FSCA),1)
ifneq ($(GAME_ROT_FSCA),0)
$(OBJDIR)/src/game/math_sub.o: GAME_CPPFLAGS += -DRE4DC_TRIG_FSCA_ROT=1
endif
endif
endif
# GAME_ACOS_LEAN=1 (exact; acts with GAME_FDLIBM=1): acosf / asinf (ef_acos.c, ef_asin.c) built
#                  -fno-math-errno, so their sqrtf is the bare fsqrt without the errno guard (a libgcc
#                  __unordsf2 call per acosf, ~0.1 ms / tick, mostly I-cache misses). The guard's other
#                  path is unreachable there: both square roots take (1 -/+ x) * 0.5 with 0.5 <= |x| < 1,
#                  so the argument lies in (0, 0.25] and the result is fsqrt's either way.
GAME_ACOS_LEAN ?= 0
ifneq ($(GAME_ACOS_LEAN),0)
$(OBJDIR)/fdlibm/ef_acos.o $(OBJDIR)/fdlibm/ef_asin.o: KOS_CFLAGS += -fno-math-errno
endif
# GAME_VEC_NORM_INLINE=1 (exact): PSVECNormalize inline (C_VECNormalize's body) in the cloth unit, the
#                 orientation builders and C_MTXRotAxisRad (include/vec.h, sdk mtx.c). =2: each call
#                 compared with C_VECNormalize ("VNRM").
GAME_VEC_NORM_INLINE ?= 0
ifneq ($(GAME_VEC_NORM_INLINE),0)
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_VEC_NORM_INLINE inlines the contract-off normalize body: needs GAME_FP_CONTRACT=off)
endif
$(OBJDIR)/src/game/pendulum.o $(OBJDIR)/src/game/math_sub.o: GAME_CPPFLAGS += -DRE4DC_VEC_NORM_INLINE=$(GAME_VEC_NORM_INLINE)
$(OBJDIR)/sdk/mtx.o: SDK_CFLAGS += -DRE4DC_VEC_NORM_INLINE=$(GAME_VEC_NORM_INLINE)
$(OBJDIR)/platform/mtx.o: PLATFORM_CPPFLAGS += -DRE4DC_VEC_NORM_INLINE=$(GAME_VEC_NORM_INLINE)
endif
# GAME_MTXINV_SCHED=1 (exact; with GAME_SH4_MATH=1 and GAME_FP_CONTRACT=off): PSMTXInverse's hand-written
#                 body (platform/mtx_sh4.S) list-scheduled: the same instructions on the same operands as
#                 the RE4DC_FP_CONTRACT_OFF body, in dual-issue order (tools/game30/mtx_inverse_sched.py;
#                 proof tools/game30/prove_mtxinv_sched.sh: fpsym2 --strict vs the old body).
GAME_MTXINV_SCHED ?= 0
ifneq ($(GAME_MTXINV_SCHED),0)
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_MTXINV_SCHED schedules the contract-off PSMTXInverse body: needs GAME_FP_CONTRACT=off)
endif
ifneq ($(GAME_SH4_MATH),1)
$(error GAME_MTXINV_SCHED schedules platform/mtx_sh4.S's body: needs GAME_SH4_MATH=1)
endif
$(OBJDIR)/platform/mtx_sh4.o: KOS_CFLAGS += -DRE4DC_MTXINV_SCHED=1
endif
# ---- end lane gskel ----
# GAME_COL_PREFETCH=1: the scenery collision walks (block chains, block polygon lists) prefetch the next
#                    block and the next polygon's record, vertex and normal. Loads only: same answers.
GAME_COL_PREFETCH ?= 0
ifeq ($(GAME_COL_PREFETCH),1)
$(OBJDIR)/src/game/atari.o: GAME_CPPFLAGS += -DRE4DC_COL_PREFETCH=1
endif

ifeq ($(LOGIC_TRACE),1)
PLATFORM_OBJS += $(OBJDIR)/logic_trace.o
# One uninterruptible append per re4dc_log call (platform/mem.cpp), so other threads' log lines
# cannot cut into a trace line. Trace builds only: release mem.o is unchanged.
$(OBJDIR)/platform/mem.o: PLATFORM_CPPFLAGS += -DRE4DC_LOG_ATOMIC=1
$(OBJDIR)/src/game/main.o $(OBJDIR)/src/game/rnd.o: GAME_CPPFLAGS += -DRE4DC_LOGIC_TRACE=1
$(OBJDIR)/logic_trace.o: logic_trace.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -DRE4DC_LOGIC_TRACE=1 -DRE4DC_LOGIC_TRACE_DELAY_US=$(LOGIC_TRACE_DELAY_US) -DRE4DC_LOGIC_TRACE_MASK_RENDER=$(LOGIC_TRACE_MASK_RENDER) $(if $(filter-out 0,$(LOGIC_TRACE_OBJ_TO)),-DRE4DC_LOGIC_TRACE_OBJ_FROM=$(LOGIC_TRACE_OBJ_FROM) -DRE4DC_LOGIC_TRACE_OBJ_TO=$(LOGIC_TRACE_OBJ_TO)) $(if $(filter-out 0,$(LOGIC_TRACE_EM_TO)),-DRE4DC_LOGIC_TRACE_EM_FROM=$(LOGIC_TRACE_EM_FROM) -DRE4DC_LOGIC_TRACE_EM_TO=$(LOGIC_TRACE_EM_TO)) -MMD -MP -c $< -o $@
endif

ifneq ($(GAME_TICK_LOG),0)
PLATFORM_OBJS += $(OBJDIR)/tick_log.o
$(OBJDIR)/src/game/main.o $(OBJDIR)/src/game/debug.o: GAME_CPPFLAGS += -DRE4DC_TICK_LOG=$(GAME_TICK_LOG)
$(OBJDIR)/tick_log.o: tick_log.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -DRE4DC_TICK_LOG=$(GAME_TICK_LOG) -MMD -MP -c $< -o $@
endif

# GAME_SCHED=1: GCC's post-register-allocation list scheduler (sched2) and peephole2 on every
# object; GAME_SCHED=game limits it to the recovered game code and the SDK (not the platform layer /
# native renderer, which other streams own). sched2 orders each block for the SH-4 pipeline: dual
# issue of different groups, 2-cycle loads, 3-cycle FPU results, fdiv/fsqrt busy time. Flycast
# charges ~1 cycle per instruction and does not see any of that; real hardware does
# (tools/sh4_cycles.py estimates the gain). Nothing that runs before or in RTL combine (where -O1
# forms its fmac) changes, so the RTL leaving combine is identical to the reference build in every
# function (tools/rtl_norm_cmp.py over -fdump-rtl-combine of every translation unit ->
# proofs/sched-combine-identity.txt); later passes only allocate registers, order, and fill delay
# slots, so the FP operations each execution path performs are identical by construction.
# (-fcaller-saves: +11 KB text and no modelled gain; -fipa-ra/-flra-remat: no effect. Left out.)
GAME_SCHED ?= 0
GAME_SCHED_FLAGS = -fschedule-insns2 -fpeephole2
ifeq ($(GAME_SCHED),1)
GAME_CPPFLAGS += $(GAME_SCHED_FLAGS)
PLATFORM_CPPFLAGS += $(GAME_SCHED_FLAGS)
SDK_CFLAGS += $(GAME_SCHED_FLAGS)
else ifeq ($(GAME_SCHED),game)
GAME_CPPFLAGS += $(GAME_SCHED_FLAGS)
SDK_CFLAGS += $(GAME_SCHED_FLAGS)
endif

# ---------------------------------------------------------------------------------------------
# Fusing policy 6B (USER SIGN-OFF 2026-09-23), in two separately gated steps:
#   GAME_FP_CONTRACT=off  step 1 (with GAME_FDLIBM=1 by default and the render-only exemption
#                         GAME_FP_RENDER=fast, both below): -ffp-contract=off on every logic, game, SDK
#                         and platform object. GCC then
#                         forms no fmac anywhere (~1,360 sites become fmul + fadd/fsub): the ONE-TIME
#                         approved behaviour change. Recapture the determinism baseline on this build
#                         (LOGIC_TRACE=1 GAME_FP_CONTRACT=off) and gate everything after it against
#                         that baseline. Logic then uses only IEEE fadd/fsub/fmul/fdiv, so it no longer
#                         depends on how an emulator implements the SH-4 fmac. GAME_SH4_MATH switches to
#                         the unfused kernel bodies (RE4DC_FP_CONTRACT_OFF in platform/mtx_sh4.S).
#   GAME_O2=hot|game      step 2 (needs GAME_FP_CONTRACT=off): -O2 with the decomp-safety guards on the
#                         hot gameplay objects (list below, from the logic stream's profile) or on every
#                         game + SDK object. Without contraction no -O2 pass changes an FP result (no
#                         reassociation without -ffast-math), so the FP dataflow is identical by
#                         construction; the guards keep CodeWarrior-era integer/pointer semantics.
#                         Objects with their own -O3/-Os policy (native renderer) keep it: their
#                         target-specific flags come later on the command line.
# Never (logic): -ffast-math family, -fsingle-precision-constant, -mfsrra/-mfsca, ftrv/fipr kernels,
# O2/Os without GAME30_DECOMP_SAFE.
# Hot gameplay objects (logic stream, proto/Makefile.logic.mk LOGIC_HOT_OBJS: profiled logic and
# game render-side units; native renderer, libraries and generated stubs excluded). Defined
# before the rules below: make expands a rule's target list when it reads the rule.
GAME30_HOT_OBJS = \
	$(OBJDIR)/platform/mtx.o \
	$(OBJDIR)/sdk/mtx.o \
	$(OBJDIR)/sdk/mtx44.o \
	$(OBJDIR)/sdk/mtxvec.o \
	$(OBJDIR)/sdk/quat.o \
	$(OBJDIR)/sdk/vec.o \
	$(OBJDIR)/src/game/Espgen42.o \
	$(OBJDIR)/src/game/Espgen43.o \
	$(OBJDIR)/src/game/EtcModel.o \
	$(OBJDIR)/src/game/act_btn.o \
	$(OBJDIR)/src/game/area.o \
	$(OBJDIR)/src/game/at_mod.o \
	$(OBJDIR)/src/game/at_sub.o \
	$(OBJDIR)/src/game/at_sub2.o \
	$(OBJDIR)/src/game/atari.o \
	$(OBJDIR)/src/game/atariInfo.o \
	$(OBJDIR)/src/game/cMotBase.o \
	$(OBJDIR)/src/game/cam_ctrl.o \
	$(OBJDIR)/src/game/cam_extra.o \
	$(OBJDIR)/src/game/cam_motion.o \
	$(OBJDIR)/src/game/cam_qfps.o \
	$(OBJDIR)/src/game/cam_sys.o \
	$(OBJDIR)/src/game/camera.o \
	$(OBJDIR)/src/game/cinesco.o \
	$(OBJDIR)/src/game/cloth.o \
	$(OBJDIR)/src/game/ctrl.o \
	$(OBJDIR)/src/game/ctrl00.o \
	$(OBJDIR)/src/game/ctrl01.o \
	$(OBJDIR)/src/game/ctrl10.o \
	$(OBJDIR)/src/game/ctrl11.o \
	$(OBJDIR)/src/game/ctrl12.o \
	$(OBJDIR)/src/game/ctrl14.o \
	$(OBJDIR)/src/game/dmg.o \
	$(OBJDIR)/src/game/eff_sys.o \
	$(OBJDIR)/src/game/em.o \
	$(OBJDIR)/src/game/emBar.o \
	$(OBJDIR)/src/game/emBarred.o \
	$(OBJDIR)/src/game/em_cloth.o \
	$(OBJDIR)/src/game/em_dm_val.o \
	$(OBJDIR)/src/game/em_set.o \
	$(OBJDIR)/src/game/em_sub.o \
	$(OBJDIR)/src/game/embarrel.o \
	$(OBJDIR)/src/game/embox.o \
	$(OBJDIR)/src/game/emdata.o \
	$(OBJDIR)/src/game/emdoor.o \
	$(OBJDIR)/src/game/emhit.o \
	$(OBJDIR)/src/game/emitem.o \
	$(OBJDIR)/src/game/emmine.o \
	$(OBJDIR)/src/game/emobj.o \
	$(OBJDIR)/src/game/emrack.o \
	$(OBJDIR)/src/game/emrock.o \
	$(OBJDIR)/src/game/emshield.o \
	$(OBJDIR)/src/game/emswitch.o \
	$(OBJDIR)/src/game/emtorch.o \
	$(OBJDIR)/src/game/emtree.o \
	$(OBJDIR)/src/game/emwep.o \
	$(OBJDIR)/src/game/emwindow.o \
	$(OBJDIR)/src/game/esp.o \
	$(OBJDIR)/src/game/esp00.o \
	$(OBJDIR)/src/game/esp01.o \
	$(OBJDIR)/src/game/esp02.o \
	$(OBJDIR)/src/game/esp03.o \
	$(OBJDIR)/src/game/esp04.o \
	$(OBJDIR)/src/game/esp05.o \
	$(OBJDIR)/src/game/esp06.o \
	$(OBJDIR)/src/game/esp07.o \
	$(OBJDIR)/src/game/esp08.o \
	$(OBJDIR)/src/game/esp09.o \
	$(OBJDIR)/src/game/esp0a.o \
	$(OBJDIR)/src/game/esp0b.o \
	$(OBJDIR)/src/game/esp0c.o \
	$(OBJDIR)/src/game/esp0d.o \
	$(OBJDIR)/src/game/esp0e.o \
	$(OBJDIR)/src/game/esp0f.o \
	$(OBJDIR)/src/game/esp10.o \
	$(OBJDIR)/src/game/esp11.o \
	$(OBJDIR)/src/game/esp12.o \
	$(OBJDIR)/src/game/esp13.o \
	$(OBJDIR)/src/game/esp14.o \
	$(OBJDIR)/src/game/esp15.o \
	$(OBJDIR)/src/game/esp16.o \
	$(OBJDIR)/src/game/esp17.o \
	$(OBJDIR)/src/game/esp18.o \
	$(OBJDIR)/src/game/esp19.o \
	$(OBJDIR)/src/game/esp1a.o \
	$(OBJDIR)/src/game/esp1b.o \
	$(OBJDIR)/src/game/esp3f.o \
	$(OBJDIR)/src/game/esp40.o \
	$(OBJDIR)/src/game/esp41.o \
	$(OBJDIR)/src/game/esp42.o \
	$(OBJDIR)/src/game/esp43.o \
	$(OBJDIR)/src/game/esp44.o \
	$(OBJDIR)/src/game/esp45.o \
	$(OBJDIR)/src/game/esp46.o \
	$(OBJDIR)/src/game/esp47.o \
	$(OBJDIR)/src/game/esp48.o \
	$(OBJDIR)/src/game/esp49.o \
	$(OBJDIR)/src/game/esp4a.o \
	$(OBJDIR)/src/game/esp4b.o \
	$(OBJDIR)/src/game/esp4c.o \
	$(OBJDIR)/src/game/esp4d.o \
	$(OBJDIR)/src/game/esp4e.o \
	$(OBJDIR)/src/game/esp4f.o \
	$(OBJDIR)/src/game/esp_app.o \
	$(OBJDIR)/src/game/esp_efm.o \
	$(OBJDIR)/src/game/esp_sub.o \
	$(OBJDIR)/src/game/espgen.o \
	$(OBJDIR)/src/game/espgen00.o \
	$(OBJDIR)/src/game/espgen01.o \
	$(OBJDIR)/src/game/espgen02.o \
	$(OBJDIR)/src/game/espgen10.o \
	$(OBJDIR)/src/game/espgen40.o \
	$(OBJDIR)/src/game/espgen44.o \
	$(OBJDIR)/src/game/espgen45.o \
	$(OBJDIR)/src/game/est.o \
	$(OBJDIR)/src/game/event.o \
	$(OBJDIR)/src/game/fade.o \
	$(OBJDIR)/src/game/flr_at.o \
	$(OBJDIR)/src/game/foot_shadow.o \
	$(OBJDIR)/src/game/foot_shadow_tbl.o \
	$(OBJDIR)/src/game/game.o \
	$(OBJDIR)/src/game/geometry.o \
	$(OBJDIR)/src/game/hermite.o \
	$(OBJDIR)/src/game/id_sys.o \
	$(OBJDIR)/src/game/ik.o \
	$(OBJDIR)/src/game/item_model.o \
	$(OBJDIR)/src/game/light.o \
	$(OBJDIR)/src/game/light01.o \
	$(OBJDIR)/src/game/light02.o \
	$(OBJDIR)/src/game/light03.o \
	$(OBJDIR)/src/game/light04.o \
	$(OBJDIR)/src/game/light05.o \
	$(OBJDIR)/src/game/light06.o \
	$(OBJDIR)/src/game/light07.o \
	$(OBJDIR)/src/game/light08.o \
	$(OBJDIR)/src/game/light10.o \
	$(OBJDIR)/src/game/lightInfo.o \
	$(OBJDIR)/src/game/lightPath.o \
	$(OBJDIR)/src/game/light_area.o \
	$(OBJDIR)/src/game/main.o \
	$(OBJDIR)/src/game/map_obj.o \
	$(OBJDIR)/src/game/math_sub.o \
	$(OBJDIR)/src/game/mes.o \
	$(OBJDIR)/src/game/mirror.o \
	$(OBJDIR)/src/game/model.o \
	$(OBJDIR)/src/game/motion.o \
	$(OBJDIR)/src/game/obj.o \
	$(OBJDIR)/src/game/obj00.o \
	$(OBJDIR)/src/game/obj01.o \
	$(OBJDIR)/src/game/obj02.o \
	$(OBJDIR)/src/game/obj03.o \
	$(OBJDIR)/src/game/obj04.o \
	$(OBJDIR)/src/game/obj05.o \
	$(OBJDIR)/src/game/obj06.o \
	$(OBJDIR)/src/game/obj08.o \
	$(OBJDIR)/src/game/obj09.o \
	$(OBJDIR)/src/game/obj10.o \
	$(OBJDIR)/src/game/obj12.o \
	$(OBJDIR)/src/game/obj13.o \
	$(OBJDIR)/src/game/obj14.o \
	$(OBJDIR)/src/game/obj15.o \
	$(OBJDIR)/src/game/obj16.o \
	$(OBJDIR)/src/game/obj18.o \
	$(OBJDIR)/src/game/obj19.o \
	$(OBJDIR)/src/game/obj1b.o \
	$(OBJDIR)/src/game/obj1c.o \
	$(OBJDIR)/src/game/obj1d.o \
	$(OBJDIR)/src/game/obj20.o \
	$(OBJDIR)/src/game/obj26.o \
	$(OBJDIR)/src/game/objBull.o \
	$(OBJDIR)/src/game/objGondola.o \
	$(OBJDIR)/src/game/objMissile.o \
	$(OBJDIR)/src/game/objPillar.o \
	$(OBJDIR)/src/game/objRobo.o \
	$(OBJDIR)/src/game/objRocket.o \
	$(OBJDIR)/src/game/objSubWep.o \
	$(OBJDIR)/src/game/objTrolley.o \
	$(OBJDIR)/src/game/objWep.o \
	$(OBJDIR)/src/game/objYagura.o \
	$(OBJDIR)/src/game/path.o \
	$(OBJDIR)/src/game/pendulum.o \
	$(OBJDIR)/src/game/pl_ashley.o \
	$(OBJDIR)/src/game/pl_body.o \
	$(OBJDIR)/src/game/pl_class.o \
	$(OBJDIR)/src/game/pl_cloth.o \
	$(OBJDIR)/src/game/pl_debug.o \
	$(OBJDIR)/src/game/pl_dmg.o \
	$(OBJDIR)/src/game/pl_event.o \
	$(OBJDIR)/src/game/pl_knife.o \
	$(OBJDIR)/src/game/pl_leon.o \
	$(OBJDIR)/src/game/pl_npc.o \
	$(OBJDIR)/src/game/pl_push.o \
	$(OBJDIR)/src/game/pl_sub.o \
	$(OBJDIR)/src/game/pl_wep.o \
	$(OBJDIR)/src/game/player.o \
	$(OBJDIR)/src/game/quake.o \
	$(OBJDIR)/src/game/rnd.o \
	$(OBJDIR)/src/game/room_jmp.o \
	$(OBJDIR)/src/game/route_ck.o \
	$(OBJDIR)/src/game/sce_at.o \
	$(OBJDIR)/src/game/sce_com.o \
	$(OBJDIR)/src/game/sce_sys.o \
	$(OBJDIR)/src/game/scheduler.o \
	$(OBJDIR)/src/game/scroll.o \
	$(OBJDIR)/src/game/se_at.o \
	$(OBJDIR)/src/game/shadow.o \
	$(OBJDIR)/src/game/shape.o \
	$(OBJDIR)/src/game/snd.o \
	$(OBJDIR)/src/game/snd_efx.o \
	$(OBJDIR)/src/game/snd_iss0.o \
	$(OBJDIR)/src/game/snd_iss1.o \
	$(OBJDIR)/src/game/snd_iss2.o \
	$(OBJDIR)/src/game/snd_iss3.o \
	$(OBJDIR)/src/game/snd_iss4.o \
	$(OBJDIR)/src/game/snd_main.o \
	$(OBJDIR)/src/game/snd_ram.o \
	$(OBJDIR)/src/game/snd_seq0.o \
	$(OBJDIR)/src/game/snd_seq1.o \
	$(OBJDIR)/src/game/snd_seq2.o \
	$(OBJDIR)/src/game/snd_seq3.o \
	$(OBJDIR)/src/game/snd_str0.o \
	$(OBJDIR)/src/game/snd_str1.o \
	$(OBJDIR)/src/game/snd_str2.o \
	$(OBJDIR)/src/game/snd_str3.o \
	$(OBJDIR)/src/game/snd_str4.o \
	$(OBJDIR)/src/game/snd_sub0.o \
	$(OBJDIR)/src/game/snd_sub1.o \
	$(OBJDIR)/src/game/snd_sub2.o \
	$(OBJDIR)/src/game/snd_sub3.o \
	$(OBJDIR)/src/game/stage.o \
	$(OBJDIR)/src/game/sub2.o \
	$(OBJDIR)/src/game/trans.o \
	$(OBJDIR)/src/game/trans_lit.o \
	$(OBJDIR)/src/game/trans_ot.o \
	$(OBJDIR)/src/game/view.o
GAME30_HOT_MODULE_PATTERNS = \
	$(OBJDIR)/mod/em12/%.o \
	$(OBJDIR)/mod/em10g/%.o \
	$(OBJDIR)/mod/em23/%.o \
	$(OBJDIR)/mod/wep02/%.o

# ACTOR_VTX_KERNEL=1 (the 30 fps rethink, vertex-loop lane; render only): the actors30 meshlet vertex
#                    passes (native_actor_fast.cpp pass_positions / pass_lights: every character's
#                    transform, outcode and fast light) on software-pipelined SH-4 loops (platform/avk_sh4.S,
#                    generated by tools/game30/avk/mkavk.py): two vertices in flight, in-kernel skin palette
#                    switches, s16 and u16 UVs, s8 normals through a float table; the same float operations
#                    as ACTOR_POS_ASM / ACTOR_LIGHT_ASM (u16 UVs: fmul + fadd where positions_c may fuse).
#                    Outcode bits reordered (near first) for every producer. =2: check build, the previous
#                    path recomputes each kernel vertex and every word is compared ("VTXK" log lines).
ACTOR_VTX_KERNEL ?= 0
ifneq ($(ACTOR_VTX_KERNEL),0)
PLATFORM_OBJS += $(OBJDIR)/platform/avk_sh4.o
$(OBJDIR)/platform/avk_sh4.o: platform/avk_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) $(AVK_SFLAGS) -c $< -o $@
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_VTX_KERNEL=$(ACTOR_VTX_KERNEL)
endif
# AVK_RIGID6=1 (needs ACTOR_VTX_KERNEL; render only, exact): rigid parts with stride 6 positions (props, weapons,
#              attachments: positions_asm<kPos6>, ~65% of pass_positions at the r101 entry) take the pipelined
#              rigid6 kernels (mkavk.py @p6: the index x 6 through r14) instead of the one-vertex loop.
AVK_RIGID6 ?= 0
ifneq ($(AVK_RIGID6),0)
ifeq ($(ACTOR_VTX_KERNEL),0)
$(error AVK_RIGID6 needs ACTOR_VTX_KERNEL)
endif
AVK_SFLAGS += -DRE4DC_AVK_RIGID6=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_AVK_RIGID6=1
endif
# ACTOR_LIGHT_N16=1 (needs ACTOR_VTX_KERNEL; render only): pass_lights' fast directional fold for s16 normals
#              (the owner path's parts: stride 8 skinned / rigid, stride 6 rigid) on pipelined kernels
#              (mkavk.py @n16: re4dc_avk_light_{skin,rigid}_n16, light_rigid_n16s6) instead of the portable
#              per-vertex loop (one skin_light_dirs call per vertex). Same lights, fold, directions and colour
#              matrix; the dot products by fipr (the s8 kernels' operation) where the loop used fmac.
#              Per-vertex alpha (alpha_state & 256) keeps the loop. =2: compare build, the loop relights every
#              kernel vertex and the colours are compared ("LN16" log lines, with the fallback reasons).
ACTOR_LIGHT_N16 ?= 0
ifneq ($(ACTOR_LIGHT_N16),0)
ifeq ($(ACTOR_VTX_KERNEL),0)
$(error ACTOR_LIGHT_N16 needs ACTOR_VTX_KERNEL)
endif
AVK_SFLAGS += -DRE4DC_ACTOR_LIGHT_N16=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_LIGHT_N16=$(ACTOR_LIGHT_N16)
endif

GAME_FP_CONTRACT ?= fast
GAME_O2 ?= 0
# Render-only objects exempt from contract-off (see GAME_FP_RENDER below). Game code reaches them only
# through submit/bind/frame entry points that take const inputs; they reference no data symbol
# defined outside themselves and write only TA/PVR data, their own statics and the renderer's
# per-frame workspace. native_ui has no contracted FP (listed for completeness, compiles the same).
# NOT exempt although renderer-side: gx_stub (GXProject hands screen coordinates back to game code),
# native_model (two-way interface with trans.o: re4dc_model_skipped_writeback/source_span/stamp),
# the bridges and native_motion (joint matrices).
GAME30_RENDER_EXEMPT_OBJS = \
	$(OBJDIR)/platform/native_static.o \
	$(OBJDIR)/platform/native_actor.o \
	$(OBJDIR)/platform/native_actor_fast.o \
	$(OBJDIR)/platform/native_ui.o \
	$(OBJDIR)/native-reuse/pvr_geometry.o \
	$(OBJDIR)/native-reuse/room_package.o \
	$(OBJDIR)/native-reuse/native_draw_plan.o \
	$(OBJDIR)/native-reuse/source_lighting.o
# GAME_CONCAT_COL=1 (design-logic P3, needs GAME_FP_CONTRACT=off): the contract-off MTXConcat kernel
# computed column by column (b column loaded once, a_ik loaded straight into each product register)
# and list-scheduled for SH-4 dual issue: the same fmul/fadd on the same operands in the same roles
# (tools/game30/mtx_concat_col.py generates it; tools/game30/prove_concat_col.sh: fpsym2 --strict vs
# the build's own C_MTXConcat over every alias partition). hwsim: 206 -> 102 cycles per call.
GAME_CONCAT_COL ?= 0
ifeq ($(GAME_CONCAT_COL),1)
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_CONCAT_COL=1 replaces the contract-off MTXConcat body: needs GAME_FP_CONTRACT=off)
endif
endif
# GAME_MULTVEC_SCHED=1 (design-logic P3b, needs GAME_FP_CONTRACT=off): the contract-off MTXMultVec body
# with its three rows interleaved for SH-4 dual issue: the same fmul/fadd on the same operands in the
# same roles, all loads before the stores (tools/game30/prove_multvec_sched.sh: fpsym2 --strict vs the
# build's own C_MTXMultVec). hwsim: 56 -> 34 cycles per call.
GAME_MULTVEC_SCHED ?= 0
ifeq ($(GAME_MULTVEC_SCHED),1)
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_MULTVEC_SCHED=1 replaces the contract-off MTXMultVec body: needs GAME_FP_CONTRACT=off)
endif
endif
# GAME_VEC_INLINE=1 (needs GAME_FP_CONTRACT=off): the small PSVEC* routines (add, subtract, scale,
# square magnitude, dot, cross, square distance) inline in game units (include/vec.h): the SDK's own C_*
# bodies, same operations in the same order, instead of two calls each (PS* -> C_*). Bit-identical with
# contraction off; the platform/native renderer units keep the calls.
GAME_VEC_INLINE ?= 0
ifeq ($(GAME_VEC_INLINE),1)
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_VEC_INLINE=1 inlines the contract-off SDK vector bodies: needs GAME_FP_CONTRACT=off)
endif
GAME_CPPFLAGS += -DRE4DC_VEC_INLINE=1
endif
GAME30_DECOMP_SAFE = -fwrapv -fno-strict-aliasing -fno-delete-null-pointer-checks \
	-fno-isolate-erroneous-paths-dereference
GAME30_O2_FLAGS = -O2 $(GAME30_DECOMP_SAFE)
GAME30_FP_FLAGS =
ifeq ($(GAME_FP_CONTRACT),off)
GAME30_FP_FLAGS = -ffp-contract=off
$(OBJDIR)/platform/mtx_sh4.o: KOS_CFLAGS += -DRE4DC_FP_CONTRACT_OFF=1
ifeq ($(GAME_CONCAT_COL),1)
$(OBJDIR)/platform/mtx_sh4.o: KOS_CFLAGS += -DRE4DC_CONCAT_COL=1
endif
ifeq ($(GAME_MULTVEC_SCHED),1)
$(OBJDIR)/platform/mtx_sh4.o: KOS_CFLAGS += -DRE4DC_MULTVEC_SCHED=1
endif
# Render-only exemption (coordinator decision 2): these native renderer objects keep the default
# contraction (fmac) because nothing they compute flows back into gameplay state: their FP results
# go only to TA/PVR vertex data, renderer-private caches and draw lists (evidence in the game30
# report: interface census + STRICT trace of the exempt vs non-exempt build). Logic, SDK, game,
# bridges, GX emulation and native_motion stay contract-off. GAME_FP_RENDER=off drops the exemption.
GAME_FP_RENDER ?= fast
ifeq ($(GAME_FP_RENDER),fast)
$(GAME30_RENDER_EXEMPT_OBJS): GAME30_FP_FLAGS =
else ifneq ($(GAME_FP_RENDER),off)
$(error GAME_FP_RENDER must be fast or off)
endif
else ifneq ($(GAME_FP_CONTRACT),fast)
$(error GAME_FP_CONTRACT must be fast or off)
endif
# ACTOR_VTX_KERNEL's asm repeats the contracted (fmac) render code of native_actor_fast.cpp: it needs that object
# built with contraction on (GAME_FP_CONTRACT=fast, or =off with the GAME_FP_RENDER=fast exemption).
ifneq ($(ACTOR_VTX_KERNEL),0)
ifeq ($(GAME_FP_CONTRACT),off)
ifneq ($(GAME_FP_RENDER),fast)
$(error ACTOR_VTX_KERNEL repeats native_actor_fast.o's contracted render code: needs GAME_FP_RENDER=fast with GAME_FP_CONTRACT=off)
endif
endif
endif
# Per-object flags: recursive, so target/pattern-specific values below reach each compile (and each
# member compile of a REL module) at recipe time. Placed after GAME_OPT, so -O2 wins over -O1.
GAME30_OBJ_FLAGS =
GAME_CPPFLAGS += $(GAME30_FP_FLAGS) $(GAME30_OBJ_FLAGS)
PLATFORM_CPPFLAGS += $(GAME30_FP_FLAGS) $(GAME30_OBJ_FLAGS)
SDK_CFLAGS += $(GAME30_FP_FLAGS) $(GAME30_OBJ_FLAGS)
ifneq ($(GAME_O2),0)
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_O2 changes fmac formation unless GAME_FP_CONTRACT=off (6B step 1 first))
endif
ifeq ($(GAME_O2),hot)
$(GAME30_HOT_OBJS) $(GAME30_HOT_MODULE_PATTERNS): GAME30_OBJ_FLAGS = $(GAME30_O2_FLAGS)
else ifeq ($(GAME_O2),game)
GAME_CPPFLAGS += $(GAME30_O2_FLAGS)
SDK_CFLAGS += $(GAME30_O2_FLAGS)
$(OBJDIR)/platform/mtx.o: GAME30_OBJ_FLAGS = $(GAME30_O2_FLAGS)
else
$(error GAME_O2 must be 0, hot or game)
endif
endif
# GAME_COLD_OS=1 (needs GAME_FP_CONTRACT=off): -Os for code that never runs in the frame loop of
# the route's gameplay (title/save/options/merchant/puzzle/debug screens and the Sscrn sub-screen
# REL, SUBSCREEN=1). Image bytes are heap-4 bytes (ARENA_FIT=1); with contraction off the FP
# results are the same at any -O level, and the decomp guards are kept as for -O2.
GAME_COLD_OS ?= 0
GAME30_COLD_OBJS = \
	$(OBJDIR)/src/game/title.o \
	$(OBJDIR)/src/game/card.o \
	$(OBJDIR)/src/game/option.o \
	$(OBJDIR)/src/game/t_option.o \
	$(OBJDIR)/src/game/merchant.o \
	$(OBJDIR)/src/game/puzzle.o \
	$(OBJDIR)/src/game/db_cam.o \
	$(OBJDIR)/src/game/debug.o \
	$(OBJDIR)/src/game/dbmodule.o \
	$(OBJDIR)/src/game/t_bugcheck.o \
	$(OBJDIR)/src/game/mercenaries.o
GAME30_COLD_MODULE_PATTERNS = $(OBJDIR)/mod/Sscrn/%.o
ifeq ($(GAME_COLD_OS),1)
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_COLD_OS changes fmac formation unless GAME_FP_CONTRACT=off)
endif
$(GAME30_COLD_OBJS) $(GAME30_COLD_MODULE_PATTERNS): GAME30_OBJ_FLAGS = -Os $(GAME30_DECOMP_SAFE)
else ifneq ($(GAME_COLD_OS),0)
$(error GAME_COLD_OS must be 0 or 1)
endif

# GAME_FDLIBM=1 (needs GAME_FP_CONTRACT=off; part of 6B step 1, before the baseline is recaptured):
# the single-precision libm the game calls (sinf/cosf/tanf/atanf and the acosf/asinf/atan2f cores,
# __kernel_*, the pi/2 reduction and the sqrtf errno-path core) compiled from the game's own recovered sources
# (src/lib/fdlibm, newlib 1.8.2 as shipped with the original) with -ffp-contract=off, in place of the
# toolchain's prebuilt newlib members, which were built with fmac (127 reachable fmac in 10 functions
# remain after GAME_FP_CONTRACT=off alone). With it no logic path executes fmac at all. Linked as
# ordinary objects ahead of libm, so the archive members defining these symbols are not pulled; the
# public wrappers that stay in libm (acosf, asinf, atan2f) call these cores.
# Coordinator decision 1: part of step 1, so GAME_FP_CONTRACT=off turns it on by default (one
# baseline recapture); GAME_FDLIBM=0 with contract-off only for the drift-attribution arm.
ifeq ($(GAME_FP_CONTRACT),off)
GAME_FDLIBM ?= 1
else
GAME_FDLIBM ?= 0
endif
GAME30_FDLIBM_UNITS = ef_acos ef_asin ef_atan2 ef_rem_pio2 ef_sqrt kf_cos kf_rem_pio2 kf_sin kf_tan sf_atan sf_cos \
	sf_sin sf_tan
# GAME_TRIG=1 (needs GAME_FDLIBM=1): sinf/cosf from game30_trig.c, the same fdlibm source with
# __kernel_sinf/__kernel_cosf and the |x| <= 2^7*pi/2 part of __ieee754_rem_pio2f inlined, -O2 with
# the decomp-safety guards and -ffp-contract=off: bit-identical by construction (same operations, same
# order) and checked for all 2^32 inputs on the host (tools/trig_exhaustive.sh, FTZ/DAZ).
GAME_TRIG ?= 0
ifeq ($(GAME_TRIG),1)
ifneq ($(GAME_FDLIBM),1)
$(error GAME_TRIG=1 replaces the GAME_FDLIBM sinf/cosf: needs GAME_FDLIBM=1)
endif
GAME30_FDLIBM_UNITS := $(filter-out sf_sin sf_cos,$(GAME30_FDLIBM_UNITS))
PLATFORM_OBJS += $(OBJDIR)/game30_trig.o
$(OBJDIR)/game30_trig.o: game30_trig.c
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -w $(GAME_OPT) -O2 -ffp-contract=off $(GAME30_DECOMP_SAFE) -I$(ROOT)/include -MMD -MP -c $< -o $@
else ifneq ($(GAME_TRIG),0)
$(error GAME_TRIG must be 0 or 1)
endif
ifeq ($(GAME_FDLIBM),1)
ifneq ($(GAME_FP_CONTRACT),off)
$(error GAME_FDLIBM=1 belongs to 6B step 1: needs GAME_FP_CONTRACT=off)
endif
PLATFORM_OBJS += $(patsubst %,$(OBJDIR)/fdlibm/%.o,$(GAME30_FDLIBM_UNITS))
$(OBJDIR)/fdlibm/%.o: $(ROOT)/src/lib/fdlibm/%.c
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -w $(GAME_OPT) -ffp-contract=off $(GAME30_DECOMP_SAFE) -I$(ROOT)/include -MMD -MP -c $< -o $@
endif

# ---------------------------------------------------------------------------------------------
# D367 B1 (user-approved census item; CHANGES GAMEPLAY once it parks): ACT_CAP=N caps the Ganados
# (ids 0x10..0x20) that run their AI / motion tick at N per logic tick (act_cap.cpp). The others
# are parked: no emMove, plDist2 kept current, still alive in EmMgr for every counter (kill count,
# waves, bell, doors). Engaged, threatening, damaged, in-view or near Ganados are never parked.
# 0 (default) builds nothing. N at or above the live Ganado count parks nothing and the logic trace
# is STRICT against the reference.
#   ACT_CAP_ROOM=0xSSRR  room the cap works in (default 0x101 = r101; 0 = every room)
#   ACT_CAP_RANGE_M=M    engagement radius in metres, never parked inside it (default 12)
#   ACT_CAP_VIEW_M=M     view frustum inflation in metres (default 3)
#   ACT_CAP_CREEP=K      a parked Ganado still runs every K-th tick, staggered (default 4; 0 = frozen)
#   ACT_CAP_LOG=N        one "AC" stats line per N ticks through re4dc_log (measurement builds only)
# em.o depends on the generated header in every build, so switching N (or back to 0) in one OBJDIR
# recompiles it; the default build compiles em.cpp without it (RE4DC_ACT_CAP undefined = off).
ACT_CAP ?= 0
ACT_CAP_ROOM ?= 0x101
ACT_CAP_RANGE_M ?= 12
ACT_CAP_VIEW_M ?= 3
ACT_CAP_CREEP ?= 4
ACT_CAP_LOG ?= 0
.PHONY: act-cap-force
$(OBJDIR)/act-cap.h: act-cap-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_ACT_CAP %s\n#define RE4DC_ACT_CAP_ROOM %s\n#define RE4DC_ACT_CAP_RANGE_M %s\n#define RE4DC_ACT_CAP_VIEW_M %s\n#define RE4DC_ACT_CAP_CREEP %s\n#define RE4DC_ACT_CAP_LOG %s\n' '$(ACT_CAP)' '$(ACT_CAP_ROOM)' '$(ACT_CAP_RANGE_M)' '$(ACT_CAP_VIEW_M)' '$(ACT_CAP_CREEP)' '$(ACT_CAP_LOG)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/src/game/em.o: $(OBJDIR)/act-cap.h
ifneq ($(ACT_CAP),0)
PLATFORM_OBJS += $(OBJDIR)/act_cap.o
$(OBJDIR)/src/game/em.o: GAME_CPPFLAGS += -include $(OBJDIR)/act-cap.h
$(OBJDIR)/act_cap.o: act_cap.cpp $(OBJDIR)/act-cap.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -include $(OBJDIR)/act-cap.h -MMD -MP -c $< -o $@
endif

# GROUND_LIGHT_FIX=bits (look-gaps ground 2026-09-26; render-only, default off): light with the transformed normal at
# unit length, as GX does (Dolphin's vertex shader normalises the first transformed normal before lighting). The
# source normal matrix is inverse-transpose(view x placement) and carries the placement scale: r101's ground layers
# (BINs 2-5, 12, 46, 54, 70 ...) are placed at scale 10, so their normals were 0.1 long and the ground was lit at about
# ambient only (try-it D2: the GameCube ground 1.3-3.2x brighter than every port path). 1: native mesh prelight
# (native_static light_part, once per part at its first draw). 2: the generic GX path (native_model; raw S8/64
# normals are ~1.97 long at scale 1: try-it D8's over-lit walls). 3: both. 0 (default) builds nothing.
GROUND_LIGHT_FIX ?= 0
ifneq ($(GROUND_LIGHT_FIX),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_GROUND_LIGHT_FIX=$(GROUND_LIGHT_FIX)
$(OBJDIR)/platform/native_model.o: PLATFORM_CPPFLAGS += -DRE4DC_GROUND_LIGHT_FIX=$(GROUND_LIGHT_FIX)
endif

# Default-off register Hermite kernel; 2 checks each admitted call against C.
GAME_HF_ASM ?= 0
ifneq ($(GAME_HF_ASM),0)
ifeq ($(GAME_HERMITE_FAST),0)
$(error GAME_HF_ASM needs GAME_HERMITE_FAST)
endif
PLATFORM_OBJS += $(OBJDIR)/platform/hf_sh4.o
$(OBJDIR)/platform/hf_sh4.o: platform/hf_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -DRE4DC_HF_PF=$(GAME_HF_PF) -c $< -o $@
$(OBJDIR)/src/game/motion.o: GAME_CPPFLAGS += -DRE4DC_HF_ASM=$(GAME_HF_ASM)
endif
# ---- lane logic (2026-10-04; gameplay CPU, exact; gate: LOGIC_TRACE STRICT) ----
# GAME_HF_REG=1 (exact; with GAME_HERMITE_FAST, not with GAME_HF_ASM): hermiteFast once per common key layout
#               (5, 0, 6) at an even key address: aligned frame / count loads, a constant stride, the value /
#               tangent pair in registers; the same search, history, decode conversions and blend expression
#               (motion.cpp hfReg). =2 (check build): hermiteFast runs first and is compared ("HFR" lines).
GAME_HF_REG ?= 0
ifneq ($(GAME_HF_REG),0)
ifeq ($(GAME_HERMITE_FAST),0)
$(error GAME_HF_REG needs GAME_HERMITE_FAST)
endif
ifneq ($(GAME_HF_ASM),0)
$(error GAME_HF_REG and GAME_HF_ASM both replace the hermite entry)
endif
$(OBJDIR)/src/game/motion.o: GAME_CPPFLAGS += -DRE4DC_HF_REG=$(GAME_HF_REG)
endif
# GAME_SND_WALL_ALT=1 (audio only; report candidate 12): sndSurroundCalc tests a tracked SE's wall occlusion (a line
#                     query to the player's head) on every other frame and reuses the slot's last verdict in
#                     between (snd.cpp). Only an occluded SE's muffled volume can lag one frame; the logic trace
#                     stays STRICT (the sound queries are hashed apart).
GAME_SND_WALL_ALT ?= 0
ifneq ($(GAME_SND_WALL_ALT),0)
$(OBJDIR)/src/game/snd.o: GAME_CPPFLAGS += -DRE4DC_SND_WALL_ALT=$(GAME_SND_WALL_ALT)
endif
# GAME_CLOTH_SPRING=1 (exact): Cloth::calcSpeed (esp4e sheets) computes each spring's force once and adds its
#                     negation at the other end (the source evaluates every spring from both ends; the second
#                     evaluation is the first negated bit for bit; cloth.cpp). =2 (check build): the source step
#                     runs on the same input after it and the speed grids are compared ("CSPR" lines).
GAME_CLOTH_SPRING ?= 0
ifneq ($(GAME_CLOTH_SPRING),0)
$(OBJDIR)/src/game/cloth.o: GAME_CPPFLAGS += -DRE4DC_CLOTH_SPRING=$(GAME_CLOTH_SPRING)
endif

# Draw original non-scenery objects on coarse images; candidate, default off.
COARSE_SOURCE_OBJECTS ?= 0
ifneq ($(COARSE_SOURCE_OBJECTS),0)
ifneq ($(COARSE_SOURCE_OBJECTS),1)
$(error COARSE_SOURCE_OBJECTS must be 0 or 1)
endif
ifneq ($(COARSE),1)
$(error COARSE_SOURCE_OBJECTS needs COARSE=1)
endif
ifneq ($(PACE_CATCHUP),2)
$(error COARSE_SOURCE_OBJECTS needs PACE_CATCHUP=2)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_COARSE_SOURCE_OBJECTS=$(COARSE_SOURCE_OBJECTS)
endif

# COARSE_SCENERY_FALLBACK=1 (trans.cpp, coarse.cpp; default 0): coarse images skip source scenery and the
# diagnostic collision piece only in rooms the PS2 world package covers (r101); other rooms (r100, r103,
# ...) draw their own Standard scenery through native_static. Render only (2026-09-28: r100 was grey).
COARSE_SCENERY_FALLBACK ?= 0
ifneq ($(COARSE_SCENERY_FALLBACK),0)
ifneq ($(COARSE_SOURCE_OBJECTS),1)
$(error COARSE_SCENERY_FALLBACK needs COARSE_SOURCE_OBJECTS=1)
endif
ifneq ($(PS2_WORLD_DRAW),1)
$(error COARSE_SCENERY_FALLBACK needs PS2_WORLD_DRAW=1 (re4dc_ps2_world_covers))
endif
$(OBJDIR)/src/game/trans.o $(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_COARSE_SCENERY_FALLBACK=$(COARSE_SCENERY_FALLBACK)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_COARSE_SCENERY_FALLBACK=$(COARSE_SCENERY_FALLBACK)
endif

# COARSE_SAT_SCENERY_ONLY=1 (coarse.cpp; default 0; needs PS2_WORLD_DRAW=1): a coarse image whose scenery another
# path draws (the PS2 world, or the room's own scenery under COARSE_SCENERY_FALLBACK) draws no collision piece at
# all; without it only piece 0 is skipped and the gameplay-only pieces (AEV wall areas, sce_at.cpp sceAtSetScrAt)
# draw as flat grey walls (r100 bridge after s20, 2026-10-04 hardware report). Render only.
COARSE_SAT_SCENERY_ONLY ?= 0
ifneq ($(COARSE_SAT_SCENERY_ONLY),0)
ifneq ($(COARSE_SAT_SCENERY_ONLY),1)
$(error COARSE_SAT_SCENERY_ONLY must be 0 or 1)
endif
ifneq ($(PS2_WORLD_DRAW),1)
$(error COARSE_SAT_SCENERY_ONLY needs PS2_WORLD_DRAW=1)
endif
$(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_COARSE_SAT_SCENERY_ONLY=1
endif

# Unsupported source actors on coarse images; unqualified candidate, default off.
COARSE_SOURCE_ACTORS ?= 0
ifneq ($(COARSE_SOURCE_ACTORS),0)
ifneq ($(COARSE_SOURCE_ACTORS),1)
$(error COARSE_SOURCE_ACTORS must be 0 or 1)
endif
ifneq ($(COARSE),1)
$(error COARSE_SOURCE_ACTORS requires COARSE=1)
endif
ifneq ($(PACE_CATCHUP),2)
$(error COARSE_SOURCE_ACTORS requires PACE_CATCHUP=2)
endif
ifeq ($(GAME_ATCHK_LIST),0)
$(error COARSE_SOURCE_ACTORS requires enabled GAME_ATCHK_LIST generations)
endif
$(OBJDIR)/src/game/trans.o $(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_COARSE_SOURCE_ACTORS=$(COARSE_SOURCE_ACTORS)
endif

# Full authored PS2 r101 world consumer, default off; no gameplay/source suppression.
PS2_WORLD_DRAW ?= 0
ifneq ($(PS2_WORLD_DRAW),0)
ifneq ($(PS2_WORLD_DRAW),1)
$(error PS2_WORLD_DRAW must be 0 or 1)
endif
ifneq ($(COARSE),1)
$(error PS2_WORLD_DRAW needs COARSE=1)
endif
ifneq ($(COARSE_WORLD),0)
$(error PS2_WORLD_DRAW replaces the diagnostic world; use COARSE_WORLD=0)
endif
ifneq ($(PVR_STREAM),1)
$(error PS2_WORLD_DRAW needs PVR_STREAM=1)
endif
ifneq ($(TREE_IMPOSTOR),1)
$(error PS2_WORLD_DRAW needs TREE_IMPOSTOR=1 for the existing PT list)
endif
$(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_PS2_WORLD_DRAW=1
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ps2_world.o $(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_DRAW=1
endif
# WORLD_AUTOSORT=1: world transparency correction. Existing PVR bank
# sorting; menus/pickups retain source order, planar overlays retain layer order.
# Enabled for the PS2 world + ordered UI profile after the r109 appearance,
# bridge/inventory STRICT and r102 CPU gates. Use 0 for a comparison arm.
WORLD_AUTOSORT ?= $(if $(filter 11,$(PS2_WORLD_DRAW)$(SS_UI_ORDER)),1,0)
ifneq ($(WORLD_AUTOSORT),0)
ifneq ($(WORLD_AUTOSORT),1)
$(error WORLD_AUTOSORT must be 0 or 1)
endif
ifneq ($(PS2_WORLD_DRAW)$(SS_UI_ORDER),11)
$(error WORLD_AUTOSORT needs PS2_WORLD_DRAW=1 SS_UI_ORDER=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_AUTOSORT=1
endif
# PS2_PRELOAD_LEAN=1 (needs PS2_WORLD_ROOMS=2 and QUALITY_ASSETS=1; native_ui.cpp + native_static.cpp, render only,
# default 0): with the room's PS2 world package open, the room preload loads the package's own textures instead of
# the room archive's (GameCube scenery the PS2 world replaces) and the Standard index's; those load on first sight
# if anything draws them (user r21o play 2026-10-03: 4.9 / 6.1 s of reloads after the r100 cutscenes, a full pool
# while running; TEX_USE_CENSUS: 103 of 105 room textures idle for 20 s on the r100 east walk).
PS2_PRELOAD_LEAN ?= 0
ifneq ($(PS2_PRELOAD_LEAN),0)
ifneq ($(PS2_WORLD_ROOMS),2)
$(error PS2_PRELOAD_LEAN needs PS2_WORLD_ROOMS=2)
endif
ifneq ($(QUALITY_ASSETS),1)
$(error PS2_PRELOAD_LEAN needs QUALITY_ASSETS=1)
endif
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_PRELOAD_LEAN=1
endif
# TEX_PACK=1 (needs TEX_RESIDENT=1; native_ui.cpp + room/texture_package.cpp, default 0): texture packages load
# from dc/tex.pak (tools/d367/texpack.py, every dc/tex package of the staged disc in one file with a sorted index)
# instead of one dc/tex/<n>/<key>.re4tex open per texture; keys not in the pack (or no pack) use the per-file path.
# r100 room entry (IO_PROBE): 130 opens were 3.9 of 6.5 s with 234 directory-sector reads. Same bytes uploaded.
# Failure policy (platform/include/texpack_index.inc): pack absent -> per-file; a read error -> nothing loaded now,
# the key not remembered as missing, init retried 3 times then once per room load; an invalid pack (count, offsets,
# extents, key order, index CRC) -> one loud INVALID line, per-file loads.
#   TEX_PACK_FAULT=N (test only, default 0): the first N pack reads fail as read errors (the retry test).
TEX_PACK ?= 0
TEX_PACK_FAULT ?= 0
ifneq ($(TEX_PACK),0)
ifneq ($(TEX_RESIDENT),1)
$(error TEX_PACK needs TEX_RESIDENT=1)
endif
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/native-reuse/texture_package.o: PLATFORM_CPPFLAGS += -DRE4DC_TEX_PACK=1
ifneq ($(TEX_PACK_FAULT),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_TEX_PACK_FAULT=$(TEX_PACK_FAULT)
endif
endif
# TEX_USE_CENSUS=1 (test only, native_ui.cpp, default 0): every 600 frames, the resident textures and how many the
# last 2 s / 20 s drew ("tex use census"), to size what the room preload loads but nothing draws.
TEX_USE_CENSUS ?= 0
ifneq ($(TEX_USE_CENSUS),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_TEX_USE_CENSUS=1
endif
# CLOSED_PASS_KEEP=1 (needs PS2_WORLD_DRAW=1; native_ui.cpp, render only, default 0): a draw that asks for a PVR list
# this scene already closed (an opaque or punch-through packet after the translucent list opened) stays in the open
# list instead of halting ("native closed pass requested"; user r21o play 2026-10-03, r100 after pressing A). The TA
# latches the list type at the list's first header, so the packet draws with its own blend (an opaque packet's
# ONE/ZERO looks opaque) in the open list. Logged with the caller ("PS2PASS kept") for the root fix.
CLOSED_PASS_KEEP ?= 0
ifneq ($(CLOSED_PASS_KEEP),0)
ifneq ($(PS2_WORLD_DRAW),1)
$(error CLOSED_PASS_KEEP needs PS2_WORLD_DRAW=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_CLOSED_PASS_KEEP=1
endif

# PS2_WORLD_KERNEL (render only, default off): 1 = the coarse-world kernel shape on the PS2 world
# (box/plane group classify, fast path without the clipper for wholly-inside groups, static
# reference light cached per adopted owner); emitted words equal the old path's. 2 = 1 plus the
# old tests in parallel ("PS2KERNEL ... unsafe/extra/badin/badcolor"; test builds only).
# The object is built at -O2 -ffinite-math-only (after GAME_OPT's -O1; -ffp-contract=off stays; the
# inputs are finite: the draw entry refuses a non-finite camera, and w >= 40 before any divide).
PS2_WORLD_KERNEL ?= 0
ifneq ($(PS2_WORLD_KERNEL),0)
ifneq ($(PS2_WORLD_DRAW),1)
$(error PS2_WORLD_KERNEL needs PS2_WORLD_DRAW=1)
endif
$(OBJDIR)/platform/native_ps2_world.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_KERNEL=$(PS2_WORLD_KERNEL) -O2 -ffinite-math-only
# =4 (test): =3 plus whole strips on the fast path with the PVR's back-face cull in the header
# (native_ui.cpp's re4dc_ps2_world_packet_cull); emitted words differ, the image should not.
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_KERNEL=$(PS2_WORLD_KERNEL)
endif
# PS2_WORLD_COLOR_ALL=1 (test, default off): cache every range corner's packed colour, not only the
# lit ones (static heap; the adopt log line prints all= / bytes= for the memory decision).
PS2_WORLD_COLOR_ALL ?= 0
ifneq ($(PS2_WORLD_COLOR_ALL),0)
$(OBJDIR)/platform/native_ps2_world.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_COLOR_ALL=1
endif

# UI_HUD_MASK (renderer/hud-source-mask-r1, default 0): the HUD backing + red/amber lens through a
# private composite of the source colour texture and its mask (two 64x64 ARGB4444 packages, 16 KiB
# VRAM). Only ui_bridge.o and native_ui.o read it; the stamp rebuilds both when it changes.
UI_HUD_MASK ?= 0
ifeq ($(filter $(UI_HUD_MASK),0 1),)
$(error UI_HUD_MASK must be 0 or 1)
endif
$(OBJDIR)/ui_bridge.o $(OBJDIR)/platform/native_ui.o: GAME_CPPFLAGS += -DRE4DC_UI_HUD_MASK=$(UI_HUD_MASK)
$(OBJDIR)/ui_bridge.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_UI_HUD_MASK=$(UI_HUD_MASK)
UI_HUD_MASK_STAMP := $(OBJDIR)/ui-hud-mask.txt
.PHONY: ui-hud-mask-force
$(UI_HUD_MASK_STAMP): ui-hud-mask-force
	@mkdir -p $(dir $@)
	@printf '%s\n' 'UI_HUD_MASK=$(UI_HUD_MASK)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/ui_bridge.o $(OBJDIR)/platform/native_ui.o: $(UI_HUD_MASK_STAMP)

# PS2_WORLD_MESH (render only, default off): the PS2 r101 world converted offline to R4IM v3 + an R4PW
# placement sidecar (tools/ps2_world_r4im.py; staged as dc/native/r101/ps2-world.re4mesh / .r4pw) and drawn
# by native_static.cpp's MeshDraw (cluster LOD, the meshlet fast path, direct TA) instead of
# native_ps2_world.cpp's own path. The .r4p is not loaded. Prelit ARGB1555 corners: nothing lit at runtime.
PS2_WORLD_MESH ?= 0
ifneq ($(PS2_WORLD_MESH),0)
ifneq ($(PS2_WORLD_DRAW),1)
$(error PS2_WORLD_MESH needs PS2_WORLD_DRAW=1)
endif
ifneq ($(NATIVE_MESH)$(MESH_LOD)$(MESH_DIRECT)$(TA_DIRECT),1111)
$(error PS2_WORLD_MESH needs NATIVE_MESH=1 MESH_LOD=1 MESH_DIRECT=1 TA_DIRECT=1)
endif
$(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_PS2_WORLD_MESH=1
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ps2_world.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_MESH=1
endif
# PS2_WORLD_HDR_CACHE=1 (native_ui.cpp, render only, exact, default 0; needs PS2_WORLD_MESH=1): the PS2 world's
# direct bind (re4dc_ps2_world_direct_begin) keeps each material's compiled header (texture key/size, pass, cull, fog)
# with its texture Entry in a 4-way 128-slot table (5 KiB), valid while that Entry holds the key at the same VRAM address:
# a hit skips the texture lookup and the header compile. Exact in pixels: the same header words 0..3; words 4..7, which
# KOS pvr_poly_compile leaves unset (stack contents; unused by the PVR for these headers), go out as zeros
# (perf-20261004 candidate 4).
# =2 (diagnostic): every hit also runs the uncached lookup + compile and counts a different Entry or header word
# (PS2HDR log line: checked / mismatched).
PS2_WORLD_HDR_CACHE ?= 0
ifneq ($(PS2_WORLD_HDR_CACHE),0)
ifeq ($(PS2_WORLD_MESH),0)
$(error PS2_WORLD_HDR_CACHE needs PS2_WORLD_MESH=1)
endif
ifneq ($(filter-out 1 2 3,$(PS2_WORLD_HDR_CACHE)),)
$(error PS2_WORLD_HDR_CACHE must be 0, 1, 2 or 3)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_HDR_CACHE=$(PS2_WORLD_HDR_CACHE)
# =3 (layout control, diagnostic): both paths linked, PS2_WORLD_HDR_CACHE_SELECT=0|1 (one .data word) picks one.
ifeq ($(PS2_WORLD_HDR_CACHE),3)
PS2_WORLD_HDR_CACHE_SELECT ?= 0
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_HDR_CACHE_SELECT=$(PS2_WORLD_HDR_CACHE_SELECT)
endif
endif
# PS2_PASS_MASK=1 (native_static.cpp, render only, exact, default 0; needs PS2_WORLD_MESH=1): ps2_pass skips a
# placement without a part in the pass on a per-placement pass-bit byte (2 KiB table, built when the package opens)
# instead of reading its placement + mesh records and scanning the mesh's parts, for each of the three passes.
# =2 (diagnostic): the scan runs too and a different decision is counted (PS2MASK log line).
PS2_PASS_MASK ?= 0
ifneq ($(PS2_PASS_MASK),0)
ifeq ($(PS2_WORLD_MESH),0)
$(error PS2_PASS_MASK needs PS2_WORLD_MESH=1)
endif
ifneq ($(filter-out 1 2 3,$(PS2_PASS_MASK)),)
$(error PS2_PASS_MASK must be 0, 1, 2 or 3)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_PASS_MASK=$(PS2_PASS_MASK)
# =3 (layout control, diagnostic): PS2_PASS_MASK_SELECT=0|1 (one .data word) picks the scan or the mask.
ifeq ($(PS2_PASS_MASK),3)
PS2_PASS_MASK_SELECT ?= 0
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_PASS_MASK_SELECT=$(PS2_PASS_MASK_SELECT)
endif
endif
# PS2_INTERIOR_CULL=1 (native_static.cpp, render only, meant image-identical (see =2), default 0; needs PS2_WORLD_MESH=1,
# PS2_WORLD_ROOMS and MESH_LOD): an offline-built interior cell for the r100 house (include/ps2_interior_cell.inc, from
# tools/d367/ps2world/interior/build_cell.py). While the camera eye is inside one of the cell's sub-cells (and the
# near-plane corners are within the cell's near margin), a PS2 world placement, cluster or meshlet whose world box
# lies wholly outside the house box is drawn only if the box can be seen through one of that sub-cell's portals
# (conservative frustum test from the eye through each portal rectangle). Anything touching the house box always draws.
# Active only on the r100 package the cell was built from (mesh + sidecar CRCs).
# =2 (check build): nothing is lost: the hidden geometry is drawn again in a check pass in flat magenta (untextured,
# unfogged; native_ui.cpp patches the direct header), and each frame the displayed framebuffer is scanned for magenta
# pixels (PCCHECK log lines): any such pixel is a pixel =1 would lose. Known: a 1 px raster crack on a shared edge of
# the east wall (tris 1673/1765 of the cell build, screen column 3-5) at the stair foot shows the outdoors for 2-4 frames
# of a whole-house walk in some runs (view-timing dependent); ray sampling cannot see raster cracks.
# =3 (layout control, diagnostic): =1's code with PS2_INTERIOR_CULL_SELECT=0|1 (one .data word) off / on.
PS2_INTERIOR_CULL ?= 0
ifneq ($(PS2_INTERIOR_CULL),0)
ifeq ($(PS2_WORLD_MESH),0)
$(error PS2_INTERIOR_CULL needs PS2_WORLD_MESH=1)
endif
ifneq ($(filter-out 1 2 3,$(PS2_INTERIOR_CULL)),)
$(error PS2_INTERIOR_CULL must be 0, 1, 2 or 3)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_INTERIOR_CULL=$(PS2_INTERIOR_CULL)
# The cell tables are the disc file dc/native/r100/interior.cell (tools/d367/ps2world/interior/interior-r100.cell; a
# fixture without it simply does not cull), read into an r100-only heap-4 block that route movies borrow.
$(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_INTERIOR_CULL=$(PS2_INTERIOR_CULL)
$(OBJDIR)/route_movie_bridge.o: GAME_CPPFLAGS += -DRE4DC_PS2_INTERIOR_CULL=$(PS2_INTERIOR_CULL)
ifeq ($(PS2_INTERIOR_CULL),2)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_INTERIOR_CULL=2
endif
# PS2_INTERIOR_ACTORS=1 (lane pc; render only; default 0; needs PS2_INTERIOR_CULL 1/2/3 and CROWD_INVIS_SKIP=1): the
# cell for Ganados too. CROWD_INVIS_SKIP's Trans decision (coarse_actor_owner_ganado.inc re4dc_invis_decide) also
# skips a source-path Ganado whose source-mesh ball box lies wholly outside the house box and is hidden by the cell
# set up at Trans start from the camera Trans sees (native_static.cpp re4dc_ps2_interior_trans; Render's pass 0
# counts any view change, PCACT view=mismatches/checked). Same skip path, settled-parts rule and CROWD_LOD note as
# CROWD_INVIS_SKIP's source path; owner-path Ganados are not taken. With PS2_INTERIOR_CULL=2 nothing is skipped and
# each such box is drawn as an opaque magenta box (PCACT boxes / drawn / unchecked), covered by the framebuffer scan.
# With =3 the actor part follows PS2_INTERIOR_CULL_SELECT.
# PS2_INTERIOR_ACTORS=2 (lane pc2, 2026-10-06; render only; default 0): =1 plus owner-path Ganados (the ACTOR_TRANSACTION
# owner path). Trans (re4dc_invis_decide) marks an owner-path Ganado the crowd policy keeps when its drawn cast chunks'
# pregate balls are all within the fog gate's far plane and their world box is hidden by the cell; the next Render's
# transaction runs unchanged up to the owned submission (plan, semantics, crowd_policy, actor_acquire), leaves the
# CROWD_LOD notes its runs would leave (native_actor_fast.cpp re4dc_actor_owned_crowd_replay: CROWD_INVIS_SKIP's
# re4dc_actor_crowd_note under its settled-parts rule) and skips the submission. With PS2_INTERIOR_CULL=2 nothing is
# skipped: the box is drawn magenta and the crowd entry the submission left is compared with the replay's
# (INVISPCO checked / check_mis, must stay 0).
PS2_INTERIOR_ACTORS ?= 0
ifneq ($(PS2_INTERIOR_ACTORS),0)
ifeq ($(filter $(PS2_INTERIOR_ACTORS),1 2),)
$(error PS2_INTERIOR_ACTORS must be 0, 1 or 2)
endif
ifneq ($(CROWD_INVIS_SKIP),1)
$(error PS2_INTERIOR_ACTORS needs CROWD_INVIS_SKIP=1)
endif
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_PS2_INTERIOR_ACTORS=1
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_INTERIOR_ACTORS=1
ifeq ($(PS2_INTERIOR_ACTORS),2)
PS2_INTERIOR_OWNER := $(if $(filter 2,$(PS2_INTERIOR_CULL)),2,1)
$(OBJDIR)/coarse_ganado.o $(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_PS2_INTERIOR_OWNER=$(PS2_INTERIOR_OWNER)
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_INTERIOR_OWNER=$(PS2_INTERIOR_OWNER)
# PS2_INTERIOR_OWNER_SELECT=0|1 (layout control, diagnostic; unset in every real build): the owner-path skip behind one .data word.
ifneq ($(PS2_INTERIOR_OWNER_SELECT),)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_PS2_INTERIOR_OWNER_SELECT=$(PS2_INTERIOR_OWNER_SELECT)
endif
endif
endif
ifeq ($(PS2_INTERIOR_CULL),3)
PS2_INTERIOR_CULL_SELECT ?= 0
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_INTERIOR_CULL_SELECT=$(PS2_INTERIOR_CULL_SELECT)
endif
endif
# PS2_FOLIAGE_FAR=<source units, mm> (native_static.cpp, render only, CHANGES THE LOOK, default 0 = off; needs
# PS2_WORLD_MESH=1): the PS2 world's punch-through / translucent passes (ps2_pass 1 and 2: foliage, fences, alpha
# cards) reject placements, clusters and meshlets whose nearest depth is past this distance (the opaque pass keeps the
# fog far). A user look decision (perf-20261004 candidate 9): measure / capture only.
PS2_FOLIAGE_FAR ?= 0
ifneq ($(PS2_FOLIAGE_FAR),0)
ifeq ($(PS2_WORLD_MESH),0)
$(error PS2_FOLIAGE_FAR needs PS2_WORLD_MESH=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_FOLIAGE_FAR=$(PS2_FOLIAGE_FAR)
endif
# PS2_WORLD_ROOMS=1 (render only, default off; needs PS2_WORLD_MESH=1): the PS2 world in r100, r103, r104 and r106 too
# (the room list: native_static.cpp re4dc_ps2_world_room)
# (tools/ps2_room_r4im.py, staged as dc/native/r%03x/ps2-world.re4mesh / .r4pw). Each room opens its own
# package at its first coarse draw (another room's is freed first); a room whose package fails to open
# (missing, no heap) draws its own scenery again (COARSE_SCENERY_FALLBACK) and is not retried until retired.
# =2 (heap-4 reclaim): the package opens at the room's first scenery bind instead, and when it opens the room's
# scenery mesh package is not (COARSE_NO_STD_SCENERY's skip and census): r103's Standard package (1,143,808 B)
# and the PS2 world do not both fit. Images the coarse path does not draw (door demo, death, sub screens) draw
# the PS2 world where the scenery package would have drawn (the first scenery part of the image), so they show
# the same world. A package that does not open leaves the room on its scenery package, as =1.
PS2_WORLD_ROOMS ?= 0
ifneq ($(PS2_WORLD_ROOMS),0)
ifeq ($(PS2_WORLD_MESH),0)
$(error PS2_WORLD_ROOMS needs PS2_WORLD_MESH=1)
endif
ifneq ($(PS2_WORLD_ROOMS),1)
ifneq ($(PS2_WORLD_ROOMS),2)
$(error PS2_WORLD_ROOMS is 0, 1 or 2)
endif
ifneq ($(COARSE_NO_STD_SCENERY),0)
$(error PS2_WORLD_ROOMS=2 and COARSE_NO_STD_SCENERY both own the scenery skip)
endif
ifneq ($(NATIVE_PKG_HIGH),1)
$(error PS2_WORLD_ROOMS=2 needs NATIVE_PKG_HIGH=1 (the only layout gated without the package))
endif
$(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_PS2_WORLD_ROOMS=$(PS2_WORLD_ROOMS)
endif
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ps2_world.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_ROOMS=$(PS2_WORLD_ROOMS)
endif
# PS2_WORLD_DYNAMIC=1 (render only, default 0; needs PS2_WORLD_ROOMS; issue #3): the PS2 world follows the scenery
# objects the room code moves, turns or hides (r105's emblem puzzle and its door, r100's gate swaps, r101's ladder, room
# doors). The package is baked at each row's rest pose; dc/native/r%03x/ps2-world.ids (tools/ps2_room_ids.py, from the
# room's OBJ export) gives each placement its scroll id, scroll.cpp setObj reports the game object of each id with its
# rest matrix (re4dc_ps2_dyn_bind), and native_static.cpp skips a placement while its object is hidden and draws it
# through mat * inverse(rest) once the object left its rest pose. Ids shared by several placements stay baked, as does
# a room without the ids file. Heap 4: the ids file plus 56 B per unique id (r105 45 ids, r100 83) while the room's
# PS2 world is open. Not followed: part animation inside one object (chest lids).
PS2_WORLD_DYNAMIC ?= 0
ifneq ($(PS2_WORLD_DYNAMIC),0)
ifneq ($(PS2_WORLD_DYNAMIC),1)
$(error PS2_WORLD_DYNAMIC must be 0 or 1)
endif
ifeq ($(PS2_WORLD_ROOMS),0)
$(error PS2_WORLD_DYNAMIC needs PS2_WORLD_ROOMS=1 or 2)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_DYNAMIC=1
$(OBJDIR)/src/game/scroll.o: GAME_CPPFLAGS += -DRE4DC_PS2_WORLD_DYNAMIC=1
endif
# PS2_WORLD_PARTS=1: a unique scenery placement whose source child pose changes
# uses the existing source object renderer. The PS2 copy is suppressed for that
# owner; gameplay, part hierarchy and animation timing remain source-owned.
PS2_WORLD_PARTS ?= 0
ifneq ($(PS2_WORLD_PARTS),0)
ifneq ($(PS2_WORLD_PARTS),1)
$(error PS2_WORLD_PARTS must be 0 or 1)
endif
ifneq ($(PS2_WORLD_DYNAMIC),1)
$(error PS2_WORLD_PARTS needs PS2_WORLD_DYNAMIC=1)
endif
ifneq ($(COARSE_SOURCE_OBJECTS)$(COARSE_SCENERY_FALLBACK),11)
$(error PS2_WORLD_PARTS needs COARSE_SOURCE_OBJECTS=1 COARSE_SCENERY_FALLBACK=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_PARTS=1
$(OBJDIR)/src/game/scroll.o $(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PS2_WORLD_PARTS=1
endif
# ITEM_UI_ORDER=1: item pickup uses the same source-ordered UI/model stream
# as inventory examination, without claiming that the subscreen heap is swapped.
ITEM_UI_ORDER ?= 0
ifneq ($(ITEM_UI_ORDER),0)
ifneq ($(ITEM_UI_ORDER),1)
$(error ITEM_UI_ORDER must be 0 or 1)
endif
ifneq ($(SS_UI_ORDER),1)
$(error ITEM_UI_ORDER needs SS_UI_ORDER=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ITEM_UI_ORDER=1
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_ITEM_UI_ORDER=1
endif
# PS2_WORLD_REGISTRY=1 (render only, default 0; needs PS2_WORLD_ROOMS): re4dc_ps2_world_room's room list comes from
# platform/include/ps2_world_rooms.inc, generated by tools/d367/ps2world/world_registry.py from the package manifest
# (every package the runtime's own open checks accept, with its textures, room identity and source hashes) instead
# of the hand list. A listed room without its package on the disc logs "PS2MESH open failed" and draws its own
# scenery, as a failed open does today.
PS2_WORLD_REGISTRY ?= 0
ifneq ($(PS2_WORLD_REGISTRY),0)
ifneq ($(PS2_WORLD_REGISTRY),1)
$(error PS2_WORLD_REGISTRY must be 0 or 1)
endif
ifeq ($(PS2_WORLD_ROOMS),0)
$(error PS2_WORLD_REGISTRY needs PS2_WORLD_ROOMS=1 or 2)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_REGISTRY=1
$(OBJDIR)/platform/native_static.o: platform/include/ps2_world_rooms.inc
endif
# PS2_OPEN_READ=1 (default 0; needs PS2_WORLD_ROOMS and IO_ALIGNED=1): ps2_open reads the world package and its R4PW
# sidecar through read_package (IO_ALIGNED's whole-file reader: aligned body stream, seek away and back, tail through
# the block cache), not one plain fs_read each. PS2_OPEN_TRACE showed r210's 6,120 B sidecar read (8 B past its last
# 32 B unit, 32-byte-aligned destination) never return: the KOS stream stall R4_5A that read_package avoids.
PS2_OPEN_READ ?= 0
ifneq ($(PS2_OPEN_READ),0)
ifneq ($(PS2_OPEN_READ),1)
$(error PS2_OPEN_READ must be 0 or 1)
endif
ifeq ($(PS2_WORLD_ROOMS),0)
$(error PS2_OPEN_READ needs PS2_WORLD_ROOMS=1 or 2)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_OPEN_READ=1
endif
# PS2_OPEN_TRACE=1 (diagnostic, default 0; needs PS2_WORLD_ROOMS): ps2_open logs each step it completes (both opens
# with sizes, the heap-4 block and its alignment, each read with destination / size / result, adopt, the R4PW
# checks) as "PS2OPEN ..." lines, so a stall names the last completed operation.
PS2_OPEN_TRACE ?= 0
ifneq ($(PS2_OPEN_TRACE),0)
ifneq ($(PS2_OPEN_TRACE),1)
$(error PS2_OPEN_TRACE must be 0 or 1)
endif
ifeq ($(PS2_WORLD_ROOMS),0)
$(error PS2_OPEN_TRACE needs PS2_WORLD_ROOMS=1 or 2)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_OPEN_TRACE=1
endif
# SCENERY_ENCODING=1 (render only, default 0): the native scenery path (native_static.cpp open()) adopts each room
# package by its own validated header colour encoding (instanced_mesh.hpp adopt_by_encoding): oct packages exactly as
# before; prelit packages (convert_room_bins.py --color prelit: route r104-r107, r210, any room with more than 16 CLR0
# colours) draw their stored ARGB1555 corners and are never lit again; any other encoding is still rejected. Off, a
# prelit scenery package is rejected ("color encoding") and a room whose PS2 world package is absent has no world.
SCENERY_ENCODING ?= 0
ifneq ($(SCENERY_ENCODING),0)
ifneq ($(SCENERY_ENCODING),1)
$(error SCENERY_ENCODING must be 0 or 1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_ENCODING=1
endif
# PS2_WORLD_FOG_SOURCE=1 (render only, default 0): the PS2 world headers (native_ui.cpp re4dc_ps2_world_packet,
# _packet_cull, _direct_begin) take PVR table fog only if the source GX fog was on at the frame's scenery draw
# (re4dc_fog_enabled latched by native_ps2_world.cpp at pass 0 and kept for the later PT / TR flush; model_bridge.cpp
# reads the same state per model part). Off, they always take table fog: in a room whose source fog is off (r210) the
# table is the previous room's, or never loaded on a direct entry, and every PS2 world surface is drawn as the fog
# colour (flat grey).
PS2_WORLD_FOG_SOURCE ?= 0
ifneq ($(PS2_WORLD_FOG_SOURCE),0)
ifneq ($(PS2_WORLD_FOG_SOURCE),1)
$(error PS2_WORLD_FOG_SOURCE must be 0 or 1)
endif
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_ps2_world.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_FOG_SOURCE=1
endif
# MESH_CLASSIFY=1 (native_static.cpp, default 0): the meshlet fast path classifies each meshlet's box
# first and skips per-vertex outcodes (and strip code scans) in wholly visible meshlets (+~1.5 KiB image).
MESH_CLASSIFY ?= 0
ifneq ($(MESH_CLASSIFY),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_MESH_CLASSIFY=$(MESH_CLASSIFY)
endif
# MESH_VP_SCHED (native_static.cpp, default 0; HW_LEAN=0 keeps the original kernel): 1 = the meshlet transform's kChecksAll loop
# software-pipelined over two vertices (room/mesh_fastpath_sched.hpp, generated by tools/mesh_vp_sched.py): the
# same FP operations, bit-identical cache entries and outcode bits. 2 = diagnostic: the reference kernel draws,
# the pipelined one runs into a scratch cache and every meshlet is compared (VPSCHED log lines, +8.5 KiB bss).
MESH_VP_SCHED ?= 0
ifneq ($(MESH_VP_SCHED),0)
ifneq ($(filter-out 1 2 3,$(MESH_VP_SCHED)),)
$(error MESH_VP_SCHED must be 0, 1, 2 or 3)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_MESH_VP_SCHED=$(MESH_VP_SCHED)
ifeq ($(MESH_VP_SCHED),3)
# 3 = layout control (diagnostic): both kernels linked, MESH_VP_SCHED_SELECT=0|1 (one .data word) picks the reference
# or the pipelined one, so a TA_HASH pair is not confounded by a static-layout shift.
MESH_VP_SCHED_SELECT ?= 0
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_MESH_VP_SCHED_SELECT=$(MESH_VP_SCHED_SELECT)
endif
endif
# MESH_STRIP_LEAN (native_static.cpp, default 0; independent of MESH_VP_SCHED): 1 = the meshlet strip walk for
# kChecksAll meshlets on the store-queue sink (MESH_DIRECT, depth cull, SH4) with its counters in registers
# and rescheduled outcode / store-queue copy loops (room/mesh_strip_lean.hpp): the same decisions, TA bursts
# and final counters; other paths keep the original walk. 2 = diagnostic: the original walk draws, the lean
# walk runs dry into RAM per meshlet and is compared (STRIPLEAN log lines, +16 KiB bss). 3 = layout control
# (diagnostic): both walks linked, MESH_STRIP_LEAN_SELECT=0|1 (one .data word) picks one.
MESH_STRIP_LEAN ?= 0
ifneq ($(MESH_STRIP_LEAN),0)
ifneq ($(filter-out 1 2 3,$(MESH_STRIP_LEAN)),)
$(error MESH_STRIP_LEAN must be 0, 1, 2 or 3)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_MESH_STRIP_LEAN=$(MESH_STRIP_LEAN)
ifeq ($(MESH_STRIP_LEAN),3)
MESH_STRIP_LEAN_SELECT ?= 0
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_MESH_STRIP_LEAN_SELECT=$(MESH_STRIP_LEAN_SELECT)
endif
endif
# MESH_PRIME_LAZY=1 (native_static.cpp, exact, default 0): the meshlet cache's constant words are
# written only for the entries meshlets use, not all 256 at every per-part borrow.
MESH_PRIME_LAZY ?= 0
ifneq ($(MESH_PRIME_LAZY),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_MESH_PRIME_LAZY=$(MESH_PRIME_LAZY)
endif
# MESH_CLIP_LEAN=1 (native_static.cpp, needs HW_LEAN=1, default 0): the near/far clipper drops a strip whose
# corners are all outside one frustum plane (homogeneous test; it would draw no pixels) and runs clip_vertex
# once per corner instead of once per triangle using it. Exact in pixels; the TA stream loses off-screen triangles.
MESH_CLIP_LEAN ?= 0
ifneq ($(MESH_CLIP_LEAN),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_MESH_CLIP_LEAN=$(MESH_CLIP_LEAN)
endif
# MESH_CLIP_ACCEPT=1 (native_static.cpp, render only, exact: the same TA words; default 0; needs MESH_CLIP_LEAN=1 and
# HW_LEAN=1): a strip the clipper takes (a corner nearer than near, or longer than the slab) runs clip_vertex once per
# corner for any strip length (a three-corner ring) and packs each corner once; a triangle with all three corners at
# depth >= near is the clipper's accept case and is written from the packed corners after the clipper's own far and
# screen tests, none at depth >= near is dropped as the clipper drops it, and only a crossing triangle calls
# clip_projected_triangle (perf-20261004 candidate 8: world near-plane clipping). =2 (diagnostic): every accepted or
# dropped triangle also runs clip_projected_triangle into scratch and a different count or word is counted (CLIPACC log).
MESH_CLIP_ACCEPT ?= 0
ifneq ($(MESH_CLIP_ACCEPT),0)
ifneq ($(MESH_CLIP_LEAN)$(HW_LEAN),11)
$(error MESH_CLIP_ACCEPT needs MESH_CLIP_LEAN=1 HW_LEAN=1)
endif
ifneq ($(filter-out 1 2 3,$(MESH_CLIP_ACCEPT)),)
$(error MESH_CLIP_ACCEPT must be 0, 1, 2 or 3)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_MESH_CLIP_ACCEPT=$(MESH_CLIP_ACCEPT)
# =3 (layout control, diagnostic): both paths linked, MESH_CLIP_ACCEPT_SELECT=0|1 (one .data word) picks one.
ifeq ($(MESH_CLIP_ACCEPT),3)
MESH_CLIP_ACCEPT_SELECT ?= 0
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_MESH_CLIP_ACCEPT_SELECT=$(MESH_CLIP_ACCEPT_SELECT)
endif
endif
# UI_HUD_LENS_ALPHA (render only, needs UI_HUD_MASK=1; 0 = the source alpha 0xa5): the HUD lens backing's
# minimum alpha (0..255). User, 2026-09-28: more opaque, so the unlit ammo segments stop reading "88".
UI_HUD_LENS_ALPHA ?= 0
ifneq ($(UI_HUD_LENS_ALPHA),0)
ifneq ($(UI_HUD_MASK),1)
$(error UI_HUD_LENS_ALPHA needs UI_HUD_MASK=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_UI_HUD_LENS_ALPHA=$(UI_HUD_LENS_ALPHA)
endif
# MEMPROF=1 (diagnostic builds only): wrap memset/memcpy and log the heaviest call sites by bytes every
# 120 frames (platform/memprof.cpp; logged from native_ps2_world.cpp's flush).
MEMPROF ?= 0
ifneq ($(MEMPROF),0)
GAME_LDFLAGS += -Wl,--wrap=memset -Wl,--wrap=memcpy
$(OBJDIR)/platform/memprof.o $(OBJDIR)/platform/native_ps2_world.o: PLATFORM_CPPFLAGS += -DRE4DC_MEMPROF=1
endif

# ACTOR_CENSUS=1 (diagnostic): ACENSUS log lines, the models reaching re4dc_actor_submit per 120 frames.
ACTOR_CENSUS ?= 0
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_CENSUS=$(ACTOR_CENSUS) -DRE4DC_ACTOR_CENSUS_SKIP_OBJ00=$(ACTOR_CENSUS_SKIP_OBJ00)
ACTOR_CENSUS_SKIP_OBJ00 ?= 0
# SKIN_CENSUS=1 (diagnostic, trans.cpp): SKINCEN log lines, Trans() skinned infos per 120 frames (deferred
#               to the native actor path / defer failed / CPU-skinned by CalcSk1_x / morphed).
SKIN_CENSUS ?= 0
ifneq ($(SKIN_CENSUS),0)
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_SKIN_CENSUS=1
endif
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_CENSUS=$(ACTOR_CENSUS)
# ENC_CENSUS=1 (diagnostic, default 0, lane enc; measurement builds only, read-only): one "ENC" log line per
#              presented frame (native_ui's PC-sampler frame mark, so hwproject frames line up): Ganados and other
#              enemies alive, Ganados reaching commonModelTrans (the game's view test), drawn by the actor owner /
#              left to the source path / failed, owned ones by view distance, and the crowd tiers drawn
#              (coarse.cpp re4dc_enc_frame; the note wraps coarse_actor_transaction.inc's draw). Needs COARSE.
ENC_CENSUS ?= 0
ifneq ($(ENC_CENSUS),0)
ifeq ($(COARSE),0)
$(error ENC_CENSUS needs COARSE (coarse.cpp defines re4dc_enc_frame))
endif
$(OBJDIR)/coarse.o $(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ENC_CENSUS=1
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ENC_CENSUS=1
# ENC_CENSUS=2 (diagnostic, lane iv 2026-10-05; measurement builds only): =1 plus the Ganados' visibility states
#              ("ENCV" lines: hidden / outside the game's view test / crowd-culled off-screen / fog-skipped / submitted
#              but emitted nothing / drawn / source path) and per-state wrappers (trans.cpp re4dc_iv_t_* around
#              emTrans, re4dc_iv_r_* around ModelRender, picked by the Ganado's state in the previous drawn image), so
#              the hw model's call tree prices each state; "ENCVE" lines (where off / fog / empty Ganados are against
#              the frustum, every 8th image of each) and live effects attached to / owned by Ganados per state ("fx=").
#              Changes the code layout: per-state costs only.
ifeq ($(ENC_CENSUS),2)
$(OBJDIR)/src/game/trans.o $(OBJDIR)/coarse.o $(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ENCV=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_CROWD_OUTPUT=1 -DRE4DC_ENCV=1
endif
endif
# ENC_SKIP_GANADO=1 (diagnostic A/B only, default 0, lane enc; NEVER a play build): trans.cpp emTrans gives Ganados
#                  (kindid 0, ids 0x10..0x20) no transform pass (no OT entry, screen matrices, skinning, lights or
#                  draw), so a view's hw ms with and without it prices the Ganados' render side. They are invisible.
ENC_SKIP_GANADO ?= 0
ifneq ($(ENC_SKIP_GANADO),0)
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_ENC_SKIP_GANADO=1
endif
# EL_CENSUS=1 (diagnostic, default 0, lane el 2026-10-05; measurement builds only, read-only): el_census.cpp, the
#              census that bounds exact reuse in the enemies' logic over global ticks EL_CENSUS_FROM..EL_CENSUS_TO
#              (pG->Frame_cnt): line queries keyed by their complete inputs (repeats this tick / last tick / 2-8
#              ticks back, outputs compared, work and candidate-polygon counters, by caller chain and enemy),
#              getNearPoint repeats, unchanged skeletons after move(), redundant part-world passes. "ELC" log lines
#              at the first hook after EL_CENSUS_TO. Hooks in atari.cpp, route_ck.cpp, em.cpp, model.cpp.
EL_CENSUS ?= 0
EL_CENSUS_FROM ?= 2300
EL_CENSUS_TO ?= 2379
ifneq ($(EL_CENSUS),0)
PLATFORM_OBJS += $(OBJDIR)/el_census.o
$(OBJDIR)/el_census.o: el_census.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -DRE4DC_EL_CENSUS=1 -DRE4DC_EL_CENSUS_FROM=$(EL_CENSUS_FROM) -DRE4DC_EL_CENSUS_TO=$(EL_CENSUS_TO) -MMD -MP -c $< -o $@
$(OBJDIR)/src/game/atari.o $(OBJDIR)/src/game/route_ck.o $(OBJDIR)/src/game/em.o $(OBJDIR)/src/game/model.o: GAME_CPPFLAGS += -DRE4DC_EL_CENSUS=1
endif
# GAME_LQ_MEMO=1 (lane el 2026-10-05; enemy logic, line queries; exact): cSatMgr::wallAdjust (atari.cpp) asks its
#                line question twice around the sphere pass; when the first hit nothing and neither end moved since
#                (bit for bit) the second gets that answer without a walk (fight / prejump: about 0.26 hw ms per
#                tick). Trace builds give the first walk's decision notes again (logic_trace.cpp). =2: the second
#                query always walks and the memo's answers are compared ("LQM pair= pairsame= pairmis=", must be 0).
#                (A memo of the route line tests, rckLineHitCheck, was measured and dropped: its world check cost
#                what its hits saved; docs/lanes/el-20261005.md.)
GAME_LQ_MEMO ?= 0
ifneq ($(GAME_LQ_MEMO),0)
$(OBJDIR)/src/game/atari.o $(OBJDIR)/logic_trace.o: GAME_CPPFLAGS += -DRE4DC_LQ_MEMO=$(GAME_LQ_MEMO)
endif

# QUALITY_LOD_PX (default 5, the Standard RQ_LOD_COARSE threshold): the projected-pixel error Standard's mesh
# LOD accepts (MESH_LOD_PX applies to Original only). Larger values are a visible change.
QUALITY_LOD_PX ?= 5
ifneq ($(QUALITY_LOD_PX),5)
$(OBJDIR)/platform/quality.o: PLATFORM_CPPFLAGS += -DRE4DC_QUALITY_LOD_PX=$(QUALITY_LOD_PX)
endif

# Diagnostic-only projection of room bytes while borrowed by the sub screen.
# Trace-only capacity profiles. Large r104 inventory needs more than 8192 raw ranges.
# Both comparison arms use the selected profile; never enabled in performance/production images.
LOGIC_TRACE_SPANS ?= 6144
ifneq ($(filter-out 6144 16384,$(LOGIC_TRACE_SPANS)),)
$(error LOGIC_TRACE_SPANS must be 6144 or 16384)
endif
LOGIC_TRACE_SWAPPED ?= 0
ifeq ($(LOGIC_TRACE_SWAPPED),1)
ifneq ($(LOGIC_TRACE),1)
$(error LOGIC_TRACE_SWAPPED requires LOGIC_TRACE=1)
endif
ifneq ($(SS_PACK),1)
$(error LOGIC_TRACE_SWAPPED requires SS_PACK=1)
endif
$(OBJDIR)/logic_trace.o: GAME_CPPFLAGS += -DRE4DC_LOGIC_TRACE_SPANS=$(LOGIC_TRACE_SPANS)
$(OBJDIR)/logic_trace.o $(OBJDIR)/sscrn_bridge.o: GAME_CPPFLAGS += -DRE4DC_LOGIC_TRACE_SWAPPED=1
$(OBJDIR)/platform/subscreen_backing.o: PLATFORM_CPPFLAGS += -DRE4DC_LOGIC_TRACE_SWAPPED=1
endif

# LOGIC_TRACE_OWNERSHIP=1 (diagnostic, needs LOGIC_TRACE=1): logic trace schema 5. The source room lifetime
# sites (stage.cpp StageSet heap reload / REL relink, game.cpp gameRoomMemInit) mark the room's player, enemy,
# object, effect and effect-generator lists released, and gameRoomInit publishes each list again right after
# resetting its head (main_mem.h RE4DC_TRACE_OWNER_*). A released list is logged as unowned instead of hashing
# freed memory; the padscript "room" feed keeps its exact old reads. 0 (default): no code.
LOGIC_TRACE_OWNERSHIP ?= 0
ifneq ($(filter-out 0 1,$(LOGIC_TRACE_OWNERSHIP)),)
$(error LOGIC_TRACE_OWNERSHIP must be 0 or 1)
endif
ifeq ($(LOGIC_TRACE_OWNERSHIP),1)
ifneq ($(LOGIC_TRACE),1)
$(error LOGIC_TRACE_OWNERSHIP requires LOGIC_TRACE=1)
endif
$(OBJDIR)/logic_trace.o $(OBJDIR)/src/game/game.o $(OBJDIR)/src/game/stage.o: GAME_CPPFLAGS += -DRE4DC_LOGIC_TRACE_OWNERSHIP=1
endif

# Isolated timing qualification only, excluded from the clean trace patch.
H2_EXTERNAL_DELAY ?= 0
ifeq ($(H2_EXTERNAL_DELAY),1)
ifneq ($(LOGIC_TRACE),1)
$(error H2_EXTERNAL_DELAY requires LOGIC_TRACE=1)
endif
$(OBJDIR)/logic_trace.o: GAME_CPPFLAGS += -DRE4DC_H2_EXTERNAL_DELAY=1
endif
