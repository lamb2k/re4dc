# Lane scenery19 (scenery redesign, P2; SCENERY19-STATUS.md). Default 0: no code, image unchanged.
# SCENERY_CHUNK=1 (exact, render only; needs PS2_WORLD_LEAN, PS2_STRIP_GROUPS, MESH_STRIP_LEAN=1, MESH_VP_SCHED=1):
# the PS2 world's per-part draw (native_static.cpp MeshDraw run / clusters / meshlets / strip groups) runs as one
# chunk walker compiled at -O2 with the knob-off expressions for every decision that changes pixels (far rejection,
# LOD), and, when the room has an R4RC 'SCNK' section, each repeated corner position is transformed once.
SCENERY_CHUNK ?= 0
ifneq ($(SCENERY_CHUNK),0)
ifeq ($(filter 1 2,$(SCENERY_CHUNK)),)
$(error SCENERY_CHUNK must be 0, 1 or 2)
endif
ifneq ($(PS2_STRIP_GROUPS),1)
$(error SCENERY_CHUNK needs PS2_STRIP_GROUPS=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_CHUNK=$(SCENERY_CHUNK)
endif
# SCENERY_SELECT_ONLY=1 (exact, render only): eligible chunk selection borrows
# placement inputs in a small context, without constructing an emitter first.
# The shared selector, queued snapshots and replay order remain the same.
SCENERY_SELECT_ONLY ?= 0
ifneq ($(SCENERY_SELECT_ONLY),0)
ifneq ($(SCENERY_SELECT_ONLY),1)
$(error SCENERY_SELECT_ONLY must be 0 or 1)
endif
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_SELECT_ONLY needs SCENERY_CHUNK)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_SELECT_ONLY=1
endif
# SCENERY_SUBMIT_BATCH=1 (spike, exact rendering): keep the TA store-queue
# mutex across compatible resident parts within one synchronous chunk replay.
# Every part still sends its own header and starts at the original SQ address.
# No texture load, pass transition or source-task boundary retains the mutex.
# Private qualification only: emit every target while observing real PVS source
# receipts through production batching. Fine candidate dispatch is a later unit.
PS2_PVS_BATCH_COMPOSE ?= 0
ifneq ($(PS2_PVS_BATCH_COMPOSE),0)
ifneq ($(PS2_PVS_BATCH_COMPOSE),1)
$(error PS2_PVS_BATCH_COMPOSE must be 0 or 1)
endif
PVSBC_REQUIRE_ONE := PS2_PVS SCENERY_SUBMIT_BATCH SCENERY_CHUNK SCENERY_SELECT_ONLY SCENERY_REPLAY_LEAN TA_DIRECT MESH_DIRECT PS2_WORLD_MESH PS2_WORLD_HDR_CACHE PS2_STRIP_GROUPS MESH_FASTPATH MESH_VP_SCHED HW_LEAN PVR_STREAM D349_RENDERER_STACK PS2_WORLD_SOURCE_OWNER PS2_WORLD_SOURCE_TEX_PREP
ifneq ($(strip $(foreach v,$(PVSBC_REQUIRE_ONE),$(if $(filter 1,$($(v))),,bad))),)
$(error PS2_PVS_BATCH_COMPOSE needs the qualified PVS/direct/chunk/lean/source preparation path at 1)
endif
ifneq ($(PS2_PVS_DEFAULT),0)
$(error PS2_PVS_BATCH_COMPOSE needs PS2_PVS_DEFAULT=0)
endif
ifneq ($(filter-out 0,$(WORLD_SCRATCH) $(TA_GUARD) $(PS2_WORLD_TRANSITION_OWNER) $(PS2_WORLD_R11F_OWNER) $(SCENERY_PIECE_STATE) $(SCENERY_DEDUP) $(SCENERY_CONE) $(CPU_BACKFACE) $(TA_MATERIAL_DIAG) $(WORLD_HOLE_DIAG) $(PS2_WORLD_PREFLIGHT_DIAG)),)
$(error PS2_PVS_BATCH_COMPOSE has an unqualified owner, scratch or diagnostic path)
endif
ifneq ($(filter-out 0 1,$(PS2_INTERIOR_CULL)),)
$(error PS2_PVS_BATCH_COMPOSE does not qualify interior header-check mode)
endif
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_PVS_BATCH_COMPOSE=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_PVS_DEFAULT=0
endif
SCENERY_SUBMIT_BATCH ?= 0
ifneq ($(SCENERY_SUBMIT_BATCH),0)
ifneq ($(SCENERY_SUBMIT_BATCH),1)
$(error SCENERY_SUBMIT_BATCH must be 0 or 1)
endif
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_SUBMIT_BATCH needs SCENERY_CHUNK)
endif
ifneq ($(TA_DIRECT)$(MESH_DIRECT)$(PS2_WORLD_MESH)$(PS2_WORLD_HDR_CACHE),1111)
$(error SCENERY_SUBMIT_BATCH needs TA_DIRECT=1 MESH_DIRECT=1 PS2_WORLD_MESH=1 PS2_WORLD_HDR_CACHE=1)
endif
ifeq ($(PS2_PVS_BATCH_COMPOSE),0)
ifneq ($(filter-out 0,$(PS2_PVS) $(WORLD_SCRATCH) $(TA_GUARD)),)
$(error SCENERY_SUBMIT_BATCH does not yet qualify PS2_PVS, WORLD_SCRATCH or TA_GUARD)
endif
else
ifneq ($(filter-out 0,$(WORLD_SCRATCH) $(TA_GUARD)),)
$(error SCENERY_SUBMIT_BATCH does not qualify WORLD_SCRATCH or TA_GUARD)
endif
endif
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_SUBMIT_BATCH=1
endif
# SCENERY_REPLAY_LEAN=1 (exact, render only): reuse one emitter per chunk replay,
# retain the existing inside-cluster decisions and avoid screen-memo key copies.
# Composes independently with SCENERY_SELECT_ONLY and SCENERY_SUBMIT_BATCH.
SCENERY_REPLAY_LEAN ?= 0
ifneq ($(SCENERY_REPLAY_LEAN),0)
ifneq ($(SCENERY_REPLAY_LEAN),1)
$(error SCENERY_REPLAY_LEAN must be 0 or 1)
endif
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_REPLAY_LEAN needs SCENERY_CHUNK)
endif
ifneq ($(TA_DIRECT)$(MESH_DIRECT)$(PS2_WORLD_MESH),111)
$(error SCENERY_REPLAY_LEAN needs TA_DIRECT=1 MESH_DIRECT=1 PS2_WORLD_MESH=1)
endif
ifneq ($(filter-out 0,$(WORLD_SCRATCH)),)
$(error SCENERY_REPLAY_LEAN needs WORLD_SCRATCH=0 (ordinary per-part scratch lifetime))
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_REPLAY_LEAN=1
endif
# Capture each queued draw's dynamic owner UV offset before its owner scope ends.
# Restores the pending draw across capacity drains; no change for static offsets.
SCENERY_UV_SNAPSHOT ?= 0
ifneq ($(SCENERY_UV_SNAPSHOT),0)
ifneq ($(SCENERY_UV_SNAPSHOT),1)
$(error SCENERY_UV_SNAPSHOT must be 0 or 1)
endif
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_UV_SNAPSHOT needs SCENERY_CHUNK)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_UV_SNAPSHOT=1
endif
# SCENERY_SELECT_LEAN2=1 (exact, render only): read packed meshlet bounds
# directly and share each crossed plane across its groups, returning final picks.
SCENERY_SELECT_LEAN2 ?= 0
ifneq ($(SCENERY_SELECT_LEAN2),0)
ifneq ($(SCENERY_SELECT_LEAN2),1)
$(error SCENERY_SELECT_LEAN2 must be 0 or 1)
endif
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_SELECT_LEAN2 needs SCENERY_CHUNK)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_SELECT_LEAN2=1
endif
# SCENERY_EMIT_PREFETCH=1 (exact, render only): hint selected meshlet headers
# two picks ahead and their input one pick ahead, including the next queued
# part. Empty indexed picks skip the unused gather; nonempty gathers read the
# immutable vertex count once. Selection, binding and the strip walk stay exact.
SCENERY_EMIT_PREFETCH ?= 0
ifneq ($(SCENERY_EMIT_PREFETCH),0)
ifneq ($(SCENERY_EMIT_PREFETCH),1)
$(error SCENERY_EMIT_PREFETCH must be 0 or 1)
endif
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_EMIT_PREFETCH needs SCENERY_CHUNK)
endif
ifneq ($(TA_DIRECT)$(MESH_DIRECT)$(PS2_WORLD_MESH),111)
$(error SCENERY_EMIT_PREFETCH needs TA_DIRECT=1 MESH_DIRECT=1 PS2_WORLD_MESH=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_EMIT_PREFETCH=1
endif
# SCENERY_DEDUP=1 (exact, render only; needs SCENERY_CHUNK, MESH_VP_SCHED=1, HW_LEAN): each PS2 world meshlet's corners
# are reordered at room load (repeated grid positions last), and a draw transforms each position once and builds the
# repeats from it. Heap 4: 4 bytes per meshlet + 1 per repeat (r101 ~33 KB), freed with the room's world.
SCENERY_DEDUP ?= 0
# SCENERY_DEDUP=2: the same draw, but the tables are the room file's R4RC 'SCDD' section (scdd_compile.py; data set
# rc19s = rc19 + SCDD): no load-time hashing and no allocation of its own (the room file block, r101 43.9 KB). A room
# without the section, or a section that does not match the package, draws as knob off (SCNDEDUP log line says why).
ifneq ($(SCENERY_DEDUP),0)
ifeq ($(SCENERY_DEDUP),1)
$(error SCENERY_DEDUP=1 is retired: its load-time reorder moved plain meshlets that pool-indexed meshlets address; use 2)
endif
ifeq ($(filter 2 3,$(SCENERY_DEDUP)),)
$(error SCENERY_DEDUP must be 0, 2 or 3)
endif
# Mode3: byte-neutral offline ps2-dd3.* alternate; no SCDD table or load reorder.
ifeq ($(SCENERY_DEDUP),3)
# The header reader must have one definition in every translation unit.
GAME_CPPFLAGS += -DRE4DC_SCENERY_DEDUP=3
PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_DEDUP=3
ifneq ($(IO_ALIGNED),1)
$(error SCENERY_DEDUP=3 needs IO_ALIGNED=1 for source header binding)
endif
ifeq ($(filter 1 2,$(PS2_WORLD_ROOMS)),)
$(error SCENERY_DEDUP=3 needs PS2_WORLD_ROOMS=1 or 2)
endif
ifneq ($(filter-out 0,$(WORLD_VERT) $(SCENERY21_AB)),)
$(error SCENERY_DEDUP=3 uses its own alternate data; WORLD_VERT and SCENERY21_AB must be 0)
endif
endif
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_DEDUP needs SCENERY_CHUNK)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_DEDUP=$(SCENERY_DEDUP)
# SCENERY_DEDUP_LOADONLY=1 (test arm only): with =2, the section is loaded but not applied (equalises heap 4).
ifeq ($(SCENERY_DEDUP_LOADONLY),1)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_DEDUP_LOADONLY=1
endif
# SCENERY_DEDUP_CHECK=1 (check build only): every built repeat compared with the knob-off kernel, mismatches logged.
ifeq ($(SCENERY_DEDUP_CHECK),1)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_DEDUP_CHECK=1
endif
endif
# SCENERY_UNIT_CONCAT=1 (exact, render only; needs SCENERY_CHUNK): ps2_pass skips concat_u's products for a placement
# whose rotation / scale part is exactly the identity (Ninja guide NJD_EVAL_UNIT_ANG / SCL): r103 134 of 134 placements,
# r100 180 of 283, r101 15 of 223. Check: PS2_WORLD_LEAN with bit 8 counts check_bad against concat.
SCENERY_UNIT_CONCAT ?= 0
ifneq ($(SCENERY_UNIT_CONCAT),0)
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_UNIT_CONCAT needs SCENERY_CHUNK)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_UNIT_CONCAT=1
endif
# SCENERY_SCREEN_MEMO=1 (exact, render only): load_screen reloads its last matrix when the inputs (mvq, projection
# p[1..4], viewport) match the last call, instead of rebuilding it.
SCENERY_SCREEN_MEMO ?= 0
ifneq ($(SCENERY_SCREEN_MEMO),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_SCREEN_MEMO=1
endif
# SCENERY_FAR_LOD=<n> (approximation, render only): the PS2 world's LOD pick allows n times the quality setting's
# projected error (lod_px), so distant clusters take coarser levels sooner. 0 = off (default).
SCENERY_FAR_LOD ?= 0
ifneq ($(SCENERY_FAR_LOD),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_FAR_LOD=$(SCENERY_FAR_LOD)
endif
# CHUNK_SUBMIT=1: the shared chunk-submit back end (platform/chunk_submit.h / .cpp) for user lanes
# (character-draw-path, rigid models). Default 0: not built.
CHUNK_SUBMIT ?= 0
ifneq ($(CHUNK_SUBMIT),0)
$(OBJDIR)/platform/chunk_submit.o: PLATFORM_CPPFLAGS += -O2 -DRE4DC_CHUNK_SUBMIT=1
endif
# --- lane scenery21 (scenery-pieces, P2 second half; SCENERY21-STATUS.md). Default 0: no code, image unchanged.
# Data: the sc21 set (tools/d367/scenery21/scn21_build.py): every PS2 world room's package with facing-grouped strip groups
# (ps2-world.re4mesh + ps2-world.r4sg) and its room file with the SCCN / SCPS sections. Without the data (or with a stale
# section) each knob logs why and draws as knob off for that room.
# SCENERY_CONE=1 (render only; needs SCENERY_CHUNK, PS2_STRIP_GROUPS): per strip group back-face cone (SCCN); chunk_select
# drops a group whose every triangle faces the side the part's cull removes. SCENERY_CONE_SIGN=+1|-1: the projection's
# handedness (fixed; calibrated by the look check).
SCENERY_CONE ?= 0
SCENERY_CONE_SIGN ?= 1
ifneq ($(SCENERY_CONE),0)
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_CONE needs SCENERY_CHUNK)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_CONE=1 -DRE4DC_SCENERY_CONE_SIGN=$(SCENERY_CONE_SIGN)
endif
# SCENERY_PIECE_STATE=1 (exact; needs PS2_WORLD_HDR_CACHE): per part header-slot word (SCPS): a bind goes straight to its
# header-cache slot (still checked: key, entry, VRAM address) instead of hashing and scanning the set.
SCENERY_PIECE_STATE ?= 0
ifneq ($(SCENERY_PIECE_STATE),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_PIECE_STATE=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_PIECE_STATE=1
endif
# SCENERY21_AB=1 (console A/B bench disc only; needs BENCHMARK=1): arm B (bench start screen) reads each room's sc21 package
# / strip groups / room file from dc/native/rXXX/sc21/ when present and turns SCENERY_CONE / SCENERY_PIECE_STATE on; arm A
# reads the shipped files with both off.
SCENERY21_AB ?= 0
ifneq ($(SCENERY21_AB),0)
ifneq ($(BENCHMARK),1)
$(error SCENERY21_AB needs BENCHMARK=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY21_AB=1
ROOMFILE_SECTIONS += -DRE4DC_SCENERY21_AB=1
endif
