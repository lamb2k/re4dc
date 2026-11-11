# Lane chars31 (2026-11-11, review answer 2 items 1 and 2; default off: nothing built).
# CHARS31_COUNT=1 (diagnostic only; QA / harness discs, never a release): per-model table of the character path,
#   "C31W" / "C31" log lines every 120 UI frames (platform/include/chars31_count.inc): parts, committed with output /
#   empty, AL25 flat parts and vertices, vertices per skin kernel (s16 / u16 / rigid), meshlet-culled vertices,
#   triangles, view distance, hidden parts, model class (player / partner / Ganado / other em / object / map object /
#   Leon weapon). Draws and decides nothing.
CHARS31_COUNT ?= 0
ifeq ($(filter $(CHARS31_COUNT),0 1),)
$(error CHARS31_COUNT must be 0 or 1)
endif
ifeq ($(CHARS31_COUNT),1)
$(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_CHARS31_COUNT=1
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_CHARS31_COUNT=1
$(OBJDIR)/platform/native_actor_fast.o: platform/include/chars31_count.inc
endif
