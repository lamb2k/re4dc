# Build 32: qualification and admission diagnostics for the existing actor
# cone and UV16 controls. Zero adds no definitions or object selection.
ACTOR_FORMAT32 ?= 0
ifneq ($(words $(ACTOR_FORMAT32)),1)
$(error ACTOR_FORMAT32 must be one value, 0 or 1)
endif

# EF01 first consumed slice: immutable owned FE geometry and exact UV spans.
# This changes shared part/chunk layouts, so every game/platform TU agrees.
# Zero adds no definitions and retains the previous ABI.
ACTOR_SOURCE_SPAN ?= 0
ifneq ($(words $(ACTOR_SOURCE_SPAN)),1)
$(error ACTOR_SOURCE_SPAN must be one value, 0 or 1)
endif
ifeq ($(filter $(ACTOR_SOURCE_SPAN),0 1),)
$(error ACTOR_SOURCE_SPAN must be 0 or 1)
endif
ifeq ($(ACTOR_SOURCE_SPAN),1)
ifneq ($(ACTOR_FORMAT32)$(NATIVE_ACTOR_UV16)$(ACTOR_TRANSACTION)$(NATIVE_ACTOR_SKIN_LAZY),1111)
$(error ACTOR_SOURCE_SPAN needs ACTOR_FORMAT32=1 NATIVE_ACTOR_UV16=1 ACTOR_TRANSACTION=1 NATIVE_ACTOR_SKIN_LAZY=1)
endif
GAME_CPPFLAGS += -DRE4DC_ACTOR_SOURCE_SPAN=1
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_SOURCE_SPAN=1
endif
ifeq ($(filter $(ACTOR_FORMAT32),0 1),)
$(error ACTOR_FORMAT32 must be 0 or 1)
endif
ifeq ($(ACTOR_FORMAT32),1)
ifneq ($(NATIVE_ACTOR)$(NATIVE_ACTOR_FAST),11)
$(error ACTOR_FORMAT32 needs NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1)
endif
$(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_FORMAT32=1
endif
