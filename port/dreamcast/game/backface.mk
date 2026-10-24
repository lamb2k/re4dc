# Lane backface22 (2026-10-22; BASEBALL-RENDERER-ASSESSMENT-20261022.md item 1). Default 0: no code, image unchanged.
# BACKFACE_CENSUS=1 (test builds only, needs TA_HASH=1): platform/backface_census.cpp watches every TA burst (the TA_HASH
#   hooks) and logs "bfc:" lines per draw class every 60 presented scenes: strip vertices, vertices of culling strips,
#   triangles, back triangles, vertices in back runs of >= 3 triangles and vertices a strip split would save, under both
#   PVR sign conventions (h0/h1). Classes (platform/include/bfc_class.h): 1 PS2 world, 2 static parts, 3 Leon,
#   4 Ganados, 5 other actors (bosses, animals, Ashley; id = largest model id), 0 everything else.
BACKFACE_CENSUS ?= 0
ifneq ($(filter $(BACKFACE_CENSUS),0 1),$(BACKFACE_CENSUS))
$(error BACKFACE_CENSUS must be 0 or 1)
endif
ifeq ($(BACKFACE_CENSUS),1)
ifneq ($(TA_HASH),1)
$(error BACKFACE_CENSUS=1 needs TA_HASH=1)
endif
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/backface_census.o: PLATFORM_CPPFLAGS += -DRE4DC_BACKFACE_CENSUS=1
$(OBJDIR)/coarse_actor.o $(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_BACKFACE_CENSUS=1
endif
# CPU_BACKFACE=1 (render only; room/backface_emit.hpp): world meshlets (native_static.cpp, direct store-queue sink) and
#   actor parts (native_actor_fast.cpp, ACTOR_DIRECT) whose PVR header culls (CCW / CW) send only the triangles the ISP
#   would keep: back runs at a strip end, and inner back runs of >= 3 triangles, are not written to the TA. Front faces go
#   out with the same vertex words and winding parity. Cull-none (double-sided) parts are unchanged: today that is every
#   owned actor except the registry bosses NMR_SOURCE_CULL selects (Del Lago 0x2F, ...). The lean strip walk
#   (MESH_STRIP_LEAN) is replaced by a C walk for culling parts. Default 0: no code.
CPU_BACKFACE ?= 0
ifneq ($(filter $(CPU_BACKFACE),0 1 2),$(CPU_BACKFACE))
$(error CPU_BACKFACE must be 0, 1 or 2)
endif
# BACKFACE_EARLY_CLIP=1 (render only, needs CPU_BACKFACE=2): once the
# first world outcode proves that all-depth/screen rejection is impossible,
# stop at the first later depth crossing before doing more facing work.
# Default 0 preserves the original kernel. Use a fresh OBJDIR for each arm.
# 2026-10-23 (user): exact shortcut, so it is part of CPU_BACKFACE=2 by default; =0 only for A/B.
ifeq ($(CPU_BACKFACE),2)
BACKFACE_EARLY_CLIP ?= 1
else
BACKFACE_EARLY_CLIP ?= 0
endif
ifneq ($(filter $(BACKFACE_EARLY_CLIP),0 1),$(BACKFACE_EARLY_CLIP))
$(error BACKFACE_EARLY_CLIP must be 0 or 1)
endif
ifeq ($(BACKFACE_EARLY_CLIP),1)
ifneq ($(CPU_BACKFACE),2)
$(error BACKFACE_EARLY_CLIP=1 needs CPU_BACKFACE=2)
endif
$(OBJDIR)/platform/backface_sh4.o: KOS_CFLAGS += -DSHZ_STRIP_EARLY_CLIP=1
endif
ifneq ($(CPU_BACKFACE),0)
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_CPU_BACKFACE=$(CPU_BACKFACE)
endif
# CPU_BACKFACE=2 keeps facing/run rejection in the SH-4 strip emitter. The
# assembly is linked only for this arm; OFF and the C reference gain no object.
ifeq ($(CPU_BACKFACE),2)
ifneq ($(GAME_SH4ZAM),1)
$(error CPU_BACKFACE=2 needs GAME_SH4ZAM=1)
endif
PLATFORM_OBJS += $(OBJDIR)/platform/backface_sh4.o
# This file is included after the main link target's prerequisites were expanded.
$(TARGET): $(OBJDIR)/platform/backface_sh4.o
ifneq ($(filter-out 0 4,$(TA_HASH)),)
PLATFORM_OBJS += $(OBJDIR)/platform/backface_sh4_trace.o
$(TARGET): $(OBJDIR)/platform/backface_sh4_trace.o
$(OBJDIR)/platform/backface_sh4.o: KOS_CFLAGS += -DSHZ_STRIP_TRACE=1 -DSHZ_STRIP_TRACE_CALLBACK=_re4dc_backface_sh4_trace
endif
# The complete classifier/run/copy implementation is a reproducible patch to
# the fetchable clean SDK pin. CPU0/C1 acquire no SDK overlay or extra object.
BACKFACE_SDK_OVERLAY := $(OBJDIR)/sh4zam-strip-sdk
BACKFACE_SDK_TOOLS := ../tools/d367/backface_sh4zam_fused
BACKFACE_SDK_MANIFEST := $(BACKFACE_SDK_TOOLS)/manifest.json
BACKFACE_SDK_CPPFLAGS := -I$(BACKFACE_SDK_OVERLAY)/include
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += $(BACKFACE_SDK_CPPFLAGS)
PLATFORM_OBJS += $(OBJDIR)/platform/backface_sh4_walk.o
$(TARGET): $(OBJDIR)/platform/backface_sh4_walk.o
.PHONY: backface-sh4zam-verify
backface-sh4zam-verify:
	python3 ../tools/d367/backface_sh4zam_sdk/generate.py --check
	python3 $(BACKFACE_SDK_TOOLS)/materialize.py --output $(BACKFACE_SDK_OVERLAY)
	python3 $(BACKFACE_SDK_TOOLS)/check_area.py --overlay $(BACKFACE_SDK_OVERLAY)
$(OBJDIR)/platform/backface_sh4.o $(OBJDIR)/platform/backface_sh4_walk.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_actor_fast.o: | backface-sh4zam-verify
$(OBJDIR)/platform/backface_sh4.o: $(BACKFACE_SDK_MANIFEST) $(BACKFACE_SDK_TOOLS)/0001-strip-sq-api.patch $(BACKFACE_SDK_TOOLS)/materialize.py $(BACKFACE_SDK_TOOLS)/check_area.py
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) $(BACKFACE_SDK_CPPFLAGS) -c $(BACKFACE_SDK_OVERLAY)/source/shz_strip.S -o $@
$(OBJDIR)/platform/backface_sh4_walk.o: $(BACKFACE_SDK_MANIFEST) $(BACKFACE_SDK_TOOLS)/0001-strip-sq-api.patch $(BACKFACE_SDK_TOOLS)/materialize.py $(BACKFACE_SDK_TOOLS)/check_area.py
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(BACKFACE_SDK_CPPFLAGS) -fno-fast-math -ffp-contract=fast -c $(BACKFACE_SDK_OVERLAY)/source/shz_strip.cpp -o $@

