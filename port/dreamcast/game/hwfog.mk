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
# HAZE_SPRITE_CUT=1 (lane nohaze16 2026-10-16, user "i don't think we need those sprites at all"; render only; default 0 =
#   no code, identical image): no haze / mist sprite is drawn in any room at any Foliage setting: the camera haze around
#   Leon (Esp15: the PS2 recipe rows' near haze that HW_FOG_HAZE keeps, and every other Esp15), the mist sheets (Esp48)
#   and the PS2 haze additions (r118 / r11c). The distant haze stays as the PVR fog table (the HW_FOG_HAZE rows and the
#   EFFECT_HAZE_LEAN M3 veil are fed before the cut) and every room keeps its own fog. Code: src/game/esp_sub.cpp
#   (HazeCutNote, EspSpriteEmit, the additions loop). Generators, Rnd() draws, the effect pool, the PS2 population choice
#   and every motion run as before (draw-time only). Log: one `haze cut: room=...` line per room. Docs: docs/MIST_CUT.md.
HAZE_SPRITE_CUT ?= 0
ifneq ($(filter-out 0 1,$(HAZE_SPRITE_CUT)),)
$(error HAZE_SPRITE_CUT is 0 or 1)
endif
ifeq ($(HAZE_SPRITE_CUT),1)
ifneq ($(EFFECT_SPRITES)$(EFFECT_PS2_HAZE),11)
$(error HAZE_SPRITE_CUT=1 needs EFFECT_SPRITES=1 and EFFECT_PS2_HAZE=1)
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_HAZE_SPRITE_CUT=1
endif
# FX_MIST_PS2=1 (lane fx19 2026-10-19; approximation class, gameplay-equivalence gated; default 0 = no code, identical
#   image): the GameCube-only mist sheets (Esp48 room records the PS2 release does not have: r100's GC sheet textures,
#   every room-table sheet in r101..r10b and r117..r11b, kPs2SheetCut's r105..r200 rows) are not kept. EspSeqSet makes
#   every seed draw as before, then returns the slot to the pool, so the sheets never move, animate or reach the sprite
#   pass. HAZE_SPRITE_CUT=1 already draws none of them. Log: `mist ps2: room=...` lines (count per room).
FX_MIST_PS2 ?= 0
ifneq ($(filter-out 0 1,$(FX_MIST_PS2)),)
$(error FX_MIST_PS2 is 0 or 1)
endif
ifeq ($(FX_MIST_PS2),1)
ifneq ($(HAZE_SPRITE_CUT),1)
$(error FX_MIST_PS2=1 needs HAZE_SPRITE_CUT=1)
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_FX_MIST_PS2=1
endif
# FOLIAGE_TRIM=<level> (lane mist16 2026-10-16; user: "we should get the fixes from foliage agent in", the Options row is a
#   fast follow; render only; unset = no code, identical image). The chapter 1 outdoor translucent overdraw is the PS2
#   world's brush / leaf cards (r100 woods: 3.3 of 3.8 screens), not mist. platform/include/foliage_keys.inc classes the
#   translucent world parts' texture keys offline by texel alpha (mist-20261016/sh/census.py + gen_trim.py; docs/MIST_CUT.md).
#   1 = NEAR: near-binary cut-out cards (leaf / brush / branch cards, fence gaps) drawn in the punch-through list (alpha
#   test, no blend, no per-tile sort) and only to FOLIAGE_NEAR_MM (default 12000: the fog ramp's far half hides them
#   beyond), near-invisible parts not drawn; soft decals, shadow strips, ground blends and vertex-alpha overlays as today.
#   2 = OFF (the Options row's Off): the listed card keys (classes 1-4) are not drawn; surfaces, water and unlisted keys are.
#   re4dc_foliage is one .data word (0 FULL, 1 NEAR, 2 OFF). Needs PT_BLEND_FIX=1 (punch-through with SRCALPHA /
#   INVSRCALPHA: ONE / ZERO draws cut-out texels solid on PVR hardware, the test 8 leaves) and PS2_WORLD_MESH=1.
FOLIAGE_TRIM ?=
FOLIAGE_NEAR_MM ?= 12000
ifneq ($(FOLIAGE_TRIM),)
ifeq ($(filter $(FOLIAGE_TRIM),1 2),)
$(error FOLIAGE_TRIM is 1 (near) or 2 (off))
endif
ifneq ($(PT_BLEND_FIX)$(PS2_WORLD_MESH),11)
$(error FOLIAGE_TRIM needs PT_BLEND_FIX=1 and PS2_WORLD_MESH=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_FOLIAGE_TRIM=$(FOLIAGE_TRIM) -DRE4DC_FOLIAGE_NEAR_MM=$(FOLIAGE_NEAR_MM)
endif
# TRANS_POLICY=<mask> (lane trans17 2026-10-17, Test 17; C:\Game Dev\Emulators\TRANSPARENCY-PLAN-20261017.md; render only;
#   unset or 0 = no code, identical image; test arms until each bit is gated). The game-wide transparency master knob:
#   one offline class per PS2 world part (tools/d367/tr_classify.py -> per room ps2-world.r4tc beside the unchanged
#   R4PW, bound to its crc; no package changes), read by native_static.cpp's trans:: and the runtime word
#   re4dc_trans_policy. Built bits: 1 FLAT (uniform 14/15-alpha surfaces, the r109 / r119 cabin walls and floor, and any
#   fully opaque texture in the TR pass, drawn opaque; Tier 2: tools/d367/tr_pixdiff.py must pass), 128 DROP (TR parts
#   whose shipped texture is alpha 0 everywhere are not drawn; Tier 1), 2 CARD (near-binary cards, texel alpha error
#   <= 0.08, drawn punch-through), 4 SOFTA (soft-A cards, error 0.08-0.15, punch-through), 8 FAR (passes 1-2 stop where
#   the room's loaded PVR fog table reaches re4dc_trans_far_pct: 70 % for cards moved to punch-through, 90 % for the
#   rest; warp line `transfar <low> <high>`). Reserved, refused until built and gated: 16 VA, 32 FX, 64 WATER. Aliases (the existing knobs keep their own code and images; the
#   policy bit is their game-wide successor and is never combined with them silently):
#     FOLIAGE_TRIM=1 (Near) ~ CARD|FAR (ch1 keys only)  FOLIAGE_TRIM=2 (Off) ~ DROP of the listed card keys
#     PS2_FOLIAGE_FAR ~ FAR      MIST_CUT bit 2 ~ DROP ("PS2 removed it", Tier 3)      FX_LEVEL / FX_SPRITE_TRIM /
#     HAZE_SPRITE_CUT / MIST_CUT bits 1,4,8,32,64 ~ FX      WATER_PS2 dial ~ WATER      PS2_VERTEX_ALPHA fade ~ VA
#   FOLIAGE_TRIM's pass wins: the policy only acts on a part FOLIAGE_TRIM left in the TR pass. Log: `trans:` lines.
TRANS_POLICY ?=
ifneq ($(filter-out 0,$(TRANS_POLICY)),)
ifeq ($(filter $(TRANS_POLICY),$(shell seq 1 255)),)
$(error TRANS_POLICY is a mask 1..255)
endif
ifneq ($(shell echo $$(( $(TRANS_POLICY) & 112 ))),0)
$(error TRANS_POLICY bits 16 VA, 32 FX, 64 WATER are not built yet (lane trans17); built: 1 FLAT, 2 CARD, 4 SOFTA, 8 FAR, 128 DROP)
endif
ifneq ($(PS2_WORLD_MESH),1)
$(error TRANS_POLICY needs PS2_WORLD_MESH=1)
endif
ifeq ($(filter-out 0,$(PS2_WORLD_ROOMS)),)
$(error TRANS_POLICY needs PS2_WORLD_ROOMS (per-room ps2-world.r4tc))
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_TRANS_POLICY=$(TRANS_POLICY)
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_TRANS_POLICY=$(TRANS_POLICY)
# TRANS_POLICY_DEBUG=1 (test arms only, with DBG_WARP=1): warp line `transdbg 1` stops drawing the FLAT / OPAQUE_IN_TR
#   parts: the silhouette arm for tr_pixdiff.py --mask-diff.
TRANS_POLICY_DEBUG ?= 0
ifeq ($(TRANS_POLICY_DEBUG),1)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_TRANS_POLICY_DEBUG=1
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_TRANS_POLICY_DEBUG=1
endif
endif
# FOLIAGE_NEAR_FIX=1 (lane lake17 2026-10-17, tester report "foliage Near and Off look the same"; render only, default 0:
#   no code): at NEAR the cut-out cards move from pass 2 to the punch-through pass 1, but ps2_pass skipped every
#   placement without a native pass-1 part before the per-part test, so cards in translucent-only placements were drawn
#   in neither pass. With the fix, pass 1 at NEAR also visits placements that have pass-2 parts.
FOLIAGE_NEAR_FIX ?= 0
ifneq ($(filter-out 0 1,$(FOLIAGE_NEAR_FIX)),)
$(error FOLIAGE_NEAR_FIX must be 0 or 1)
endif
ifeq ($(FOLIAGE_NEAR_FIX),1)
ifeq ($(FOLIAGE_TRIM),)
$(error FOLIAGE_NEAR_FIX needs FOLIAGE_TRIM)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_FOLIAGE_NEAR_FIX=1
endif
