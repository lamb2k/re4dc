# Build32 review4: current-image cabin Luis through the existing registry owner.
# Default 0 adds no flags or resources. This first class keeps the ordinary
# static-material certificate and the existing palette/workspace capacities.
ACTOR_PRESENTATION32 ?= 0
ifneq ($(ACTOR_PRESENTATION32),0)
ifneq ($(ACTOR_PRESENTATION32),1)
$(error ACTOR_PRESENTATION32 must be 0 or 1)
endif
endif
ifeq ($(ACTOR_PRESENTATION32),1)
ifneq ($(ACTOR_TRANSACTION)$(COARSE_SOURCE_ACTORS)$(ACTOR_SKIN_RESERVE)$(NATIVE_ACTOR_FAST)$(NATIVE_ACTOR_SKIN_LAZY)$(NATIVE_MODEL_REGISTRY)$(NATIVE_MODEL_REGISTRY_PACK)$(ROUTE_CH22),11111111)
$(error ACTOR_PRESENTATION32 requires ACTOR_TRANSACTION=1 COARSE_SOURCE_ACTORS=1 ACTOR_SKIN_RESERVE=1 NATIVE_ACTOR_FAST=1 NATIVE_ACTOR_SKIN_LAZY=1 NATIVE_MODEL_REGISTRY=1 NATIVE_MODEL_REGISTRY_PACK=1 ROUTE_CH22=1)
endif
ifneq ($(ACTOR_SKIN_OWNER_POOL),0)
$(error ACTOR_PRESENTATION32 requires ACTOR_SKIN_OWNER_POOL=0)
endif
ifneq ($(NATIVE_MODEL_REGISTRY_BONES),96)
ifneq ($(NATIVE_MODEL_REGISTRY_BONES),128)
$(error ACTOR_PRESENTATION32 requires the existing Luis-capable NATIVE_MODEL_REGISTRY_BONES=96 or 128 profile)
endif
endif
ifneq ($(strip $(SKIN_RECIPE32)),)
ifneq ($(SKIN_RECIPE32),0)
$(error ACTOR_PRESENTATION32 and SKIN_RECIPE32 require separate joint source-credit qualification)
endif
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_PRESENTATION32=1 -DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_PRESENTATION32=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_PRESENTATION32=1
$(OBJDIR)/src/game/trans.o: platform/include/source_actor_presentation32.inc
$(OBJDIR)/coarse_actor.o: actor_presentation32.inc
endif
