# CPU world-pass submission elapsed time, not GPU or the frame-present wait.
# Default off: no object, flags, storage or hooks are compiled into the image.
WORLD_DRAW_METER ?= 0
ifneq ($(filter $(WORLD_DRAW_METER),0 1),$(WORLD_DRAW_METER))
$(error WORLD_DRAW_METER must be 0 or 1)
endif
ifeq ($(WORLD_DRAW_METER),1)
ifneq ($(PS2_WORLD_DRAW),1)
$(error WORLD_DRAW_METER=1 needs PS2_WORLD_DRAW=1)
endif
PLATFORM_OBJS += $(OBJDIR)/world_draw_meter.o
$(TARGET): $(OBJDIR)/world_draw_meter.o
$(OBJDIR)/platform/native_ps2_world.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/qa_menu.o $(OBJDIR)/world_draw_meter.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_DRAW_METER=1
$(OBJDIR)/world_draw_meter.o: world_draw_meter.cpp world_draw_meter.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -MMD -MP -c $< -o $@
-include $(OBJDIR)/world_draw_meter.d
endif