endif
# ACTOR_BACKFACE=1 (render, look change; needs CPU_BACKFACE=1 or 2): Leon, the Ganados and El Gigante (owned path) use the source model's cull
#   mode instead of cull none, so CPU_BACKFACE drops their back faces too; alpha-mask and no-depth-write materials stay
#   double-sided. Default 0: no code.
# BACKFACE_KEEP_ALL=1 (test only, needs CPU_BACKFACE=1): the C walk runs its facing test but keeps every triangle, to
#   separate the walk change's cost from the drop (lane backface-sh4zam23 census). Default 0: no code.
BACKFACE_KEEP_ALL ?= 0
ifeq ($(BACKFACE_KEEP_ALL),1)
ifneq ($(CPU_BACKFACE),1)
$(error BACKFACE_KEEP_ALL=1 needs CPU_BACKFACE=1)
endif
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_BACKFACE_KEEP_ALL=1
endif
ACTOR_BACKFACE ?= 0
ifneq ($(filter $(ACTOR_BACKFACE),0 1),$(ACTOR_BACKFACE))
$(error ACTOR_BACKFACE must be 0 or 1)
endif
ifeq ($(ACTOR_BACKFACE),1)
ifeq ($(filter $(CPU_BACKFACE),1 2),)
$(error ACTOR_BACKFACE=1 needs CPU_BACKFACE=1 or 2)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_BACKFACE=1
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_BACKFACE=1
endif
# ACTOR_BACKFACE_CONE=1 (lane backface-cone23, 2026-10-23; render only, look change as ACTOR_BACKFACE): Leon, the Ganados,
#   El Gigante and Ashley take the source model's cull (alpha-mask / no-depth-write materials stay double-sided, as
#   ACTOR_BACKFACE), so the ISP drops their back faces; their opaque parts are converted with strips split by
#   (skinning palette entry, facing) and each meshlet gets a normal cone in its palette entry's space. A meshlet whose
#   whole cone faces away from the camera is skipped before its skinning transform, lighting and TA writes; the rest draw
#   through the unchanged paths (no per-triangle CPU test). =2: check build (rejected meshlets are transformed and
#   every triangle checked with the TA's area rule; "ABFC ... bad=" must stay 0). Census: "ABFC"/"ABFC2" log lines.
#   Not with ACTOR_BACKFACE=1 (it is a superset of its cull choice). Default 0: no code.
ACTOR_BACKFACE_CONE ?= 0
ifneq ($(filter $(ACTOR_BACKFACE_CONE),0 1 2),$(ACTOR_BACKFACE_CONE))
$(error ACTOR_BACKFACE_CONE must be 0, 1 or 2)
endif
ifneq ($(ACTOR_BACKFACE_CONE),0)
ifeq ($(ACTOR_BACKFACE),1)
$(error ACTOR_BACKFACE_CONE replaces ACTOR_BACKFACE=1; set only one)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_BACKFACE=1 -DRE4DC_ACTOR_BACKFACE_CONE=$(ACTOR_BACKFACE_CONE)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_BACKFACE=1 -DRE4DC_ACTOR_BACKFACE_CONE=1
endif
# BACKFACE_CONE=1 (world; lane backface-cone23): the world half of the cone pair is lane scenery21's SCENERY_CONE (per PS2
#   strip group back-face cone, chunk_select; needs SCENERY_CHUNK=1 PS2_STRIP_GROUPS=1 and the sc21 data set). This alias
#   sets SCENERY_CONE=1 (Makefile, before engine_preview.mk reads it). Default 0: no code.
BACKFACE_CONE ?= 0
ifneq ($(filter $(BACKFACE_CONE),0 1),$(BACKFACE_CONE))
$(error BACKFACE_CONE must be 0 or 1)
endif
# BACKFACE_ROOMS=1 (lane fix-hideout23, issue #55 item 1; render only; needs CPU_BACKFACE=2): the CPU back-face cull runs
#   only in the rooms of BACKFACE_ROOM_LIST (pG->room_id values, comma separated; default 0x10d, the chapter 2-1 merchant
#   cave); in every other room the world and actor emitters send the TA what CPU_BACKFACE=0 sends. Why: the r10d cave draws
#   its whole world from the ladder arrival, 1.76 MB of TA parameters per scene MODELLED (TA_BIN_DIAG) against a
#   2,000,896 B bank (about 1.81 MB in FSAA) and 162 KB of the 230 KB OPB pool; the issue #55 console video shows a
#   multi-second frozen picture with a broken triangle there. With the cull the r10d peak is 1.13 MB / 99 KB (-36% / -39%).
#   The flag follows the room at each scene open (native_ui.cpp stream_open). Default 0: no code.
BACKFACE_ROOMS ?= 0
BACKFACE_ROOM_LIST ?= 0x10d
ifneq ($(filter $(BACKFACE_ROOMS),0 1),$(BACKFACE_ROOMS))
$(error BACKFACE_ROOMS must be 0 or 1)
endif
ifeq ($(BACKFACE_ROOMS),1)
ifneq ($(CPU_BACKFACE),2)
$(error BACKFACE_ROOMS=1 needs CPU_BACKFACE=2)
endif
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_BACKFACE_ROOMS=1 -DRE4DC_BACKFACE_ROOM_LIST=$(BACKFACE_ROOM_LIST)
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_BACKFACE_ROOMS=1
endif
