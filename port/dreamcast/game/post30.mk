# D367 post30: the GameCube's full-screen post look on the PVR (look-gaps 2026-09-26, part post). Included at the end
# of the Makefile. Every knob defaults to 0 and then contributes nothing (identical image). Render only.
#   POST_F00=1   Filter00's contrast lift (LIT blur type 2 feedback + contrast; r101 x1.44 on mid-tones) as ONE
#                full-screen translucent quad in the PVR tile buffer: blend (DESTCOLOR, ONE), colour grey c, so
#                d -> d + c d (8-bit, before the RGB565 write-out). c follows the live Filter00 parameters (the
#                flat-field steady state at a mid-tone). Queued at Filter00Render's OT slot in the deferred
#                translucent queue: opaque / punch-through and the translucent parts drawn before it are lifted,
#                later translucent parts and the UI quads (the HUD, OT 0x13..0x15) are not. No texture, no VRAM.
#   POST_F00=4   the same plus the bias: gain, invert, add h, invert = max(0, g d - h) (four quads), the exact
#                flat-field curve above its knee (near-black stays black).
#   FILTER00_DC=1  the GameCube Filter00 per room, Dreamcast native (2026-10-11): POST_F00=1's one full-screen gain quad
#                (=4: POST_F00=4's four quads with the bias knee; the Dolphin on/off pairs fit the gain within
#                0.2..0.5 of 255 of the knee, the GameCube bias is 2..9 % of white, so =1 is the candidate at a
#                quarter of the PVR fill) driven by the room's own LightEnv blur / contrast (cLightMgr::setBlur), so only the rooms whose
#                GameCube data turns Filter00 on get it (r101 r102 r103 r104 r105 r107 r10b; not r100 r106 r10a ...).
#                No frame copy: the contrast acts per pixel (no half-size glow blur), blur types 0 / 1 (feedback
#                ghosting) are not drawn. With LOOK_TOGGLE it is on in preset B only. Excludes POST_F00.
#   POST_F00_DIAG=1  test builds: log per 600 frames how many UI quads were queued before the post (drawn after it,
#                unlike the GameCube) and how many opaque packets followed it (drawn before it on the PVR).
#   PVR_DITHER=1 assert the RGB565 write-out dither (FB_W_CTRL bit 3) after vid_set_mode and log the register.
#                KOS's vid_set_mode already sets it for PM_RGB565, so this changes nothing on a stock KOS;
#                =2 (diagnostic, not a candidate) clears it to show the undithered 565 write-out.
#   Look knobs (look study 2026-10-10, C:\Game Dev\Emulators\look-study-20261010; render only, default 0 = the
#   previous image; none is in the play recipe):
#   FOG_CURVE=1  the GameCube fog curve: the PVR fog table follows the source GXSetFog curve out to the source fog
#                end (r101 linear -7.1..175 m: 17.6 % at 25 m; r100 exp2: 28-37 % at 25 m) instead of ramping to
#                100 % over the last 20 % before the cull far (FOG_FAR), so there is no fog wall. Scenery and actors
#                are still culled at the cull far, so they pop there at the curve's density. =2: the same curve
#                plus a smooth ramp to FOG_CAP % (default 100) over the last 20 % before the cull far, and at least
#                FOG_CAP % beyond it (a capped fog wall).
#   FOG_CAP=n    FOG_CURVE=2's density at the cull far, percent (1..100).
#   FOG_RGB_PCT=n  the fog colour (and so the PVR background) scaled to n % (1..99): a darker horizon, the GC sky
#                reads 48,47,40 against the fog colour 113,108,90 in r101. 0 = as the source.
#   FOG_FAR_CAP=1  the fixed 25 m caps of the PS2 world draw (native_ps2_world.cpp, ps2_pass) and of the coarse
#                view (coarse.cpp kFar: blocks and actors) follow FOG_FAR (needs FOG_FAR > 25000): with FOG_FAR=45000
#                the world and the actors are drawn to 45 m where the source far plane allows it (r101 70 m, r100
#                cut 0 42.7 m; r100's house cut stays 24.8 m, the source's own).
#   SKY_FAR=1    the room's sky / backdrop placements of the PS2 world (r100 SMD rows 2, 3, 75, 33..37; r101 rows
#                0..2: the cloud dome and the treeline cards) skip the cull far and draw to the projection far,
#                fogged by the table as the rest (useful with FOG_CURVE, which leaves them visible). =2: the same
#                with their fog off (an unfogged sky dome and treeline).
#   LOOK_TOGGLE=1  test builds: the look presets at run time (native_static.cpp re4dc_looks, disc 2 order: GD = the
#                GameCube fog curve + SKY_FAR=1 + fog colour 70 %, GM = GD + the r100 outdoor colour match (one
#                full-screen DESTCOLOR multiply quad, native_ui.cpp re4dc_look_grade_post), GS = GD + the PVR vertical
#                flicker filter forced on (VSCALE 1025; KOS already sets it for 480i TV), GA = GM + GS, DC = the play
#                build, GX = GD with the filter forced off; issue #11: the scaler is never written on VGA, and on a TV
#                only when the value changes, in the render-done interrupt with no render in flight). Hold X and press START to step them; the preset name
#                shows top left for 3 s (BIOS font, one textured quad; X + Y + START keeps it shown) and on the VMU
#                PACE page; DBG_WARP's `look <n>` sets one at load and `lookosd` keeps the label shown. Needs
#                EFFECT_PS2_TOGGLE=1 (the same chord and the VMU label slot; a preset also sets the effect look). The
#                draw distance stays the build's FOG_FAR (build FOG_FAR=45000 FOG_FAR_CAP=1 for a farther disc).
#                User decision 2026-10-11 (test 7): two presets, A: Current (boot), B: GameCube (GD fog + GM colour
#                match + FILTER00_DC, today's character textures; the CG character bake preset was dropped); needs
#                FILTER00_DC=1 (or 4). LOOK_TOGGLE_ALL=1 (test builds) restores the 11 study presets.
POST_F00 ?= 0
FILTER00_DC ?= 0
LOOK_TOGGLE_ALL ?= 0
POST_F00_DIAG ?= 0
LOOK_TOGGLE ?= 0
PVR_DITHER ?= 0
FOG_CURVE ?= 0
FOG_CAP ?= 100
FOG_RGB_PCT ?= 0
FOG_FAR_CAP ?= 0
# LAKE_FAR=<mm> (lane lake17 2026-10-17, user option (a) after the tester's lake report; render only, default 0: no code):
#   the lake rooms r10b / r11a / r11b draw the PS2 world, the coarse view and the fog to this far instead of the 25 m cap
#   (native_static.cpp re4dc_far_cap); the fog ramp still reaches 100 % fog colour at it. Needs FOG_FAR_CAP=0,
#   PS2_WORLD_ROOMS (the room of the open PS2 world) and a value above 25000.
# Per room (user decision 2026-10-17): LAKE_FAR applies to r10b (the boat, Del Lago); LAKE_FAR_SHORE=<mm> to the shore
#   rooms r11a / r11b and defaults to LAKE_FAR when unset. 0 for a group keeps its 25 m cap. Both 0 (default): no code.
LAKE_FAR ?= 0
LAKE_FAR_SHORE ?= $(LAKE_FAR)
ifneq ($(LAKE_FAR)$(LAKE_FAR_SHORE),00)
ifneq ($(LAKE_FAR),0)
ifeq ($(shell test $(LAKE_FAR) -gt 25000 && echo y),)
$(error LAKE_FAR is 0 or a far in mm above 25000)
endif
endif
ifneq ($(LAKE_FAR_SHORE),0)
ifeq ($(shell test $(LAKE_FAR_SHORE) -gt 25000 && echo y),)
$(error LAKE_FAR_SHORE is 0 or a far in mm above 25000)
endif
endif
ifeq ($(FOG_FAR_CAP),1)
$(error LAKE_FAR needs FOG_FAR_CAP=0)
endif
endif
SKY_FAR ?= 0
ifneq ($(filter-out 0 1 2,$(FOG_CURVE))$(filter-out 0 1,$(FOG_FAR_CAP))$(filter-out 0 1 2,$(SKY_FAR)),)
$(error FOG_CURVE / SKY_FAR are 0..2, FOG_FAR_CAP 0 or 1)
endif
ifeq ($(LOOK_TOGGLE),1)
ifneq ($(EFFECT_PS2_TOGGLE),1)
$(error LOOK_TOGGLE=1 needs EFFECT_PS2_TOGGLE=1 (the X + START chord and the VMU label))
endif
ifneq ($(FOG_CURVE)$(FOG_RGB_PCT)$(SKY_FAR),000)
$(error LOOK_TOGGLE=1 sets the fog curve, colour and sky at run time: leave FOG_CURVE / FOG_RGB_PCT / SKY_FAR at 0)
endif
ifneq ($(PS2_WORLD_MESH),1)
$(error LOOK_TOGGLE needs PS2_WORLD_MESH=1 (the sky placements are PS2 world rows))
endif
# re4dc_look_set sets each preset's effect look (re4dc_ps2fx_set): native_static.o needs the toggle define too.
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_EFFECT_PS2_TOGGLE=1
# Issue #11: the scaler write waits for an idle PVR (KOS pvr_state.render_busy, pvr_internal.h).
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -I$(KOS_BASE)/kernel/arch/dreamcast/hardware/pvr
endif
ifneq ($(filter-out 0 1 4,$(FILTER00_DC))$(filter-out 0 1,$(LOOK_TOGGLE_ALL)),)
$(error FILTER00_DC is 0, 1 or 4, LOOK_TOGGLE_ALL 0 or 1)
endif
ifneq ($(FILTER00_DC),0)
ifneq ($(POST_F00),0)
$(error FILTER00_DC is POST_F00 per room: leave POST_F00 at 0)
endif
ifneq ($(D349_RENDERER_STACK),1)
$(error FILTER00_DC needs D349_RENDERER_STACK=1 (the deferred translucent queue))
endif
endif
ifeq ($(LOOK_TOGGLE)$(LOOK_TOGGLE_ALL)$(FILTER00_DC),100)
$(error LOOK_TOGGLE=1: preset B draws Filter00, build FILTER00_DC=1 (or LOOK_TOGGLE_ALL=1 for the 11 study presets))
endif
ifeq ($(LOOK_TOGGLE_ALL),1)
ifneq ($(LOOK_TOGGLE),1)
$(error LOOK_TOGGLE_ALL=1 needs LOOK_TOGGLE=1)
endif
endif
ifneq ($(filter-out 0 1,$(LOOK_TOGGLE)),)
$(error LOOK_TOGGLE is 0 or 1)
endif
ifneq ($(FOG_CURVE)$(FOG_RGB_PCT)$(FOG_FAR_CAP)$(SKY_FAR)$(LOOK_TOGGLE),00000)
ifneq ($(NATIVE_FOG),1)
$(error FOG_CURVE / FOG_RGB_PCT / FOG_FAR_CAP / SKY_FAR / LOOK_TOGGLE need NATIVE_FOG=1)
endif
endif
ifeq ($(FOG_FAR_CAP),1)
ifeq ($(shell test $(FOG_FAR) -gt 25000 && echo y),)
$(error FOG_FAR_CAP=1 needs FOG_FAR > 25000)
endif
endif
ifneq ($(SKY_FAR),0)
ifneq ($(PS2_WORLD_MESH),1)
$(error SKY_FAR needs PS2_WORLD_MESH=1 (the sky placements are PS2 world rows))
endif
endif
ifneq ($(POST_F00),0)
ifneq ($(D349_RENDERER_STACK),1)
$(error POST_F00 needs D349_RENDERER_STACK=1 (the deferred translucent queue))
endif
endif
.PHONY: post30-force
$(OBJDIR)/post30.h: post30-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_POST_F00 %s\n#define RE4DC_POST_F00_DIAG %s\n#define RE4DC_PVR_DITHER %s\n' '$(if $(filter 1 4,$(FILTER00_DC)),$(FILTER00_DC),$(POST_F00))' '$(POST_F00_DIAG)' '$(PVR_DITHER)' > $@.tmp
ifneq ($(FILTER00_DC),0)
	@printf '#define RE4DC_FILTER00_DC 1\n' >> $@.tmp
