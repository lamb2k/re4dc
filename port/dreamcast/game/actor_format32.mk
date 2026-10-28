# Build 32: qualification and admission diagnostics for the existing actor
# cone and UV16 controls. Zero adds no definitions or object selection.
ACTOR_FORMAT32 ?= 0
ifneq ($(words $(ACTOR_FORMAT32)),1)
$(error ACTOR_FORMAT32 must be one value, 0 or 1)
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
