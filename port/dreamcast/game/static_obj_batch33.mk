# Build33: final-output header batching. Absent/0 adds no definition.
STATIC_OBJ_BATCH33 ?= 0
ifneq ($(words $(STATIC_OBJ_BATCH33)),1)
$(error STATIC_OBJ_BATCH33 must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(STATIC_OBJ_BATCH33)),)
$(error STATIC_OBJ_BATCH33 must be 0 or 1)
endif
ifeq ($(STATIC_OBJ_BATCH33),1)
ifeq ($(filter 1 2,$(STATIC_OBJ_BATCH)),)
$(error STATIC_OBJ_BATCH33=1 needs STATIC_OBJ_BATCH=1 or 2)
endif
ifneq ($(PVR_STREAM)$(D349_RENDERER_STACK),11)
$(error STATIC_OBJ_BATCH33=1 needs PVR_STREAM=1 D349_RENDERER_STACK=1)
endif
ifneq ($(TA_GUARD),0)
$(error STATIC_OBJ_BATCH33=1 needs TA_GUARD=0; its physical packet counter assumes one header per send)
endif
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_STATIC_OBJ_BATCH33=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_STATIC_OBJ_BATCH33=1
endif
