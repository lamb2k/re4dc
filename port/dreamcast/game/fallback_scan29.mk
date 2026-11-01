# Build 29: only explicitly converted FE/v3 offline bakes use this reader.
FALLBACK_SCAN29 ?= 0
ifneq ($(words $(FALLBACK_SCAN29)),1)
$(error FALLBACK_SCAN29 must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(FALLBACK_SCAN29)),)
$(error FALLBACK_SCAN29 must be 0 or 1)
endif
ifeq ($(FALLBACK_SCAN29),1)
ifneq ($(NATIVE_ACTOR)$(NATIVE_ACTOR_FAST),11)
$(error FALLBACK_SCAN29=1 needs NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1)
endif
ifneq ($(MODEL_STREAM_FIX),1)
$(error FALLBACK_SCAN29=1 needs MODEL_STREAM_FIX=1 for preencoded source streams)
endif
ifneq ($(NATIVE_ACTOR_PRELIT),1)
$(error FALLBACK_SCAN29=1 needs NATIVE_ACTOR_PRELIT=1)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_FALLBACK_SCAN29=1
endif