endif
ifeq ($(LOOK_TOGGLE_ALL),1)
	@printf '#define RE4DC_LOOK_TOGGLE_ALL 1\n' >> $@.tmp
endif
ifneq ($(FOG_CURVE),0)
	@printf '#define RE4DC_FOG_CURVE %s\n#define RE4DC_FOG_CAP %s\n' '$(FOG_CURVE)' '$(FOG_CAP)' >> $@.tmp
endif
ifneq ($(FOG_RGB_PCT),0)
	@printf '#define RE4DC_FOG_RGB_PCT %s\n' '$(FOG_RGB_PCT)' >> $@.tmp
endif
ifeq ($(FOG_FAR_CAP),1)
	@printf '#define RE4DC_FAR_CAP %s\n' '$(FOG_FAR)' >> $@.tmp
endif
ifeq ($(LOOK_TOGGLE),1)
	@printf '#define RE4DC_LOOK_TOGGLE 1\n' >> $@.tmp
endif
ifneq ($(LAKE_FAR)$(LAKE_FAR_SHORE),00)
	@printf '#define RE4DC_LAKE_FAR_ON 1\n#define RE4DC_LAKE_FAR %s\n#define RE4DC_LAKE_FAR_SHORE %s\n' '$(LAKE_FAR)' '$(LAKE_FAR_SHORE)' >> $@.tmp
endif
ifneq ($(SKY_FAR),0)
	@printf '#define RE4DC_SKY_FAR %s\n' '$(SKY_FAR)' >> $@.tmp
endif
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
POST30_GAME = $(OBJDIR)/src/game/filter00.o $(OBJDIR)/coarse.o $(OBJDIR)/pace.o $(OBJDIR)/dbgwarp_bridge.o
POST30_PLATFORM = $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/vi.o $(OBJDIR)/platform/native_static.o \
	$(OBJDIR)/platform/native_ps2_world.o $(OBJDIR)/platform/pad.o
$(POST30_GAME) $(POST30_PLATFORM): $(OBJDIR)/post30.h
$(POST30_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/post30.h
$(POST30_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/post30.h
