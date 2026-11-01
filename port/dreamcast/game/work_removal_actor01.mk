# Public work-removal spikes, 2026-11-01. Neither switch is a release enable.
# Defaults compile no additional code; the source restores diagnostic line numbers.
#
# ACTOR_PADDING_FIRST01=1: skip the existing 32..256-byte all-zero scan when
# byte zero already proves the actor list is nonempty. Zero-prefix lists retain
# a full zero proof. No cache, geometry, owner, or admission changes.
ACTOR_PADDING_FIRST01 ?= 0
ifneq ($(ACTOR_PADDING_FIRST01),0)
ifneq ($(ACTOR_PADDING_FIRST01),1)
$(error ACTOR_PADDING_FIRST01 must be 0 or 1)
endif
endif
ifneq ($(ACTOR_PADDING_FIRST01),0)
ifneq ($(NATIVE_ACTOR_FAST),1)
$(error ACTOR_PADDING_FIRST01 needs NATIVE_ACTOR_FAST=1 ACTOR_REPLAY_SKIN=1)
endif
ifneq ($(ACTOR_REPLAY_SKIN),1)
$(error ACTOR_PADDING_FIRST01 needs NATIVE_ACTOR_FAST=1 ACTOR_REPLAY_SKIN=1)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_PADDING_FIRST01=1
endif
