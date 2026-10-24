# t2exact.mk - lane t2exact (2026-10-15): tranche 2 exact levers of PERF-BACKLOG-CH1-2 (A2b, B5; B4 and B6 were dropped: docs/lanes/t2exact.md). Every
# knob defaults to 0: no effect, the image is unchanged. docs/lanes/t2exact.md has the measurements and gates.
#
# GC_CENSUS_TRIM=1 (A2b; exact, render only): the GC render census's leftover per-call work, without a change to any
# value: (#3) gx_fast.h - the hot GXGetProjectionv / GXGetViewportv / GXSetProjection callers (re4dc_draw_model_part,
# EspCommonTrans, the ID quad, CameraSetProjection) copy / store gx_stub.cpp's state words inline; (#11) trans.cpp
# sourceActorIdentity reads room heap 4's live flag and generation in place of re4dc_room4_state(), and
# re4dc_coarse_actor_source / re4dc_coarse_ganado_source find a static chunk table element from the table's
# address range (chunk_find.h) instead of comparing every element. Census #12 (re4dc_model_diagnostic_enabled) is
# lane g1parts' G1_DIAG_INLINE and is not repeated here.
GC_CENSUS_TRIM ?= 0
ifneq ($(GC_CENSUS_TRIM),0)
ifneq ($(GC_CENSUS_TRIM),1)
$(error GC_CENSUS_TRIM must be 0 or 1)
endif
# gx_stub.cpp's GXGetViewportv adds the alternate-line jitter when RES_ALTERNATE is on (game30.mk: RENDER_OPTION=1
# without RENDER_DOUBLE=1); the inline copy must do the same (gx_stub.cpp checks the two agree).
T2X_GXF_JITTER := $(if $(filter 1,$(RENDER_OPTION)),$(if $(filter 1,$(RENDER_DOUBLE)),0,1),0)
GAME_CPPFLAGS += -DRE4DC_GC_CENSUS_TRIM=1 -DRE4DC_GXF_JITTER=$(T2X_GXF_JITTER)
PLATFORM_CPPFLAGS += -DRE4DC_GC_CENSUS_TRIM=1 -DRE4DC_GXF_JITTER=$(T2X_GXF_JITTER)
endif
#
# HOT_COLD_SPLIT=1 (B5; exact, code placement only): every C++ / C object is compiled with -include cold_decls.h, which
# declares the port's diagnostic report functions cold (re4dc_log, re4dc_missing). GCC then predicts the blocks that
# only lead to such a call as never taken and lays them out after the hot
# path of their function, so a hot function's cache lines hold more of the code it runs every frame (and the image is
# ~4 KB smaller). Not used: -freorder-blocks-and-partition (cold blocks in a separate section) does not assemble on SH
# ("pcrel too far": the constant pools stay with the hot part), and -freorder-blocks-algorithm=stc for the -O1 objects
# grew the image by 13 KB with no fewer I-cache fills (MODELLED; docs/lanes/t2exact.md). The game's results are
# unchanged (block placement only; fp-contract stays off). An I-cache lever: the hw model counts the fills, the console
# A/B (benchmark disc, same-tree control) prices them.
HOT_COLD_SPLIT ?= 0
ifneq ($(HOT_COLD_SPLIT),0)
ifneq ($(HOT_COLD_SPLIT),1)
$(error HOT_COLD_SPLIT must be 0 or 1)
endif
T2X_COLD_FLAGS = -include $(abspath cold_decls.h)
GAME_CPPFLAGS += $(T2X_COLD_FLAGS)
PLATFORM_CPPFLAGS += $(T2X_COLD_FLAGS)
endif
#
# PS2_PVS=1 (B4 rescoped by the coordinator 10-15: an offline potentially visible set; exact, render only; needs
# PS2_WORLD_ROOMS and MESH_LOD): native_static.cpp namespace pvs reads /cd/dc/native/rXXX/ps2-world.pvs (built by
# tools/d367/ps2world/pvs: pvs_prep.py, pvs_cast.cpp, pvs_emit.py) for the room's package. Per frame the camera's cell
# gives a bit set over the package's cluster instances; ps2_pass skips a cluster whose bit is clear (it cannot be seen
# from anywhere in the cell: the opaque world occludes it) and a placement with none set. No file, another package's
# file, or a camera outside the cells: everything is drawn as before. Runtime toggle re4dc_ps2_pvs_on (default
# PS2_PVS_DEFAULT, 1), warp line "pvs 0|1", re4dc_ps2_pvs_set() for a benchmark sweep row.
PS2_PVS ?= 0
PS2_PVS_DEFAULT ?= 1
ifneq ($(PS2_PVS),0)
ifneq ($(PS2_PVS),1)
$(error PS2_PVS must be 0 or 1)
endif
ifeq ($(PS2_WORLD_ROOMS),0)
$(error PS2_PVS needs PS2_WORLD_ROOMS=1 or 2)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_PVS=1 -DRE4DC_PS2_PVS_DEFAULT=$(PS2_PVS_DEFAULT)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_PVS=1
ifneq ($(strip $(PVS23_CERTIFICATES)),)
# Private generated descriptor; its absolute path and SHA belong in the QA manifest.
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PVS23_CERTIFICATES=\"$(PVS23_CERTIFICATES)\"
endif
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_PS2_PVS=1
endif
#
# PS2_PVS_EFFECTIVE0_SOURCES=1: permit an actual nonempty base source when
# every higher authored level is empty and the real nonempty fallback is active.
# Source receipts/material/numeric guards and the sixteen-panel cap are unchanged.
PS2_PVS_EFFECTIVE0_SOURCES ?= 0
ifneq ($(PS2_PVS_EFFECTIVE0_SOURCES),0)
ifneq ($(PS2_PVS_EFFECTIVE0_SOURCES),1)
$(error PS2_PVS_EFFECTIVE0_SOURCES must be 0 or 1)
endif
ifneq ($(PS2_PVS),1)
$(error PS2_PVS_EFFECTIVE0_SOURCES needs PS2_PVS=1)
endif
ifneq ($(MESH_LOD),1)
$(error PS2_PVS_EFFECTIVE0_SOURCES needs MESH_LOD=1)
endif
ifeq ($(filter 1 2,$(PS2_WORLD_ROOMS)),)
$(error PS2_PVS_EFFECTIVE0_SOURCES needs PS2_WORLD_ROOMS=1 or 2)
endif
ifneq ($(PS2_WORLD_NONEMPTY_LOD),1)
$(error PS2_PVS_EFFECTIVE0_SOURCES needs PS2_WORLD_NONEMPTY_LOD=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_PVS_EFFECTIVE0_SOURCES=1
endif
#
# SG_SELECT_LEAN=1 (job 2; exact, render only; needs PS2_STRIP_GROUPS=1): lean::sg_select_lean / sg_coef_lean /
# box_mask_lean in native_static.cpp give the same results bit for bit, cheaper: each plane keeps only its non-zero
# terms of the knob-off fmac chain, in the same order (P = max(n, 0), Q = min(n, 0): one per axis; a +0 term leaves
# the value as it was), the crossed planes are picked without a shift loop, the group box is converted once, the
# plane records are read in order, and the meshlet's group records are prefetched as soon as box_mask_lean says it
# crosses a plane. box_mask_lean is box_mask's expressions with the plane loop written out. =2: the check build (both
# versions run, every output compared, SGLEAN ... sel_bad / bm_bad counted). Runtime switch re4dc_sg_lean_on (1; warp
# line "sglean 0|1", re4dc_sg_select_lean_set() for a benchmark POC disc row): 0 runs the original functions.
SG_SELECT_LEAN ?= 0
ifneq ($(SG_SELECT_LEAN),0)
ifeq ($(filter 1 2,$(SG_SELECT_LEAN)),)
$(error SG_SELECT_LEAN must be 0, 1 or 2)
endif
ifneq ($(PS2_STRIP_GROUPS),1)
$(error SG_SELECT_LEAN needs PS2_STRIP_GROUPS=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SG_SELECT_LEAN=$(SG_SELECT_LEAN)
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_SG_SELECT_LEAN=$(SG_SELECT_LEAN)
endif
