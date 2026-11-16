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
# CHAR_VIS31=1 (render only, exact; default 0; needs PROP_GATE=1 ENEMY_VIS_CULL=1 PS2_INTERIOR_ACTORS=2, the release
#   recipe): a skinned room object PROP_GATE keeps by its fog bound skips its draw when its world bound is outside the
#   view frustum, inside a hiding PS2 interior cell (PS2_INTERIOR_ACTORS) or behind a room OCCL occluder
#   (ENEMY_VIS_CULL), through PROP_GATE's own skip path (src/game/trans.cpp charVisHidden; "CHAR_VIS31 models" lines
#   every 600 frames). +~0.6 KiB.
# CHAR_VIS31=2: also the part level: any native actor part (props, objects, Leon, Ashley) wholly outside the side planes
#   of the view or behind the eye skips positions, skin, light and packing (platform/native_actor_fast.cpp cv_hidden;
#   port of lane castlebudget's ACTOR_PART_FRUSTUM; "CHAR_VIS31 frame= tests= culled=" lines). +~2 KiB more.
CHAR_VIS31 ?= 0
ifeq ($(filter $(CHAR_VIS31),0 1 2),)
$(error CHAR_VIS31 must be 0, 1 or 2)
endif
ifneq ($(CHAR_VIS31),0)
ifneq ($(PROP_GATE)$(ENEMY_VIS_CULL)$(PS2_INTERIOR_ACTORS),112)
$(error CHAR_VIS31 needs PROP_GATE=1 ENEMY_VIS_CULL=1 PS2_INTERIOR_ACTORS=2 (the release recipe))
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_CHAR_VIS31=1
endif
ifeq ($(CHAR_VIS31),2)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_CHAR_VIS31=1
endif
