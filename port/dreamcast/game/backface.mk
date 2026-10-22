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
$(OBJDIR)/platform/backface_sh4.o: KOS_CFLAGS += -DRE4DC_BACKFACE_SH4_TRACE=1
endif
$(OBJDIR)/platform/backface_sh4.o: platform/backface_sh4.S
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -c $< -o $@
endif
# ACTOR_BACKFACE=1 (render, look change; needs CPU_BACKFACE=1 or 2): Leon, the Ganados and El Gigante (owned path) use the source model's cull
#   mode instead of cull none, so CPU_BACKFACE drops their back faces too; alpha-mask and no-depth-write materials stay
#   double-sided. Default 0: no code.
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
