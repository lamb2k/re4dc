# MODEL_PART_DUMP=<frame> (lane gcleft26 2026-10-26; diagnostic, default 0, never in a cost or release image): for the
#   UI frames <frame> .. <frame>+2, platform/native_ui.cpp logs one "PARTDUMP" line per model part that reaches
#   re4dc_model_result (the counters behind "native model DIAGNOSTIC" parts / input / emitted): the texture key of the
#   part's last packet reserve (a content id, comparable across builds; 0 = culled before any reserve), input and
#   emitted vertices. Used to attribute the drawn-part / vertex change between two recipes. Default 0: no define.
MODEL_PART_DUMP ?= 0
ifneq ($(MODEL_PART_DUMP),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_MODEL_PART_DUMP=$(MODEL_PART_DUMP)
endif
