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

# PROP_GATE_EARLY01=1: before constructing the gate's pose bound, refuse an
# empty info list or a fully bounded head info with an existing reason-4
# metadata failure / already materialized position buffer (reason 5).
# This never culls a model. Unknown spans, skipped head infos, stream headers,
# weights and lazy-skin registry checks retain the original path.
PROP_GATE_EARLY01 ?= 0
ifneq ($(PROP_GATE_EARLY01),0)
ifneq ($(PROP_GATE_EARLY01),1)
$(error PROP_GATE_EARLY01 must be 0 or 1)
endif
endif
ifneq ($(PROP_GATE_EARLY01),0)
ifneq ($(PROP_GATE),1)
ifneq ($(PROP_GATE),2)
$(error PROP_GATE_EARLY01 needs PROP_GATE=1 or 2)
endif
endif
ifneq ($(FRONT_NATIVE),1)
ifneq ($(FRONT_NATIVE),2)
$(error PROP_GATE_EARLY01 needs FRONT_NATIVE=1 or 2)
endif
endif
ifneq ($(SCENERY_GATE),1)
$(error PROP_GATE_EARLY01 needs SCENERY_GATE=1)
endif
ifneq ($(FRONT_LEAN),1)
$(error PROP_GATE_EARLY01 needs FRONT_LEAN=1)
endif
ifneq ($(NATIVE_ACTOR_SKIN_LAZY),1)
$(error PROP_GATE_EARLY01 needs NATIVE_ACTOR_SKIN_LAZY=1)
endif
ifneq ($(SKIN_PALETTE_LAZY),1)
ifneq ($(SKIN_PALETTE_LAZY),2)
$(error PROP_GATE_EARLY01 needs SKIN_PALETTE_LAZY=1 or 2)
endif
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PROP_GATE_EARLY01=1
endif
