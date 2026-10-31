# K45 fix plan (K45-FIX-PLAN-20261031.md, user 10-31 "You implement all fixes"): default-off repairs of K45 speed
# switches whose per-frame bookkeeping costs more than the work they save (calibrated hw model, hwcal31).

# F4 WORLD_VALID_MEMO31: keep a positive worldPackageCurrent answer until a heap-4 open / close / cell free, a heap-4
# handle or status change, or a package publish / revoke. Same answers, fewer checks.
WORLD_VALID_MEMO31 ?= 0
ifneq ($(WORLD_VALID_MEMO31),0)
ifneq ($(WORLD_VALID_MEMO31),1)
$(error WORLD_VALID_MEMO31 must be exactly 0 or 1)
endif
ifneq ($(WORLD_MUTATION31),1)
$(error WORLD_VALID_MEMO31 needs WORLD_MUTATION31=1)
endif
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_WORLD_VALID_MEMO31=1
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_VALID_MEMO31=1
endif

# F3 ACTOR_SPAN_MEMO31: keep the source-span scan result per part content (blob, UV array, counts) instead of per
# owner frame; dropped on model unload / move / retire and when the stream is rewritten. Owner check unchanged.
ACTOR_SPAN_MEMO31 ?= 0
ifneq ($(ACTOR_SPAN_MEMO31),0)
ifneq ($(ACTOR_SPAN_MEMO31),1)
$(error ACTOR_SPAN_MEMO31 must be exactly 0 or 1)
endif
ifneq ($(ACTOR_SOURCE_SPAN),1)
$(error ACTOR_SPAN_MEMO31 needs ACTOR_SOURCE_SPAN=1)
endif
GAME_CPPFLAGS += -DRE4DC_ACTOR_SPAN_MEMO31=1
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_SPAN_MEMO31=1
endif
