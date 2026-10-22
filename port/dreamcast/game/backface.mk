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
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_BACKFACE_CENSUS=1
endif
# CPU_BACKFACE=1 (render only; room/backface_emit.hpp): world meshlets (native_static.cpp, direct store-queue sink) and
#   actor parts (native_actor_fast.cpp, ACTOR_DIRECT) whose PVR header culls (CCW / CW) send only the triangles the ISP
#   would keep: back runs at a strip end, and inner back runs of >= 3 triangles, are not written to the TA. Front faces go
#   out with the same vertex words and winding parity. Cull-none (double-sided) parts are unchanged: today that is every
#   owned actor except the registry bosses NMR_SOURCE_CULL selects (Del Lago 0x2F, ...). The lean strip walk
#   (MESH_STRIP_LEAN) is replaced by a C walk for culling parts. Default 0: no code.
CPU_BACKFACE ?= 0
ifneq ($(filter $(CPU_BACKFACE),0 1),$(CPU_BACKFACE))
$(error CPU_BACKFACE must be 0 or 1)
endif
ifeq ($(CPU_BACKFACE),1)
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_CPU_BACKFACE=1
endif
# ACTOR_BACKFACE=1 (render, look change; needs CPU_BACKFACE=1): Leon, the Ganados and El Gigante (owned path) use the source model's cull
#   mode instead of cull none, so CPU_BACKFACE drops their back faces too; alpha-mask and no-depth-write materials stay
#   double-sided. Default 0: no code.
ACTOR_BACKFACE ?= 0
ifneq ($(filter $(ACTOR_BACKFACE),0 1),$(ACTOR_BACKFACE))
$(error ACTOR_BACKFACE must be 0 or 1)
endif
ifeq ($(ACTOR_BACKFACE),1)
ifneq ($(CPU_BACKFACE),1)
$(error ACTOR_BACKFACE=1 needs CPU_BACKFACE=1)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_BACKFACE=1
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_BACKFACE=1
endif
