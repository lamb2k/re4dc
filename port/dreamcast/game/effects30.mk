# D367 effects30: effect sprites (EspCommonTrans). Included at the end of the Makefile. Every
# knob defaults to 0 and then contributes nothing (identical image).
#   EFFECT_LEAN=1    the common sprite draw keeps only the GX state the native side reads
#                    (projection, normal matrix, channel control/material colour, TEV scale);
#                    no blend/TEV/vertex-format/texture-load/display-list stub traffic. The
#                    heat-shimmer and frame-buffer ("nega") variants are untouched. Render only.
#   EFFECT_SPRITES=1 native PVR sprites for the approved classes: weapon muzzle flash (owners
#                    0x34..0x4f), the core effects of the same shot (owner 0) and blood (owner
#                    0x10). Excluded: full-screen sheets (0xd0), room ambient/screen effects (0x01),
#                    masked, spline (Esp1b), texture-render targets, non-blend modes. Sprites go
#                    into the deferred translucent queue in OT order; on queue pressure a sprite
#                    is dropped, never the frame. Render only.
#   EFFECT_SPRITE_MAX=N  sprites per frame (default 64).
#   EFFECT_ROOM=M    (needs EFFECT_SPRITES=1) bit mask: the room's own effects join the native
#                    sprite classes. 1: the room owner's est sets (owner 0x01: r101's pyre, R101Init:
#                    flames, smoke, embers); 2: the room effect sets SstSet starts at room init (owner
#                    0xd0: glows, light shafts, smoke), apart from 4: their camera haze particles (id
#                    0x15) and mist sheets (id 0x48), the fill-heavy class (r101: ~3 Mpx a frame).
#                    3 = the fires and glows, 7 = everything the GameCube draws. Same eligibility
#                    rules otherwise (no mask stage, render target, Esp1b spline or non-blend mode).
#                    With the knob on, a sprite wholly off screen or wholly beyond the fogged View far
#                    (ACTOR_FOG_GATE's value; the fog table is at 100% there) is not queued, for every
#                    class. Render only.
#   COARSE_FX_SPRITES=1 (needs COARSE=1, EFFECT_SPRITES=1 and PACE_TRANS_SKIP bit 2048): a drawn coarse
#                    image's logic-only EspTrans also queues the live effects the sprite path draws
#                    (EspCommonTrans + the EFFECT_SPRITES / EFFECT_ROOM classes), so they draw as native
#                    sprites in the effect OT, and coarse.cpp draws no opaque marker for them. =2: no
#                    markers at all (the other effects are not drawn in coarse images). The queue step
#                    writes no game state for these classes (the render-target flag 0x10000 is not
#                    eligible). Render only.
EFFECT_LEAN ?= 0
EFFECT_SPRITES ?= 0
# The source laser uses Esp19, a line rather than an EspCommonTrans sprite.
# Native packet extension only: existing OT queue and frame storage, no texture.
NATIVE_LASER ?= 0
ifneq ($(filter-out 0 1,$(NATIVE_LASER)),)
$(error NATIVE_LASER is 0 or 1)
endif
ifeq ($(NATIVE_LASER),1)
ifneq ($(EFFECT_SPRITES),1)
$(error NATIVE_LASER needs EFFECT_SPRITES=1)
endif
$(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/esp_sub.o $(OBJDIR)/src/game/esp19.o: GAME_CPPFLAGS += -DRE4DC_NATIVE_LASER=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_NATIVE_LASER=1
endif
COARSE_FX_SPRITES ?= 0
ifneq ($(COARSE_FX_SPRITES),0)
ifneq ($(EFFECT_SPRITES),1)
$(error COARSE_FX_SPRITES needs EFFECT_SPRITES=1)
endif
$(OBJDIR)/src/game/trans.o $(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/esp_sub.o $(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_COARSE_FX_SPRITES=$(COARSE_FX_SPRITES)
endif
EFFECT_SPRITE_MAX ?= 64
EFFECT_ROOM ?= 0
# FX_CORE_TEX_PREP=1: prepare the one current core 0x1d sprite texture from
# accepted r11c callbacks before scene submission. Potential draw only; source
# callbacks/RNG and the ordinary loader/four-open FX cap are unchanged.
FX_CORE_TEX_PREP ?= 0
ifneq ($(FX_CORE_TEX_PREP),0)
ifneq ($(FX_CORE_TEX_PREP)$(EFFECT_SPRITES)$(UI_HANDLES)$(TEX_RESIDENT)$(UI_VRAM)$(D349_RENDERER_STACK),111111)
$(error FX_CORE_TEX_PREP must be 0 or 1 and needs EFFECT_SPRITES=1 UI_HANDLES=1 TEX_RESIDENT=1 UI_VRAM=1 D349_RENDERER_STACK=1)
endif
ifeq ($(filter 1 2 3 4 5 6 7,$(EFFECT_ROOM)),)
$(error FX_CORE_TEX_PREP needs EFFECT_ROOM in 1..7 for the existing four-open FX cap)
endif
$(OBJDIR)/src/game/esp_sub.o $(OBJDIR)/src/game/esp0a.o $(OBJDIR)/src/game/esp0e.o: GAME_CPPFLAGS += -DRE4DC_FX_CORE_TEX_PREP=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FX_CORE_TEX_PREP=1
endif
#   ESP_SPRITE_FAST=1 (needs EFFECT_LEAN=1 and EFFECT_SPRITES=1; lane fx 2026-10-04): the effect sprite pass without
#                    work nothing reads. EspCommonTrans returns at once for a sprite the native path does not take
#                    (under EFFECT_LEAN nothing draws it: only m_Mat and GX state were written), and after the native
#                    sprite for one it does (no normal matrix inverse/load); the coarse sprite pass reads the fogged
#                    View far once per pass; re4dc_effect_sprite tests finiteness on the bits and reuses the last
#                    compiled sprite header when texture, blend and screen flag match. Render only, writes no game
#                    state. (The lane's EspTrans dead-slot skip over GAME_FX_SCAN's live map measured neutral and
#                    was left out at integration, 2026-10-05.)
#   ESP47_SKIP_LEAN=1 (needs PACE_CATCHUP; lane fx 2026-10-04): on an iteration that draws nothing, Esp47 (screen
#                    wrap overlays, queued by the logic-only effect pass for its m_Pos wrap) keeps the wrap and the
#                    shifted m_Pos round trips and drops its sprite draws. Render only.
ESP_SPRITE_FAST ?= 0
ifneq ($(ESP_SPRITE_FAST),0)
ifneq ($(EFFECT_LEAN)$(EFFECT_SPRITES),11)
$(error ESP_SPRITE_FAST needs EFFECT_LEAN=1 and EFFECT_SPRITES=1)
endif
$(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_ESP_SPRITE_FAST=$(ESP_SPRITE_FAST)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ESP_SPRITE_FAST=$(ESP_SPRITE_FAST)
endif
# Build 6: decline unconditional Essential cuts before matrix/projection;
# share a header within a consecutive sprite run.
# Queue reservations and the order/colour/depth of every sprite are unchanged.
ESP_SETUP_LEAN ?= 0
ifneq ($(filter-out 0 1,$(ESP_SETUP_LEAN)),)
$(error ESP_SETUP_LEAN is 0 or 1)
endif
ifeq ($(ESP_SETUP_LEAN),1)
ifneq ($(ESP_SPRITE_FAST),1)
$(error ESP_SETUP_LEAN needs ESP_SPRITE_FAST=1)
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_ESP_SETUP_LEAN=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ESP_SETUP_LEAN=1
endif
ESP47_SKIP_LEAN ?= 0
ifneq ($(ESP47_SKIP_LEAN),0)
ifeq ($(PACE_CATCHUP),0)
$(error ESP47_SKIP_LEAN needs PACE_CATCHUP (pace.cpp re4dc_pace_skipping))
endif
$(OBJDIR)/src/game/esp47.o: GAME_CPPFLAGS += -DRE4DC_ESP47_SKIP_LEAN=$(ESP47_SKIP_LEAN)
endif
#   EFFECT_PS2_HAZE=1 (needs EFFECT_SPRITES=1 and EFFECT_ROOM bit 4; lane ph 2026-10-05): the room generator's
#                    camera haze (Esp15, owner 0xd0) as the PS2 release draws it, in the rooms whose PS2 EFF has it
#                    (r100, r101, r103; others unchanged): a fixed subset of the live sprites (pool slot % 5 / 2 / 1)
#                    inside the PS2's camera box (5.0 / 5.0 / 5.3 m deep), the PS2 size (x1.48 / 1.46 / 1.64), colour,
#                    alpha (34 / 35 / 35 against GC 70 / 25 / 30) and fades (near 3.0 -> 0.5 m, far: last 30 % of the
#                    box). About 11 / 8 / 11 sprites in view against GC 60 / 39 / 41 live. Render only: the
#                    generator, its Rnd() draws and every sprite's motion run as before; only the draw is changed.
#   EFFECT_PS2_STREAK=1 (needs EFFECT_SPRITES=1 and EFFECT_ROOM bit 2): r100's house window streaks (sst 0x09
#                    records 5, 8, 13: the Esp0a copies, up to ~80 static additive sprites; the stairs glare) are
#                    not drawn, as on the PS2. =2 (needs EFFECT_FADE_CLAMP=1) also draws the PS2's light shafts in
#                    their place (texture e9: the stairs window's, inside its PS2 area 13, and the back window's
#                    two). Render only: the generators, their Rnd() and the copies themselves still run.
#   EFFECT_FADE_CLAMP=1 port fix: ChannelSet's near fade (m_Del_far -> m_Del_near) goes negative inside m_Del_near;
#                    the GameCube's (u8) store saturates that to 0, SH-4 wrapped it (near-opaque sprites inside the
#                    near distance: haze within 1 m, the streak copies, the dust). Clamped at 0. Render only.
#   EFFECT_PS2_TOGGLE=1 test builds (needs one of the three above): the look starts at the GameCube's (as the
#                    base) and hold X + press START steps GC -> GF (fade clamp) -> PH (PS2 haze) -> PS (PS2 haze +
#                    streak) over the built ones (START is masked while the chord is down; L/R must be up: R + START
#                    paces, L + START is the debug slot); the PACE_VMU page shows the look after its GPU (or MODE)
#                    line; DBG_WARP's warp.txt `fxmode <flags>` (1 clamp, 2 haze, 4 streak) sets it at load.
#   EFFECT_HAZE_LEAN=<mask> (Phase 2 B6, STUDY2 section 1; needs EFFECT_PS2_HAZE=1; render only, default 0): cheaper
#                    outdoor haze in r100 / r101 / r103 while the PS2 haze look is on. 1 (M1): the GameCube mist
#                    sheets (id 0x48: f6 / cb / d0 / f3 / 33) the PS2 deleted are not drawn. 2 (M3): the fog table
#                    carries ~55 % of the haze's mean veil (1 -> 5 m ramp; r100 0.034, r101 0.025, r103 0.035 x the
#                    indoor fade in 8 steps) and only ~30 % of the PS2 subset draws (slot % 16 / 7 / 3) at alpha x1.5.
#                    4 (M2): each haze sprite is an octagon (apothem 0.9 of the half side: -33 % pixels). Generators,
#                    Rnd() and sprite motion are untouched (draw-time choices only).
#   EFFECT_HAZE_LEAN_TOGGLE=1 (test builds; needs EFFECT_HAZE_LEAN=7 and LOOK_TOGGLE=1): the haze mode at run time,
#                    X + D-pad up + START steps W (as off) -> M1 -> M2 -> M3 -> all; the name shows top left for 3 s.
#   PS2_FX_ROOMS=1 (lane psfx 2026-10-13, user option A; needs EFFECT_PS2_HAZE=1 and EFFECT_PS2_STREAK>=1; render only,
#                    default 0): the PS2 haze recipe and the PS2's removed window streaks in more route rooms, from
#                    the PS2 rNNN.dat EFF (re4-ps2-table-survey-20261013 WORLD-FX.md). r106: both haze sets (GC 30 x
#                    2.6 m, R 6.5 m, alpha 30 / 25 -> PS2 10 x 2.0 m, R 5.0 / 4.0 m, alpha 40 / 35; near fades 3.0 ->
#                    0.5 m / 2.0 -> 1.0 m) and its five Esp0a window streak records (sst 0x08 / 0x09 / 0x0b: their
#                    id-0 copies are not drawn). r10a: GC 41 x 1.33 m, R 6.3 m, alpha 20 -> PS2 10 x 1.7 m, R 4.0 m,
#                    alpha 20 (near 2.0 -> 1.0 m). As EFFECT_PS2_HAZE: the generators, their Rnd() draws, the pool
#                    and every sprite's motion run as before; only the draw changes.
PS2_FX_ROOMS ?= 0
ifneq ($(PS2_FX_ROOMS),0)
ifneq ($(PS2_FX_ROOMS),1)
$(error PS2_FX_ROOMS is 0 or 1)
endif
ifneq ($(EFFECT_PS2_HAZE),1)
$(error PS2_FX_ROOMS needs EFFECT_PS2_HAZE=1)
endif
ifeq ($(filter 1 2,$(EFFECT_PS2_STREAK)),)
$(error PS2_FX_ROOMS needs EFFECT_PS2_STREAK=1 or 2)
endif
endif
## Stage-1 PS2 recipe extensions are draw-only and independently reversible.
PS2_FX_STAGE1 ?= 0
ifneq ($(PS2_FX_STAGE1),0)
ifneq ($(PS2_FX_STAGE1)$(PS2_FX_ROOMS),11)
$(error PS2_FX_STAGE1 must be 0 or 1 and needs PS2_FX_ROOMS=1)
endif
endif
# Bounded read-only selection of exact PS2 haze draw counts. Independent default-off gate.
PS2_FX_POPULATION ?= 0
ifneq ($(PS2_FX_POPULATION),0)
ifneq ($(PS2_FX_POPULATION)$(PS2_FX_STAGE1),11)
$(error PS2_FX_POPULATION must be 0 or 1 and needs PS2_FX_STAGE1=1)
endif
endif
# Added PS2-only haze remains draw-local; no effect controllers or RNG draws.
PS2_FX_ADDITIONS ?= 0
ifneq ($(PS2_FX_ADDITIONS),0)
ifneq ($(PS2_FX_ADDITIONS)$(PS2_FX_POPULATION)$(ESP_SPRITE_FAST),111)
$(error PS2_FX_ADDITIONS must be 0 or 1 and needs PS2_FX_POPULATION=1 ESP_SPRITE_FAST=1)
endif
ifeq ($(filter 1 2,$(COARSE_FX_SPRITES)),)
$(error PS2_FX_ADDITIONS needs COARSE_FX_SPRITES=1 or 2)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PS2_FX_ADDITIONS=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_FX_ADDITIONS=1
endif
# Common chapter-one haze recipe/state replacement is render-owned and optional.
PS2_FX_COMMON_HAZE ?= 0
ifneq ($(PS2_FX_COMMON_HAZE),0)
ifneq ($(PS2_FX_COMMON_HAZE)$(PS2_FX_POPULATION)$(ESP_SPRITE_FAST),111)
$(error PS2_FX_COMMON_HAZE must be 0 or 1 and needs PS2_FX_POPULATION=1 ESP_SPRITE_FAST=1)
endif
ifeq ($(filter 1 2,$(COARSE_FX_SPRITES)),)
$(error PS2_FX_COMMON_HAZE needs COARSE_FX_SPRITES=1 or 2)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PS2_FX_COMMON_HAZE=1
endif
# PS2_FX_ROOMS_EXT=1 (test 11 lane fx 2026-10-14; needs PS2_FX_ROOMS=1; render only, default 0): the effects the PS2
#                    release deleted in the other chapter 1 / 2-1 rooms, from the decoded GC / PS2 rNNN EFF records
#                    (tools/audit_ps2_fx_recipes.py --scope inventory over /root/probe/worldfx-cache). Not drawn: every
#                    room-table mist sheet (id 0x48, owner 0xd0 SST / 0x01 EST) in r101-r10b, r117-r11b (the PS2 has
#                    no Esp48 record in any of them; r100 keeps its small d9 sparks and is left out), r109's SST 2
#                    backdrop sprites (id 0, tex 1f: the PS2 dropped the whole SST 2), and r101's four Esp0a window
#                    streak records' static copies (SST 5 / 7 / 12, tex 32, Del 35/10 and 25/4: the PS2 has no Esp0a
#                    there). As EFFECT_PS2_HAZE: generators, Rnd() draws, the pool and every effect's motion run as before.
PS2_FX_ROOMS_EXT ?= 0
ifneq ($(PS2_FX_ROOMS_EXT),0)
ifneq ($(PS2_FX_ROOMS_EXT)$(PS2_FX_ROOMS),11)
$(error PS2_FX_ROOMS_EXT must be 0 or 1 and needs PS2_FX_ROOMS=1)
endif
endif
# PS2_FX_GEN=1 (test 11 lane fx 2026-10-14; needs PS2_FX_ROOMS=1; render only, default 0): PS2 effect parity for every
#                    stage-1 room in one pass. tools/ps2_fx_parity.py diffs each room's GC and PS2 rNNN EFF records
#                    (r100-r11f: matched / changed / cut / added) and emits src/game/ps2_fx_gen.inc, one draw-time
#                    selector per GameCube record the PS2 deleted that a drawn cEsp can be told apart by (owner, id,
#                    texture, blend, Del, start colour, Life_max; unique against the room's kept records). Those
#                    sprites are not drawn; the hand rows (PS2_FX_ROOMS / STAGE1 / POPULATION / ADDITIONS / ROOMS_EXT)
#                    stay as overrides and run first. Report: docs/PS2_FX_PARITY.md. As EFFECT_PS2_HAZE: generators,
#                    Rnd() draws, the pool and every effect's motion run as before. Log: "ps2fx gen:" once per row/room.
PS2_FX_GEN ?= 0
ifneq ($(PS2_FX_GEN),0)
ifneq ($(PS2_FX_GEN)$(PS2_FX_ROOMS),11)
$(error PS2_FX_GEN must be 0 or 1 and needs PS2_FX_ROOMS=1)
endif
endif
# EFM_PS2_CUT=1 (lane items 2026-10-14; render only, default 0): effect models (Efm, effect record Id 0xFC..0xFF:
#                    debris / break pieces) that the PS2 release deleted from the room or core EFF are not drawn
#                    (r101 0x02, r106 0x5a, r10a 0x7b, r10b 0x7b / 0x7c, r119 0x14 / 0x16 / 0x17, r11a 0x0f, core 0x3e;
#                    eff_sys.cpp kEfmPs2Cut, the ps2_source=NONE rows of ps2lib/breakables). trans.cpp ModelRender
#                    returns before the draw; the object, its records, Rnd() and its motion run as before. Log:
#                    "efm ps2 cut:" once per row and room.
EFM_PS2_CUT ?= 0
ifneq ($(EFM_PS2_CUT),0)
ifneq ($(EFM_PS2_CUT),1)
$(error EFM_PS2_CUT is 0 or 1)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_EFM_PS2_CUT=1
$(OBJDIR)/src/game/eff_sys.o: GAME_CPPFLAGS += -DRE4DC_EFM_PS2_CUT=1
endif
# FX_PS2_NONE_CUT=1 (lane purge-fx24 2026-10-24; render only, default 0; needs FX_PS2_PACK=1): effect sprites whose
#                    picture the PS2 dropped are not drawn. platform/fx_none_cut.inc (tools/d367/purge-fx24/
#                    fx_none_cut.py from ps2lib effects-tex: the ps2_source=NONE rows, per room by tex.pak key; keys that
#                    are NONE in every library row also apply in rooms the library does not cover). re4dc_effect_sprite
#                    returns before the queue; the effect, its records, Rnd() and motion run as before. Pair with
#                    EFM_PS2_CUT=1 (the Efm models). Log: "fx ps2 none cut:" once per key and room visit.
FX_PS2_NONE_CUT ?= 0
ifneq ($(FX_PS2_NONE_CUT),0)
ifneq ($(FX_PS2_NONE_CUT)$(FX_PS2_PACK),11)
$(error FX_PS2_NONE_CUT is 0 or 1 and needs FX_PS2_PACK=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FX_PS2_NONE_CUT=1
endif
# FX_NONE_CUT_PACK=1 (lane heap-margin25 2026-10-25, default 0: no effect; needs FX_PS2_NONE_CUT=1): the same cut table
#                    packed (platform/fx_none_cut_pack.inc from fx_none_cut.inc by tools/d367/purge-fx24/fx_none_cut_pack.py,
#                    which proves every (room, key) answer equal): each key once, rows as one-byte key indices per room, the
#                    per-entry decision in one u16. Same cuts, same log lines; the image (and so r100 s30 heap 4) ~4 KB smaller.
FX_NONE_CUT_PACK ?= 0
ifneq ($(FX_NONE_CUT_PACK),0)
ifneq ($(FX_NONE_CUT_PACK)$(FX_PS2_NONE_CUT),11)
$(error FX_NONE_CUT_PACK is 0 or 1 and needs FX_PS2_NONE_CUT=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FX_NONE_CUT_PACK=1
endif
# FX_EARLY_CUT=1 (lane fxcut28 2026-10-28; render only, default 0): the effect cuts decide before the work they skip.
#                    FX_PS2_NONE_CUT declines a dropped picture inside load() before eviction / budget / file I/O (no
#                    upload of a picture it then discards) and remembers the image descriptor, so later frames skip the
#                    resolve; the Essential filter (FX_LEVEL=3) declines its unconditional cuts before the matrix and
#                    projection (the early half of ESP_SETUP_LEAN, without its header sharing). Same sprites drawn.
# FX_CUT_LOG=1 (test only, default 0): "fx cut log:" every 120 effect frames: sprites drawn, PS2-none cuts, early
#                    skips, texture package opens, missing / resident-only declines (both arms of an FX_EARLY_CUT A/B).
FX_EARLY_CUT ?= 0
ifneq ($(FX_EARLY_CUT),0)
ifneq ($(filter-out 1 2,$(FX_EARLY_CUT)),)
$(error FX_EARLY_CUT is 0, 1 or 2 (test only: the texture half without the Essential half))
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_FX_EARLY_CUT=$(FX_EARLY_CUT)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FX_EARLY_CUT=1
endif
FX_CUT_LOG ?= 0
ifneq ($(FX_CUT_LOG),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FX_CUT_LOG=1
endif
# ITEMS_CENSUS=1 (lane items 2026-10-14; diagnostic, test builds only, default 0; log only): "itemcen:" lines, the
#                    ModelData signature of every item model (cItmSys::DataLoad) and effect model (EspDataLoad) the game
#                    registers; tools/d367/items_census.py counts the GameCube fallbacks against the PS2 library.
ITEMS_CENSUS ?= 0
ifneq ($(ITEMS_CENSUS),0)
$(OBJDIR)/src/game/eff_sys.o: GAME_CPPFLAGS += -DRE4DC_ITEMS_CENSUS=1
$(OBJDIR)/src/game/item_model.o: GAME_CPPFLAGS += -DRE4DC_ITEMS_CENSUS=1
endif
# FX_LEVEL=0|1|2 (test 11 lane fx 2026-10-14; needs PS2_FX_ROOMS=1; render only; unset by default = no code): one
#                    effects-quality dial over every PS2-derived room effect recipe (room SST / EST effects with the PS2
#                    look on, the PS2-added haze, r11b's PS2 rain). 0 = PS2 as-is, 1 = reduced, 2 = low; each level
#                    scales the drawn fraction (a fixed pool-slot hash: spawn counts and Rnd() untouched), sprite
#                    size, alpha, a view-depth cap and a per-frame room-sprite budget (esp_sub.cpp kFxLevel, with
#                    per-recipe overrides kFxLevelOverride). The value is the build default of the runtime variable
#                    re4dc_fx_level (re4dc_fx_level_set / _cycle for a menu or tester toggle).
# SHORE_FX_LEVEL=1|2 (lane lake20 2026-10-20; render only; unset by default = no code): the FX_LEVEL dial for the night
#                    lake shore only (r11b; the r11b walk is effects-bound, ~16 fps in Flycast): r11b draws at this
#                    level, every other room at FX_LEVEL (0 when FX_LEVEL is unset). Needs PS2_FX_ROOMS=1.
SHORE_FX_LEVEL ?=
ifneq ($(SHORE_FX_LEVEL),)
ifneq ($(filter $(SHORE_FX_LEVEL),1 2),$(SHORE_FX_LEVEL))
$(error SHORE_FX_LEVEL must be 1 or 2)
endif
FX_LEVEL ?= 0
endif
FX_LEVEL ?=
ifneq ($(FX_LEVEL),)
ifneq ($(filter $(FX_LEVEL),0 1 2 $(if $(filter 1,$(FX_TRIM)),3))$(PS2_FX_ROOMS),$(FX_LEVEL)1)
$(error FX_LEVEL must be 0, 1 or 2 (3 = Essential, with FX_TRIM=1) and needs PS2_FX_ROOMS=1)
endif
endif
# EFFECT_OWNERS_ALL=1 (test 11 lane fx 2026-10-14, parity census; needs EFFECT_SPRITES=1 and EFFECT_ROOM; render only, default
#                    0): native sprite eligibility by effect class instead of the owner whitelist: every EspCommonTrans
#                    sprite draws whatever its owner (Leon's blood / splashes PL00 0x03, crate / barrel / door / padlock
#                    breaks and torches Et 0x55..0xbb, door locks 0xc9 / 0xcb, boat, animal, trap, Del Lago effects).
#                    Room tables keep EFFECT_ROOM's rules; mask / render-target / non-blend sprites stay out. With
#                    FX_LEVEL the admitted owners get a per-frame budget (kFxLevel owners; never thinned or resized).
#                    Test 12: needs FX_LEVEL (never unbudgeted: the budget is 48 / 32 / 16 at level 0 / 1 / 2, so the
#                    admitted owners cannot take the whole 64-sprite cap); Leon's PL00 effects are opted out of it.
# FX_LEVEL_TOGGLE=1 (test builds, default 0): Y + START steps the runtime FX level 0 -> 1 -> 2 (3 s label, LOOK_TOGGLE's
#                    on-screen text). Needs FX_LEVEL (the boot level) and LOOK_TOGGLE=1.
FX_LEVEL_TOGGLE ?= 0
ifeq ($(FX_LEVEL_TOGGLE),1)
ifeq ($(FX_LEVEL),)
$(error FX_LEVEL_TOGGLE=1 needs FX_LEVEL)
endif
ifneq ($(LOOK_TOGGLE),1)
$(error FX_LEVEL_TOGGLE=1 needs LOOK_TOGGLE=1)
endif
GAME_CPPFLAGS += -DRE4DC_FX_LEVEL_TOGGLE=1
PLATFORM_CPPFLAGS += -DRE4DC_FX_LEVEL_TOGGLE=1
else ifneq ($(FX_LEVEL_TOGGLE),0)
$(error FX_LEVEL_TOGGLE is 0 or 1)
endif
# FX_TRIM=1 (lane fx-trim23 2026-10-23, user "the goal is to have fewer effects"; render only, default 0; needs FX_LEVEL):
#                    the FX_LEVEL dial over every effect sprite game-wide (fire, smoke, dust, sparks, blood, glows of enemies,
#                    objects, weapons and rooms), not only the PS2 room recipes. At levels 1 / 2: an effect id keeps its first
#                    6 / 4 sprites a frame and a fixed pool-slot hash keeps 4 / 3 of 8 beyond them; sprites deeper than
#                    30 / 20 m or under 24 / 48 screen pixels are not drawn; at most 48 / 32 such sprites a frame. Draw time
#                    only (effects still spawn, move and draw their Rnd()); Leon's own effects and screen sprites are never
#                    trimmed. Level 0 draws as without it. esp_sub.cpp kFxTrim. FX_TRIM_LOG=1 (test only): "fx trim:" lines.
#                    FX_LEVEL=3 (with FX_TRIM=1; user 10-23 "Essential only"): the room dial at 0 plus the Essential filter
#                    (esp_sub.cpp FxEssentialCut): gameplay effects kept (Leon's own effects, hit blood, explosions, fire and
#                    flames, blob shadows), atmosphere cut (mist / haze, dust, ambient smoke and sparks, glows, shafts, glare,
#                    FX_STRIP21 trails / ribbons; owner 0x00 keeps its glows: grenade blasts, laser glint), at most 2 sprites a frame per owner of one smoke / spark layer or unknown
#                    id. Runtime re4dc_fx_essential; FX_LEVEL_TOGGLE steps 0 -> 1 -> 2 -> Essential -> 0.
FX_TRIM ?= 0
FX_TRIM_LOG ?= 0
ifeq ($(FX_LEVEL)$(FX_TRIM),30)
$(error FX_LEVEL=3 needs FX_TRIM=1)
endif
ifneq ($(filter-out 0 1,$(FX_TRIM) $(FX_TRIM_LOG)),)
$(error FX_TRIM and FX_TRIM_LOG are 0 or 1)
endif
ifneq ($(FX_TRIM)$(FX_TRIM_LOG),00)
ifeq ($(FX_LEVEL),)
$(error FX_TRIM / FX_TRIM_LOG need FX_LEVEL)
endif
endif
ifeq ($(FX_TRIM_LOG),1)
ifneq ($(FX_TRIM),1)
$(error FX_TRIM_LOG=1 needs FX_TRIM=1)
endif
endif
# R117_FX_QUALIFIED_FALLBACK=1 (default 0; render only): if a complete church puzzle colour's
# PS2 replacement batch is refused, let only its matching GC copies pass Essential for that
# frame, effect pool and live room generation. Successful replacement still suppresses the
# copies. Ordinary sprite/texture/queue limits remain. No room-wide or texture-wide exemption.
R117_FX_QUALIFIED_FALLBACK ?= 0
ifneq ($(words $(R117_FX_QUALIFIED_FALLBACK)),1)
$(error R117_FX_QUALIFIED_FALLBACK is 0 or 1)
endif
ifneq ($(filter-out 0 1,$(R117_FX_QUALIFIED_FALLBACK)),)
$(error R117_FX_QUALIFIED_FALLBACK is 0 or 1)
endif
ifeq ($(R117_FX_QUALIFIED_FALLBACK),1)
ifneq ($(FX_TRIM)$(PS2_FX_ADDITIONS),11)
$(error R117_FX_QUALIFIED_FALLBACK needs FX_TRIM=1 and PS2_FX_ADDITIONS=1)
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_R117_FX_QUALIFIED_FALLBACK=1
endif
# FX_FLIPBOOK=N (test 12 fx lane, render only, default 0): an effect flipbook (a TPL of >= FX_FLIPBOOK_MIN pictures: the
#                    r101 pyre fire, smoke) draws every Nth picture only (picture p - p % N), so N times fewer distinct
#                    textures and the animation's working set can fit VRAM (benchmark-r101: the fire's ~90 pictures
#                    thrash the cache and the EFFECT_ROOM guard declines ~93% of the effect sprites). m_Ptn_no, timers
#                    and Rnd() are untouched; only the TPL picture fetched for the native sprite changes.
FX_FLIPBOOK ?= 0
FX_FLIPBOOK_MIN ?= 8
ifneq ($(filter-out 0 2 3 4,$(FX_FLIPBOOK)),)
$(error FX_FLIPBOOK is 0, 2, 3 or 4)
endif
# FX_TEX_POOL=<KB> (test 12 fx lane, render only, default 0; needs EFFECT_SPRITES=1 and EFFECT_ROOM): a resident effect
#                    texture pool in native_ui.cpp. Effect sprite textures are pinned until the pool holds <KB> KB, so
#                    the room's effect set loads once and stays out of the LRU eviction; pins end at room retirement.
FX_TEX_POOL ?= 0
ifneq ($(FX_TEX_POOL),0)
ifneq ($(EFFECT_SPRITES)$(if $(filter-out 0,$(EFFECT_ROOM)),1,0),11)
$(error FX_TEX_POOL needs EFFECT_SPRITES=1 and EFFECT_ROOM)
endif
endif
# FX_PS2_PACK=1 (test 12 fx lane, render only, default 0; needs TEX_PAL4_ALPHA=1): effect textures may come from a
#                    PS2-sourced pack (tools/d367/test12fx/fx_ps2_pack.py: the PS2 picture, PAL4, under the GameCube key).
#                    Such a package marks in its header flags the texels the source UVs cover, so a picture smaller than
#                    the GameCube one is sampled whole (native_ui.cpp RE4DC_COVER_W/H); FX_SPRITE_TRIM skips it. Without
#                    the pack the knob changes nothing on screen.
FX_PS2_PACK ?= 0
ifneq ($(filter-out 0 1,$(FX_PS2_PACK)),)
$(error FX_PS2_PACK is 0 or 1)
endif
EFFECT_OWNERS_ALL ?= 0
ifneq ($(EFFECT_OWNERS_ALL),0)
ifneq ($(EFFECT_OWNERS_ALL)$(EFFECT_SPRITES)$(if $(filter-out 0,$(EFFECT_ROOM)),1,0),111)
$(error EFFECT_OWNERS_ALL must be 0 or 1 and needs EFFECT_SPRITES=1 and EFFECT_ROOM)
endif
ifeq ($(FX_LEVEL),)
$(error EFFECT_OWNERS_ALL=1 needs FX_LEVEL (the admitted-owner budget))
endif
endif
# TRAP_FX=1 (lane fix-water-traps23 2026-10-23, GitHub #55 item 8; needs EFFECT_SPRITES=1; render only, default 0): the
#                    tripwire bombs' effects (em2a's EFF, effect owner 0x22: the blast of em2aTrap2Bomb, EstSet 0x22 0 / 4 /
#                    6, and the armed trap's sprites) are drawn as native sprites; they were off the owner whitelist, so
#                    the bombs on doors and trees went off with no explosion. Mask / render-target / non-blend sprites
#                    stay out. Log: one "trap fx:" line per room at its first owner-0x22 sprite. No effect state or Rnd().
TRAP_FX ?= 0
ifneq ($(TRAP_FX),0)
ifneq ($(TRAP_FX)$(EFFECT_SPRITES),11)
$(error TRAP_FX must be 0 or 1 and needs EFFECT_SPRITES=1)
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_TRAP_FX=1
endif
# EFFECT_TORCH=1 (issue #30, test 11 lane fx 2026-10-14; needs EFFECT_SPRITES=1 ESP_SPRITE_FAST=1; render only, default 0):
#                    the Esp0e glows (torch / lamp flames) of the torch objects et0b / et0c / et10 / et14 / et19 / et1c / et38
#                    (owners 0x5f 0x60 0x64 0x68 0x6d 0x70 0x8c; r11b's nine cEmTorch are et14) are drawn as native
#                    sprites: Esp0e_Trans's one-frame screen copy becomes eligible, and every Esp0e glow copy is drawn
#                    at its source's view depth (Esp0e_HideCheck's 150 mm) with the depth test on, as the stand-in for
#                    the GameCube's Z-buffer peek (GXPeekZ is a stub). No effect state or Rnd() draw changes.
EFFECT_TORCH ?= 0
ifneq ($(EFFECT_TORCH),0)
ifneq ($(EFFECT_TORCH)$(EFFECT_SPRITES)$(ESP_SPRITE_FAST),111)
$(error EFFECT_TORCH must be 0 or 1 and needs EFFECT_SPRITES=1 ESP_SPRITE_FAST=1)
endif
$(OBJDIR)/src/game/esp0e.o: GAME_CPPFLAGS += -DRE4DC_EFFECT_TORCH=1
endif
# RAIN_PS2=1 (issue #30, test 11 lane fx 2026-10-14; needs NATIVE_LASER=1 (its native line) and the D349 renderer; render
#                    only, default 0): r11b's Filter06 rain (GameCube: GX lines, stubbed here) drawn as native lines in the
#                    PS2 amount: 100 of the source's 1600 particles at alpha x 80 / 60 (PS2 r11b: level 100, alpha 80,
#                    same speed). Only that subset moves; Filter06SetParam and its Rnd() draws are unchanged. Drawn
#                    after the translucent drain (gx_stub.cpp draw sync), straight into the TR list (no frame storage).
#                    Log: "rain ps2:" every 120 drawn images. The PS2's full-screen Esp08 sheet is not drawn.
RAIN_PS2 ?= 0
ifneq ($(RAIN_PS2),0)
ifneq ($(RAIN_PS2)$(NATIVE_LASER),11)
$(error RAIN_PS2 must be 0 or 1 and needs NATIVE_LASER=1)
endif
$(OBJDIR)/src/game/filter06.o: GAME_CPPFLAGS += -DRE4DC_RAIN_PS2=1
$(OBJDIR)/platform/gx_stub.o: PLATFORM_CPPFLAGS += -DRE4DC_RAIN_PS2=1
endif
# RAIN_DC=1 (lane rain17 2026-10-18, user 10-18 "reimplement the rain as a cheaper dreamcast native solution"; needs
#                    RAIN_PS2=1 (its draw-sync hook); render only, an APPROXIMATION, default 0): the night lake's rain as
#                    RAIN_DC_N (default 160) short vertical gouraud streaks in screen space with a view depth (hidden
#                    by nearer scenery), one untextured TR header + one strip each, no texture, no frame storage. Look
#                    reference: the PS2's full-screen Esp08 sheet (r11b SST set 3 / r11a set 5, tex 0xC5, a 100), which
#                    costs a whole translucent screen a frame; the streaks cover ~0.02 screens. Private xorshift
#                    generator (no Rnd()); shown while the game's Filter06 rain is queued in r11a / r11b. Log "rain dc:".
# RAIN_PS2_SHEET_REF=1 (lane rain17 2026-10-18; REFERENCE arm for the look and cost of the PS2 rain, NEVER in a recipe;
#                    needs EFFECT_SPRITES=1): r11a / r11b's rain set drawn as the PS2 draws it, one
#                    full-screen Esp08 sheet (PS2 r11b.dat EFF#7 SST3 rec 67: tex 0xC5, 700x540 of 512x448, rgb 180 a 100,
#                    3x1 tiles scrolled (-0.003, -0.090) a frame), as up to 8 native effect sprites (esp_sub.cpp). Log "ps2 sheet:".
RAIN_PS2_SHEET_REF ?= 0
ifneq ($(RAIN_PS2_SHEET_REF),0)
ifneq ($(RAIN_PS2_SHEET_REF)$(EFFECT_SPRITES),11)
$(error RAIN_PS2_SHEET_REF must be 0 or 1 and needs EFFECT_SPRITES=1)
endif
$(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/esp_sub.o $(OBJDIR)/src/game/esp08.o: GAME_CPPFLAGS += -DRE4DC_RAIN_PS2_SHEET_REF=1
endif
RAIN_DC ?= 0
ifneq ($(RAIN_DC),0)
ifneq ($(RAIN_DC)$(RAIN_PS2),11)
$(error RAIN_DC must be 0 or 1 and needs RAIN_PS2=1)
endif
RAIN_DC_N ?= 160
$(OBJDIR)/src/game/filter06.o: GAME_CPPFLAGS += -DRE4DC_RAIN_DC=1 -DRE4DC_RAIN_DC_N=$(RAIN_DC_N)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_RAIN_DC=1
endif
# RAIN_R10C_DC=1: private experimental r10c Filter06 callback adapter, default0.
# No production recipe. Render profile is sheet-informed, not qualified PS2 appearance.
RAIN_R10C_DC ?= 0
ifneq ($(RAIN_R10C_DC),0)
ifneq ($(RAIN_R10C_DC),1)
$(error RAIN_R10C_DC is exactly 0 or 1)
endif
ifneq ($(RAIN_DC),1)
$(error RAIN_R10C_DC needs RAIN_DC=1)
endif
ifneq ($(RAIN_PS2),1)
$(error RAIN_R10C_DC needs RAIN_PS2=1)
endif
ifneq ($(D349_RENDERER_STACK),1)
$(error RAIN_R10C_DC needs D349_RENDERER_STACK=1 for the actual ADEB flush)
endif
ifneq ($(PVR_STREAM),1)
$(error RAIN_R10C_DC needs PVR_STREAM=1)
endif
ifneq ($(NATIVE_LASER),1)
$(error RAIN_R10C_DC needs NATIVE_LASER=1)
endif
ifneq ($(EFFECT_SPRITES),1)
$(error RAIN_R10C_DC needs EFFECT_SPRITES=1)
endif
$(OBJDIR)/src/game/filter06.o: GAME_CPPFLAGS += -DRE4DC_RAIN_R10C_DC=1
endif
# LAKE_FIX_TOGGLE=1 (lane lake20 2026-10-20; scenario / QA discs only, default 0 = no code): the lake switches at run time
#                    from one flag, re4dc_lake_fix (native_ui.cpp; the scenario menu's A button, bench.cpp BENCH_SCENARIO):
#                    on = SHORE_FX_LEVEL in r11b, half of the RAIN_DC_N rain streaks, SS11_ROOM_EVICT's evict; off = as
#                    without the switches. Needs SHORE_FX_LEVEL, SS11_ROOM_EVICT=1 and RAIN_DC=1.
LAKE_FIX_TOGGLE ?= 0
ifeq ($(LAKE_FIX_TOGGLE),1)
ifeq ($(SHORE_FX_LEVEL),)
$(error LAKE_FIX_TOGGLE=1 needs SHORE_FX_LEVEL)
endif
ifneq ($(SS11_ROOM_EVICT)$(RAIN_DC),11)
$(error LAKE_FIX_TOGGLE=1 needs SS11_ROOM_EVICT=1 and RAIN_DC=1)
endif
$(OBJDIR)/src/game/esp_sub.o $(OBJDIR)/src/game/filter06.o: GAME_CPPFLAGS += -DRE4DC_LAKE_FIX_TOGGLE=1
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/bench.o: PLATFORM_CPPFLAGS += -DRE4DC_LAKE_FIX_TOGGLE=1
endif
# LAKE_NIGHT_FX=1 (issue #30, lane lakefx165 2026-10-18; needs EFFECT_SPRITES=1 ESP_SPRITE_FAST=1; render only, default
#                    0): the night lake's torch flames. In r11a / r11b every sprite of the torch owner 0x68 (et14, cEmTorch)
#                    is drawn as a native sprite, not only its Esp0e glow (EFFECT_TORCH). Log "lake fx:" every 1024 checks.
LAKE_NIGHT_FX ?= 0
ifneq ($(LAKE_NIGHT_FX),0)
ifneq ($(LAKE_NIGHT_FX)$(EFFECT_SPRITES)$(ESP_SPRITE_FAST),111)
$(error LAKE_NIGHT_FX must be 0 or 1 and needs EFFECT_SPRITES=1 ESP_SPRITE_FAST=1)
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_LAKE_NIGHT_FX=1
endif
EFFECT_HAZE_LEAN ?= 0
EFFECT_HAZE_LEAN_TOGGLE ?= 0
EFFECT_PS2_HAZE ?= 0
EFFECT_PS2_STREAK ?= 0
EFFECT_FADE_CLAMP ?= 0
EFFECT_PS2_TOGGLE ?= 0
ifneq ($(filter-out 0 1,$(EFFECT_PS2_HAZE))$(filter-out 0 1 2,$(EFFECT_PS2_STREAK))$(filter-out 0 1,$(EFFECT_FADE_CLAMP))$(filter-out 0 1,$(EFFECT_PS2_TOGGLE)),)
$(error EFFECT_PS2_HAZE / EFFECT_FADE_CLAMP / EFFECT_PS2_TOGGLE are 0 or 1, EFFECT_PS2_STREAK 0..2)
endif
ifneq ($(EFFECT_PS2_HAZE)$(EFFECT_PS2_STREAK),00)
ifneq ($(EFFECT_SPRITES),1)
$(error EFFECT_PS2_HAZE / EFFECT_PS2_STREAK need EFFECT_SPRITES=1)
endif
endif
ifeq ($(EFFECT_PS2_HAZE),1)
ifeq ($(filter 4 5 6 7,$(EFFECT_ROOM)),)
$(error EFFECT_PS2_HAZE needs EFFECT_ROOM bit 4 (the haze class drawn))
endif
endif
ifneq ($(EFFECT_PS2_STREAK),0)
ifeq ($(filter 2 3 6 7,$(EFFECT_ROOM)),)
$(error EFFECT_PS2_STREAK needs EFFECT_ROOM bit 2 (the room glows / streaks drawn))
endif
endif
ifeq ($(EFFECT_PS2_STREAK),2)
ifneq ($(EFFECT_FADE_CLAMP),1)
$(error EFFECT_PS2_STREAK=2 needs EFFECT_FADE_CLAMP=1 (the shafts' near fade))
endif
endif
ifneq ($(EFFECT_HAZE_LEAN),0)
ifeq ($(filter $(EFFECT_HAZE_LEAN),1 2 3 4 5 6 7),)
$(error EFFECT_HAZE_LEAN is a mask 1..7)
endif
ifneq ($(EFFECT_PS2_HAZE),1)
$(error EFFECT_HAZE_LEAN needs EFFECT_PS2_HAZE=1)
endif
ifneq ($(filter 2 3 6 7,$(EFFECT_HAZE_LEAN)),)
$(OBJDIR)/platform/native_static.o: $(OBJDIR)/effects30.h
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/effects30.h
endif
endif
ifeq ($(EFFECT_HAZE_LEAN_TOGGLE),1)
ifneq ($(EFFECT_HAZE_LEAN)$(LOOK_TOGGLE),71)
$(error EFFECT_HAZE_LEAN_TOGGLE=1 needs EFFECT_HAZE_LEAN=7 and LOOK_TOGGLE=1 (the X + START chord and the label))
endif
$(OBJDIR)/platform/pad.o: PLATFORM_CPPFLAGS += -DRE4DC_EFFECT_HAZE_LEAN_TOGGLE=1
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_EFFECT_HAZE_LEAN_TOGGLE=1
else ifneq ($(EFFECT_HAZE_LEAN_TOGGLE),0)
$(error EFFECT_HAZE_LEAN_TOGGLE is 0 or 1)
endif
ifeq ($(EFFECT_PS2_TOGGLE),1)
ifeq ($(EFFECT_PS2_HAZE)$(EFFECT_PS2_STREAK)$(EFFECT_FADE_CLAMP),000)
$(error EFFECT_PS2_TOGGLE needs EFFECT_PS2_HAZE, EFFECT_PS2_STREAK or EFFECT_FADE_CLAMP)
endif
$(OBJDIR)/platform/pad.o: PLATFORM_CPPFLAGS += -DRE4DC_EFFECT_PS2_TOGGLE=1
$(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_EFFECT_PS2_TOGGLE=1
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_EFFECT_PS2_TOGGLE=1
endif
.PHONY: effects30-force
$(OBJDIR)/effects30.h: effects30-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_EFFECT_LEAN %s\n#define RE4DC_EFFECT_SPRITES %s\n#define RE4DC_EFFECT_SPRITE_MAX %s\n' '$(EFFECT_LEAN)' '$(EFFECT_SPRITES)' '$(EFFECT_SPRITE_MAX)' > $@.tmp
ifneq ($(EFFECT_ROOM),0)
	@printf '#define RE4DC_EFFECT_ROOM %s\n' '$(EFFECT_ROOM)' >> $@.tmp
endif
ifneq ($(EFFECT_PS2_HAZE),0)
	@printf '#define RE4DC_EFFECT_PS2_HAZE %s\n' '$(EFFECT_PS2_HAZE)' >> $@.tmp
endif
ifneq ($(EFFECT_PS2_STREAK),0)
	@printf '#define RE4DC_EFFECT_PS2_STREAK %s\n' '$(EFFECT_PS2_STREAK)' >> $@.tmp
endif
ifneq ($(EFFECT_FADE_CLAMP),0)
	@printf '#define RE4DC_EFFECT_FADE_CLAMP %s\n' '$(EFFECT_FADE_CLAMP)' >> $@.tmp
endif
ifneq ($(EFFECT_PS2_TOGGLE),0)
	@printf '#define RE4DC_EFFECT_PS2_TOGGLE %s\n' '$(EFFECT_PS2_TOGGLE)' >> $@.tmp
endif
ifneq ($(EFFECT_HAZE_LEAN),0)
	@printf '#define RE4DC_EFFECT_HAZE_LEAN %s\n' '$(EFFECT_HAZE_LEAN)' >> $@.tmp
endif
ifneq ($(EFFECT_HAZE_LEAN_TOGGLE),0)
	@printf '#define RE4DC_EFFECT_HAZE_LEAN_TOGGLE 1\n' >> $@.tmp
endif
ifneq ($(PS2_FX_ROOMS),0)
	@printf '#define RE4DC_PS2_FX_ROOMS %s\n' '$(PS2_FX_ROOMS)' >> $@.tmp
endif
ifneq ($(PS2_FX_STAGE1),0)
	@printf '#define RE4DC_PS2_FX_STAGE1 %s\n' '$(PS2_FX_STAGE1)' >> $@.tmp
endif
ifneq ($(PS2_FX_POPULATION),0)
	@printf '#define RE4DC_PS2_FX_POPULATION %s\n' '$(PS2_FX_POPULATION)' >> $@.tmp
endif
ifneq ($(PS2_FX_ADDITIONS),0)
	@printf '#define RE4DC_PS2_FX_ADDITIONS %s\n' '$(PS2_FX_ADDITIONS)' >> $@.tmp
endif
ifneq ($(PS2_FX_COMMON_HAZE),0)
	@printf '#define RE4DC_PS2_FX_COMMON_HAZE %s\n' '$(PS2_FX_COMMON_HAZE)' >> $@.tmp
endif
ifneq ($(PS2_FX_ROOMS_EXT),0)
	@printf '#define RE4DC_PS2_FX_ROOMS_EXT %s\n' '$(PS2_FX_ROOMS_EXT)' >> $@.tmp
endif
ifneq ($(PS2_FX_GEN),0)
	@printf '#define RE4DC_PS2_FX_GEN %s\n' '$(PS2_FX_GEN)' >> $@.tmp
endif
ifneq ($(EFFECT_OWNERS_ALL),0)
	@printf '#define RE4DC_EFFECT_OWNERS_ALL %s\n' '$(EFFECT_OWNERS_ALL)' >> $@.tmp
endif
ifneq ($(FX_LEVEL),)
	@printf '#define RE4DC_FX_LEVEL %s\n' '$(if $(filter 3,$(FX_LEVEL)),0,$(FX_LEVEL))' >> $@.tmp
endif
ifneq ($(SHORE_FX_LEVEL),)
	@printf '#define RE4DC_SHORE_FX_LEVEL %s\n' '$(SHORE_FX_LEVEL)' >> $@.tmp
endif
ifneq ($(FX_TRIM),0)
	@printf '#define RE4DC_FX_TRIM 1\n#define RE4DC_FX_ESSENTIAL_BOOT %s\n' '$(if $(filter 3,$(FX_LEVEL)),1,0)' >> $@.tmp
endif
ifneq ($(FX_TRIM_LOG),0)
	@printf '#define RE4DC_FX_TRIM_LOG 1\n' >> $@.tmp
endif
ifneq ($(EFFECT_TORCH),0)
	@printf '#define RE4DC_EFFECT_TORCH %s\n' '$(EFFECT_TORCH)' >> $@.tmp
endif
ifneq ($(FX_PS2_PACK),0)
	@printf '#define RE4DC_FX_PS2_PACK 1\n' >> $@.tmp
endif
ifneq ($(FX_TEX_POOL),0)
	@printf '#define RE4DC_FX_TEX_POOL %s\n' '$(FX_TEX_POOL)' >> $@.tmp
endif
ifneq ($(FX_FLIPBOOK),0)
	@printf '#define RE4DC_FX_FLIP_PTN(p, n) ((n) >= %s ? (p) - (p) %% %s : (p))\n' '$(FX_FLIPBOOK_MIN)' '$(FX_FLIPBOOK)' >> $@.tmp
else
	@printf '#define RE4DC_FX_FLIP_PTN(p, n) (p)\n' >> $@.tmp
endif
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
EFFECTS30_GAME = $(OBJDIR)/src/game/esp_sub.o
EFFECTS30_PLATFORM = $(OBJDIR)/platform/native_ui.o
$(EFFECTS30_GAME) $(EFFECTS30_PLATFORM): $(OBJDIR)/effects30.h
$(EFFECTS30_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/effects30.h
$(EFFECTS30_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/effects30.h

# FX_STRIP21: source Esp01/Esp02 view-space quads, original UVs/current color,
# existing effect deferred FIFO and PVR owner. Experimental; never in a recipe.
FX_STRIP21 ?= 0
ifneq ($(filter-out 0 1,$(FX_STRIP21)),)
$(error FX_STRIP21 is 0 or 1)
endif
ifeq ($(FX_STRIP21),1)
ifneq ($(EFFECT_SPRITES),1)
$(error FX_STRIP21 needs EFFECT_SPRITES=1)
endif
$(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/esp_sub.o $(OBJDIR)/src/game/esp01.o $(OBJDIR)/src/game/esp02.o: GAME_CPPFLAGS += -DRE4DC_FX_STRIP21=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FX_STRIP21=1
endif
# CLOTH_NATIVE=1 (lane fix-fx-missing23 2026-10-23, issue #55 "missing cloth/flags/hanging fabrics"; render only,
#   approximation; default 0 = no code, identical image): the esp4e cloth sheets (cloth.cpp clothTrans, immediate GX that
#   gx_stub sinks) are drawn through the native effect FIFO as view-space strips (native_effect_strip21.inc
#   re4dc_effect_mesh21), one colour per sheet (material x scenery ambient + picked lights). The simulation was always
#   running (its ~1 ms at the r101 cross); only the draw is new. Log: `cloth native:` every 600 frames. Needs FX_STRIP21=1.
CLOTH_NATIVE ?= 0
ifneq ($(filter-out 0 1,$(CLOTH_NATIVE)),)
$(error CLOTH_NATIVE is 0 or 1)
endif
ifeq ($(CLOTH_NATIVE),1)
ifneq ($(FX_STRIP21),1)
$(error CLOTH_NATIVE needs FX_STRIP21=1)
endif
$(OBJDIR)/src/game/cloth.o: GAME_CPPFLAGS += -DRE4DC_FX_STRIP21=1 -DRE4DC_CLOTH_NATIVE=1
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_CLOTH_NATIVE=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_CLOTH_NATIVE=1
endif
# FLASHLIGHT_POOL=1 (lane fix-fx-missing23 2026-10-23, issue #55 item 3 "missing flashlight", user option B; render only,
#   approximation; default 0 = no code, identical image): in a room whose light data attach a spot light to Leon (the
#   night rooms: r11d / r11e chest spot + ~4 m point), trans.cpp draws one additive radial pool quad ahead of him with the
#   depth test inverted (native_flashlight_pool.inc), so the world in front of him brightens like the GameCube's spot.
#   Generated texture (no GameCube asset). Log: `flashlight pool:` once per room. Needs FX_STRIP21=1 (shares its quad path).
#   Tuning (test arms): FLASHLIGHT_POOL_DIST (3500), FLASHLIGHT_POOL_SIZE (1800), FLASHLIGHT_POOL_GAIN (percent, 150). Torch = player-attached spot, radius <= 4000.
FLASHLIGHT_POOL ?= 0
ifneq ($(filter-out 0 1,$(FLASHLIGHT_POOL)),)
$(error FLASHLIGHT_POOL is 0 or 1)
endif
ifeq ($(FLASHLIGHT_POOL),1)
ifneq ($(FX_STRIP21),1)
$(error FLASHLIGHT_POOL needs FX_STRIP21=1)
endif
FLASHLIGHT_POOL_TUNE := $(if $(FLASHLIGHT_POOL_DIST),-DRE4DC_FLASHLIGHT_POOL_DIST=$(FLASHLIGHT_POOL_DIST)) $(if $(FLASHLIGHT_POOL_SIZE),-DRE4DC_FLASHLIGHT_POOL_SIZE=$(FLASHLIGHT_POOL_SIZE)) $(if $(FLASHLIGHT_POOL_GAIN),-DRE4DC_FLASHLIGHT_POOL_GAIN=$(FLASHLIGHT_POOL_GAIN))
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_FX_STRIP21=1 -DRE4DC_FLASHLIGHT_POOL=1 $(FLASHLIGHT_POOL_TUNE)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FLASHLIGHT_POOL=1
endif

# RAIN_R10C_DIAG: private memory-only causal observation, defaults off independently of render arm.
RAIN_R10C_DIAG ?= 0
ifneq ($(RAIN_R10C_DIAG),0)
ifneq ($(RAIN_R10C_DIAG),1)
$(error RAIN_R10C_DIAG is exactly 0 or 1)
endif
ifneq ($(RAIN_DC),1)
$(error RAIN_R10C_DIAG needs RAIN_DC=1)
endif
ifneq ($(RAIN_PS2),1)
$(error RAIN_R10C_DIAG needs RAIN_PS2=1)
endif
ifneq ($(D349_RENDERER_STACK),1)
$(error RAIN_R10C_DIAG needs D349_RENDERER_STACK=1)
endif
ifneq ($(PVR_STREAM),1)
$(error RAIN_R10C_DIAG needs PVR_STREAM=1)
endif
ifneq ($(NATIVE_LASER),1)
$(error RAIN_R10C_DIAG needs NATIVE_LASER=1)
endif
ifneq ($(EFFECT_SPRITES),1)
$(error RAIN_R10C_DIAG needs EFFECT_SPRITES=1)
endif
ifneq ($(RAIN_R10C_DC),0)
ifneq ($(RAIN_R10C_DC),1)
$(error RAIN_R10C_DIAG requires strict RAIN_R10C_DC=0 or 1)
endif
endif
$(OBJDIR)/src/game/filter06.o $(OBJDIR)/src/game/espgen44.o: GAME_CPPFLAGS += -DRE4DC_RAIN_R10C_DIAG=1
endif

# EF03: internal native strip/cloth outcomes. Public int entrypoints retain ABI.
NATIVE_DRAW_OUTCOMES ?= 0
ifneq ($(filter-out 0 1,$(NATIVE_DRAW_OUTCOMES)),)
$(error NATIVE_DRAW_OUTCOMES is 0 or 1)
endif
ifeq ($(NATIVE_DRAW_OUTCOMES),1)
ifneq ($(FX_STRIP21),1)
$(error NATIVE_DRAW_OUTCOMES needs FX_STRIP21=1)
endif
$(OBJDIR)/src/game/esp_sub.o $(OBJDIR)/src/game/cloth.o: GAME_CPPFLAGS += -DRE4DC_NATIVE_DRAW_OUTCOMES=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_NATIVE_DRAW_OUTCOMES=1
endif
