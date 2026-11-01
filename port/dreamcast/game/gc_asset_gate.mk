# Included by game/Makefile only after the runtime callsite patch is integrated.
# Off emits no flags, dependencies or linked object, preserving program bytes.
GC_ASSET_GATE ?= 0
GC_ASSET_MOTION_UNKNOWN ?= 0
ifneq ($(GC_ASSET_MOTION_UNKNOWN),0)
ifneq ($(GC_ASSET_MOTION_UNKNOWN),1)
$(error GC_ASSET_MOTION_UNKNOWN must be 0 or 1)
endif
ifneq ($(GC_ASSET_GATE),1)
$(error GC_ASSET_MOTION_UNKNOWN requires GC_ASSET_GATE=1)
endif
endif
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/gc_asset_motion_unknown.o,$(PLATFORM_OBJS))
# GC_ASSET_CATALOG_PIN_FILE=<file> (gate-ON twins): read the catalog pin from tools/d367/gc_port23/make_catalog.sh output
# (<out>/gc-assets.pin) instead of passing GC_ASSET_CATALOG_SHA256. Empty by default: no effect.
GC_ASSET_CATALOG_PIN_FILE ?=
ifneq ($(GC_ASSET_CATALOG_PIN_FILE),)
GC_ASSET_CATALOG_SHA256 := $(strip $(shell cat $(GC_ASSET_CATALOG_PIN_FILE)))
endif
GC_ASSET_CATALOG_SHA256 ?= 0
# GC_ASSET_PROF=1 (requires GC_ASSET_GATE=1): log texture fingerprint / catalog read time (GC-ASSET-PROF). Diagnostic.
GC_ASSET_PROF ?= 0
ifneq ($(GC_ASSET_PROF),0)
ifneq ($(GC_ASSET_PROF)$(GC_ASSET_GATE),11)
$(error GC_ASSET_PROF=1 requires GC_ASSET_GATE=1)
endif
PLATFORM_CPPFLAGS += -DRE4DC_GC_ASSET_PROF=1
endif
# GC_ASSET_SRC=1 (requires GC_ASSET_GATE=1): log each payload capture's digest prefix, entry point and caller (GC-ASSET-SRC). Diagnostic only: judge.py rejects GC-ASSET-SRC lines, so never in a gate run.
GC_ASSET_SRC ?= 0
ifneq ($(GC_ASSET_SRC),0)
ifneq ($(GC_ASSET_SRC)$(GC_ASSET_GATE),11)
$(error GC_ASSET_SRC=1 requires GC_ASSET_GATE=1)
endif
PLATFORM_CPPFLAGS += -DRE4DC_GC_ASSET_SRC=1
endif
# GC_ASSET_HARVEST=1: offline catalog harvest build (logs catalog misses, no quarantine). Not a gate run.
GC_ASSET_HARVEST ?= 0
ifneq ($(GC_ASSET_HARVEST),0)
ifneq ($(GC_ASSET_HARVEST)$(GC_ASSET_GATE),11)
$(error GC_ASSET_HARVEST=1 requires GC_ASSET_GATE=1)
endif
PLATFORM_CPPFLAGS += -DRE4DC_GC_ASSET_HARVEST=1
endif
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

ifeq ($(GC_ASSET_MOTION_UNKNOWN),1)
ifneq ($(NATIVE_ACTOR)$(NATIVE_ACTOR_FAST),11)
$(error GC_ASSET_MOTION_UNKNOWN supports only NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1)
endif
# This detector has partial route coverage. Raw TR / shadow and alternate world
# emitters are not admitted as complete Motion coverage; wired remains unchanged.
PLATFORM_CPPFLAGS += -DRE4DC_GC_ASSET_MOTION_UNKNOWN=1
GAME_CPPFLAGS += -DRE4DC_GC_ASSET_MOTION_UNKNOWN=1
PLATFORM_OBJS += $(OBJDIR)/platform/gc_asset_motion_unknown.o
endif
