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

# F1 ACTOR_TINY_KEEP31: keep the blob of a part whose GX list is too small to hold it in place (per-submit blobs were
# rebuilt every draw: r100 ~43 a frame, K45 or not); 4 KB store keyed by the whole GX list and the conversion inputs.
# F2 (cone split then unsplit) was these same parts reconverting; it ends with F1.
ACTOR_TINY_KEEP31 ?= 0
ifneq ($(ACTOR_TINY_KEEP31),0)
ifneq ($(ACTOR_TINY_KEEP31),1)
$(error ACTOR_TINY_KEEP31 must be exactly 0 or 1)
endif
GAME_CPPFLAGS += -DRE4DC_ACTOR_TINY_KEEP31=1
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_TINY_KEEP31=1
endif

# F2 ACTOR_CONE_GAIN31=N: keep a part's back-face cone split only when its records (skinned vertices) grow by at most
# N% over the plain build; decided once per part at conversion. 0 = off.
ACTOR_CONE_GAIN31 ?= 0
ifneq ($(ACTOR_CONE_GAIN31),0)
ifneq ($(ACTOR_BACKFACE_CONE),1)
$(error ACTOR_CONE_GAIN31 needs ACTOR_BACKFACE_CONE=1)
endif
GAME_CPPFLAGS += -DRE4DC_ACTOR_CONE_GAIN31=$(ACTOR_CONE_GAIN31)
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_CONE_GAIN31=$(ACTOR_CONE_GAIN31)
endif

# K45DIAG31 (diagnostic, no draw change): "K45D" lines on why actor parts are converted again (in-place repeats vs
# per-submit blobs larger than their GX list).
K45DIAG31 ?= 0
ifneq ($(K45DIAG31),0)
GAME_CPPFLAGS += -DRE4DC_K45DIAG31=1
PLATFORM_CPPFLAGS += -DRE4DC_K45DIAG31=1
endif
