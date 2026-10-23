# WORLD_SCRATCH=1: private bounded-window bench image, default ordinary A.
# Runtime B/C admission is closed until final ELF + modules + KOS are reviewed.
WORLD_SCRATCH ?= 0
# Source fastpath defaults to1; this validation knob does not change it.
MESH_FASTPATH ?= 1
ifneq ($(filter $(WORLD_SCRATCH),0 1),$(WORLD_SCRATCH))
$(error WORLD_SCRATCH must be 0 or 1)
endif
ifeq ($(WORLD_SCRATCH),1)
ifneq ($(PS2_WORLD_DRAW)$(PS2_WORLD_MESH)$(MESH_FASTPATH)$(MESH_DIRECT)$(PVR_STREAM)$(NATIVE_STATIC)$(NATIVE_MESH)$(D349_RENDERER_STACK),11111111)
$(error WORLD_SCRATCH=1 needs PS2_WORLD_DRAW/PS2_WORLD_MESH/MESH_FASTPATH/MESH_DIRECT/PVR_STREAM/NATIVE_STATIC/NATIVE_MESH/D349_RENDERER_STACK=1)
endif
ifneq ($(CPU_BACKFACE),0)
$(error WORLD_SCRATCH=1 requires CPU_BACKFACE=0 for all A/B/C arms)
endif
PLATFORM_OBJS += $(OBJDIR)/world_scratch.o
$(TARGET): $(OBJDIR)/world_scratch.o
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/world_scratch.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_SCRATCH=1
$(OBJDIR)/qa_menu.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_SCRATCH=1
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_WORLD_SCRATCH=1
$(OBJDIR)/qa_menu.o: world_scratch.h
$(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ui.o: world_scratch.h
$(OBJDIR)/world_scratch.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/dbgwarp.h
$(OBJDIR)/world_scratch.o: world_scratch.cpp world_scratch.h $(OBJDIR)/dbgwarp.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -MMD -MP -c $< -o $@
-include $(OBJDIR)/world_scratch.d
endif
