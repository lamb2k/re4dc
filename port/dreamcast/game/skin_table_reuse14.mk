# EF14 prepared skin tables: bounded by the existing owner reservation.
ACTOR_TABLE_REUSE14 ?= 0
ifneq ($(words $(ACTOR_TABLE_REUSE14)),1)
$(error ACTOR_TABLE_REUSE14 must be exactly 0 or 1)
endif
ifneq ($(filter-out 0 1,$(ACTOR_TABLE_REUSE14)),)
$(error ACTOR_TABLE_REUSE14 must be exactly 0 or 1)
endif
ifneq (x$(ACTOR_TABLE_REUSE14),x$(strip $(ACTOR_TABLE_REUSE14)))
$(error ACTOR_TABLE_REUSE14 must be exactly 0 or 1)
endif
ifeq ($(ACTOR_TABLE_REUSE14),1)
ifneq ($(ACTOR_TRANSACTION):$(NATIVE_ACTOR_FAST):$(ACTOR_SKIN_OWNER_POOL),1:1:0)
$(error ACTOR_TABLE_REUSE14 requires ACTOR_TRANSACTION=1 NATIVE_ACTOR_FAST=1 ACTOR_SKIN_OWNER_POOL=0)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_TABLE_REUSE14=1
endif
