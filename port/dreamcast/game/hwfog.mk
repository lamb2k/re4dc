# HW_FOG_HAZE=1 (lane hwfog 2026-10-14, issue #29; render only, default 0): the distant part of a room's camera haze
#   (Esp15, owner 0xd0, as EFFECT_PS2_HAZE draws it) is carried by the PVR fog table instead of translucent sprites.
#   hwfog.cpp holds one row per room: the keep depth (haze sprites nearer than it are still drawn: the close, visible
#   mist), the haze box depth and the mean veil the replaced sprites laid over the scene (measured per room, see
#   port/dreamcast/docs/HW_FOG_HAZE.md). re4dc_fog_frame (platform/native_static.cpp) folds that veil into the GXSetFog table, ramped from the
#   keep depth to the box depth and scaled by the haze's own indoor fade (8 steps, so the table is rewritten only when a
#   step changes). The haze code (src/game/esp_sub.cpp) asks re4dc_hwfog_haze() per haze sprite it would draw.
#   Generators, their Rnd() draws, the effect pool and every sprite's motion are unchanged (draw-time only).
#   Needs NATIVE_FOG=1 and EFFECT_PS2_HAZE=1. Default 0: hwfog.cpp is not built and no hook compiles in (identical image).
HW_FOG_HAZE ?= 0
#   HW_FOG_VEIL_PCT=n (test builds, veil calibration; default 100): every row's veil scaled to n % (0 = the distant
#   haze sprites are skipped with no veil in their place).
HW_FOG_VEIL_PCT ?= 100
#   HW_FOG_HAZE_TOGGLE=1 (test discs, console A/B; needs HW_FOG_HAZE=1, LOOK_TOGGLE=1, EFFECT_HAZE_LEAN_TOGGLE=0): X + D-pad up
#   + START switches the replacement off / on live (off = every haze sprite drawn, no veil); a 3 s label shows the state.
HW_FOG_HAZE_TOGGLE ?= 0
ifneq ($(filter-out 0 1,$(HW_FOG_HAZE_TOGGLE)),)
$(error HW_FOG_HAZE_TOGGLE is 0 or 1)
endif
ifeq ($(HW_FOG_HAZE_TOGGLE),1)
ifneq ($(HW_FOG_HAZE)$(LOOK_TOGGLE)$(EFFECT_HAZE_LEAN_TOGGLE),110)
$(error HW_FOG_HAZE_TOGGLE=1 needs HW_FOG_HAZE=1, LOOK_TOGGLE=1 (the X + START chord, the label) and EFFECT_HAZE_LEAN_TOGGLE=0 (same chord))
endif
$(OBJDIR)/platform/pad.o: PLATFORM_CPPFLAGS += -DRE4DC_HW_FOG_HAZE_TOGGLE=1
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_HW_FOG_HAZE_TOGGLE=1
HWFOG_TOGGLE_DEF := -DRE4DC_HW_FOG_HAZE_TOGGLE=1
endif
ifneq ($(filter-out 0 1,$(HW_FOG_HAZE)),)
$(error HW_FOG_HAZE is 0 or 1)
endif
ifeq ($(HW_FOG_HAZE),1)
ifneq ($(NATIVE_FOG)$(EFFECT_PS2_HAZE),11)
$(error HW_FOG_HAZE=1 needs NATIVE_FOG=1 and EFFECT_PS2_HAZE=1)
endif
# The haze hook (re4dc_hwfog_haze in src/game/esp_sub.cpp's EFFECT_PS2_HAZE draw) is carried by the effects lane
# (lane/t11-fx): refuse a tree without it (the fog veil would double the still-drawn haze).
ifeq ($(shell grep -c re4dc_hwfog_haze $(ROOT)/src/game/esp_sub.cpp 2>/dev/null),)
$(error HW_FOG_HAZE=1: cannot read src/game/esp_sub.cpp)
endif
ifeq ($(shell grep -c re4dc_hwfog_haze $(ROOT)/src/game/esp_sub.cpp 2>/dev/null),0)
$(error HW_FOG_HAZE=1 needs the re4dc_hwfog_haze hook in src/game/esp_sub.cpp (lane/t11-fx))
endif
PLATFORM_OBJS += $(OBJDIR)/hwfog.o
# Included after the link rule: name the object as its prerequisite here.
$(TARGET): $(OBJDIR)/hwfog.o
$(OBJDIR)/hwfog.o: hwfog.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -Iplatform/include -DRE4DC_HW_FOG_VEIL_PCT=$(HW_FOG_VEIL_PCT) $(HWFOG_TOGGLE_DEF) -MMD -MP -c $< -o $@
-include $(OBJDIR)/hwfog.d
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_HW_FOG_HAZE=1
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_HW_FOG_HAZE=1
endif
# MIST_CUT=<mask> (lane mist16 2026-10-16, tester hack evidence; render only, test arms; unset = no code, identical
#   image): the build default of the runtime mask re4dc_mist_cut (port/dreamcast/docs/MIST_CUT.md), one bit per effect
#   class not drawn: 1 haze / mist (Esp15 camera haze, Esp48 sheets; the fog-table veil of HW_FOG_HAZE / EFFECT_HAZE_LEAN
#   stays), 2 world translucent mist cards (native_static.cpp kMistParts), 4 window glows / streaks (room table 0xd0
#   Esp0a / Esp0e), 32 room dust / smoke / particles (other 0xd0), 8 fire / torches / lamps, 64 every other effect
#   owner (shots, blood, sparks), 128 water (Esp42 / Esp45), 16 = diagnostic ceiling only: no translucent world part at
#   all (foliage, ground overlays, shadow decals). Arms: B = 1, C = 2, D = 3 (all mist), E = 239 (every effect sprite +
#   mist cards), F = 255. Generators, Rnd() draws, the effect pool and motion are unchanged (draw-time only).
MIST_CUT ?=
ifneq ($(MIST_CUT),)
ifeq ($(filter $(MIST_CUT),$(shell seq 1 255)),)
$(error MIST_CUT is a mask 1..255)
endif
ifneq ($(EFFECT_SPRITES)$(EFFECT_PS2_HAZE),11)
$(error MIST_CUT needs EFFECT_SPRITES=1 and EFFECT_PS2_HAZE=1)
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_MIST_CUT=$(MIST_CUT)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_MIST_CUT=$(MIST_CUT)
endif
