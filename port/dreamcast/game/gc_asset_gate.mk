# Included by game/Makefile only after the runtime callsite patch is integrated.
# Off emits no flags, dependencies or linked object, preserving program bytes.
GC_ASSET_GATE ?= 0
GC_ASSET_CATALOG_SHA256 ?= 0
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/gc_asset_gate.o,$(PLATFORM_OBJS))
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/gc_asset_members.o,$(PLATFORM_OBJS))
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/gc_asset_disc.o,$(PLATFORM_OBJS))
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/gc_asset_payloads.o,$(PLATFORM_OBJS))
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/gc_asset_audio.o,$(PLATFORM_OBJS))
ifeq ($(filter $(GC_ASSET_GATE),0 1),)
$(error GC_ASSET_GATE must be 0 or 1)
endif
ifeq ($(GC_ASSET_GATE),1)
ifneq ($(PVR_STREAM),1)
$(error GC_ASSET_GATE requires PVR_STREAM=1; buffered nonstream consumption is not qualified)
endif
ifneq ($(AICA_AUDIO),1)
$(error GC_ASSET_GATE requires AICA_AUDIO=1; silent-backend lifecycle coverage is not qualified)
endif
PLATFORM_CPPFLAGS += -DRE4DC_GC_ASSET_GATE=1
PLATFORM_CPPFLAGS += -DRE4DC_GC_ASSET_CATALOG_SHA256=\"$(GC_ASSET_CATALOG_SHA256)\"
GAME_CPPFLAGS += -DRE4DC_GC_ASSET_GATE=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_GC_ASSET_COARSE_LEON=$(COARSE_LEON)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_GC_ASSET_LEON_HAND_PACK=$(if $(and $(filter 1,$(COARSE_LEON)),$(filter 1,$(ACTOR_TRANSACTION))),$(or $(LEON_HAND_PACK),0),0)
$(OBJDIR)/platform/native_movie_stream.o: KOS_CFLAGS += -DRE4DC_GC_ASSET_GATE=1
$(OBJDIR)/platform/room_file.o: KOS_CFLAGS += -DRE4DC_GC_ASSET_GATE=1
PLATFORM_OBJS += $(OBJDIR)/platform/gc_asset_gate.o
PLATFORM_OBJS += $(OBJDIR)/platform/gc_asset_members.o
PLATFORM_OBJS += $(OBJDIR)/platform/gc_asset_disc.o
PLATFORM_OBJS += $(OBJDIR)/platform/gc_asset_payloads.o
PLATFORM_OBJS += $(OBJDIR)/platform/gc_asset_audio.o
endif
