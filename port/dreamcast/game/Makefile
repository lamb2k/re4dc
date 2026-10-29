# The boot-forward RE4 executable: the recovered game sources compiled for
# SH-4 over a Dreamcast implementation of the platform interfaces they call
# (platform/). This is the game's own main(), scheduler, title, game state
# machine, scenario system, rooms, player, enemies and tools, not the room
# viewer in ../room.
#
#   make            build re4dc-game.elf (tools/link.sh: link-name aliases,
#                   then loud stubs for whatever is still unresolved)
#   make census     compile everything and list the symbols the platform
#                   layer still has to provide (no ELF is produced)
#
# Sources outside this directory are never written to: objects go under obj/.

TARGET = re4dc-game.elf
.DEFAULT_GOAL := all
ROOT = ../../..

# The executable is the DOL's own code (src/game). The REL modules (stage
# rooms, sub-screens, tools, enemies) each define their own _prolog/_epilog
# and re-compile shared sources per module, so they join through the module
# table with per-module symbol prefixes; the census still
# compiles them all to keep the platform inventory complete.
GAME_DIRS = src/game
CENSUS_DIRS = src/game src/st src/st1 src/Sscrn \
	src/tools src/Tools src/t_camera src/t_emlist src/t_esp src/t_event \
	src/t_id src/t_light src/t_movie src/t_sce
# yz2asm.cpp / memset_2.cpp are whole-function PowerPC asm with C replacements
# in platform/; t_util_{menu,nomenu,id}.cpp are the REL-specific re-includes of
# t_util.cpp (one object per REL on the GameCube).
GAME_EXCLUDE = src/game/yz2asm.cpp src/game/memset_2.cpp \
	src/tools/t_util_menu.cpp src/tools/t_util_nomenu.cpp src/tools/t_util_id.cpp
GAME_SRCS = $(filter-out $(addprefix $(ROOT)/,$(GAME_EXCLUDE)), \
	$(foreach d,$(GAME_DIRS),$(wildcard $(ROOT)/$(d)/*.cpp)))

CENSUS_SRCS = $(filter-out $(addprefix $(ROOT)/,$(GAME_EXCLUDE)), \
	$(foreach d,$(CENSUS_DIRS),$(wildcard $(ROOT)/$(d)/*.cpp)))
PLATFORM_SRCS = $(filter-out platform/backface_sh4_trace.cpp,$(wildcard platform/*.cpp))
ifneq ($(VMU_CONTEXT),1)
PLATFORM_SRCS := $(filter-out platform/vmu_lcd.cpp,$(PLATFORM_SRCS))
endif
# SDK units compiled from the game's src/lib with the CodeWarrior asm bodies
# stripped (platform/sdk/strip_cw_asm.py) over the shim headers in platform/sdk.
SDK_UNITS = mtx mtxvec mtx44 vec quat OSAlloc
SDK_GEN = $(addprefix platform/sdk/gen/,$(addsuffix .c,$(SDK_UNITS)))

OBJDIR = obj

# Diagnostic only: exact player life/damage/death callers. Default 0 changes no game code.
# Keep this define on the three traced source units; no platform, overlay or recipe default change.
DEATH_TRACE ?= 0
ifneq ($(DEATH_TRACE),0)
ifneq ($(DEATH_TRACE),1)
$(error DEATH_TRACE must be 0 or 1)
endif
$(OBJDIR)/src/game/em_sub.o $(OBJDIR)/src/game/pl_dmg.o $(OBJDIR)/src/game/game.o: GAME_CPPFLAGS += -DRE4DC_DEATH_TRACE=1
endif

# Native Ganado routine-byte repair; default off preserves the original object bytes.
GANADO_ROUTINE_BYTES ?= 0
ifneq ($(GANADO_ROUTINE_BYTES),0)
ifneq ($(GANADO_ROUTINE_BYTES),1)
$(error GANADO_ROUTINE_BYTES must be 0 or 1)
endif
$(OBJDIR)/mod/em10g/shared/src/em10/em10.o: GAME_CPPFLAGS += -DRE4DC_GANADO_ROUTINE_BYTES=1
endif

# EM35_ROUTINE_BYTES=1 (lane fix-mendez-freeze23 2026-10-23, #55 item 5; default 0 = image unchanged): Mendez's
# routine-byte repair, as GANADO_ROUTINE_BYTES. The catch hit stored the GC big-endian word 0x010D000n, which on the
# Dreamcast set routine 1/0 step 0xD (no such Wait step): Mendez froze for the rest of the fight. The bear hug / catch
# player callbacks' word test (EM_RTN) also read the wrong bytes and released Leon at once.
EM35_ROUTINE_BYTES ?= 0
ifneq ($(EM35_ROUTINE_BYTES),0)
ifneq ($(EM35_ROUTINE_BYTES),1)
$(error EM35_ROUTINE_BYTES must be 0 or 1)
endif
$(OBJDIR)/mod/em35/src/em35/em35.o: GAME_CPPFLAGS += -DRE4DC_EM35_ROUTINE_BYTES=1
endif

# EVD_MOVIE_NO_READ=1 (lane purge-movies24 2026-10-24, GC asset purge; default 0 = image unchanged; needs
# ROUTE_MOVIES=1): a route event whose PS2 movie is on the disc (re4dc_movie_available) no longer preloads or
# ARAM-loads its GameCube evd. r100 s03/s20/s30/s40/s41/s43/s44 and r101 s00/s21/s30 (r11c and r11f already read
# none while their movies own the events). The movie path never read the evd; only the source preloads did. Pairs
# with data set evdmv24 (the GC evd files off the disc).
EVD_MOVIE_NO_READ ?= 0
ifneq ($(EVD_MOVIE_NO_READ),0)
ifneq ($(EVD_MOVIE_NO_READ),1)
$(error EVD_MOVIE_NO_READ must be 0 or 1)
endif
$(OBJDIR)/mod/st1_0/src/st1/r100.o $(OBJDIR)/mod/st1_1/src/st1/r101.o: GAME_CPPFLAGS += -DRE4DC_EVD_MOVIE_NO_READ=1
endif

# EM_ADMISSION_DISP_FIX=1 (default 0): restore the caller's display flags when
# readEm cannot find a free module slot, as on its transport-failure return.
EM_ADMISSION_DISP_FIX ?= 1
ifneq ($(EM_ADMISSION_DISP_FIX),0)
ifneq ($(EM_ADMISSION_DISP_FIX),1)
$(error EM_ADMISSION_DISP_FIX must be 0 or 1)
endif
$(OBJDIR)/src/game/read.o: GAME_CPPFLAGS += -DRE4DC_EM_ADMISSION_DISP_FIX=1
endif

# UI_POLY_ORDER: keep pickup/subscreen polygon headers in the source UI list.
UI_POLY_ORDER ?= 0
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_UI_POLY_ORDER=$(UI_POLY_ORDER)
# REL modules linked into the image. On the GameCube each stage REL is its
# own link (config/G4BE08/modules/<mod>/splits.txt lists its units; the
# rooms it does not hold resolve to its _unresolved). tools/gen_modules.py
# turns every module in MODULES into one partially linked object whose only
# global symbols are its renamed entry points (obj/modules.mk), and
# platform/modules.cpp maps the REL header ids to them for OSLink.
MODULES = st1_0 st1_1 st1_2 st1_3 wep02 em12 em23 em15 em26 em28 em21 em2a em29 em2e em13 em27
# ROUTE_CH13=1 (route lane c13, default 0: no effect): chapter 1-3's rooms. Links em18 (module 22, the merchant:
# r102), em17 (21, r108's Ganados; joins the EM10_SHARED group) and em24 (8: r108 / r10a), and r102's s00 is
# presented by its PS2 movie (src/st1/r102.cpp, route-movies.h RE4DC_ROUTE_CH13). r10b (the lake, chapter 1-3's
# end): pl0f (module 43, Leon's boat) and em2f (39, Del Lago).
ROUTE_CH13 ?= 0
ifneq ($(ROUTE_CH13),0)
ifneq ($(ROUTE_CH13),1)
$(error ROUTE_CH13 must be 0 or 1)
endif
# ROUTE_OVL=1 (default with ROUTE_CH13=1): r10b's boat (pl0f) and Del Lago (em2f) are room overlays, not
# resident code: tools/link.sh writes pl0f.ovl / em2f.ovl (as SUBSCREEN_OVL's sscrn.ovl) and strips them from
# the image; platform/modules.cpp reads one into heap 4 when the game links that module and frees it at the
# unlink (r10b exit). The resident image stays no larger than without ROUTE_CH13's r10b code.
ROUTE_OVL ?= 1
ifeq ($(ROUTE_OVL),1)
MODULES += em18 em17 em24 pl0f:ovl em2f:ovl
export RE4DC_LINK_OVERLAY += .ovl_pl0f .ovl_em2f
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_OVL=1
$(OBJDIR)/src/game/game.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_OVL=1
else
MODULES += em18 em17 em24 pl0f em2f
endif
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH13=1
# r108 / r10a play their resident BGM0 track for the second room track (src/game/snd.cpp; the BGM1 slot is 0 bytes).
$(OBJDIR)/src/game/snd.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH13=1
# r10b: espgen45 (the lake height field) keeps hA/hB/pos but skips its GX-only normal/bump/display-list buffers
# (1.36 MB of heap 4; GX is a stub here: WATER45_NATIVE draws the surface).
$(OBJDIR)/src/game/espgen45.o: GAME_CPPFLAGS += -DRE4DC_WATER45_LEAN=1
WATER45_GRID_SKIP ?= 1
ifeq ($(WATER45_GRID_SKIP),1)
$(OBJDIR)/src/game/espgen45.o $(OBJDIR)/src/game/Espgen42.o: GAME_CPPFLAGS += -DRE4DC_WATER45_GRID_SKIP=1
endif
# r10a / r11a: espgen42 (the room lake water) without its height grid (hA / hB / pos / nrm / bump / display list) or
# its per-frame update (r11a ~18 hw ms of logic). Logic reads only the plane; the init's shared-RNG draws are kept.
WATER42_GRID_SKIP ?= 1
ifeq ($(WATER42_GRID_SKIP),1)
$(OBJDIR)/src/game/Espgen42.o: GAME_CPPFLAGS += -DRE4DC_WATER42_GRID_SKIP=1
endif
# WATER45_NATIVE=1 (default with ROUTE_CH13=1): espgen45 draws the lake surface natively (re4dc_water45_draw: the
# plane over the grid and far border, the GameCube's scene x TEV colour as a PVR multiply, fogged per corner). Without
# it nothing draws the water (GX stub, no water mesh in the PS2 world): the fog-coloured background shows (pale lake).
WATER45_NATIVE ?= 1
ifeq ($(WATER45_NATIVE),1)
$(OBJDIR)/src/game/espgen45.o $(OBJDIR)/src/game/espgen.o $(OBJDIR)/src/game/trans.o $(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_WATER45_NATIVE=1
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WATER45_NATIVE=1
endif
# LAKE_RIPPLES=n (Phase 2 C4, default 0: no effect, platform/native_lake.cpp not built; n = 1 or 2 layers; needs
# WATER45_NATIVE=1): a moving surface on the r10b lake: n translucent layers of a small tileable ripple texture
# (made at the first lake frame, 8 KiB VRAM) scrolled per frame over each WATER45_NATIVE cell, faded with the fog, and
# a per-corner sun glint in the offset colour; the multiply stays. LAKE_TILE (mm per repeat), LAKE_ALPHA tune it.
LAKE_RIPPLES ?= 0
LAKE_TILE ?= 2800.0f
LAKE_ALPHA ?= 0.35f
ifneq ($(LAKE_RIPPLES),0)
ifneq ($(WATER45_NATIVE),1)
$(error LAKE_RIPPLES needs WATER45_NATIVE=1)
endif
$(OBJDIR)/src/game/espgen45.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_lake.o: GAME_CPPFLAGS += -DRE4DC_LAKE_RIPPLES=$(LAKE_RIPPLES)
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_lake.o $(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_LAKE_RIPPLES=$(LAKE_RIPPLES) -DRE4DC_LAKE_TILE=$(LAKE_TILE) -DRE4DC_LAKE_ALPHA=$(LAKE_ALPHA)
endif
# LAKE_ZBIAS=s (test 11 item B, default 0: no effect; render only; needs LAKE_RIPPLES): the ripple layers' PVR depth
# (1/w of every clipped vertex, native_lake.cpp) times s. The layers lie in the WATER45_NATIVE multiply's plane, so the
# two translucent draws tie in depth and their order is the sorter's choice (audit 10-14: espgen45.cpp re4dc_water45_quad
# then re4dc_lake_cell; on the console PVR the order can flip). s > 1 (1.001) puts the ripples just in front of the
# multiply (the order Flycast shows today); s < 1 (0.999, check value) just behind it (the ripples darken away).
# A decimal between 0.9 and 1.1.
LAKE_ZBIAS ?= 0
ifneq ($(LAKE_ZBIAS),0)
ifeq ($(filter 1 2,$(LAKE_RIPPLES)),)
$(error LAKE_ZBIAS needs LAKE_RIPPLES=1 or 2)
endif
ifeq ($(shell echo '$(LAKE_ZBIAS)' | grep -Eq '^(0\.9[0-9]*|1\.0[0-9]*|1\.1)$$' && echo ok),)
$(error LAKE_ZBIAS must be 0 or a decimal between 0.9 and 1.1 (e.g. 1.001))
endif
$(OBJDIR)/platform/native_lake.o: PLATFORM_CPPFLAGS += -DRE4DC_LAKE_ZBIAS=$(LAKE_ZBIAS)f
endif
# WATER_PS2=1 (lane water16 2026-10-16; render only, default 0; needs WATER45_NATIVE=1): the room water of r107, r108,
# r10a, r10b, r11a and r11b as the PS2 draws it. The PS2 has no generator water (Espgen42_Trans is `jr ra`, Espgen45_Trans
# only clears a flag): its rooms stack Esp08 world planes (a flat dark base, two scrolling 0xf2 water layers, an
# animated noise layer). espgen45.cpp re4dc_water_ps2_draw draws those planes once per drawn image from the generated
# table src/game/water_ps2_table.inc (tools/d367/water/water_ps2_table.py) as native layers (platform/include/
# native_water_ps2.inc: eye-centred grids of textured translucent strips, UV repeat, table fog). In r10b it replaces the
# WATER45_NATIVE multiply and the LAKE_RIPPLES layers. No PS2 record is spawned: effect slots, generators, areas and
# Rnd() are untouched (logic STRICT). WATER_PS2_FLIP=n: animated layers show every n-th picture (default 8: 8 of the
# 60 0xfe frames, 17.8 KB of VRAM; 4 doubles it). WATER_PS2_ROOMS: hex mask of the rooms drawn (bit 0 r107, 1 r108,
# 2 r10a, 3 r10b, 4 r11a, 5 r11b). Default 0x3f = all six (10-16, lane water16b): r10b / r11b fit after the vq16w VQ set
# (data sets vq16w + water16i); 0x17 = r107 r108 r10a r11a was test 15's first landing (user option A).
WATER_PS2 ?= 0
WATER_PS2_FLIP ?= 8
WATER_PS2_ROOMS ?= 0x3f
ifneq ($(WATER_PS2),0)
ifneq ($(WATER_PS2)$(WATER45_NATIVE),11)
$(error WATER_PS2 must be 0 or 1 and needs WATER45_NATIVE=1)
endif
$(OBJDIR)/src/game/espgen45.o: GAME_CPPFLAGS += -DRE4DC_WATER_PS2=1 -DRE4DC_WATER_PS2_FLIP=$(WATER_PS2_FLIP) \
  -DRE4DC_WATER_PS2_ROOMS=$(WATER_PS2_ROOMS)
$(OBJDIR)/src/game/Espgen42.o $(OBJDIR)/src/game/espgen.o: GAME_CPPFLAGS += -DRE4DC_WATER_PS2=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_WATER_PS2=1
endif
# WATER_PS2_EXT=1 (lane fix-water-traps23 2026-10-23, GitHub #55 item 2; render only, default 0; needs WATER_PS2=1): the
# rivers of r10c / r10d / r10e and the r10c waterfall curtains as the PS2 draws them (SST Esp08 world planes of the room
# EFF: dark base 0xf7, noise 0xfe / 0xef, water 0xf2, falling-water streaks 0xc5), from src/game/water_ps2_ext.inc
# (tools/d367/water/water_ps2_ext.py, read from the PS2 disc). Same native water layer as WATER_PS2, rows carry their
# plane axes (vertical / tilted waterfall planes). WATER_PS2_EXT_ROOMS: bit 0 r10c, 1 r10d, 2 r10e (default 7).
# Effect slots, generators, areas and Rnd() untouched (logic STRICT). Log: "water ext: ... not loaded" once per row.
WATER_PS2_EXT ?= 0
WATER_PS2_EXT_ROOMS ?= 7
ifneq ($(WATER_PS2_EXT),0)
ifneq ($(WATER_PS2_EXT)$(WATER_PS2),11)
$(error WATER_PS2_EXT must be 0 or 1 and needs WATER_PS2=1)
endif
$(OBJDIR)/src/game/espgen45.o: GAME_CPPFLAGS += -DRE4DC_WATER_PS2_EXT=1 -DRE4DC_WATER_PS2_EXT_ROOMS=$(WATER_PS2_EXT_ROOMS)
endif
# PS2_CH1_ENEMY=1 (lane alivecap 2026-10-15, user 10-15 "the PS2 logic holistically for enemy spawns in chapter 1, with
#   our game cutting out more when it hits our threshold"; CHANGES GAMEPLAY by design; default 0 = off): one umbrella
#   for every PS2 enemy-spawn rule of the stage 1 route (1-1 .. 2-1: r100-r10e, r117-r119, r11a, r11b; table in
#   C:\Game Dev\Emulators\ALIVECAP-20261015.md) plus the cap on top. It forces PS2_ENEMY_RULES=1 (list start bits:
#   r101 villagers, r103 animals, r107 fish + Ganados, r10a snakes; r101 waves < 5 / villagers < 9; r107 areas 6/7/8),
#   ORs PS2_ENEMY_ROOMS with 0x33f (0x01 r100 trap, 0x02 r101 s21 / dog, 0x04 r104, 0x08 r108 bell rows, 0x10 r11a,
#   0x20 r11b, 0x100 r101 area-15 trio, 0x200 r118 0x7D), sets ALIVE_CAP=6 when not given (r101 through
#   R101_ALIVE_CAP, the same N) and ALIVE_CAP_PARK=1 (more than N alive anyway: the farthest off-screen Ganado is
#   parked and re-queued, never deleted) and R101_CAP_WAVES=1 (r101's reset waves capped too). PS2 gates stricter than the cap (r101 waves < 5, r111 < 5, r113 / r118 < 6)
#   stay as they are. Chapter 2-2 / 2-3 bits (0x40 r11c, 0x80 r11d) are not part of it.
PS2_CH1_ENEMY ?= 0
ifneq ($(PS2_CH1_ENEMY),0)
ifneq ($(PS2_CH1_ENEMY),1)
$(error PS2_CH1_ENEMY must be 0 or 1)
endif
override PS2_ENEMY_RULES := 1
override PS2_ENEMY_ROOMS := $(shell printf '0x%x' $$(( $(or $(PS2_ENEMY_ROOMS),0) | 0x33f )))
ifeq ($(or $(ALIVE_CAP),0),0)
override ALIVE_CAP := 6
endif
override ALIVE_CAP_PARK := 1
override R101_CAP_WAVES := 1
endif
# PS2_CH2_ENEMY=1 (lane ch2code16 2026-10-16, user 10-15 per-chapter rule "the PS2 logic holistically for enemy spawns ...
#   with our game cutting out more when it hits our threshold"; CHANGES GAMEPLAY by design; default 0 = off; needs
#   ROUTE_CH22=1 ROUTE_CH23=1 and PS2_ENEMY_CH22_DIR / PS2_ENEMY_CH23_DIR): the one umbrella for every PS2 enemy-spawn
#   change of chapters 2-2 and 2-3 (r111 r112 r113 r11c r11d r11e r10f r11f r200; table in
#   C:\Game Dev\Emulators\CH2-CODE-COMPLETE-20261016.md): the qualified PS2 list rows (platform/ps2_enemy_ch22.cpp /
#   ps2_enemy_ch23.cpp, applied at list read) and the PS2 room code (r111 alive < 5 by area, r113 0xB7 below 6, r10f,
#   r11f, r200 truck wave 0x6A..0x70), PS2_ENEMY_ROOMS |= 0x80 (r11d, the PS2 Bella-sisters village), plus the cap on
#   top: ALIVE_CAP=6 when not given and ALIVE_CAP_PARK=1 (as PS2_CH1_ENEMY). Without it ROUTE_CH22 / ROUTE_CH23 keep
#   the GameCube lists and room code. Documented cap exceptions (kept sends: their callers use the returned enemy):
#   the r10f gondola riders and 32 / 35, the r11c cabin below. Park never acts in r10f, r11c, r11d.
#   The PS2 cabin is part of the unit (user decision 10-16: "why wouldn't it if we are using the enemy cap for ps2 as a
#   standing decision"): r11c as on the PS2 (PS2_ENEMY_ROOMS 0x40: 7 new em13 rows, HP +200, waves of 5 refilled below 5
#   alive, kill limit 40 / timer 9000). Its peak stays under the cap; park never acts in r11c (its script keeps the
#   enemy pointers). The GameCube cabin (9 sent at once) remains only with PS2_CH2_ENEMY=0.
PS2_CH2_ENEMY ?= 0
ifeq ($(filter $(PS2_CH2_ENEMY),0 1),)
$(error PS2_CH2_ENEMY must be 0 or 1)
endif
ifneq ($(PS2_CH2_CABIN),)
$(error PS2_CH2_CABIN was folded into PS2_CH2_ENEMY (user 10-16): the PS2 cabin is always on with it)
endif
ifeq ($(PS2_CH2_ENEMY),1)
ifneq ($(or $(ROUTE_CH22),0)$(or $(ROUTE_CH23),0),11)
$(error PS2_CH2_ENEMY=1 needs ROUTE_CH22=1 ROUTE_CH23=1)
endif
override PS2_ENEMY_RULES := 1
override PS2_ENEMY_ROOMS := $(shell printf '0x%x' $$(( $(or $(PS2_ENEMY_ROOMS),0) | 0x80 | 0x40 )))
ifeq ($(or $(ALIVE_CAP),0),0)
override ALIVE_CAP := 6
endif
override ALIVE_CAP_PARK := 1
$(OBJDIR)/src/game/stage.o: GAME_CPPFLAGS += -DRE4DC_PS2_CH2_ENEMY=1
endif
# PS2_CH3_ENEMY=1 (castle lane 2026-10-15, user 10-15 "the PS2 logic holistically for enemy spawns" per chapter;
#   CHANGES GAMEPLAY by design; default 0 = off; needs ROUTE_CH31=1): one umbrella for every PS2 enemy-spawn change of
#   chapter 3 (3-1 .. 3-4: r200 r202 r207 r203 r201 r208 r204 r205 r209 r20a r20b r20c r20f r206 r20d r20e; table in
#   C:\Game Dev\Emulators\CASTLE-ROUTE-20261015.md) plus the cap on top. It forces PS2_ENEMY_RULES=1; adopts the PS2
#   emleon02 / emleon03 rows of r201 r203 r207 r208 / r204 r20e (platform/ps2_enemy_ch3.cpp, private table
#   PS2_ENEMY_CH3_DIR/ps2_enemy_ch3_data.inc from tools/d367/castle/ps2_enemy_ch3.py; every baseline byte checked);
#   ORs PS2_ENEMY_CASTLE with 0x03 (r208 room code, r20b waves); sets ALIVE_CAP=6 when not given. Chapter 3 rooms
#   hold only (no ALIVE_CAP_PARK: their code keeps wrap pointers). Not ported on purpose: Easy-only branches; r205
#   (Normal result identical: the PS2 list holds 0x57 / 0x6D and R205Init sends both); r209 (same as GC).
PS2_CH3_ENEMY ?= 0
PS2_ENEMY_CH3_DIR ?=
ifneq ($(PS2_CH3_ENEMY),0)
ifneq ($(PS2_CH3_ENEMY)$(ROUTE_CH31),11)
$(error PS2_CH3_ENEMY must be 0 or 1 and needs ROUTE_CH31=1)
endif
ifeq ($(wildcard $(PS2_ENEMY_CH3_DIR)/ps2_enemy_ch3_data.inc),)
$(error PS2_CH3_ENEMY needs PS2_ENEMY_CH3_DIR/ps2_enemy_ch3_data.inc (tools/d367/castle/ps2_enemy_ch3.py))
endif
override PS2_ENEMY_RULES := 1
override PS2_ENEMY_CASTLE := $(shell printf '0x%x' $$(( $(or $(PS2_ENEMY_CASTLE),0) | 0x03 )))
ifeq ($(or $(ALIVE_CAP),0),0)
override ALIVE_CAP := 6
endif
$(OBJDIR)/src/game/stage.o $(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_PS2_CH3_ENEMY=1
$(OBJDIR)/platform/ps2_enemy_ch3.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_CH3_ENEMY=1 -DRE4DC_PS2_ENEMY_RULES=1 -I$(PS2_ENEMY_CH3_DIR)
$(OBJDIR)/platform/ps2_enemy_ch3.o: $(PS2_ENEMY_CH3_DIR)/ps2_enemy_ch3_data.inc
endif
# PS2_CH4_ENEMY=1 (lane ch4found16 2026-10-16, user 10-15 "the PS2 logic holistically for enemy spawns" per chapter;
#   CHANGES GAMEPLAY by design; default 0 = off; needs ROUTE_CH41=1): one umbrella for every PS2 enemy-spawn change of
#   chapter 4 (4-1 .. 4-4: r206 r210 r222 r201 r219 r211 r216 r212 r213 r214 r217 r218 r215 r229 r221 r22b r220 r223
#   r224 r21d r225 r21b r226 r227 r228 r22a; table in C:\Game Dev\Emulators\CH4-FOUNDATIONS-20261016.md) plus the cap on
#   top. It forces PS2_ENEMY_RULES=1; adopts the PS2 emleon04 / emleon05 rows of r211..r222 / r21b..r22a
#   (platform/ps2_enemy_ch4.cpp, private table PS2_ENEMY_CH4_DIR/ps2_enemy_ch4_data.inc from
#   tools/d367/castle/ps2_enemy_ch4.py; every baseline byte checked); ORs PS2_ENEMY_CASTLE with 0xE4 (r216 one display
#   armor + its area stub, r226 reinforcement block, r227 far-side task, r223 Normal init sends); sets ALIVE_CAP=6 when
#   not given. Chapter 4 rooms hold only (no ALIVE_CAP_PARK there: their code keeps cEmWrap pointers of its sends).
#   Not ported on purpose: Easy-only / Pro-only branches; r21a (optional room: its reworked list and wave code, bit
#   0x08); r214's PS2 enemy pool 60 -> 70 (a CNS memory setting, not a spawn rule).
PS2_CH4_ENEMY ?= 0
PS2_ENEMY_CH4_DIR ?=
ifneq ($(PS2_CH4_ENEMY),0)
ifneq ($(PS2_CH4_ENEMY)$(ROUTE_CH41),11)
$(error PS2_CH4_ENEMY must be 0 or 1 and needs ROUTE_CH41=1)
endif
ifeq ($(wildcard $(PS2_ENEMY_CH4_DIR)/ps2_enemy_ch4_data.inc),)
$(error PS2_CH4_ENEMY needs PS2_ENEMY_CH4_DIR/ps2_enemy_ch4_data.inc (tools/d367/castle/ps2_enemy_ch4.py))
endif
override PS2_ENEMY_RULES := 1
override PS2_ENEMY_CASTLE := $(shell printf '0x%x' $$(( $(or $(PS2_ENEMY_CASTLE),0) | 0xE4 )))
ifeq ($(or $(ALIVE_CAP),0),0)
override ALIVE_CAP := 6
endif
$(OBJDIR)/src/game/stage.o $(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_PS2_CH4_ENEMY=1
$(OBJDIR)/platform/ps2_enemy_ch4.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_CH4_ENEMY=1 -DRE4DC_PS2_ENEMY_RULES=1 -I$(PS2_ENEMY_CH4_DIR)
$(OBJDIR)/platform/ps2_enemy_ch4.o: $(PS2_ENEMY_CH4_DIR)/ps2_enemy_ch4_data.inc
endif
# PS2_ENEMY_RULES=1 (test 9 lane PS2EN, default 0; changes gameplay by design): the PS2 USA enemy rules of the
# chapter 1 rooms. Enemy list emleon00 gets the PS2 start-alive bits / flags (stage.cpp, at list read); r101 sends
# its reset waves when fewer than 5 Ganados are alive (GameCube: after 5 / 10 kills) and holds two villagers back
# as reinforcements (fewer than 9 alive, PS2 area 0x21); r107 holds three Ganados and five fish until PS2 areas
# 6 / 7 / 8. r103 (3 cows, 3 chickens) and r10a (2 snakes) only lose list entries the PS2 never spawns.
PS2_ENEMY_RULES ?= 0
ifneq ($(PS2_ENEMY_RULES),0)
$(OBJDIR)/src/game/stage.o $(OBJDIR)/mod/st1_1/src/st1/r101.o $(OBJDIR)/mod/st1_1/src/st1/r107.o: GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_RULES=$(PS2_ENEMY_RULES)
endif
# ANIMALS_OFF=1 (user 2026-10-17 "Get rid of them asap"; CHANGES GAMEPLAY by design: no eggs from chickens; default 0 = off;
#   needs PS2_ENEMY_RULES=1): the ambient animals of the stage 1 enemy lists (emleon00 / emleon01) are not spawned:
#   every cow (em26) and chicken (em28), and the dog (em21) only when ambient (list set 0: the r103 farm dog 0x56).
#   The scripted dogs stay: the r100 bear-trap dog (0x09, set 1) and the r119 El Gigante dog (0x29, set 2); crows,
#   snakes and fish are untouched. Removed rows: r101 0x34 cow, 0x4E / 0x4F chickens; r103 0x50..0x55 cows, 0x56 dog,
#   0x57 0x58 0x5A..0x5D chickens (0x4E 0x50 0x54 0x55 0x57 0x58 0x5C are already off with PS2_ENEMY_RULES: the PS2 lists
#   never spawn them). No room code sends, counts or waits on these rows (r101's s21 removal handles a missing 0x34 /
#   0x4F); their escape alarm (Status_flg[1] bit 29) is read only by other animals and chapter 3+ enemies. Applied at
#   spawn (EmSetFromList), so a save made with animals loads without them. C:\Game Dev\Emulators\ANIMALSOFF-20261017.md
ANIMALS_OFF ?= 0
ifeq ($(filter $(ANIMALS_OFF),0 1),)
$(error ANIMALS_OFF must be 0 or 1)
endif
ifeq ($(ANIMALS_OFF),1)
ifeq ($(PS2_ENEMY_RULES),0)
$(error ANIMALS_OFF=1 needs PS2_ENEMY_RULES=1 (PS2_CH1_ENEMY=1 sets it))
endif
$(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_ANIMALS_OFF=1
endif
# PS2_ENEMY_ROOMS=<mask> (lane ps2enemy 2026-10-14, default 0: no effect; needs PS2_ENEMY_RULES=1; changes gameplay
# by design): more PS2 USA room-code enemy rules (st1_0..2.rel, decoded per room), one bit per room:
#   0x01 r100: the after-state trap 0x7A is not set; list entries 3 / 4 take the PS2 flags (swapped)
#   0x02 r101: the house event (s21) sends 9 Ganados (not 0x3E / 0x44) and removes the dog 0x34 and entry 0x4F
#   0x04 r104: 7 Ganados at the start (not 12), 6 patrols (the dash-in drops two, sends two), dash-in 0xFC/0xFD,
#        waves only after the dash, by area while fewer than 7 are alive, at most twice each; area 0x15 far-deletes
#        down to 7 then sends 0xF8/0xF9; areas 0x16/0x17 send 0xF2/0xFE while fewer than 8; entry 0xF1 PS2 flags;
#        the merchant 0x5E is drawn / moved only in PS2 area 0x18 after s20
#   0x08 r108: the bell reinforcements come from the half of the village Leon stands in (x > 13500: 6 entries,
#        else 5), up to 3 never-sent entries
#   0x10 r11a: list-1 entries 0x16/0x18/0x1C/0x1D held back: 2 at entry by side, the rest one at a time from PS2
#        areas (flags 64/65) while fewer than 9 are alive (the ROUTE_CH22 r11a code, now also in chapter 2-1)
#   0x20 r11b: the shore ambush leaves 0x3E/0x3F for later (PS2 area 0x0B, fewer than 2 em22 alive); the 8 fish
#        are drawn / moved only while Leon is in PS2 area 0x0A
#   0x40 r11c (needs ROUTE_CH22; lane alivecap 2026-10-15): Luis' cabin as on the PS2 (st1_3.rel): 7 new em13 rows,
#        HP +200, Character 2 -> 6; waves of 5 refilled below 5 alive, kill limit 40 / timer 9000 (easy 30 / 7200)
#   0x80 r11d (needs ROUTE_CH23; lane alivecap 2026-10-15): the PS2 Bella-sisters village (6 start dead and come
#        in by area / reinforcement, HP +200, set / Character as the PS2 list)
#   0x100 r101 (needs 0x02): the square trio 0x22-0x24 is not sent at the fight start but from PS2 area 15 (rsf 6 set,
#        7 / 8 clear, fewer than 7 alive; rsf 11, emNum + 3). Needs include/r101_ps2_area15.h (PS2 quad, pending)
#   0x200 r118: 0x7D held at R118Init, sent once in the PS2 area (Room_flg[2] bit 31 there) while fewer than 6 are
#        alive (rsf 2). Needs include/r118_ps2_area.h (PS2 quad, pending)
# ROUTE_CH22 no longer applies the r100 / r104 / r11a rows itself (bits 0x01 / 0x04 / 0x10 own them).
# include/em_far_delete.h: the shared PS2 EmFarDelete / EmFarDeleteNoWrap helper (header-only; r301 / r327 lanes).
PS2_ENEMY_ROOMS ?= 0
ifneq ($(PS2_ENEMY_ROOMS),0)
ifneq ($(PS2_ENEMY_RULES),1)
$(error PS2_ENEMY_ROOMS needs PS2_ENEMY_RULES=1)
endif
$(OBJDIR)/src/game/stage.o $(OBJDIR)/mod/st1_0/src/st1/r100.o $(OBJDIR)/mod/st1_1/src/st1/r101.o $(OBJDIR)/mod/st1_1/src/st1/r104.o $(OBJDIR)/mod/st1_1/src/st1/r108.o $(OBJDIR)/mod/st1_3/src/st1/r108.o $(OBJDIR)/mod/st1_2/src/st1/r11a.o $(OBJDIR)/mod/st1_2/src/st1/r11b.o: GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_ROOMS=$(PS2_ENEMY_ROOMS)
$(OBJDIR)/mod/st1_3/src/st1/r11c.o $(OBJDIR)/mod/st1_3/src/st1/r11d.o $(OBJDIR)/mod/st1_3/src/st1/r118.o: GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_ROOMS=$(PS2_ENEMY_ROOMS)
$(OBJDIR)/platform/ps2_enemy_ch22.o $(OBJDIR)/platform/ps2_enemy_ch23.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_ENEMY_ROOMS=$(PS2_ENEMY_ROOMS)
endif
# ALIVE_CAP=N (lane alivecap 2026-10-15, user rule 10-15 "Ganados at 6"; CHANGES GAMEPLAY by design; default 0 = off):
#   at most N Ganados (ids 0x10..0x20) alive at once in every room. Start-list Ganados beyond N are held at room entry
#   (their list entry untouched) and come in one at a time, at least 30 frames apart, outside events / pauses, while
#   fewer than N are alive, farthest from Leon first (em_set.cpp). SceCountEmAlive counts held ones as alive, so room
#   scripts' alive tests, waves and kill counts read as uncapped; SceDestroyEm drops held ones of its range. Room-code
#   sends are not deferred. r101: with PS2_ENEMY_ROOMS bit 0x02 the cap is R101_ALIVE_CAP=N (crowd12's r101 hold
#   order, queued sends and villager rule; the generic hold stands aside there); without the bit the generic hold
#   runs in r101 too. Setting R101_ALIVE_CAP to another value as well is an error.
# ALIVE_CAP_LOG=1 (diagnostic, default 0): "alivecap:" lines (holds, releases, destroys).
# ALIVE_CAP_PARK=1 (default 0; set by PS2_CH1_ENEMY): when more than N are alive anyway (sends kept for callers that
#   use the returned enemy, event Ganados), the farthest off-screen unhurt Ganado in its plain AI routine is parked:
#   destroyed and re-queued in the hold (list entry alive, not set), so it still counts as alive and comes back below
#   the cap; no kill or death link. Not in rooms whose code holds pointers of its sends (r101 r104 r10a r10c r10f
#   r11c r11d).
ALIVE_CAP ?= 0
ALIVE_CAP_LOG ?= 0
# ALIVE_CAP_DEFER_FLAGS_BEGIN: preserve original setFlag commands on held handles.
# Default off; apply after original first AI initialization, never force admission.
ALIVE_CAP_DEFER_FLAGS ?= 0
ifneq ($(words $(ALIVE_CAP_DEFER_FLAGS)),1)
$(error ALIVE_CAP_DEFER_FLAGS must be 0 or 1)
endif
ifneq ($(filter-out 0 1,$(ALIVE_CAP_DEFER_FLAGS)),)
$(error ALIVE_CAP_DEFER_FLAGS must be 0 or 1)
endif
ifeq ($(ALIVE_CAP_DEFER_FLAGS),1)
ifeq ($(ALIVE_CAP),0)
$(error ALIVE_CAP_DEFER_FLAGS=1 requires ALIVE_CAP)
endif
$(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_DEFER_FLAGS=1
$(OBJDIR)/mod/%.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_DEFER_FLAGS=1
endif
# ALIVE_CAP_DEFER_FLAGS_END
# ALIVE_CAP_DEFER_GOTO_R207_BEGIN: source-proven r207 queued movement only.
# Other rooms, including unresolved r214 event capacity, keep their old behavior.
ALIVE_CAP_DEFER_GOTO_R207 ?= 0
ifneq ($(words $(ALIVE_CAP_DEFER_GOTO_R207)),1)
$(error ALIVE_CAP_DEFER_GOTO_R207 must be 0 or 1)
endif
ifneq ($(filter-out 0 1,$(ALIVE_CAP_DEFER_GOTO_R207)),)
$(error ALIVE_CAP_DEFER_GOTO_R207 must be 0 or 1)
endif
ifeq ($(ALIVE_CAP_DEFER_GOTO_R207),1)
ifeq ($(ALIVE_CAP),0)
$(error ALIVE_CAP_DEFER_GOTO_R207=1 requires ALIVE_CAP)
endif
ifneq ($(ALIVE_CAP_DEFER_FLAGS),1)
$(error ALIVE_CAP_DEFER_GOTO_R207=1 requires ALIVE_CAP_DEFER_FLAGS=1)
endif
$(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_DEFER_GOTO_R207=1
$(OBJDIR)/mod/%.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_DEFER_GOTO_R207=1
endif
# ALIVE_CAP_DEFER_GOTO_R207_END
# ALIVE_CAP_NOVIS=1 (I-006, default off): stage-2 Novistadors (id2D) share
# the existing ALIVE_CAP budget with Ganados. Creation/send holds and fresh
# accounting only; castle pointer-owner rooms remain excluded from parking.
ALIVE_CAP_NOVIS ?= 0
# PARTS_LINKED_FLAG: preserve the source indexing promise on linked fallback.
# Demand-backed parts can reuse a model after a prior contiguous joint.
PARTS_LINKED_FLAG ?= 1
ifneq ($(words $(PARTS_LINKED_FLAG)),1)
$(error PARTS_LINKED_FLAG must be 0 or 1)
endif
ifneq ($(filter-out 0 1,$(PARTS_LINKED_FLAG)),)
$(error PARTS_LINKED_FLAG must be 0 or 1)
endif
ifeq ($(PARTS_LINKED_FLAG),1)
$(OBJDIR)/src/game/model.o: GAME_CPPFLAGS += -DRE4DC_PARTS_LINKED_FLAG=1
endif
# ALIVE_CAP_R202_GATE_BEGIN: default-off original gate/operator initial admission.
# The normal r202 camera event needs operator2E's rock. At cap4, visit its
# original ESL record before operator21; all eligibility/held/death guards remain.
ALIVE_CAP_R202_GATE ?= 0
ifneq ($(words $(ALIVE_CAP_R202_GATE)),1)
$(error ALIVE_CAP_R202_GATE must be 0 or 1)
endif
ifneq ($(filter-out 0 1,$(ALIVE_CAP_R202_GATE)),)
$(error ALIVE_CAP_R202_GATE must be 0 or 1)
endif
ifeq ($(ALIVE_CAP_R202_GATE),1)
ifneq ($(ALIVE_CAP),4)
$(error ALIVE_CAP_R202_GATE=1 requires ALIVE_CAP=4)
endif
$(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_R202_GATE=1
endif
# ALIVE_CAP_R202_GATE_END
# CAP_COMPARE=1 (below): the cap values the sources compare with (the constants, or the runtime re4dc_cap_rt)
CAP_COMPARE ?= 0
ALIVE_CAP_N = $(if $(filter 1,$(CAP_COMPARE)),re4dc_cap_rt,$(ALIVE_CAP))
R101_CAP_N = $(if $(filter 1,$(CAP_COMPARE)),re4dc_cap_rt,$(R101_ALIVE_CAP))
ifneq ($(ALIVE_CAP),0)
ALIVE_CAP_R101 := $(shell [ $$(( ($(PS2_ENEMY_ROOMS)) & 2 )) -ne 0 ] && echo 1 || echo 0)
ifneq ($(filter-out 0 $(ALIVE_CAP),$(R101_ALIVE_CAP)),)
$(error ALIVE_CAP=$(ALIVE_CAP) with R101_ALIVE_CAP=$(R101_ALIVE_CAP): set ALIVE_CAP only (it sets r101's cap too))
endif
ifeq ($(ALIVE_CAP_R101),1)
R101_ALIVE_CAP := $(ALIVE_CAP)
endif
$(OBJDIR)/src/game/em_set.o $(OBJDIR)/src/game/sce_com.o $(OBJDIR)/src/game/sce_sys.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP=$(ALIVE_CAP) -DRE4DC_ALIVE_CAP_R101=$(ALIVE_CAP_R101) -DRE4DC_ALIVE_CAP_LOG=$(ALIVE_CAP_LOG)
$(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_N=$(ALIVE_CAP_N)
ifneq ($(ALIVE_CAP_NOVIS),0)
$(OBJDIR)/src/game/em_set.o $(OBJDIR)/mod/st2_1/src/st2/r205.o $(OBJDIR)/mod/st2_2/src/st2/r213.o $(OBJDIR)/mod/st2_3/src/st2/r21d.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_NOVIS=$(ALIVE_CAP_NOVIS)
endif
ifneq ($(or $(ALIVE_CAP_PARK),0),0)
$(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_PARK=1
endif
# Room modules that call the shared PS2 far delete (include/em_far_delete.h: r301 / r327) see the cap's held
# entries (RE4DC_ALIVE_CAP_ON; only that header tests it).
$(OBJDIR)/mod/%.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_ON=1
endif
# PS2_ENEMY_CASTLE=<mask> (lane castle 2026-10-15, default 0: no effect; needs PS2_ENEMY_RULES=1; changes gameplay by
# design): PS2 USA room-code enemy rules for the castle (st2_*.rel, Normal mode, each read from the PS2 disassembly;
# Easy-only branches are not ported). One bit per room; reserved bits are not implemented yet:
#   0x01 r208 (st2_0 0x11598 / 0x11ff0 / 0x13e18 / 0x13e58 / 0x14180; needs the PS2 emleon02 rows: PS2_CH3_ENEMY):
#        R208Init sends 6 (3, 5, 6, 7, 1, 0x11; rank >= 7: 3, 0x5F, 0x60, 7, 0x61, 0x5E) where the GC sends 9 / 11;
#        group A (areas 6/7) sends its two events + 0xD only while fewer than 4 are alive, 0x3C / 0x3D at exactly
#        1; group D sends 0x23 / 0x25 (GC also 0x24 / 0x26); area 0x15 opens it below 5 alive (GC <= 5); the
#        over-the-wall feed after the crank runs while the reset count is < 9 (GC <= 5), every 300 / 190 frames
#        (GC 590 / 320). Not ported (open, ps2code lane): the PS2's extra virtual call on each fed Ganado and its
#        wrap bookkeeping of fed Ganados (R208_EmSetEvent / R208_setEm setPtr into W+724).
#   0x02 r20b: the hall waves never send list row 3 (em[1]); the random wave (Rnd() % 6, same draw) sends one
#        Ganado in cases 0-2 (0x14 / 0x15 / 0x16) where the GC sends two (st2_1 R20bEmSetMain 0x14618..0x14da8)
#   0x04 r216: the init sends only the display armor 0xE8 (armor[3]); the GC sends 0xE5..0xE8 (st2_2 R216Init 0x10e58)
#   0x08 r21a (reserved: alive-gated waves), 0x10 r205 (reserved: +0x57)
#   0x20 r226 (lane ch4found16; st2_3 R226Main 0x1a07c): after the statue wakes (Rsf 9), in area flag 71 / 72 and
#        below 11 alive, 0xB3 then 0xB5 are sent once more (PS2-only Rsf 18 / 19 / 20 latches); GC: none
#   0x40 r227 (lane ch4found16; st2_3 task 0x1eaf8, started by both far-side setups 0x201a8 / 0x20348): 0xF7 then
#        0xF5 come one per frame while fewer than 7 are alive and area flag 64 is clear; the setups take the other
#        five only (GC sends all seven and walks 0xF7 / 0xF5 in 900 / 1350 frames later)
#   0x80 r223 (lane ch4found16; st2_3 R223Init 0x11fe0): Normal sends 0xD2 0xD3 0xD7 (after 0xDA) and 0xE1 (list -1);
#        needs the PS2 emleon05 rows (PS2_CH4_ENEMY), which clear the start-alive bit of those four
#   With 0x04 the r216 areas 5 / 6 armor show / hide is a stub, as on the PS2.
PS2_ENEMY_CASTLE ?= 0
ifneq ($(PS2_ENEMY_CASTLE),0)
ifneq ($(PS2_ENEMY_RULES),1)
$(error PS2_ENEMY_CASTLE needs PS2_ENEMY_RULES=1)
endif
$(OBJDIR)/mod/st2_0/src/st2/r208.o $(OBJDIR)/mod/st2_1/src/st2/r20b.o $(OBJDIR)/mod/st2_2/src/st2/r216.o $(OBJDIR)/mod/st2_3/src/st2/r223.o $(OBJDIR)/mod/st2_3/src/st2/r226.o $(OBJDIR)/mod/st2_3/src/st2/r227.o: GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_CASTLE=$(PS2_ENEMY_CASTLE)
endif
# R101_ALIVE_CAP=N (lane crowd12 2026-10-14; CHANGES GAMEPLAY by design; default 0 = off; needs PS2_ENEMY_ROOMS bit 0x02):
#   at most N Ganados alive at once in the r101 village fight. Start-list Ganados beyond N are held at room entry
#   (fresh fight only); the room code's sends beyond N (the square three at the alert, the s21 house nine) are
#   queued; the PS2 villagers join only while fewer than N are alive. Queued / held Ganados come in one at a time,
#   at least 30 frames apart, while fewer than N are alive, until the bell. Each one that comes in adds one to the
#   kill base (emNum) exactly as it adds one to the alive count, so kills = emNum - alive and the bell's 15 / 18
#   kills or 11,700 / 13,500-frame timer are unchanged. The reset waves are unchanged (they fire below 5 alive).
# R101_CAP_LOG=1 (diagnostic, default 0): "r101cap:" lines (holds, queue, releases, waves, the bell's kills / timer).
R101_ALIVE_CAP ?= 0
R101_CAP_LOG ?= 0
ifneq ($(R101_ALIVE_CAP)$(R101_CAP_LOG),00)
$(OBJDIR)/mod/st1_1/src/st1/r101.o: GAME_CPPFLAGS += -DRE4DC_R101_ALIVE_CAP=$(R101_ALIVE_CAP) -DRE4DC_R101_CAP_LOG=$(R101_CAP_LOG) -DRE4DC_R101_CAP_N=$(R101_CAP_N)
endif
# CAP_COMPARE=1 (lane cap16 2026-10-16, user "can we do a comparison of 3 vs 5 or 6 simultaneous zombies"; STRESS / TEST ONLY,
#   default 0; needs DBG_WARP=1 and ALIVE_CAP (PS2_CH1_ENEMY=1 sets it)): the alive cap becomes a runtime value
#   (re4dc_cap_rt, default ALIVE_CAP) set by a `cap <N>` warp line, read by the r101 cap (R101_ALIVE_CAP code) and the
#   generic ALIVE_CAP hold; the same disc then runs every cap. With BENCHMARK=1 it builds the cap comparison disc
#   "RE4DC Cap Compare (NOT THE GAME)": 8 scenes (r101 cross at cap 3 / 4 / 5 / 6, r103 farm at cap 3 / 6 with and without
#   the animals), the start screen picks one with X / Y / A / B (r101) or the d-pad (farm), and the results screen adds the
#   Ganados alive, drawn / skipped ticks, ms per picture and the logic split. Knob off: the sources compare with the
#   constants exactly as before (RE4DC_ALIVE_CAP_N / RE4DC_R101_CAP_N = ALIVE_CAP / R101_ALIVE_CAP).
ifneq ($(CAP_COMPARE),0)
ifneq ($(CAP_COMPARE)$(DBG_WARP),11)
$(error CAP_COMPARE must be 0 or 1 and needs DBG_WARP=1 (stress / test builds only))
endif
ifeq ($(or $(ALIVE_CAP),0),0)
$(error CAP_COMPARE=1 needs ALIVE_CAP (PS2_CH1_ENEMY=1))
endif
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_CAP_COMPARE=$(ALIVE_CAP)
# with MIST_CUT=<mask> (hwfog.mk; the disc builds it with a mask and every scene sets its own): the `mistcut` warp line
ifneq ($(MIST_CUT),)
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_CAP_MISTCUT=1
endif
$(OBJDIR)/src/game/em_set.o $(OBJDIR)/mod/st1_1/src/st1/r101.o: GAME_CPPFLAGS += -include $(CURDIR)/cap_compare.h
ifeq ($(BENCHMARK),1)
$(OBJDIR)/bench.o: PLATFORM_CPPFLAGS += -DRE4DC_BENCH_SCENES=14 -DRE4DC_BENCH_CAPCMP=1 '-DRE4DC_BENCH_NAME="CAP COMPARE"' \
  '-DRE4DC_BENCH_MENU="X/Y/A/B: R101 CAP 3/4/5/6"' '-DRE4DC_BENCH_MENU2="UP/DN: FARM C3 +/-ANIMALS, LT/RT: C6"'   '-DRE4DC_BENCH_MENU3="UP+X/Y/A: R101 T1/T2/T3, DN+X/Y/A: FARM"'
endif
endif
# R101_CAP_WAVES=1 (lane alivecap 2026-10-15, set by PS2_CH1_ENEMY; default 0; needs R101_ALIVE_CAP): the reset waves go
#   through the cap as well (queued beyond it; the wave's emNum += 5 counts the ones sent, each queued one adds its 1
#   when released), so r101 never has more than N alive (crowd12's cap left the waves: up to 9).
ifneq ($(or $(R101_CAP_WAVES),0),0)
$(OBJDIR)/mod/st1_1/src/st1/r101.o: GAME_CPPFLAGS += -DRE4DC_R101_CAP_WAVES=1
endif
# em27ObaHitCk scans enemy slots through the sparse backing (workAt) instead of raw slot math, which read an
# unbacked slot's 0xFF filler as a NaN position and dragged the fish to NaN (r10b dock / boss collision storm).
$(OBJDIR)/mod/em27/src/em27/em27.o: GAME_CPPFLAGS += -DRE4DC_EM27_SLOT_FIX=1
# A door into a room the disc does not carry shows "Coming Soon" and holds (route_end.cpp, src/game/sce_at.cpp).
$(OBJDIR)/src/game/sce_at.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH13=1
# ROUTE_SOON_RETURN=1 (lane route19, default 0: hold as above): Coming Soon shows, fades back and cancels the door like a
# locked one, so the player stays in the room and can take another exit (Test 17 r11b -> r10c soft-lock).
ifneq ($(or $(ROUTE_SOON_RETURN),0),0)
$(OBJDIR)/src/game/sce_at.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_SOON_RETURN=1
$(OBJDIR)/route_end.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_SOON_RETURN=1
endif
# ROUTE_SOON_KEY=1 (lane route20, default 0; needs ROUTE_SOON_RETURN=1): the r11b -> r10c gate's Coming Soon also gives
# the chapter 2-1 church key (item 0x3C) once, with r10c's key flags, since r10c is not on the disc (Test 17.1 block).
ifneq ($(or $(ROUTE_SOON_KEY),0),0)
$(OBJDIR)/route_end.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_SOON_KEY=1
endif
# ROUTE_CH21_FULL=1 (lane ch2rooms20, default 0 = image unchanged): chapter 2-1's own path r11b -> r10c (the dam, the
# insignia key) -> r10e -> r119, and r10d (the ladder), with the rooms' data set ch21r on the disc (a door into a room
# whose world package is on the disc no longer shows Coming Soon, so ROUTE_SOON_KEY's handover never fires there).
# Code: r10c's seven-Ganado ambush (06-0C) goes through the alive cap (held sends return 0 and are null-checked; was a
# kept exception that peaked at 7+).
ROUTE_CH21_FULL ?= 0
ifneq ($(ROUTE_CH21_FULL),0)
$(OBJDIR)/mod/st1_2/src/st1/r10c.o $(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH21_FULL=1
# Audio (needs AICA_SPILL=1): r10c's room banks plus em12 (601 KB prebuilt) exceed the room arena by 44 KB even at
# 8 kHz; its FOOT bank is marked tail-first (aica_banks.py fit --tail-blk 5) and goes to the BGM0 slot's idle tail.
$(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_AICA_TAIL_FIRST=1
endif
# ROUTE_CH21=1 (route lane r11b, default 0: no effect; needs ROUTE_CH13=1 and ROUTE_OVL=1): chapter 2-1 starts in
# r11b (the lake shore, entered through r10b door 6 after the chapter 1-3 save). em22 (module 5, the wolves of the
# shore ambush) is a third room overlay (em22.ovl, linked after pl0f / em2f so theirs are unchanged), and r11b's
# s00 is presented by its PS2 movie (src/st1/r11b.cpp). r11b's own exits lead to rooms this disc does not carry
# (r11a, r10c, r10d): the ROUTE_CH13 door check shows "Coming Soon".
ROUTE_CH21 ?= 0
ifneq ($(ROUTE_CH21),0)
ifneq ($(ROUTE_CH21)$(ROUTE_OVL),11)
$(error ROUTE_CH21 must be 0 or 1 and needs ROUTE_OVL=1)
endif
MODULES += em22:ovl
export RE4DC_LINK_OVERLAY += .ovl_em22
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH21=1
$(OBJDIR)/mod/st1_2/src/st1/r11b.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH21=1
# r119 (route lane r119, the village square, El Gigante; r11a door 0): em2b (module 30, the giant) is a fourth room
# overlay (em2b.ovl, linked after em22 so the earlier overlays are unchanged); r119's four events (s00 entrance,
# s10 the dog, s20 death, s30 the parasite) are presented by their PS2 movies (src/st1/r119.cpp).
MODULES += em2b:ovl
export RE4DC_LINK_OVERLAY += .ovl_em2b
$(OBJDIR)/mod/st1_2/src/st1/r119.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH21=1
$(OBJDIR)/route_movie_bridge.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH21=1
# r118 (route lane r118, the church; r119 door 0): no new module (its entry enemy em22 is r11b's overlay); slot 1's
# BGM (bio4midi #9) plays on the resident slot-0 track, as r108 / r10a (src/game/snd.cpp).
$(OBJDIR)/src/game/snd.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH21=1
# r117 (route lane r117, the church interior, chapter 2-1's end; r118 door 4, key 0x3C): Ashley joins (SubCharInit
# -> enemy module 3 = pl11.rel, module 47, cSubAshley), so pl11 is a fifth room overlay (pl11.ovl, linked after em2b;
# it is re-read in every room she is in). em11 (module 13, the Ganados R117Init sets on a later visit) joins the
# EM10_SHARED group (em11_set.cpp only; alone it would carry a second em10.cpp). s00 / s10 are presented by their PS2
# movies (src/st1/r117.cpp); the chapter end (SceSetChapterEnd(CHAPTER_2_1, -1)) and its save run unchanged.
MODULES += pl11:ovl em11
# The CH21 stream file has 17 entries (r118's 0:23): the reader's table takes 32 (it refused the file at 16).
# AICA_STR_ENT_MAX (lane audio16, 10-16; default 32 = image unchanged): the reader's stream table size. The chapter 1
# stream file (aica_banks.py --streams ch1, data set snd16: 45 entries with the merchant's 15 voice streams) needs 48;
# a file with more entries than the table is refused whole ("header invalid", every disc stream silent), so snd16 and
# AICA_STR_ENT_MAX=48 ship together. 32 bytes of .bss per entry (48: +512 B). The 2 KB header holds up to 63; above
# 63 (lane ch4found16: the castle disc's ch3 + ch4 file, 73 entries, AICA_STR_ENT_MAX=80) the header is whole 2 KB
# sectors and the reader reads the rest once at boot (the 8 KB stream cache holds up to 255 entries).
AICA_STR_ENT_MAX ?= 32
$(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_STR_ENT_MAX=$(AICA_STR_ENT_MAX)
# AICA_SPILL (lane ch2code16, 10-16; default 0 = image unchanged): banks the frozen layout has no room for use space
# it leaves idle, instead of staying silent. (1) A prebuilt room-arena bank that does not fit the arena goes to the
# unused tail of the BGM0 slot (the room's bio4midi bank is often far smaller than the 264,576 B slot: r11c's #6 uses
# 48,000; r11c's Luis, pl14 55,324 B at 8 kHz, is 8.8 KB over the arena). A later BGM0 load that would overlap it
# silences it first (logged). (2) A runtime-converted BGM1 bank with no free AICA RAM (the layout has no BGM1 slot:
# r11f's Mendez music, 139,420 B at 8 kHz) goes to the top of the room arena, above the room's banks; a room bank that
# later needs that space drops it (logged), the next room load frees it. Chapter 2 recipe only.
AICA_SPILL ?= 0
ifeq ($(AICA_SPILL),1)
$(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_AICA_SPILL=1
endif
export RE4DC_LINK_OVERLAY += .ovl_pl11
$(OBJDIR)/mod/st1_3/src/st1/r117.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH21=1
ROUTE_MOVIE_GAME_CH21 = $(OBJDIR)/mod/st1_2/src/st1/r11b.o $(OBJDIR)/mod/st1_2/src/st1/r119.o $(OBJDIR)/mod/st1_3/src/st1/r117.o
endif
endif
# ROUTE_CH22=1 (default 0): chapter 2-2 room adapters and Luis' cabin overlay.
# The overlay follows the five CH21 slots; the chapter movie list remains explicit.
ROUTE_CH22 ?= 0
PS2_ENEMY_CH22_DIR ?=
ifneq ($(ROUTE_CH22),0)
ifneq ($(ROUTE_CH22)$(ROUTE_CH21)$(ROUTE_OVL),111)
$(error ROUTE_CH22 must be 0 or 1 and needs ROUTE_CH21=1 ROUTE_OVL=1)
endif
MODULES += pl14:ovl
export RE4DC_LINK_OVERLAY += .ovl_pl14
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH22=1
$(OBJDIR)/src/game/snd.o $(OBJDIR)/mod/st1_3/src/st1/r11c.o $(OBJDIR)/mod/pl14/src/pl14/pl14.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH22=1
ROUTE_CH22_ROOM_OBJS = $(OBJDIR)/mod/st1_3/src/st1/r111.o $(OBJDIR)/mod/st1_3/src/st1/r112.o \
    $(OBJDIR)/mod/st1_3/src/st1/r113.o $(OBJDIR)/mod/st1_3/src/st1/r11c.o $(OBJDIR)/mod/st1_2/src/st1/r11a.o
$(ROUTE_CH22_ROOM_OBJS) $(OBJDIR)/src/game/stage.o $(OBJDIR)/src/game/trans.o $(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH22=1
ifeq ($(PS2_CH2_ENEMY),1)
ifeq ($(wildcard $(PS2_ENEMY_CH22_DIR)/ps2_enemy_ch22_data.inc),)
$(error PS2_CH2_ENEMY needs qualified PS2_ENEMY_CH22_DIR/ps2_enemy_ch22_data.inc)
endif
$(ROUTE_CH22_ROOM_OBJS): GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_RULES=1
$(OBJDIR)/platform/ps2_enemy_ch22.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH22=1 -DRE4DC_PS2_ENEMY_RULES=1 -I$(PS2_ENEMY_CH22_DIR)
$(OBJDIR)/platform/ps2_enemy_ch22.o: $(PS2_ENEMY_CH22_DIR)/ps2_enemy_ch22_data.inc
endif
ROUTE_MOVIE_GAME_CH22 = $(OBJDIR)/mod/st1_3/src/st1/r11c.o
endif
# ROUTE_CH23=1 (default 0): chapter 2-3 room code and missing vehicle/boss/stage modules.
# The two enemy overlays append after the existing route overlays. st2_0 is resident because
# stage modules survive room changes, whereas route overlays are released on every room reset.
ROUTE_CH23 ?= 0
PS2_ENEMY_CH23_DIR ?=
# Test-only truck state and actual hit evidence; default-off code is identical.
TRUCK_DIAG ?= 0
ifneq ($(TRUCK_DIAG),0)
ifneq ($(TRUCK_DIAG)$(ROUTE_CH23)$(DBG_WARP),111)
$(error TRUCK_DIAG=1 needs ROUTE_CH23=1 DBG_WARP=1)
endif
$(OBJDIR)/mod/em3b/src/em3b/em3b.o: GAME_CPPFLAGS += -DRE4DC_TRUCK_DIAG=1
endif
# SUB_EM_FUNC=1: SetSubDamage stores Ashley's routine-4 handler explicitly (the decomp's PowerPC r4 pin in
# cSubChar::setEmFunc is dropped off PowerPC, so the handler was an uninitialised local: the guest rebooted when the
# r200 truck ran Ashley over, and any other SetSubDamage on Ashley - em3c, boats - calls garbage). Default 0 keeps
# the image identical.
SUB_EM_FUNC ?= 0
ifeq ($(filter $(SUB_EM_FUNC),0 1),)
$(error SUB_EM_FUNC must be 0 or 1)
endif
ifeq ($(SUB_EM_FUNC),1)
$(OBJDIR)/src/game/pl_sub.o: GAME_CPPFLAGS += -DRE4DC_SUB_EM_FUNC=1
endif
# MOVIE_POLL_SETTLE=1: a route movie's first audio polls tolerate KOS snd_stream_poll's -1 for a stale channel
# position (the AICA has not restarted the stream's channel yet, so it still reports the previous voice's offset,
# beyond the stream buffer) for up to 200 ms after snd_stream_start, instead of ending the movie (terminal 3, no
# picture). r11f s02/s10 failed this way whenever a game voice had just played on that channel ("chan0(0).pos =
# 21589"); r11f's movie guard then blocks progression. Default 0 keeps the image identical.
MOVIE_POLL_SETTLE ?= 0
ifeq ($(filter $(MOVIE_POLL_SETTLE),0 1),)
$(error MOVIE_POLL_SETTLE must be 0 or 1)
endif
ifeq ($(MOVIE_POLL_SETTLE),1)
$(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_MOVIE_POLL_SETTLE=1
endif
# MOVIE_AUDIO_PRIME=1 (lane fix18, #38): the KOS stream prefill asks for 2 x 32 KiB before a route movie's clock
# starts; the 48 KiB PCM cap left the second request 18,556 B short (1 underrun + ~145 ms silence in every movie).
# The prefill callback now tops the PCM up from the file first (no new memory). Default 0 keeps the image identical.
MOVIE_AUDIO_PRIME ?= 0
ifeq ($(filter $(MOVIE_AUDIO_PRIME),0 1),)
$(error MOVIE_AUDIO_PRIME must be 0 or 1)
endif
ifeq ($(MOVIE_AUDIO_PRIME),1)
$(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_MOVIE_AUDIO_PRIME=1
endif
ifneq ($(ROUTE_CH23),0)
ifneq ($(ROUTE_CH23)$(ROUTE_CH21)$(ROUTE_OVL),111)
$(error ROUTE_CH23 must be 0 or 1 and needs ROUTE_CH21=1 ROUTE_OVL=1)
endif
# em16 (module 20, r11d: the night village Ganados and the Bella sisters, chainsaw types 3 / 4) joins the em10g group
# (EM10_SHARED: em16_set.cpp only, its value-init trap fixed); r11d loads em16 + em3b only.
MODULES += em3b:ovl em35:ovl st2_0 em16
export RE4DC_LINK_OVERLAY += .ovl_em3b .ovl_em35
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH23=1
# snd.cpp ch13_bgm1_sub (castle lane c304406c; r10f lane r200-17): r200 and r10f play their resident BGM0 track for the
# BGM1 request (frozen layout, BGM1 = 0 B; bio4midi #5 is 868 KB, too big for AICA_SPILL).
$(OBJDIR)/src/game/snd.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH23=1
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH23=1
ROUTE_CH23_ROOM_OBJS = $(OBJDIR)/mod/st1_3/src/st1/r10f.o $(OBJDIR)/mod/st1_3/src/st1/r11d.o \
    $(OBJDIR)/mod/st1_3/src/st1/r11e.o $(OBJDIR)/mod/st1_3/src/st1/r11f.o $(OBJDIR)/mod/st2_0/src/st2/r200.o
$(ROUTE_CH23_ROOM_OBJS) $(OBJDIR)/src/game/stage.o $(OBJDIR)/mod/em3b/src/em3b/em3b.o $(OBJDIR)/mod/em35/src/em35/em35.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH23=1
# These room-local callbacks need the same generated movie policy as earlier chapters.
ROUTE_MOVIE_GAME_CH23 = $(OBJDIR)/mod/st1_3/src/st1/r11f.o $(OBJDIR)/mod/st2_0/src/st2/r200.o
# Existing export alias needed by r200, without enabling the unrelated world-test module set.
$(OBJDIR)/src/game/EtcModel.o: GAME_CPPFLAGS += -DRE4DC_WORLD_STAGE_MODULES=1
ifeq ($(PS2_CH2_ENEMY),1)
ifeq ($(wildcard $(PS2_ENEMY_CH23_DIR)/ps2_enemy_ch23_data.inc),)
$(error PS2_CH2_ENEMY needs qualified PS2_ENEMY_CH23_DIR/ps2_enemy_ch23_data.inc)
endif
$(ROUTE_CH23_ROOM_OBJS): GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_RULES=1
$(OBJDIR)/platform/ps2_enemy_ch23.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH23=1 -DRE4DC_PS2_ENEMY_RULES=1 -I$(PS2_ENEMY_CH23_DIR)
$(OBJDIR)/platform/ps2_enemy_ch23.o: $(PS2_ENEMY_CH23_DIR)/ps2_enemy_ch23_data.inc
endif
endif
# FOG_OFF_CLEAR=1 (castle lane 2026-10-15, default 0: no effect): while the source fog is off, load an all-clear PVR
# fog table once (native_static.cpp re4dc_fog_frame), so table-fog actor packets are not drawn with a stale or start-up
# table (warp into a fog-off castle room: Leon drawn flat grey). Render-only.
FOG_OFF_CLEAR ?= 0
ifneq ($(FOG_OFF_CLEAR),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_FOG_OFF_CLEAR=1
endif
# ROUTE_CH31=1 (castle lane 2026-10-15, default 0: no effect; needs ROUTE_CH23=1 and EM10_SHARED=1): chapter 3-1's
# remaining code modules (assets.sh discover r201 r204 r208): st2_1 (module 82: r204 r205 r206 r209 r20a..r20f,
# resident like st2_0 because stage modules survive room changes; its slot-math lint in r206.cpp fixed by --fix) and
# the castle Ganado RELs em1a (24: r208 r209), em1b (25: r201 r20c) and em14 (35: r204 r20f ...). The three are
# em10.cpp + em10_tmpl.cpp + their own <em>_set.cpp (value-init lint fixed by --fix), so they join the em10g group
# (one em10.cpp in the image, as em11 / em13 / em17); one Ganado REL is live per room on the 3-1 route.
ROUTE_CH31 ?= 0
ifneq ($(ROUTE_CH31),0)
ifneq ($(ROUTE_CH31)$(ROUTE_CH23)$(EM10_SHARED),111)
$(error ROUTE_CH31 must be 0 or 1 and needs ROUTE_CH23=1 EM10_SHARED=1)
endif
MODULES += st2_1 em1a em1b em14
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH31=1
# snd.cpp ch13_bgm1_sub: r202 plays its resident BGM0 track for the BGM1 request (frozen layout, BGM1 = 0 B).
$(OBJDIR)/src/game/snd.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH31=1
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_WARP_TEXT=4096
endif
# ROUTE_CH32=1 (castle lane 2026-10-15, default 0: no effect; needs ROUTE_CH31=1): the enemy modules of chapters 3-2
# to 3-4 (assets.sh discover r205 r209 r20a r20b r20c r20f r206 r20d r20e): em2d (32: r205 r20a), em25 (10: r20c r20f
# r20d), em19 (23: r20d; em10.cpp + em10_tmpl.cpp + em19_set.cpp, so it joins the em10g group) and em3c (68: r20e).
# Lint fixed by assets.sh discover --fix (em2d / em3c slot-math, value-init in all four). em22 (r20b) is ROUTE_CH21's
# room overlay, em23 (r20a) and em18 (r20b) are already linked.
ROUTE_CH32 ?= 0
ifneq ($(ROUTE_CH32),0)
ifneq ($(ROUTE_CH32)$(ROUTE_CH31),11)
$(error ROUTE_CH32 must be 0 or 1 and needs ROUTE_CH31=1)
endif
# em2d / em25 / em3c are room overlays (as em22 / em3b / em35: no resident image growth, heap 4 couples to image size);
# em19 shares em10.cpp, so it is resident in the em10g group.
MODULES += em2d:ovl em25:ovl em3c:ovl em19
export RE4DC_LINK_OVERLAY += .ovl_em2d .ovl_em25 .ovl_em3c
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH32=1
# snd.cpp ch13_bgm1_sub: r20a / r20b, the same BGM1 gap.
$(OBJDIR)/src/game/snd.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH32=1
endif
# ROUTE_CH41=1 (castle lane 2026-10-15, default 0: no effect; needs ROUTE_CH32=1 and WORLD_ROOM_MODULES=1, which links
# st2_2 for r211..r219): chapter 4-1's remaining modules (assets.sh discover r210 r222 r219 r211 r216 r212 r213 r214
# r217 r218 r215 r229 r221 r22b): em1c (81: r218 Ganados; em10.cpp + em10_tmpl.cpp + em1c_set.cpp, so it joins the
# em10g group), st2_3 (97: r220..r22c, the 4-1 end rooms r229 / r221 / r22b; resident like st2_0 / st2_1) and em2c
# (31: the r221 boss, a room overlay). Lint fixed by assets.sh discover --fix (em1c value-init; em2c value-init and
# four slot-math scans; st2_3 slot-math in r224.cpp / r227.cpp). em14 / em1a / em25 / em2d / em3c / em11 / em18 /
# em29 are already linked (ROUTE_CH21 / CH31 / CH32 / the route).
ROUTE_CH41 ?= 0
ifneq ($(ROUTE_CH41),0)
ifneq ($(ROUTE_CH41)$(ROUTE_CH32)$(WORLD_ROOM_MODULES),111)
$(error ROUTE_CH41 must be 0 or 1 and needs ROUTE_CH32=1 WORLD_ROOM_MODULES=1)
endif
MODULES += em1c st2_3 em2c:ovl
export RE4DC_LINK_OVERLAY += .ovl_em2c
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH41=1
# The PS2 world registry predates the r222 / r22b packages: ROUTE_CH41 lists both (native_static.cpp).
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH41=1
endif
# ROUTE_BOSS4=1 (lane ch3found16 2026-10-16 for the boss stress test, lane stress16; default 0: no effect; needs
#   ROUTE_CH32=1, which links em25, and WORLD_ROOM_MODULES=1): the chapter 4 boss modules without the chapter 4
#   gameplay route: st2_3 (97, r220..r22c incl. r221 / r228), em2c (31, Verdugo, r221, room overlay) and em38 (79,
#   Salazar + the Queen, r228, room overlay; em25's tentacles come with ROUTE_CH32). With ROUTE_CH41=1 only em38 is
#   added (CH41 links st2_3 / em2c). Lint (assets.sh discover r228): em38 value-init and its EmMgr slot scan
#   (em38EmWork: workAt, callers skip unbacked slots), as em2c.
ROUTE_BOSS4 ?= 0
ifneq ($(ROUTE_BOSS4),0)
ifneq ($(ROUTE_BOSS4)$(ROUTE_CH32)$(WORLD_ROOM_MODULES),111)
$(error ROUTE_BOSS4 must be 0 or 1 and needs ROUTE_CH32=1 WORLD_ROOM_MODULES=1)
endif
ifeq ($(ROUTE_CH41),0)
MODULES += st2_3 em2c:ovl
export RE4DC_LINK_OVERLAY += .ovl_em2c
endif
MODULES += em38:ovl
export RE4DC_LINK_OVERLAY += .ovl_em38
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_BOSS4=1
endif
# ROUTE_CH3=1 (stage 3 / GC Disc 2 first pass, default 0: no effect; needs ROUTE_CH21=1 ROUTE_OVL=1): the island
# stage modules st3_0 (module 76: r300..r30c, r30e), st3_1 (87: r30d, r30f, r310..r312), st3_2 (88: r315..r31d) and
# st3_3 (101: r320..r333) are linked resident, as st2_0 for ROUTE_CH23 (a stage REL stays linked across the rooms of
# its section, cRoomData::checkRelRead, while route overlays are released on every room reset). The first-pass
# rooms' enemy modules are room overlays: em1d (90, r300's soldiers), em1e (92, r301 / r303 / r305 soldiers), em25
# (10, r304 entry) and,
# unless ROUTE_CH23=1 already adds it, em3b (63, r301's vehicles). Lint: assets.sh discover --fix (value-init /
# slot-math, PPC line under #else). Stage-3 rooms run from a separate disc-2 test image (GD full at chapter 1-3).
ROUTE_CH3 ?= 0
ifneq ($(ROUTE_CH3),0)
ifneq ($(ROUTE_CH3)$(ROUTE_CH21)$(ROUTE_OVL),111)
$(error ROUTE_CH3 must be 0 or 1 and needs ROUTE_CH21=1 ROUTE_OVL=1)
endif
MODULES += st3_0 st3_1 st3_2 st3_3 em1d:ovl em1e:ovl
export RE4DC_LINK_OVERLAY += .ovl_em1d .ovl_em1e
# em25 (r304): ROUTE_CH32 already links the same room overlay.
ifneq ($(ROUTE_CH32),1)
MODULES += em25:ovl
export RE4DC_LINK_OVERLAY += .ovl_em25
endif
# em36 (85: r306..r310, r326) and em1f (109: r304 / r30b / r30c / r30f / r311 / r321 / r330 Ganados) room overlays.
MODULES += em36:ovl
export RE4DC_LINK_OVERLAY += .ovl_em36
# Krauser em39 (64: r31c, r329 knife fight / fight) with his arm em3a (95), U-3 em32 (77: r31b), em3d (80: r320 / r31c
# drones): room overlays, so the island rooms load complete GC enemy archives (round 3; PS2 models come from the cast lane).
MODULES += em39:ovl em3a:ovl em32:ovl em3d:ovl
export RE4DC_LINK_OVERLAY += .ovl_em39 .ovl_em3a .ovl_em32 .ovl_em3d
# em1f: WORLD_ROOM_MODULES links it resident (the St4 Ganados); otherwise a room overlay.
ifneq ($(WORLD_ROOM_MODULES),1)
MODULES += em1f:ovl
export RE4DC_LINK_OVERLAY += .ovl_em1f
endif
ifneq ($(ROUTE_CH23),1)
MODULES += em3b:ovl
export RE4DC_LINK_OVERLAY += .ovl_em3b
endif
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
# The stage-3 PS2 world packages (native_static.cpp re4dc_ps2_world_room, PS2_WORLD_REGISTRY rooms).
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
# The island rows of the generic alive cap (em_set.cpp aliveCapKeepTbl / aliveCapParkRoom; no code without ALIVE_CAP).
$(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
# r300's s00 (the island landing) is presented by its PS2 movie (src/st3/r300.cpp, ROUTE_MOVIES).
$(OBJDIR)/mod/st3_0/src/st3/r300.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
# r316s00 / r329s00 (Ashley taken / the reunion) likewise (st3 lane 2026-10-15: their GC evds are not on disc 2).
$(OBJDIR)/mod/st3_2/src/st3/r316.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
$(OBJDIR)/mod/st3_3/src/st3/r329.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
# ROUTE_MOVIE_GAME_ST3 (not _CH3: ROUTE_MOVIES_CH3 owns that name for the castle chapter 3 rooms).
# Round-10 island event hooks (st3 lane, merged by lane ch5found16): r317 (s00-s15, the knife QTE set), r31b s00, r31c
# s00-s02, r320 s00 / s01, r321 s00, r325 s00, r330 s00 as PS2 route movies when the disc carries them (source path
# otherwise). r331 / r332 (final chapter) stay with lane stress16b. The objects need RE4DC_ROUTE_CH3 like r316.
$(OBJDIR)/mod/st3_2/src/st3/r317.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
$(OBJDIR)/mod/st3_2/src/st3/r31b.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
$(OBJDIR)/mod/st3_2/src/st3/r31c.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
$(OBJDIR)/mod/st3_3/src/st3/r320.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
$(OBJDIR)/mod/st3_3/src/st3/r321.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
$(OBJDIR)/mod/st3_3/src/st3/r325.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
$(OBJDIR)/mod/st3_3/src/st3/r330.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH3=1
ROUTE_MOVIE_GAME_ST3 = $(OBJDIR)/mod/st3_0/src/st3/r300.o $(OBJDIR)/mod/st3_2/src/st3/r316.o $(OBJDIR)/mod/st3_3/src/st3/r329.o $(OBJDIR)/mod/st3_2/src/st3/r317.o $(OBJDIR)/mod/st3_2/src/st3/r31b.o $(OBJDIR)/mod/st3_2/src/st3/r31c.o $(OBJDIR)/mod/st3_3/src/st3/r320.o $(OBJDIR)/mod/st3_3/src/st3/r321.o $(OBJDIR)/mod/st3_3/src/st3/r325.o $(OBJDIR)/mod/st3_3/src/st3/r330.o
# PS2_ENEMY_ST3=<mask> (stage 3 lane, default 0: no effect; changes gameplay by design, PS2 USA = source of truth):
# the PS2 room-code enemy gates of the island. Bit 0: r30f (setem < 6, the 0xF8 send < 7). Bit 1: r301 (the PS2
# wave tasks: sends while < 9 / < 8 alive, room-save chaining, far deletes to 7 / 4). Bit 3: clamp the gates to cap 6. Bit 2: r327 (the PS2 camp: first table, late task, appear
# cut, far deletes, < 9 / < 8 gates). Bit 4: r311 skip path
# despawns Zealots 0xF0..0xF2 (PS2).
PS2_ENEMY_ST3 ?= 0
ifneq ($(PS2_ENEMY_ST3),0)
$(OBJDIR)/mod/st3_1/src/st3/r30f.o: GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_ST3=$(PS2_ENEMY_ST3)
$(OBJDIR)/mod/st3_0/src/st3/r301.o: GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_ST3=$(PS2_ENEMY_ST3)
$(OBJDIR)/mod/st3_1/src/st3/r311.o: GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_ST3=$(PS2_ENEMY_ST3)
$(OBJDIR)/mod/st3_3/src/st3/r327.o: GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_ST3=$(PS2_ENEMY_ST3)
endif
# r30a calls EtcModel.cpp's setRoomEtcBreakDisp by its C name (as r200; ROUTE_CH23 sets the same export alias).
$(OBJDIR)/src/game/EtcModel.o: GAME_CPPFLAGS += -DRE4DC_WORLD_STAGE_MODULES=1
endif
# WEAPON_MODULES=1 (issue #1 2026-10-05, default 0: no effect): Leon's other stage-1 weapons, so equipping one in the
# inventory (SubScreenExit -> ReadWepData -> DLL_Link) finds its module instead of halting "DLL link/unlink failed":
# wep01 (module 3, Punisher; the merchant's medallion reward), wep07 (54, shotgun; r101 house), wep09 (62, rifle; its
# scope variants wep21 / wep24 load the same REL), wep11 (52, TMP; TMP + stock = wep20, same REL), wep13 (59, rocket
# launcher) and wep19 (53, hand / incendiary / flash grenades). Red9 and its stock variant use wep02's REL. Lint
# (assetpipe wiring): no slot-math; their cObj placement value-init is safe (cObjMgr::construct sets serial / id after
# the constructor, as for wep02). The archives need WEAPON_RESIDENT_BYTES >= 404608 (wep21, the largest; build-r21.sh).
WEAPON_MODULES ?= 0
ifneq ($(WEAPON_MODULES),0)
ifneq ($(WEAPON_MODULES),1)
$(error WEAPON_MODULES must be 0 or 1)
endif
MODULES += wep01 wep07 wep09 wep11 wep13 wep19
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_WEAPON_MODULES=1
endif
# WEAPON_WEP04=1 (lane fix-blacktail24 2026-10-24, default 0: no effect): the Blacktail (item 0x27 / 0x28, weapon 4,
# module 70, src/wep04) links statically like the other WEAPON_MODULES weapons. Without it the equip (SubScreenExit ->
# weaponLoad -> DLL_Link) finds no module 70 entry and halts "DLL link/unlink failed" (Test 23).
WEAPON_WEP04 ?= 0
ifneq ($(WEAPON_WEP04),0)
ifneq ($(WEAPON_WEP04),1)
$(error WEAPON_WEP04 must be 0 or 1)
endif
ifeq ($(WEAPON_WEP04_OVL),1)
MODULES += wep04:ovl
else
MODULES += wep04
endif
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_WEAPON_WEP04=1
endif
# WEAPON_WEP04_OVL=1 (lane heap-margin25 2026-10-25, default 0: no effect; needs WEAPON_WEP04=1 and ROUTE_OVL=1): the
# Blacktail module is a room overlay (/cd/dc/wep04.ovl, platform/modules.cpp weapon slot) instead of resident code: the
# weapon load's DLL_Link reads it into heap 4, the weapon release's unlink frees it. The image loses its ~7.4 KB (heap 4
# couples to the image size: r100 s30 heap_before). A room reset with the Blacktail linked releases the weapon data first
# (read.cpp re4dc_weapon_ovl_room_reset), so the next room's player constructor reads and links it again. The section is
# appended last to RE4DC_LINK_OVERLAY (end of this file) so every other overlay keeps its link address.
WEAPON_WEP04_OVL ?= 0
ifneq ($(WEAPON_WEP04_OVL),0)
ifneq ($(WEAPON_WEP04_OVL)$(WEAPON_WEP04)$(ROUTE_OVL),111)
$(error WEAPON_WEP04_OVL must be 0 or 1 and needs WEAPON_WEP04=1 ROUTE_OVL=1)
endif
$(OBJDIR)/platform/modules.o $(OBJDIR)/src/game/read.o $(OBJDIR)/src/game/game.o: PLATFORM_CPPFLAGS += -DRE4DC_WEAPON_WEP04_OVL=1
$(OBJDIR)/src/game/read.o $(OBJDIR)/src/game/game.o: GAME_CPPFLAGS += -DRE4DC_WEAPON_WEP04_OVL=1
endif
# WEAPON_WEP05=1 (lane gc-audit25 2026-10-25, default 0: no effect): weapon 5 (item 0x29, archive em/wep05.drs, module
# 67, src/wep05) links statically like WEAPON_WEP04. Without it the equip (SubScreenExit / ItemMgr.debugWeapon ->
# weaponLoad -> DLL_Link) finds no module 67 entry and halts "DLL link/unlink failed" (rel/wep05.rel is not on the disc).
WEAPON_WEP05 ?= 0
ifneq ($(WEAPON_WEP05),0)
ifneq ($(WEAPON_WEP05),1)
$(error WEAPON_WEP05 must be 0 or 1)
endif
MODULES += wep05
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_WEAPON_WEP05=1
endif
include wep_modules27.mk
# EVD_ADMISSION_TXN=1 (default 0): publish SetEvd only after all required bins
# succeed; roll back only this attempt's bin references on admission failure.
EVD_ADMISSION_TXN ?= 1
ifneq ($(EVD_ADMISSION_TXN),0)
ifneq ($(EVD_ADMISSION_TXN),1)
$(error EVD_ADMISSION_TXN must be 0 or 1)
endif
$(OBJDIR)/src/game/event.o: GAME_CPPFLAGS += -DRE4DC_EVD_ADMISSION_TXN=1
endif
# EVD_START_CLEANUP=1 (default 0): locally abandon work whose init failed;
# publish its effect-model view only after validation. Admission/read ownership
# remains with the caller and is not repaired by this switch.
EVD_START_CLEANUP ?= 1
ifneq ($(EVD_START_CLEANUP),0)
ifneq ($(EVD_START_CLEANUP),1)
$(error EVD_START_CLEANUP must be 0 or 1)
endif
ifneq ($(EVD_ADMISSION_TXN),1)
$(error EVD_START_CLEANUP requires EVD_ADMISSION_TXN=1)
endif
$(OBJDIR)/src/game/event.o: GAME_CPPFLAGS += -DRE4DC_EVD_START_CLEANUP=1
endif
# EVD_START_ROLLBACK=1 (default 0): undo this call's complete new parent/bin
# admission when starting its Event fails. Preserve pre-existing owners.
EVD_START_ROLLBACK ?= 1
ifneq ($(EVD_START_ROLLBACK),0)
ifneq ($(EVD_START_ROLLBACK),1)
$(error EVD_START_ROLLBACK must be 0 or 1)
endif
ifneq ($(EVD_ADMISSION_TXN),1)
$(error EVD_START_ROLLBACK requires EVD_ADMISSION_TXN=1)
endif
ifneq ($(EVD_START_CLEANUP),1)
$(error EVD_START_ROLLBACK requires EVD_START_CLEANUP=1)
endif
$(OBJDIR)/src/game/event.o: GAME_CPPFLAGS += -DRE4DC_EVD_START_ROLLBACK=1
endif
# EVD_DEBUG_READ_CLEANUP=1 (default 0): release a fresh debug-file allocation
# when bin/event admission refuses. Transactional event admission is required.
EVD_DEBUG_READ_CLEANUP ?= 1
ifneq ($(EVD_DEBUG_READ_CLEANUP),0)
ifneq ($(EVD_DEBUG_READ_CLEANUP),1)
$(error EVD_DEBUG_READ_CLEANUP must be 0 or 1)
endif
ifneq ($(EVD_ADMISSION_TXN),1)
$(error EVD_DEBUG_READ_CLEANUP requires EVD_ADMISSION_TXN=1)
endif
$(OBJDIR)/src/game/event.o: GAME_CPPFLAGS += -DRE4DC_EVD_DEBUG_READ_CLEANUP=1
endif
# EVD_EXEC_FAILURE_CLEANUP=1 (default 0): direct em0 read/start failure returns
# failure, preserves a prior read, releases only an unborrowed fresh input and
# pairs its scenario bracket. Module exchanges retain their existing path.
EVD_EXEC_FAILURE_CLEANUP ?= 1
ifneq ($(EVD_EXEC_FAILURE_CLEANUP),0)
ifneq ($(EVD_EXEC_FAILURE_CLEANUP),1)
$(error EVD_EXEC_FAILURE_CLEANUP must be 0 or 1)
endif
ifneq ($(EVD_START_ROLLBACK),1)
$(error EVD_EXEC_FAILURE_CLEANUP requires EVD_START_ROLLBACK=1)
endif
$(OBJDIR)/src/game/event.o: GAME_CPPFLAGS += -DRE4DC_EVD_EXEC_FAILURE_CLEANUP=1
endif
# EVD_ARAM_ALLOC_RETRY=1 (default 0): preserve a prior immutable cabin preload
# after exact allocation refusal using the existing carrier epoch receipt.
EVD_ARAM_ALLOC_RETRY ?= 0
ifneq ($(EVD_ARAM_ALLOC_RETRY),0)
ifneq ($(EVD_ARAM_ALLOC_RETRY),1)
$(error EVD_ARAM_ALLOC_RETRY must be 0 or 1)
endif
ifneq ($(CABIN_SOURCE),1)
$(error EVD_ARAM_ALLOC_RETRY requires CABIN_SOURCE=1)
endif
$(OBJDIR)/src/game/event.o: GAME_CPPFLAGS += -DRE4DC_EVD_ARAM_ALLOC_RETRY=1
$(OBJDIR)/platform/native_event_file.o: PLATFORM_CPPFLAGS += -DRE4DC_EVD_ARAM_ALLOC_RETRY=1
endif
# EVD_READ_RELEASE_REFS=1 (default 0): EvtFree drops only one registration when
# an exact temporary ReadTbl row has multiple references. Final unit/carrier
# release still follows the existing reader/refusal contract.
EVD_READ_RELEASE_REFS ?= 1
ifneq ($(EVD_READ_RELEASE_REFS),0)
ifneq ($(EVD_READ_RELEASE_REFS),1)
$(error EVD_READ_RELEASE_REFS must be 0 or 1)
endif
$(OBJDIR)/src/game/event.o: GAME_CPPFLAGS += -DRE4DC_EVD_READ_RELEASE_REFS=1
endif
# EVD_READ_ADMISSION_PREFLIGHT=1 (default 0): reject impossible fresh table
# admission before acquiring a descriptor, and retain an existing swapped role.
# This does not reserve a table slot across file/diagnostic callbacks.
EVD_READ_ADMISSION_PREFLIGHT ?= 1
ifneq ($(EVD_READ_ADMISSION_PREFLIGHT),0)
ifneq ($(EVD_READ_ADMISSION_PREFLIGHT),1)
$(error EVD_READ_ADMISSION_PREFLIGHT must be 0 or 1)
endif
$(OBJDIR)/src/game/event.o: GAME_CPPFLAGS += -DRE4DC_EVD_READ_ADMISSION_PREFLIGHT=1
endif
# EVD_MODULE_VALIDATE_FIRST=1 (default 0): validate existing module/size before
# releasing its effects for exchange. Forward exchange completion is separate.
EVD_MODULE_VALIDATE_FIRST ?= 1
ifneq ($(EVD_MODULE_VALIDATE_FIRST),0)
ifneq ($(EVD_MODULE_VALIDATE_FIRST),1)
$(error EVD_MODULE_VALIDATE_FIRST must be 0 or 1)
endif
$(OBJDIR)/src/game/event.o: GAME_CPPFLAGS += -DRE4DC_EVD_MODULE_VALIDATE_FIRST=1
endif
# EVD_FORWARD_RECEIPT=1 (default 0): accepted prepared first-forward source
# receipt before/after effect release and the void MemorySwap boundary.
# Unsupported initial zero epochs and rows retain their existing behavior.
EVD_FORWARD_RECEIPT ?= 0
ifneq ($(EVD_FORWARD_RECEIPT),0)
ifneq ($(EVD_FORWARD_RECEIPT),1)
$(error EVD_FORWARD_RECEIPT must be 0 or 1)
endif
ifneq ($(CABIN_SOURCE),1)
$(error EVD_FORWARD_RECEIPT requires CABIN_SOURCE=1)
endif
ifneq ($(EVD_ARAM_ALLOC_RETRY),1)
$(error EVD_FORWARD_RECEIPT requires EVD_ARAM_ALLOC_RETRY=1)
endif
ifneq ($(EVD_MODULE_VALIDATE_FIRST),1)
$(error EVD_FORWARD_RECEIPT requires EVD_MODULE_VALIDATE_FIRST=1)
endif
$(OBJDIR)/src/game/event.o: GAME_CPPFLAGS += -DRE4DC_EVD_FORWARD_RECEIPT=1
endif
# WEAPON_HEAP4=1 (option 3 of issue lamb2k/re4dc#1, default 0: no effect): a weapon body larger than the resident
# weapon block (WEAPON_RESIDENT_BYTES; the r104 merchant's rifle 398,144 / with scope 404,608, rocket launcher
# 382,688, TMP 289,248 / with stock 299,200) is read into heap 4, the room heap, as Krauser's body goes to
# Game.pWepBuf (read.cpp ReadWepData); bodies that fit keep the resident block. Released before each room heap
# rebuild and read again by the next room's player constructor (one extra GD read per door while it is equipped).
# Heap 4 short after one motion-key eviction pass: the equip is reverted to the previously loaded weapon (or bare
# hands), item state included ("weapon heap4 alloc failed"). A route movie short of heap 4 borrows the body and
# returns it after the movie. WEAPON_HEAP4_FAILTEST=1 (test only): every heap-4 weapon allocation fails.
# WEAPON_ARCHIVE_REUSE=1: retain a successfully linked same-file weapon archive across re-equip.
# Publish the reuse identity after ReleaseWepData/load/link, invalidate it on every release,
# and check the actual file/module/backing before reuse. Distinct archives still load normally.
# EFFECT_ADMISSION_GUARD=1: reject an invalid first EFF load before publishing its owner reference.
# Existing valid duplicate/refcount behavior is preserved. Default-off source path is unchanged.
EFFECT_ADMISSION_GUARD ?= 1
ifneq ($(EFFECT_ADMISSION_GUARD),0)
ifneq ($(EFFECT_ADMISSION_GUARD),1)
$(error EFFECT_ADMISSION_GUARD must be 0 or 1)
endif
$(OBJDIR)/src/game/eff_sys.o: GAME_CPPFLAGS += -DRE4DC_EFFECT_ADMISSION_GUARD=1
endif
WEAPON_ARCHIVE_REUSE ?= 0
ifneq ($(WEAPON_ARCHIVE_REUSE),0)
ifneq ($(WEAPON_ARCHIVE_REUSE),1)
$(error WEAPON_ARCHIVE_REUSE must be 0 or 1)
endif
$(OBJDIR)/src/game/read.o: GAME_CPPFLAGS += -DRE4DC_WEAPON_ARCHIVE_REUSE=1
endif
WEAPON_HEAP4 ?= 0
WEAPON_HEAP4_FAILTEST ?= 0
# WEAPON_HEAP4_TOP=1 (with WEAPON_HEAP4): the body goes to the top of the highest free heap-4 cell that fits, so a
# weapon change in a full room (r107: rifle -> scoped rifle) finds the space it freed in one piece.
WEAPON_HEAP4_TOP ?= 0
ifneq ($(WEAPON_HEAP4),0)
ifneq ($(WEAPON_HEAP4),1)
$(error WEAPON_HEAP4 must be 0 or 1)
endif
WEAPON_HEAP4_OBJS := $(OBJDIR)/src/game/read.o $(OBJDIR)/src/game/pl_wep.o $(OBJDIR)/src/game/sscrn.o \
    $(OBJDIR)/src/game/game.o $(OBJDIR)/route_movie_bridge.o
$(WEAPON_HEAP4_OBJS): GAME_CPPFLAGS += -DRE4DC_WEAPON_HEAP4=1
$(OBJDIR)/route_movie_bridge.o $(OBJDIR)/platform/dvd.o $(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_WEAPON_HEAP4=1
ifeq ($(WEAPON_HEAP4_TOP),1)
$(OBJDIR)/src/game/read.o: GAME_CPPFLAGS += -DRE4DC_WEAPON_HEAP4_TOP=1
endif
ifeq ($(WEAPON_HEAP4_FAILTEST),1)
$(OBJDIR)/src/game/read.o: GAME_CPPFLAGS += -DRE4DC_WEAPON_HEAP4_FAILTEST=1
endif
endif
# PRIM_CAP_R107=<bytes> (default 0: no effect): caps r107's primitive buffer (room value 589,824 B) to free heap 4
# there (the scoped rifle body, WEAPON_HEAP4); measured peak use per frame ~270 KB (PRIM_WATER).
PRIM_CAP_R107 ?= 0
ifneq ($(PRIM_CAP_R107),0)
$(OBJDIR)/src/game/game.o: GAME_CPPFLAGS += -DRE4DC_PRIM_CAP_R107=$(PRIM_CAP_R107)
endif
# PRIM_CAP_R10B=<bytes> (default 0: no effect): the same cap for r10b (room value 458,752 B; measured peak 279,808,
# PRIM_WATER), for the lake boss's heap 4.
PRIM_CAP_R10B ?= 0
ifneq ($(PRIM_CAP_R10B),0)
$(OBJDIR)/src/game/game.o: GAME_CPPFLAGS += -DRE4DC_PRIM_CAP_R10B=$(PRIM_CAP_R10B)
endif
# PRIM_CAP_R202=<bytes> (castle lane 2026-10-15, default 0: no effect): the same cap for r202 (room value 425,984 B),
# so em11 (1,323,136 B) fits heap 4 next to the room archive and the PS2 world (short 73,248 B on cx-r202-s31f-01).
# Value to be set from PRIM_WATER with r202's Ganados on screen.
PRIM_CAP_R202 ?= 0
ifneq ($(PRIM_CAP_R202),0)
$(OBJDIR)/src/game/game.o: GAME_CPPFLAGS += -DRE4DC_PRIM_CAP_R202=$(PRIM_CAP_R202)
endif
# PRIM_MIN_ST3=<bytes> (default 0: no effect; st3 lane 2026-10-15): the island rooms (r300..r33f) get a primitive buffer
# of at least this many bytes (room values 262,144 .. 655,360). The buffer's tail funds the native actor palette bank
# (64 KiB); r31b's 262,144 B left Leon on the GameCube path at its entry frame (LEONGC acq=10). Costs heap 4.
PRIM_MIN_ST3 ?= 0
ifneq ($(PRIM_MIN_ST3),0)
$(OBJDIR)/src/game/game.o: GAME_CPPFLAGS += -DRE4DC_PRIM_MIN_ST3=$(PRIM_MIN_ST3)
endif
# PRIM_CAP_R320=<bytes> (lane ch5found16 2026-10-17, default 0: no effect): caps r320's primitive buffer (442,368 B after
# PRIM_MIN_ST3) for heap 4 in its gatling fight with the PS2 soldier cast; PRIM_WATER peak 288,928 B, overflow 0.
PRIM_CAP_R320 ?= 0
ifneq ($(PRIM_CAP_R320),0)
$(OBJDIR)/src/game/game.o: GAME_CPPFLAGS += -DRE4DC_PRIM_CAP_R320=$(PRIM_CAP_R320)
endif
# PRIM_CAP_R226=<bytes> (lane ch4found16 2026-10-17, default 0: no effect): the same cap for r226 (room value 442,368 B;
# PRIM_WATER peak 291,360 B cast on / 282,816 B cast off over the 150 s kill rig). Gate: PRIM_WATER overflow 0.
PRIM_CAP_R226 ?= 0
ifneq ($(PRIM_CAP_R226),0)
$(OBJDIR)/src/game/game.o: GAME_CPPFLAGS += -DRE4DC_PRIM_CAP_R226=$(PRIM_CAP_R226)
endif
# PRIM_BUF_KB=<KB> (lane cast16 2026-10-16; default 0: no effect; size only): every room's primitive buffer asks at most
# this many KB of heap 4 (GC room values: r11f 655,360 B). Set it to the worst chapter 1-2 per-frame peak (PRIM_WATER,
# primitives + native actor tail) x 1.5. A primitive that does not fit is skipped (GetPrimBuff returns 0; the sub screen
# item prims check it under this knob) and PRIM_WATER counts it ("overflow"); the gate is overflow 0. The address
# rule (SS_POOL_HIGH / SS_POOL_TOP placement) is unchanged: only the size.
PRIM_BUF_KB ?= 0
ifneq ($(PRIM_BUF_KB),0)
$(OBJDIR)/src/game/game.o $(OBJDIR)/src/Sscrn/ss_item_draw.o: GAME_CPPFLAGS += -DRE4DC_PRIM_BUF_KB=$(PRIM_BUF_KB)
endif
# PRIM_WATER=1 (test only): per-room peak primitive-buffer bytes per frame ("prim water:" lines, trans.cpp).
ifeq ($(PRIM_WATER),1)
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PRIM_WATER=1
endif
# WORLD_STAGE_MODULES=1 (world coverage lane, default 0: no effect): also link the stage modules st2_0 (r200..r203,
# r207, r208, r210, r222) and st4_0 (the St4 rooms) so those rooms can be entered for native world coverage tests
# (platform/modules.cpp MODULE(75, st2_0) / MODULE(96, st4_0)). Their porting-trap lint is clean (assets.sh discover
# --fix: four slot-math scans) and pl11 (module 47, the partner Ashley R210Init spawns; its value-init trap fixed);
# enemy modules those rooms need (em11, em1f, ...) are not linked.
WORLD_STAGE_MODULES ?= 0
ifneq ($(WORLD_STAGE_MODULES),0)
ifneq ($(WORLD_STAGE_MODULES),1)
$(error WORLD_STAGE_MODULES must be 0 or 1)
endif
MODULES += st2_0 st4_0 pl11
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_STAGE_MODULES=1
$(OBJDIR)/src/game/EtcModel.o: GAME_CPPFLAGS += -DRE4DC_WORLD_STAGE_MODULES=1
endif
# WORLD_ROOM_MODULES=1 (world coverage lane, default 0: no effect; needs WORLD_STAGE_MODULES=1): also link st2_2
# (module 83: r211..r219, lint clean) and em1f (module 109: the St4 Ganados of r406/r40a/r40b/r40d/r410; its one
# value-init trap fixed by assets.sh --fix) so one more St2 (r219) and St4 (r40a) room can be entered with their
# source script and enemies. A separate knob: WORLD_STAGE_MODULES=1 images stay as they were.
# The route recipe (ROUTE_CH21=1) excludes WORLD_STAGE_MODULES=1 (pl11 is a CH21 overlay there); with ROUTE_CH23=1
# (st2_0 linked as the chapter 2-3 stage module) WORLD_ROOM_MODULES=1 links st2_2 / em1f on top of the route set
# without WORLD_STAGE_MODULES (no st4_0, no resident pl11), so the castle rooms r211..r219 load in a route image.
WORLD_ROOM_MODULES ?= 0
ifneq ($(WORLD_ROOM_MODULES),0)
ifneq ($(WORLD_ROOM_MODULES)$(WORLD_STAGE_MODULES),11)
ifneq ($(WORLD_ROOM_MODULES)$(WORLD_STAGE_MODULES)$(ROUTE_CH23),101)
$(error WORLD_ROOM_MODULES must be 0 or 1, and 1 needs WORLD_STAGE_MODULES=1 or ROUTE_CH23=1)
endif
endif
MODULES += st2_2 em1f
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_ROOM_MODULES=1
$(OBJDIR)/src/game/quake.o: GAME_CPPFLAGS += -DRE4DC_WORLD_ROOM_MODULES=1
endif
# EM10_SHARED=1 (default 0): the Ganado RELs em12 (r100/r103) and em15 (r101) are both
# em10.cpp + their own <em>_set.cpp; link them as one object (gen_modules.py group em10g) so the
# image holds one em10.cpp (-254 KB of image = +254 KB of heap 4). Both keep their REL ids and
# entry points and share one state span (a fresh link restores it); only one Ganado REL may be
# live at a time, which holds on the r100 -> r101 -> r103 route (platform/modules.cpp logs it).
# em13 (r104's chapter 1-2 Ganados, route lane 2026-10-01) joins the group: alone it carried a
# second em10.cpp (264,538 B of text = 266 KB of heap 4 in every room); r104 loads em13 only.
# em17 (r108's chapter 1-3 Ganados, route lane c13) joins it for the same reason; r108 loads em17 + em23 only.
EM10_SHARED ?= 0
# EM1F_SHARED=1 (world coverage lane, default 0: no effect; needs WORLD_ROOM_MODULES=1 and EM10_SHARED=1): em1f
# (module 109, the St4 Ganados) joins the group too: em10.cpp + em10_tmpl.cpp + em1f_set.cpp, as the others, so the
# image drops its second em10.cpp copy. The St4 rooms that load em1f load no other group member.
EM1F_SHARED ?= 0
ifneq ($(EM1F_SHARED),0)
ifneq ($(EM1F_SHARED)$(WORLD_ROOM_MODULES)$(EM10_SHARED),111)
$(error EM1F_SHARED must be 0 or 1, and 1 needs WORLD_ROOM_MODULES=1 and EM10_SHARED=1)
endif
endif
ifeq ($(ROUTE_CH21)$(EM10_SHARED)$(WORLD_STAGE_MODULES),110)
else ifeq ($(ROUTE_CH21),1)
$(error ROUTE_CH21=1 needs EM10_SHARED=1 (em11 in the em10g group) and WORLD_STAGE_MODULES=0 (pl11 is a CH21 overlay))
endif
# DISC2=1 (stage 3 lane, default 0: no effect; needs ROUTE_CH3=1): the disc-2 (island) image. The island never links
# a stage-1 room or Ganado REL, so the image drops the resident stage-1 modules st1_0..st1_3 and the stage-1 enemy
# RELs (em12 em15 em13 em17 em11 = the em10g group, em21 em24 em26 em27 em28 em29 em2a em2e): their bytes return to
# heap 4. wep02 (Red9), em18 (the merchant: r30a / r312 / r31a / r329 / r331) and em23 (r30a) stay. Route overlays
# cost no image bytes and stay linked (their .ovl files are simply not staged on disc 2). A disc-2 room that links a
# dropped module halts at OSLink "module: id N not in the image" (the existing ROUTE check), never a silent stub.
DISC2 ?= 0
ifneq ($(DISC2),0)
ifneq ($(DISC2)$(ROUTE_CH3),11)
$(error DISC2 must be 0 or 1 and needs ROUTE_CH3=1)
endif
DISC2_DROPPED = st1_0 st1_1 st1_2 st1_3 em12 em15 em13 em17 em11 em21 em24 em26 em27 em28 em29 em2a em2e
MODULES := $(filter-out $(DISC2_DROPPED),$(MODULES))
$(OBJDIR)/platform/modules.o $(OBJDIR)/platform/dvd.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC2=1
endif
# DISC_SET=1 (default 0: no effect; DISC-LAYOUT-20261016.md, lane discsets20): the three-disc release. One program
# image on every disc; dc/disc.id says which disc it is; StageInit asks for the disc by chapters finished (1-1..2-3
# disc 1, 3-1..4-4 disc 2, island disc 3) and a wrong disc holds on the game's "insert disc N" message.
DISC_SET ?= 0
ifneq ($(DISC_SET),0)
ifneq ($(DISC_SET)$(DISC2),10)
$(error DISC_SET must be 0 or 1 and excludes DISC2=1)
endif
$(OBJDIR)/platform/dvd.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_SET=1
$(OBJDIR)/src/game/game.o $(OBJDIR)/src/game/dvd.o: GAME_CPPFLAGS += -DRE4DC_DISC_SET=1
endif
EM10_GROUP = $(filter em12 em15 em13 em17 em11 em16 em1a em1b em14 em19 em1c $(if $(filter 1,$(EM1F_SHARED)),em1f),$(MODULES))
MODULE_ARGS = $(if $(and $(filter 1,$(EM10_SHARED)),$(strip $(EM10_GROUP))),$(filter-out $(EM10_GROUP),$(MODULES)) em10g=$(subst $(eval) ,+,$(strip $(EM10_GROUP))),$(MODULES))
MODULE_OBJS =
MODULES_MK = $(OBJDIR)/modules.mk
GAME_OBJS = $(patsubst $(ROOT)/%.cpp,$(OBJDIR)/%.o,$(GAME_SRCS))
CENSUS_OBJS = $(patsubst $(ROOT)/%.cpp,$(OBJDIR)/%.o,$(CENSUS_SRCS))
PLATFORM_OBJS = $(patsubst %.cpp,$(OBJDIR)/%.o,$(PLATFORM_SRCS))
ifneq ($(ROUTE_CH22)$(PS2_CH2_ENEMY),11)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/ps2_enemy_ch22.o,$(PLATFORM_OBJS))
endif
ifneq ($(ROUTE_CH23)$(PS2_CH2_ENEMY),11)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/ps2_enemy_ch23.o,$(PLATFORM_OBJS))
endif
ifneq ($(PS2_CH3_ENEMY),1)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/ps2_enemy_ch3.o,$(PLATFORM_OBJS))
endif
ifneq ($(PS2_CH4_ENEMY),1)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/ps2_enemy_ch4.o,$(PLATFORM_OBJS))
endif
# LAKE_RIPPLES (ROUTE_CH13 block above): native_lake.cpp is built only with the knob on (1 or 2).
ifeq ($(filter 1 2,$(LAKE_RIPPLES)),)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/native_lake.o,$(PLATFORM_OBJS))
endif
# VGA_SOFT=1 (Phase 2 C5, default 0: no effect, platform/vga_soft.cpp not built): on a VGA box, the PVR's vertical
# filter (SCALER_CFG vertical scale 1025, Y_COEFF 1/4 1/2 1/4: what KOS gives 480i TV) set once after pvr_init.
# Render only. Untested on a console VGA box (issue #11 hung one writing SCALER_CFG mid-render): console first.
VGA_SOFT ?= 0
ifeq ($(VGA_SOFT),1)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_VGA_SOFT=1
else
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/vga_soft.o,$(PLATFORM_OBJS))
endif
# LETTERBOX_CLIP=1 (Phase 2 B5, default 0: platform/letterbox_clip.cpp not built; render only): while the gameplay
# letterbox bars are opaque, two black opaque polygons at the nearest depth open the frame's opaque list (the ISP rejects
# the fill behind them) and, at a 640x480 render, tile row 0 renders the opaque list only (region array of the bank being
# filled, written at scene close). =2 also clips tile row 14 (measurement arm: subtitles there would vanish).
LETTERBOX_CLIP ?= 0
ifeq ($(filter $(LETTERBOX_CLIP),0 1 2),)
$(error LETTERBOX_CLIP must be 0, 1 or 2)
endif
ifeq ($(LETTERBOX_CLIP),0)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/letterbox_clip.o,$(PLATFORM_OBJS))
else
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/letterbox_clip.o: PLATFORM_CPPFLAGS += -DRE4DC_LETTERBOX_CLIP=$(LETTERBOX_CLIP)
$(OBJDIR)/platform/letterbox_clip.o: PLATFORM_CPPFLAGS += -I$(KOS_BASE)/kernel/arch/dreamcast/hardware/pvr
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_LETTERBOX_CLIP=$(LETTERBOX_CLIP)
endif
# DOOR_FREEZE=1 (test 9 lane DOOR, default 0; render only): the door transition's stop filter (src/game/filter09.cpp,
# Filter09) on the PVR: the picture on screen frozen into a 320x240 RGB565 texture (150 KiB, only while the filter is
# in use, freed before the next room's texture preload), drawn every frame with the source's spreading feedback as
# layered quads, under the source fades (platform/native_ui.cpp DOOR_FREEZE). 0 = today's black door.
DOOR_FREEZE ?= 0
ifeq ($(filter $(DOOR_FREEZE),0 1),)
$(error DOOR_FREEZE must be 0 or 1)
endif
ifneq ($(DOOR_FREEZE),0)
$(OBJDIR)/src/game/filter09.o: GAME_CPPFLAGS += -DRE4DC_DOOR_FREEZE=$(DOOR_FREEZE)
endif
# DOOR_FREEZE_SLOW_MS=n (stills arms only, default 0): each drawn door frame logs and waits n ms (frame sequences).
DOOR_FREEZE_SLOW_MS ?= 0
ifneq ($(DOOR_FREEZE_SLOW_MS),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_DOOR_FREEZE_SLOW_MS=$(DOOR_FREEZE_SLOW_MS)
endif
SDK_OBJS = $(patsubst platform/sdk/gen/%.c,$(OBJDIR)/sdk/%.o,$(SDK_GEN))
NATIVE_REUSE_OBJS = $(OBJDIR)/native-reuse/source_lighting.o $(OBJDIR)/native-reuse/native_draw_plan.o $(OBJDIR)/native-reuse/pvr_geometry.o $(OBJDIR)/native-reuse/gpu_lifecycle.o $(OBJDIR)/native-reuse/texture_package.o $(OBJDIR)/native-reuse/room_storage.o $(OBJDIR)/ui_bridge.o $(OBJDIR)/model_bridge.o $(OBJDIR)/model_asset_bridge.o $(OBJDIR)/motion_bridge.o $(OBJDIR)/parts_bridge.o
# Native static room packages (NATIVE_STATIC below); default images carry none of it.
ifeq ($(NATIVE_STATIC),1)
NATIVE_REUSE_OBJS += $(OBJDIR)/native-reuse/room_package.o
else
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/native_static.o,$(PLATFORM_OBJS))
endif
# D367 actor path (probe PROPOSAL option A); default images carry none of it.
NATIVE_ACTOR ?= 0
ifneq ($(NATIVE_ACTOR),1)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/native_actor.o,$(PLATFORM_OBJS))
endif
# D367 actors30 (all default off). NATIVE_ACTOR_FAST=1: meshlet actor path
# (platform/native_actor_fast.cpp replaces native_actor.cpp). NATIVE_ACTOR_SKIN=1:
# trans.cpp defers the render-only CalcSk1_x pass to draw-time skinning.
# NATIVE_ACTOR_DIRECT=1: store-queue submission (needs the TA_DIRECT=1 API).
# NATIVE_ACTOR_LOD=1: whole-part LOD levels, built after conversion (at most
# NATIVE_ACTOR_LOD_BUDGET triangles simplified per frame, in the actor
# workspace: 160 KiB asked for, 96 KiB enough for most parts) and drawn by
# projected error <= NATIVE_ACTOR_LOD_PX px.
# NATIVE_ACTOR_PRELIT=1: parts of unanimated, unmorphed models keep baked
# RGB565 record colours, relit only when their light fold changes.
# NATIVE_ACTOR_UV16=1: 16-bit UV vertices where the part's range allows
# (native_ui.cpp header hook) and strip length 6 in the actor headers.
NATIVE_ACTOR_FAST ?= 0
NATIVE_ACTOR_SKIN ?= 0
# NATIVE_ACTOR_SKIN_LAZY=1 (needs NATIVE_ACTOR_SKIN=1): a deferred-skin info
# also takes no pPosBuf/pNrmBuf in Trans() (about 20 KiB of primitive buffer
# per Ganado); they are allocated at Render() only if one of its parts declines.
NATIVE_ACTOR_SKIN_LAZY ?= 0
NATIVE_ACTOR_DIRECT ?= 0
NATIVE_ACTOR_LOD ?= 0
NATIVE_ACTOR_LOD_PX ?= 2
NATIVE_ACTOR_LOD_BUDGET ?= 128
NATIVE_ACTOR_PRELIT ?= 0
NATIVE_ACTOR_UV16 ?= 0
# NATIVE_ACTOR_LOG=1: one actor-path statistics line in the boot log every 120 frames.
NATIVE_ACTOR_LOG ?= 0
# CROWD_LOD=1 (needs NATIVE_ACTOR_FAST=1, best with NATIVE_ACTOR_LOD=1): Ganado
# render tiers by camera distance - the nearest CROWD_NEAR (and any within
# CROWD_NEAR_M metres) drawn like Leon, mid (to CROWD_MID_M) at coarser LOD
# with one light colour per part, far at the coarsest level. Leon, weapons and
# objects are unchanged; nothing is culled.
CROWD_LOD ?= 0
CROWD_NEAR ?= 3
CROWD_NEAR_M ?= 7
CROWD_MID_M ?= 17
CROWD_MID_PX ?= 8
# CROWD_FLAT=1 (with CROWD_LOD=1): the near tier also takes one light colour per
# part (flat Ganado lighting, Standard); Leon, weapons and objects stay per-vertex lit.
CROWD_FLAT ?= 0
# ACTOR_SKIN_FTRV=1: skinned palette matrices (screen x [R*q | t]) built with FTRV instead of
# scalar maths (render only, native_actor_fast.cpp skin_position_matrix).
ACTOR_SKIN_FTRV ?= 0
# ACTOR_LIGHT_FAST_ONLY=1 (Build 25, render approximation): one live part colour
# for every native/generic model path; static RGB only multiplies it. No vertex
# lighting evaluator or runtime relight is compiled. Default 0 preserves source/objects.
ACTOR_LIGHT_FAST_ONLY ?= 0
ifneq ($(words $(ACTOR_LIGHT_FAST_ONLY)),1)
$(error ACTOR_LIGHT_FAST_ONLY must be 0 or 1)
endif
ifeq ($(filter $(ACTOR_LIGHT_FAST_ONLY),0 1),)
$(error ACTOR_LIGHT_FAST_ONLY must be 0 or 1)
endif
ifeq ($(ACTOR_LIGHT_FAST_ONLY),1)
ifneq ($(NATIVE_ACTOR)$(NATIVE_ACTOR_FAST),11)
$(error ACTOR_LIGHT_FAST_ONLY needs NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1)
endif
$(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/qa_menu.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_LIGHT_FAST_ONLY=1
endif
# ACTOR_EXACT_FAST=1 (render only; default 1 with ROUTE_CH21=1, else 0: no effect): the actor path's exact per-vertex
# lighting (parts whose lights do not fold into three directions, e.g. r119's trees under up to eight flickering torch
# lights: ~46 hw ms a frame) with the per-light constants out of the vertex loop and fsrra for the light distance
# (native_actor_fast.cpp pass_lights_exact); same formula and order, float rounding only.
ifeq ($(ROUTE_CH21),1)
ACTOR_EXACT_FAST ?= 1
else
ACTOR_EXACT_FAST ?= 0
endif
ifeq ($(ACTOR_EXACT_FAST),1)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_EXACT_FAST=1
endif
# GIGANTE_LIGHTS=1 (render only, default 0): El Gigante's parts (em2b, model id 0x2B, r119) under more than three
# significant torch lights keep the three strongest at the part centre (colour x attenuation) in the directional
# fold and add the rest to ambient with the camera-facing hemisphere mean (1 + l.v) / 4, instead of the exact
# per-vertex path (native_actor_fast.cpp build_lights). =2 keeps two. GIGANTE_LIGHTS_TREES=1 (the default when
# GIGANTE_LIGHTS is on) also folds r119's cEmTree (0x49): on the boss view the exact cost is the trees, not the giant
# (whose parts already fold), so GIGANTE_LIGHTS_TREES=0 leaves the image and the cost as GIGANTE_LIGHTS=0.
# Default 1 with ROUTE_CH21=1 (adopted 2026-10-10: near identical, r119 boss view -11 hw ms, quiet view -33).
ifeq ($(ROUTE_CH21),1)
GIGANTE_LIGHTS ?= 1
else
GIGANTE_LIGHTS ?= 0
endif
GIGANTE_LIGHTS_TREES ?= 1
ifneq ($(GIGANTE_LIGHTS),0)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_GIGANTE_LIGHTS=$(GIGANTE_LIGHTS) -DRE4DC_GIGANTE_LIGHTS_TREES=$(GIGANTE_LIGHTS_TREES)
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_GIGANTE_LIGHTS=$(GIGANTE_LIGHTS)
endif
# STATUE_LIGHTS=2 (lane cast16 2026-10-17; render only, approximation, default 0; needs GIGANTE_LIGHTS and
#              ACTOR_EXACT_FAST): the r226 Salazar statue (cObjRobo, kindid 1, id 0x37) is lit by 8 attenuated lights, so
#              each part fell to the exact per-vertex evaluator over all 8 (59.7 of its 68.9 ms/frame submit, Flycast).
#              =2 keeps the exact evaluator (per-vertex direction and attenuation) on the 3 lights strongest at the part and
#              adds the dropped lights as a directionless 1/4 ambient share. r226 frozen tick 400 (Flycast): whole frame
#              ~114 -> ~91 ms; look APPROVED (coordinator 10-17: slightly brighter left mass); STRICT 400 frames.
#              Static +640 B with the knob on. Castle recipe only. Knob off: the image is unchanged.
STATUE_LIGHTS ?= 0
ifneq ($(STATUE_LIGHTS),0)
ifneq ($(STATUE_LIGHTS),2)
$(error STATUE_LIGHTS must be 0 or 2)
endif
ifeq ($(GIGANTE_LIGHTS),0)
$(error STATUE_LIGHTS=2 needs GIGANTE_LIGHTS)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_STATUE_LIGHTS=$(STATUE_LIGHTS)
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_STATUE_LIGHTS=$(STATUE_LIGHTS)
endif
ifeq ($(NATIVE_ACTOR)$(NATIVE_ACTOR_FAST),11)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/native_actor.o,$(PLATFORM_OBJS))
else
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/native_actor_fast.o,$(PLATFORM_OBJS))
ifneq ($(NATIVE_ACTOR_SKIN)$(NATIVE_ACTOR_DIRECT)$(NATIVE_ACTOR_LOD)$(NATIVE_ACTOR_PRELIT)$(NATIVE_ACTOR_UV16)$(CROWD_LOD),000000)
$(error NATIVE_ACTOR_SKIN/DIRECT/LOD/PRELIT/UV16 and CROWD_LOD require NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1)
endif
endif
ifeq ($(NATIVE_ACTOR_SKIN_LAZY)$(NATIVE_ACTOR_SKIN),10)
$(error NATIVE_ACTOR_SKIN_LAZY=1 requires NATIVE_ACTOR_SKIN=1)
endif
# D367 audio: AICA_AUDIO=1 plays the recovered sound driver on the AICA
# (platform/audio_aica.cpp); default images keep the silent audio_stub.cpp.
AICA_AUDIO ?= 0
# AICA_LAYOUT_RECOVER=1: roll back failed first-layout accounting and retry a missing stream ring
# independently from valid one-shot banks. No payload budget/source-registration change; default off.
AICA_LAYOUT_RECOVER ?= 0
ifneq ($(filter-out 0 1,$(AICA_LAYOUT_RECOVER)),)
$(error AICA_LAYOUT_RECOVER must be 0 or 1)
endif
ifeq ($(AICA_LAYOUT_RECOVER),1)
ifneq ($(AICA_AUDIO),1)
$(error AICA_LAYOUT_RECOVER=1 requires AICA_AUDIO=1)
endif
$(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_AICA_LAYOUT_RECOVER=1
endif
ifneq ($(AICA_AUDIO),1)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/audio_aica.o,$(PLATFORM_OBJS))
endif
# Disc stream player I/O (platform/audio_strm.cpp, every build): its DVD reads /
# ARAM DMAs complete at the next audio frame, as on the GC, instead of inside the
# call, so streams go ready -> playing -> ended and scenario waits return.
GAME_LDFLAGS += -Wl,--wrap=DVDReadAsyncPrio -Wl,--wrap=ARQPostRequest
# SBB_STUB=1 (default 0: no effect): bgm/bio4bgm.sbb and bgm/bio4evt.sbb (332,890,112 B of GC stream payload)
# leave the disc. The stream player's reads of them are the wrapped, skipped ones above; platform/dvd.cpp gives
# both entries their retail size without opening them, so FileTbl entry numbers, DVDFileInfo and every stream
# state stay as they are. The headers the player uses come from bgm/bio4str.hed (still staged).
SBB_STUB ?= 0
ifneq ($(SBB_STUB),0)
ifneq ($(SBB_STUB),1)
$(error SBB_STUB must be 0 or 1)
endif
$(OBJDIR)/platform/dvd.o: PLATFORM_CPPFLAGS += -DRE4DC_SBB_STUB=1
endif
# AICA_STREAMS=1 (default; with AICA_AUDIO=1): streams play from bgm/aica_str.dat
# (tools/aica_banks.py; a disc without it keeps them silent). 0: silent streams.
AICA_STREAMS ?= 1
ifeq ($(AICA_AUDIO)$(AICA_STREAMS),11)
$(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_AICA_STREAMS=1
endif
# AICA_WEP_LOG=1 (test only, default 0: no effect): logs every SE voice start from the WEP block (blk 2) and every
# unmapped SE start (a sample in no loaded bank: silent), uncapped, so weapon-sound gates (issue lamb2k/re4dc#1) can
# show each shot's keyon. Audio state only; the game never reads it.
AICA_WEP_LOG ?= 0
ifneq ($(AICA_WEP_LOG),0)
$(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_AICA_WEP_LOG=1
endif
.PHONY: aica-audio-force
$(OBJDIR)/aica-audio.h: aica-audio-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_AICA_AUDIO %s\n' '$(AICA_AUDIO)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/audio_stub.o: $(OBJDIR)/aica-audio.h
$(OBJDIR)/platform/audio_stub.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/aica-audio.h
# D367 audio: AICA_AUDIO=1 plays the recovered sound driver on the AICA
# (platform/audio_aica.cpp); default images keep the silent audio_stub.cpp.
AICA_AUDIO ?= 0
ifneq ($(AICA_AUDIO),1)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/audio_aica.o,$(PLATFORM_OBJS))
endif
.PHONY: aica-audio-force
$(OBJDIR)/aica-audio.h: aica-audio-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_AICA_AUDIO %s\n' '$(AICA_AUDIO)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/audio_stub.o: $(OBJDIR)/aica-audio.h
$(OBJDIR)/platform/audio_stub.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/aica-audio.h
# MOTION_LEASE_LEAN=1 removes acquire-only telemetry timers and reuses the
# guard's existing owner slot for its extra lease; =2 compares the source lookup.
# Counts, mutex/pins/release order and cancellation ownership remain unchanged.
# Bulk motion retirement preflight; no room-reset/admission serialization claim.
MOTION_RETIRE_PREFLIGHT ?= 1
ifneq ($(words $(MOTION_RETIRE_PREFLIGHT)),1)
$(error MOTION_RETIRE_PREFLIGHT must be 0 or 1)
endif
ifeq ($(filter $(MOTION_RETIRE_PREFLIGHT),0 1),)
$(error MOTION_RETIRE_PREFLIGHT must be 0 or 1)
endif
ifeq ($(MOTION_RETIRE_PREFLIGHT),1)
$(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -DRE4DC_MOTION_RETIRE_PREFLIGHT=1
endif
MOTION_LEASE_LEAN ?= 0
.PHONY: motion-lease-lean-force
$(OBJDIR)/motion-lease-lean.h: motion-lease-lean-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_MOTION_LEASE_LEAN %s\n' '$(MOTION_LEASE_LEAN)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_motion.o: $(OBJDIR)/motion-lease-lean.h
$(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/motion-lease-lean.h
# MOTION_FAST_READ=1: motion keys read straight into their aligned residency block (one GD
# stream command + a block-cache tail) instead of one GD command per sector (W10).
# IO_ALIGNED=1 (door load U2, design-doorload): native static packages read whole into their
# aligned storage the same way (one stream + tail) instead of a misaligned body read.
MOTION_FAST_READ ?= 0
IO_ALIGNED ?= 0
# MOTION_READ_FAULT_TEST=<n> (test only, default 0): the first read of every <n>th motion key miss reports short, so
# the motion key read retry runs in Flycast (which never fails a GD read).
MOTION_READ_FAULT_TEST ?= 0
# MOTION_RESERVE=1: the two cold-clip slots of each motion binding are allocated at bind, so a
# cold miss never allocates from a full heap 4 (r100 ambush). MOTION_USAGE_LOG=1 (diagnostic):
# log each entry's first acquire ("motion use:") for the hot-set audit.
MOTION_RESERVE ?= 0
# MOTION_RESERVE_SPILL=<bytes> (with MOTION_RESERVE=1, default 0): when both cold-clip slabs are busy, a cold miss
# is cached in heap 4 (under MOTION_PRESSURE_BYTES, evicted LRU) instead of evicting a slab key, while heap 4
# keeps at least <bytes> free after it; below that margin (the r100 ambush) the slabs alone serve as before.
# Two slabs alone thrash in the r101 fight (~50 key reloads/s, each a disc read + CRC/FNV check).
MOTION_RESERVE_SPILL ?= 0
ifneq ($(MOTION_RESERVE_SPILL),0)
ifneq ($(MOTION_RESERVE),1)
$(error MOTION_RESERVE_SPILL needs MOTION_RESERVE=1)
endif
ifneq ($(NATIVE_STATIC),1)
$(error MOTION_RESERVE_SPILL needs NATIVE_STATIC=1 (re4dc_static_heap_free))
endif
$(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -DRE4DC_MOTION_RESERVE_SPILL=$(MOTION_RESERVE_SPILL)
endif
MOTION_USAGE_LOG ?= 0
# HEAP_REPLACE_LOG=1 (test only): MemReplaceHeap logs the highest live cells of the heap it replaces.
HEAP_REPLACE_LOG ?= 0
ifeq ($(HEAP_REPLACE_LOG),1)
$(OBJDIR)/src/game/main_mem.o: GAME_CPPFLAGS += -DRE4DC_HEAP_REPLACE_LOG=1
endif
# HEAP_CENSUS=1 (test only): the first failed heap-4 allocation logs heap 4's bytes per allocation tag.
HEAP_CENSUS ?= 0
ifeq ($(HEAP_CENSUS),1)
$(OBJDIR)/src/game/main_mem.o: GAME_CPPFLAGS += -DRE4DC_HEAP_CENSUS=1
endif
# HEAP4_WATER=1 (test only, issue #1 2026-10-05): heap 4's free total / largest cell after every heap-4 allocation;
# logs each new per-room low-water mark ("heap4 water:" lines) to price a resident reservation raise.
HEAP4_WATER ?= 0
ifeq ($(HEAP4_WATER),1)
$(OBJDIR)/src/game/main_mem.o: GAME_CPPFLAGS += -DRE4DC_HEAP4_WATER=1
endif
.PHONY: motion-read-force
$(OBJDIR)/motion-read.h: motion-read-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_MOTION_FAST_READ %s\n#define RE4DC_MOTION_RESERVE %s\n#define RE4DC_MOTION_USAGE_LOG %s\n#define RE4DC_IO_ALIGNED %s\n' '$(MOTION_FAST_READ)' '$(MOTION_RESERVE)' '$(MOTION_USAGE_LOG)' '$(IO_ALIGNED)' > $@.tmp
	@printf '#define RE4DC_MOTION_READ_FAULT_TEST %s\n' '$(MOTION_READ_FAULT_TEST)' >> $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_motion.o: $(OBJDIR)/motion-read.h
$(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/motion-read.h
$(OBJDIR)/platform/native_static.o: $(OBJDIR)/motion-read.h
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/motion-read.h
# Door load U6 (W10, design-doorload), default off: DVD_WAIT=1 a pump waiting for the DVD step
# owner blocks on a genwait woken at step end instead of sleeping a scheduler tick; DVD_FDCACHE=1
# DVDReadAsyncPrio keeps the last 2 files open instead of an open + close per read.
# IO_SERIAL=1 (route lane, default off): texture-package opens (room/texture_package.cpp, any thread) wait
# while DVDReadAsyncPrio has a file open. KOS iso9660 turns a DVD read into a 32-byte aligned game buffer
# into a CD stream; a concurrent open on another thread left every later fs_open failing (ENOENT) on a
# direct start in r106 (the HUD/player textures load while the room archive streams in).
DVD_WAIT ?= 0
DVD_FDCACHE ?= 0
IO_SERIAL ?= 0
# POISON_RAM=<byte> (hardware readiness, default 0 = off; test builds only): at boot, fill unallocated
# main RAM (the KOS break up to the kernel stack, then the whole game arena), the free PVR texture memory
# and the free AICA sound memory with this byte. Flycast starts with zeroed memory; a Dreamcast does not.
# A run that differs from the same fixture with POISON_RAM=0 reads memory it never wrote.
POISON_RAM ?= 0
# IMAGE_CHECK=1 (test 11 console faults, test discs only, default 0): at OSInit, before the game's first disc read,
# the screen shows the CRC-32 of the loaded code (_start.._etext, to compare with the build's), the raw KOS maple
# unit pointers, and then the loaded image compared with /cd/1ST_READ.BIN read back through the drive (mismatching
# bytes in the code and after it, first offsets); held 10 s for a photo, also logged ("image check:").
IMAGE_CHECK ?= 0
ifneq ($(filter $(IMAGE_CHECK),0 1),$(IMAGE_CHECK))
$(error IMAGE_CHECK must be 0 or 1)
endif
ifeq ($(IMAGE_CHECK),1)
$(OBJDIR)/platform/os.o: PLATFORM_CPPFLAGS += -DRE4DC_IMAGE_CHECK=1
endif
# DCINV_PURGE=1 (test 11 console faults, default 0): the SDK's DCInvalidateRange (platform/misc.cpp) writes dirty
# lines back before invalidating them (KOS dcache_purge_range, ocbp) instead of discarding them (dcache_inval_range,
# ocbi). On GC the game invalidates a buffer that hardware (EFB copy, DVD, ARAM DMA) is about to overwrite; on the
# port nothing writes behind the cache for those buffers, so ocbi only throws away the CPU's newest stores - and the
# bytes of whatever shares the first and last line. Flycast does not model the operand cache and never shows it.
# DCINV_AUDIT=1 (console proof, test discs, default 0): before each DCInvalidateRange, count the lines the operand
# cache holds dirty in that range (OC address array), per caller; "dcinv:" log lines name each caller's first discard
# and a summary every 5 s, for the crash screen.
DCINV_PURGE ?= 0
DCINV_AUDIT ?= 0
ifneq ($(filter $(DCINV_PURGE),0 1),$(DCINV_PURGE))
$(error DCINV_PURGE must be 0 or 1)
endif
ifneq ($(filter $(DCINV_AUDIT),0 1),$(DCINV_AUDIT))
$(error DCINV_AUDIT must be 0 or 1)
endif
ifneq ($(DCINV_PURGE)$(DCINV_AUDIT),00)
$(OBJDIR)/platform/misc.o: PLATFORM_CPPFLAGS += -DRE4DC_DCINV_PURGE=$(DCINV_PURGE) -DRE4DC_DCINV_AUDIT=$(DCINV_AUDIT)
endif
# MAPLE_RECV_PURGE=1 (test 12 console faults, default 0): KOS maple_frame_init clears a frame's receive buffer through
# its uncached (P2) alias and maple DMA then writes the device's answer to RAM, but nothing writes back or drops the
# buffer's cached (P1) lines first. A device frame lives in a calloc'd maple_device_t (the detect frame in .bss, cleared
# at start-up): those zeroing stores sit dirty in the operand cache and, when evicted, overwrite the answer the DMA
# has just landed (Flycast cache observer + maple DMA: DMA-OVER-DIRTY then CLOBBER-WB on the unit A0 and detect
# receive buffers within 0.1 s of boot). A link wrap of maple_frame_init (platform/misc.cpp) writes those 32 lines back
# (ocbp) before KOS clears the buffer. Boot and hot-plug window only; once clean the P1 lines are never cached again.
MAPLE_RECV_PURGE ?= 0
ifneq ($(filter $(MAPLE_RECV_PURGE),0 1),$(MAPLE_RECV_PURGE))
$(error MAPLE_RECV_PURGE must be 0 or 1)
endif
ifneq ($(MAPLE_RECV_PURGE),0)
$(OBJDIR)/platform/misc.o: PLATFORM_CPPFLAGS += -DRE4DC_MAPLE_RECV_PURGE=1
GAME_LDFLAGS += -Wl,--wrap=maple_frame_init
endif
# CRASH_SCREEN=1 (hardware readiness, default 0): a fault, a source HALT() or 30 s without a new frame
# draws a report (stop kind, PC/PR/stage, threads, newest log lines) into frame buffer 0, for a photo
# on hardware where the log ring cannot be read. platform/crash_screen.cpp.
CRASH_SCREEN ?= 0
# PVR_LATCH=1 (issue 9 hardware diagnosis, default 0; needs CRASH_SCREEN=1, PVR_PIPELINE=2): chained handlers on
# every PVR ASIC event (list done, render done, the five TA/ISP error events) and thread-side scene marks feed a
# 64-entry ring, totals and the KOS PVR state, printed on the stop screen in place of the raw asic line (KOS
# acknowledges all pending ASIC bits on every interrupt, so that line always read zero). Render-only.
PVR_LATCH ?= 0
# PVR_READY_STRICT=1 (issue 9 fix, default 0; needs PVR_PIPELINE=2): KOS starts writing the next scene into a TA bank
# whose previous scene was never handed to a render once pvr_wait_ready()'s 100 ms wait expires (pvr_scene.c
# pvr_start_ta_rendering ignores the result). Link wraps of pvr_list_begin / pvr_set_presort_mode keep waiting in
# 100 ms slices (bounded at 10 s) and present_fence does the same for pvr_present_wait; each expired slice is
# counted (with PVR_LATCH: ring codes K / Q / Y and a "rdy" stop screen row). platform/native_ui.cpp namespace ready.
PVR_READY_STRICT ?= 0
# PVR_LATCH=2 (latch v2, issue 9): as 1, plus a run of one ring code collapsed into one entry with a count, all six
# SB_ISTERR bits with the UI frame each first appeared, and each scene's TA vertex / OPB use at its close (last two
# scenes and the maximum since boot) on two more stop screen rows.
# PVR_RECOVER=1 (issue 9 fix, default 0; needs PVR_READY_STRICT=1): a render still busy after 1 s (100 ms after a
# render error) is reset (PVR soft reset of the ISP/TSP) and completed through the render-done handler chain in the
# next vblank, its frame dropped; a scene whose list-done events never all arrive gets them (TA reset first after a
# TA error). Stop screen after 8 recoveries in a row. platform/native_ui.cpp namespace pvr_recover.
PVR_RECOVER ?= 0
# UI_OS=1 (issue 9 i9d, default = PVR_RECOVER, so 0: no effect): platform/native_ui.o at -Os instead of GAME_OPT
# (-O1): 9.6 KB less .text. With LINK_TIGHT image growth costs heap 4 byte for byte (in 4 KiB arena-fit steps), and
# latch v2 + PVR_READY_STRICT + PVR_RECOVER add 6.7 KB, which took one 8 KB step of the r100 s30 movie's heap_before;
# with UI_OS the knobs-on image ends below the knobs-off one. Render-side code only (the logic trace is unchanged).
UI_OS ?= $(PVR_RECOVER)
# PVR_MID_FENCE=1 (issue 9 i9d, default = PVR_RECOVER; needs PVR_PIPELINE): the last PVR writes that could land while
# a queued render runs wait for it first (present_fence): the NATIVE_MES glyph palette banks (pvr_set_pal_entry),
# glyph cell texel loads and the LOOK_TOGGLE label texture. Render-only; Flycast renders at once, so the fences
# are free there.
PVR_MID_FENCE ?= $(PVR_RECOVER)
# TA_HEADROOM=n (issue 9 i9d, default 0: no effect; needs PVR_STREAM): n more object-pointer overflow blocks per TA
# bank (opb_overflow_count TA_OPB_OVERFLOW+n), paid for by a vertex buffer n x the initial OPB size smaller (rounded up
# to 1 KiB): 640x480, OP 16 + TR 16 + PT 8 words = 48,000 B per step, vertex 2048 -> 2001 KiB for n=1, so the
# texture pool does not shrink (measured: 2,566,912 -> 2,567,168 B free at init). r109's first scenes (TA_BIN_DIAG) need ~118.6K of the 144K pool in the
# model, ~136K at the photo-calibrated 0.87 x hardware ratio, and 1.66 MB of vertex buffer.
TA_HEADROOM ?= 0
# CRASH_TASK_DETAIL=1 (issue 21 diagnosis, default 0; needs CRASH_SCREEN=1): when the main thread waits on a game
# task's yield / resume semaphore, the stop screen shows that task's own thread first (slot, tid, state, saved pc / pr,
# wait message + object + timeout, return-address candidates), above the PVR latch rows. Stop screen only.
CRASH_TASK_DETAIL ?= 0
# CRASH_FAULT_DETAIL=1: actual exception registers and bounded fault-thread
# return-address candidates, before waiting-thread details. Default off.
CRASH_FAULT_DETAIL ?= 0
# KOS_HEAP_CHECK=1: diagnostic-only local recompile of the selected KOS
# allocator with its existing MALLOC_DEBUG checks plus an allocation event ring.
# Never rebuilds or edits the shared KOS library. Do not ship as a performance build.
KOS_HEAP_CHECK ?= 0
ifneq ($(filter-out 0 1,$(CRASH_FAULT_DETAIL) $(KOS_HEAP_CHECK)),)
$(error CRASH_FAULT_DETAIL and KOS_HEAP_CHECK must be 0 or 1)
endif
ifneq ($(CRASH_FAULT_DETAIL)$(KOS_HEAP_CHECK),00)
ifneq ($(CRASH_SCREEN),1)
$(error CRASH_FAULT_DETAIL and KOS_HEAP_CHECK need CRASH_SCREEN=1)
endif
endif
ifeq ($(KOS_HEAP_CHECK),1)
PLATFORM_OBJS += $(OBJDIR)/platform/heap_audit.o
GAME_LDFLAGS += -Wl,--wrap=malloc -Wl,--wrap=calloc -Wl,--wrap=realloc -Wl,--wrap=free -Wl,--wrap=memalign
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_KOS_HEAP_CHECK=1
$(OBJDIR)/platform/heap_audit.o: platform/heap_audit.c $(KOS_BASE)/kernel/libc/koslib/malloc.c
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -Os -I$(KOS_BASE)/kernel/libc/koslib -MMD -MP -c $< -o $@
endif
.PHONY: crash-screen-force
$(OBJDIR)/crash-screen.h: crash-screen-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_CRASH_SCREEN %s\n#define RE4DC_PVR_LATCH %s\n#define RE4DC_CRASH_TASK_DETAIL %s\n' '$(CRASH_SCREEN)' '$(PVR_LATCH)' '$(CRASH_TASK_DETAIL)' > $@.tmp
	@printf '#define RE4DC_CRASH_FAULT_DETAIL %s\n#define RE4DC_KOS_HEAP_CHECK %s\n' '$(CRASH_FAULT_DETAIL)' '$(KOS_HEAP_CHECK)' >> $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/fault.o $(OBJDIR)/platform/crash_screen.o $(OBJDIR)/platform/os.o $(OBJDIR)/platform/modules.o: $(OBJDIR)/crash-screen.h
$(OBJDIR)/platform/fault.o $(OBJDIR)/platform/crash_screen.o $(OBJDIR)/platform/os.o $(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/crash-screen.h
$(OBJDIR)/src/game/scheduler.o $(OBJDIR)/sscrn_bridge.o: $(OBJDIR)/crash-screen.h
$(OBJDIR)/src/game/scheduler.o $(OBJDIR)/sscrn_bridge.o: GAME_CPPFLAGS += -include $(OBJDIR)/crash-screen.h
.PHONY: poison-force
$(OBJDIR)/poison.h: poison-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_POISON_RAM %s\n' '$(POISON_RAM)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/mem.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/audio_aica.o: $(OBJDIR)/poison.h
$(OBJDIR)/platform/mem.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/poison.h
.PHONY: dvd-io-force
$(OBJDIR)/dvd-io.h: dvd-io-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_DVD_WAIT %s\n#define RE4DC_DVD_FDCACHE %s\n#define RE4DC_IO_SERIAL %s\n' '$(DVD_WAIT)' '$(DVD_FDCACHE)' '$(IO_SERIAL)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/dvd.o: $(OBJDIR)/dvd-io.h
$(OBJDIR)/platform/dvd.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/dvd-io.h
$(OBJDIR)/native-reuse/texture_package.o: $(OBJDIR)/dvd-io.h
$(OBJDIR)/native-reuse/texture_package.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/dvd-io.h
# D367 disc I/O probe (W10). IO_PROBE=1 (default off; the default image does not change):
# platform/io_probe.cpp runs timed disc reads at boot when /cd/dc/ioprobe.txt exists
# (sequential, cold, open/close, motion keys, seek sweep, a paced 225 KB/s stream alone and
# under a bulk loader) and shows them in the log ring, the re4dc_ioprobe struct, VMU pages
# and a PERF_HUD row. The room cycle fixture also gets room-entry telemetry ("iotime:"
# lines: wall time, source DVD and motion-key blocking).
IO_PROBE ?= 0
ifneq ($(IO_PROBE),1)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/io_probe.o $(OBJDIR)/platform/io_wrap.o,$(PLATFORM_OBJS))
else
# Diagnostic wraps (platform/io_wrap.cpp): time every blocking read, open, sleep and KOS wait
# by file, caller and thread for the "iowrap:" room-entry lines, and count the GD commands under
# them (the KOS stream start/request and sector-read entry points) for the "iocount:" lines.
GAME_LDFLAGS += -Wl,--wrap=fs_read -Wl,--wrap=fs_open -Wl,--wrap=thd_sleep -Wl,--wrap=genwait_wait
GAME_LDFLAGS += -Wl,--wrap=cdrom_stream_start -Wl,--wrap=cdrom_stream_request -Wl,--wrap=cdrom_read_sectors_ex
endif
# DVD_READ_SAFE=1 (Phase 2 D4, default 0): platform/dvd_read_safe.cpp wraps cdrom_stream_start / _request. KOS's
# dma_in_progress can stay set while a stream command runs, and then every later stream request fails ("Previous DMA
# request is in progress": r119 GC-bake texture uploads, tex.pak index reads, until the end of the run). A refused
# request is retried for 10 ms, then the stale flag is cleared (cdrom_abort_cmd with abort_dma), the stream restarted
# where it stood and the request repeated. DVD_STUCK_TEST=<seconds> + DVD_STUCK_ADDR=<address of KOS dma_in_progress>
# (test discs only) set the flag on demand. Not with IO_PROBE=1 (it wraps the same entry points).
# DISC_READ_FALLBACK=1 (issue #28, default 0; same file): a DMA read (stream request or sector read) that fails, or
# reports OK without landing (a marker in the destination's last 32 bytes survives: DreamShell's ISO loader), or a
# stream stop that times out latches the session to PIO sector reads; the read is redone by PIO. It also validates the
# sound stream table / ISS block headers (src/game/snd.cpp) and re-reads or skips a bad one instead of faulting.
# DISC_FAIL_TEST=1|2 (test discs only): every DMA stream request (1), and also every DMA sector read (2), is skipped and
# reported OK: the emulator's failure on demand.
# DISC_READ_VERIFY=1 (test 11 console faults, default 0; same file + platform/dvd.cpp): a DMA read KOS reports done is
# not handed back until the G1 GD-DMA engine is idle (SB_GDST); fs_iso9660's non-blocking 32-byte stream request is
# made blocking so it gets the same wait; DVD_READ_SAFE never aborts a refused request while the GD DMA is running (up
# to 2 s); a short or failed DVDReadAsyncPrio read is retried on a fresh handle (3 tries) and then reported
# DVD_RESULT_FATAL instead of a partial count. Each event logs a "disc read verify:" line.
# DISC_GD_ATOMIC=1 (test 11 console faults, default 0; same file): every GD-ROM BIOS syscall KOS makes runs with
# interrupts masked. KOS's vblank and G1 DMA handlers call the BIOS (exec_server, check_command) from interrupt context
# and write the cdrom driver's shared cmd_response/cmd_status, while a thread may be inside a BIOS call of its own;
# the BIOS is not re-entrant. Flycast's HLE BIOS runs each syscall atomically, so it never shows this.
DISC_GD_ATOMIC ?= 0
ifneq ($(filter $(DISC_GD_ATOMIC),0 1),$(DISC_GD_ATOMIC))
$(error DISC_GD_ATOMIC must be 0 or 1)
endif
DISC_READ_VERIFY ?= 0
ifneq ($(filter $(DISC_READ_VERIFY),0 1),$(DISC_READ_VERIFY))
$(error DISC_READ_VERIFY must be 0 or 1)
endif
ifeq ($(DISC_READ_VERIFY),1)
$(OBJDIR)/platform/dvd.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_READ_VERIFY=1
endif
# DISC_READ_METER=1 (T12 Phases disc, 2026-10-15; display / log only, default 0; needs DVD_READ_SAFE=1 and
# PHASE_METER=1): counts every GD-ROM drive call the game makes (cdrom_stream_start, cdrom_stream_request,
# cdrom_read_sectors_ex: fs_iso9660 reads all files through them, so tex.pak, motion, sound, effect and room reads all
# count) in platform/dvd_read_safe.cpp's wraps: a marker square lit while a read is in flight (green) or ran since the
# last drawn frame (orange), a row with reads/s, KB/s and ms/s the game thread spent inside those calls (the last pace
# window), and the room-entry load time (StageSet entry, or room enter for the first room, to the first gameMainLoop
# frame in the room), shown for 5 s. The music stream thread's reads (audio_aica.cpp str_main, bgm/aica_str.dat, 2 KB
# every few frames all through play) are kept apart: a thin blue bar under the marker, not in the marker or the row.
# "DISCRD:" log lines per window with game reads and per room entry. The read path only updates counters (interrupts
# masked for the few instructions) and reads the timer when the game thread calls.
DISC_READ_METER ?= 0
ifneq ($(filter $(DISC_READ_METER),0 1),$(DISC_READ_METER))
$(error DISC_READ_METER must be 0 or 1)
endif
# MOTION_STATS_LOG=1 (test 14 r103 motion thrash, crash lane 10-15; log only, default 0 = image unchanged; needs
# DISC_READ_METER=1): at each DISCRD window close, one "MOTSTAT:" line with the native motion cache's counters for the
# window (misses = key loads from the disc, evictions, KB read) and its state (resident
# bytes, the pressure cap, heap 4 free bytes), and per bound archive one "MOTWS:" line with its working set: the bytes
# of the distinct keys the game used in the window, in the current 5-window block and since the bind.
MOTION_STATS_LOG ?= 0
ifneq ($(MOTION_STATS_LOG),0)
ifneq ($(DISC_READ_METER),1)
$(error MOTION_STATS_LOG=1 needs DISC_READ_METER=1)
endif
$(OBJDIR)/platform/dvd_read_safe.o $(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -DRE4DC_MOTION_STATS_LOG=1
endif
# DISC_READ_LOG=1 (lane zeroread17 2026-10-17; diagnostic, log only, default 0; needs DISC_READ_METER=1): one "DRL:" line
# per drive call that moves data (a sector read: S, a stream start: T) with its first sector, its size and the calling
# thread, so in-play reads map to disc files through the ISO listing (isoinfo -l extents of track03).
DISC_READ_LOG ?= 0
ifneq ($(DISC_READ_LOG),0)
ifneq ($(DISC_READ_METER),1)
$(error DISC_READ_LOG=1 needs DISC_READ_METER=1)
endif
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_READ_LOG=1
endif
# DISC_COMPAT=1 (test 14 items 11/12, lane discread 2026-10-15, default 0): the disc-read compatibility set for GDEMU
# units and clones, ODEs and loaders (RE4DC-DISC-COMPAT-RESEARCH-20261015.md section 6), one knob:
# - DISC_READ_FALLBACK=2: plain sector reads only (no cdrom_stream start / cancel per read, so no stream is ever
#   cancelled with data queued and DVD_READ_SAFE's 10 ms force-abort of a refused stream request cannot run), each read
#   a bounded GD command (DMA, then DMA after a bounded drive re-init, then PIO), bounded cdrom_reinit;
# - DISC_BOOT_LOG=2: the disc log goes on screen only once a read misbehaves (=1: always during the boot, the #28 discs);
# - KOS_DISC_FIX=1: a build-time patched copy of KOS fs_iso9660.c (upstream aeee10d9: one mutex, no multi-thread /cd
#   deadlock or garbage handles) and cdrom.c (exec_cmd_timed's abort deadlock, reinit_ex's endless retry, a settle
#   delay after a drive reset, no stale GD DMA completion: kos-804b319-cdrom-dma-done.patch) is linked in place of
#   libkallisti's (patches/kos-804b319-*.patch; KOS is not modified);
# - the /cd mount takes the data track that holds the ISO9660 volume descriptor, not the last one (GD MENU Card
#   Manager's "Shrink GDI" splits the HD area into track 3 + track 4: platform/gdrom_mount.cpp).
# Packaging (mkgdi.sh, not a make knob): PAD_1ST=1 pads 1ST_READ.BIN to whole sectors; PRODUCT= sets the product number.
DISC_COMPAT ?= 0
ifneq ($(filter $(DISC_COMPAT),0 1),$(DISC_COMPAT))
$(error DISC_COMPAT must be 0 or 1)
endif
ifeq ($(DISC_COMPAT),1)
# DISC_COMPAT=1 DISC_READ_FALLBACK=0 is the timing-neutral subset (KOS fixes + the mount; 12.2's stream reads kept):
# STRICT against 12.2 in Flycast, where the plain sector reads move load completion by ticks (lane discread 10-15).
ifneq ($(filter $(origin DISC_READ_FALLBACK),command line environment),)
ifneq ($(filter $(DISC_READ_FALLBACK),0 2 3),$(DISC_READ_FALLBACK))
$(error DISC_COMPAT=1 uses DISC_READ_FALLBACK=2 (or 3: streams with the automatic fallback; 0: the subset))
endif
else
DISC_READ_FALLBACK := 2
endif
override KOS_DISC_FIX := 1
DISC_BOOT_LOG ?= 2
endif
DISC_BOOT_LOG ?= 1
ifneq ($(filter $(DISC_BOOT_LOG),1 2),$(DISC_BOOT_LOG))
$(error DISC_BOOT_LOG must be 1 or 2)
endif
KOS_DISC_FIX ?= 0
ifneq ($(filter $(KOS_DISC_FIX),0 1),$(KOS_DISC_FIX))
$(error KOS_DISC_FIX must be 0 or 1)
endif
# Build17 / issue28: opt-in bounded direct-sector DMA, same-sector PIO retry,
# and permanent session PIO after two consecutive failed DMA attempts. Streams
# are refused from startup so their untimed KOS waits cannot block the retry.
# No source/object change when absent or 0; the release recipe is unchanged.
DISC_PIO_FALLBACK ?= 0
ifneq ($(filter $(DISC_PIO_FALLBACK),0 1),$(DISC_PIO_FALLBACK))
$(error DISC_PIO_FALLBACK must be 0 or 1)
endif
ifeq ($(DISC_PIO_FALLBACK),1)
ifneq ($(KOS_DISC_FIX),1)
$(error DISC_PIO_FALLBACK=1 needs KOS_DISC_FIX=1)
endif
ifeq ($(filter 2 3,$(DISC_READ_FALLBACK)),)
$(error DISC_PIO_FALLBACK=1 needs DISC_READ_FALLBACK=2 or 3)
endif
ifneq ($(filter-out 0,$(DISC_FAIL_TEST) $(DVD_STUCK_TEST) $(DISC_DMA_DROP_TEST)),)
$(error DISC_PIO_FALLBACK uses its synthetic fake-driver gate; legacy disc fault hooks must be 0)
endif
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_PIO_FALLBACK=1
$(OBJDIR)/src/game/snd.o: GAME_CPPFLAGS += -DRE4DC_DISC_PIO_FALLBACK=1 -I$(CURDIR)/platform
$(OBJDIR)/platform/dvd_read_safe.o: platform/disc_pio_fallback.h platform/disc_pio_native.inc
$(OBJDIR)/src/game/snd.o: platform/disc_stream_table_check.h
endif
# CACHE_COHERENT_DMA=1 (lane fix-r100-props26 2026-10-26, default 0 = image unchanged): operand-cache maintenance on
# disc reads. cdrom_read_toc fills a 32-byte aligned private TOC (purged before, invalidated after the call); a
# dvd_read_safe DMA read invalidates its whole destination after it lands (the fast path only invalidated before the
# DMA, so a line refetched while the GD DMA ran stayed stale), and a late landing invalidates instead of purging.
# Found under flycast-console's SH-4 cache model (RE4DC_CONSOLE_DYNAREC=no), where T24 lost its TOC at boot.
CACHE_COHERENT_DMA ?= 0
ifneq ($(filter $(CACHE_COHERENT_DMA),0 1),$(CACHE_COHERENT_DMA))
$(error CACHE_COHERENT_DMA must be 0 or 1)
endif
ifeq ($(CACHE_COHERENT_DMA),1)
$(OBJDIR)/platform/gdrom_mount.o $(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_CACHE_COHERENT_DMA=1
endif
# DISC_DMA_WAIT_TIMEOUT=1 (issue #28 DreamShell, lane fix-dreamshell23 2026-10-23, default 0 = image unchanged; needs
# KOS_DISC_FIX=1): KOS waited on a GD DMA completion with no limit (sector reads and stream requests), so a loader that
# never completes a DMA (DreamShell's ISO loader, first read bgm/bio4str.hed) hung the boot before DISC_READ_FALLBACK=3's
# plain-read fallback could run. kos-804b319-cdrom-dma-wait-timeout.patch bounds each wait (5 s + 8 ms a sector, the v2
# command bound); a timeout closes the DMA state and returns ERR_TIMEOUT, and dvd_read_safe.cpp logs
# "disc dma wait timeout" and falls back (stream: PIO/plain fill + session latch; sector read: latch + plain read).
# DISC_DMA_DROP_TEST=1 (test discs only): the first DMA read never gets its completion (as DreamShell).
DISC_DMA_WAIT_TIMEOUT ?= 0
DISC_DMA_DROP_TEST ?= 0
ifneq ($(filter $(DISC_DMA_WAIT_TIMEOUT),0 1),$(DISC_DMA_WAIT_TIMEOUT))
$(error DISC_DMA_WAIT_TIMEOUT must be 0 or 1)
endif
ifeq ($(DISC_DMA_WAIT_TIMEOUT),1)
ifneq ($(KOS_DISC_FIX),1)
$(error DISC_DMA_WAIT_TIMEOUT=1 needs KOS_DISC_FIX=1 (DISC_COMPAT=1))
endif
endif
ifeq ($(DISC_DMA_DROP_TEST),1)
ifneq ($(DISC_DMA_WAIT_TIMEOUT),1)
$(error DISC_DMA_DROP_TEST=1 needs DISC_DMA_WAIT_TIMEOUT=1)
endif
endif
ifeq ($(KOS_DISC_FIX),1)
KOSFIX := $(OBJDIR)/kosfix
KOS_PATCHES := $(CURDIR)/../patches
PLATFORM_OBJS += $(KOSFIX)/fs_iso9660.o $(KOSFIX)/cdrom.o
$(KOSFIX)/fs_iso9660.c: $(KOS_BASE)/kernel/arch/dreamcast/fs/fs_iso9660.c $(KOS_PATCHES)/kos-804b319-fs-iso9660-aeee10d9.patch
	@rm -rf $(KOSFIX)/p-fs && mkdir -p $(KOSFIX)/p-fs/kernel/arch/dreamcast/fs
	cp $< $(KOSFIX)/p-fs/kernel/arch/dreamcast/fs/
	patch --fuzz=0 -s -p1 -d $(KOSFIX)/p-fs < $(KOS_PATCHES)/kos-804b319-fs-iso9660-aeee10d9.patch
ifeq ($(DISC_PIO_FALLBACK),1)
	patch --fuzz=0 -s -p1 -d $(KOSFIX)/p-fs < $(KOS_PATCHES)/kos-804b319-iso-pio-retry.patch
endif
	cp $(KOSFIX)/p-fs/kernel/arch/dreamcast/fs/fs_iso9660.c $@
ifeq ($(DISC_PIO_FALLBACK),1)
$(KOSFIX)/fs_iso9660.c: $(KOS_PATCHES)/kos-804b319-iso-pio-retry.patch
endif
# kos-804b319-cdrom-dma-done.patch (lane discread 10-15, the LinkOrder console stops): a GD DMA read that the BIOS
# reported completed straight away left a DMA completion to be signalled later, which ended the NEXT DMA wait before its
# data landed (console only). Stale completions are drained before every DMA and a DMA read returns with the GD-DMA
# engine idle; the counts (drained / closed) are on the crash screen's stage row ("gd s<n> e<n>").
$(KOSFIX)/cdrom.c: $(KOS_BASE)/kernel/arch/dreamcast/hardware/cdrom.c $(KOS_PATCHES)/kos-804b319-cdrom-hang-fixes.patch $(KOS_PATCHES)/kos-804b319-cdrom-dma-done.patch
	@rm -rf $(KOSFIX)/p-cd && mkdir -p $(KOSFIX)/p-cd/kernel/arch/dreamcast/hardware
	cp $< $(KOSFIX)/p-cd/kernel/arch/dreamcast/hardware/
	patch --fuzz=0 -s -p1 -d $(KOSFIX)/p-cd < $(KOS_PATCHES)/kos-804b319-cdrom-hang-fixes.patch
	patch --fuzz=0 -s -p1 -d $(KOSFIX)/p-cd < $(KOS_PATCHES)/kos-804b319-cdrom-dma-done.patch
ifeq ($(DISC_DMA_WAIT_TIMEOUT),1)
	patch --fuzz=0 -s -p1 -d $(KOSFIX)/p-cd < $(KOS_PATCHES)/kos-804b319-cdrom-dma-wait-timeout.patch
endif
	cp $(KOSFIX)/p-cd/kernel/arch/dreamcast/hardware/cdrom.c $@
ifeq ($(DISC_DMA_WAIT_TIMEOUT),1)
$(KOSFIX)/cdrom.c: $(KOS_PATCHES)/kos-804b319-cdrom-dma-wait-timeout.patch
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_DMA_WAIT_TIMEOUT=1
ifeq ($(DISC_DMA_DROP_TEST),1)
$(KOSFIX)/cdrom.o: KOS_CFLAGS += -DRE4DC_DISC_DMA_DROP_TEST=1
endif
endif
$(OBJDIR)/platform/crash_screen.o: PLATFORM_CPPFLAGS += -DRE4DC_KOS_DMA_COUNTERS=1
endif
# The stage row's GD DMA counters (platform/kos_dma_counters.h: empty unless KOS_DISC_FIX=1).
$(OBJDIR)/platform/crash_screen.o: PLATFORM_CPPFLAGS += -include $(CURDIR)/platform/kos_dma_counters.h
ifeq ($(KOS_DISC_FIX),1)
# -fmacro-prefix-map: cdrom.c's __FILE__ (assert / dbglog) names kosfix/cdrom.c, not $(OBJDIR): the image must not
# depend on the build label or directory (build-public.sh and fp_twin.sh rebuild the release image elsewhere).
$(KOSFIX)/%.o: $(KOSFIX)/%.c
	kos-cc $(KOS_CFLAGS) -O2 -fmacro-prefix-map=$(KOSFIX)/=kosfix/ -MMD -MP -c $< -o $@
endif
ifeq ($(DISC_COMPAT),1)
$(OBJDIR)/platform/gdrom_mount.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_COMPAT=1
endif
# KOS_SBRK_LAST_PAGE=1 (lane ramreclaim 2026-10-15, default 0 = image unchanged; exact): KOS mm_sbrk refuses a break that
# reaches the kernel stack's base (`new_base >= limit`), so the last 4 KiB page below the 64 KiB kernel stack can never be
# used: every console/Flycast "Out of memory. Requested sbrk_base 0x8cff0000" is that page. The game links a copy of
# kernel/mm/mm.c with `>` (patches/kos-804b319-mm-sbrk-last-page.patch); a break ending exactly at the base does not
# overlap the stack. Behaviour differs only where the stock check would have run out of KOS: +4,096 B usable KOS.
KOS_SBRK_LAST_PAGE ?= 0
ifneq ($(filter-out 0 1,$(KOS_SBRK_LAST_PAGE)),)
$(error KOS_SBRK_LAST_PAGE must be 0 or 1)
endif
ifeq ($(KOS_SBRK_LAST_PAGE),1)
KOSMM := $(OBJDIR)/kosmm
PLATFORM_OBJS += $(KOSMM)/mm.o
$(KOSMM)/mm.c: $(KOS_BASE)/kernel/mm/mm.c $(CURDIR)/../patches/kos-804b319-mm-sbrk-last-page.patch
	@rm -rf $(KOSMM)/p && mkdir -p $(KOSMM)/p/kernel/mm
	cp $< $(KOSMM)/p/kernel/mm/
	patch --fuzz=0 -s -p1 -d $(KOSMM)/p < $(CURDIR)/../patches/kos-804b319-mm-sbrk-last-page.patch
	cp $(KOSMM)/p/kernel/mm/mm.c $@
$(KOSMM)/mm.o: $(KOSMM)/mm.c
	kos-cc $(KOS_CFLAGS) -O2 -fmacro-prefix-map=$(KOSMM)/=kosmm/ -MMD -MP -c $< -o $@
endif
# DISC_READ_FALLBACK=2 (issue #28 v2, 2026-10-15; v1 gave a black screen under the ISO loader): no cdrom streams at all
# (fs_iso9660 reads by sector reads), every sector read is a bounded GD command polled from the calling thread (DMA, then
# DMA after a bounded drive re-init, then PIO; the one that works is reported and kept), cdrom_reinit is wrapped with a
# bounded CD_CMD_INIT, and an on-screen boot log (until the game's first picture) names each step and the read in
# flight; if every method fails a DISC READ FAILED screen stays up. DISC_FAIL_TEST with =2: 2 DMA reports done without a
# transfer, 3 = 2 + PIO never completes, 4 the first DMA read and its abort never finish, 5 the first read spins with
# interrupts off. Details: platform/dvd_read_safe.cpp.
# DISC_READ_FALLBACK=3 (test 15, user decision 10-16 "option A"; lane plainread16): the stream reads of =0 (fast path,
# same timing), each DMA request checked as =1 does; the first stream or sector read that fails, times out or does not
# land latches the session onto =2's plain bounded sector reads (DMA, DMA after a bounded re-init, then PIO), no stream
# is started again. DISC_FAIL_AFTER_S=N (test only, with DISC_FAIL_TEST=2 and =3): the "done without the transfer"
# failure starts after N s of uptime (a mid-game failure), not at the first read.
DISC_READ_FALLBACK ?= 0
ifneq ($(filter $(DISC_READ_FALLBACK),0 1 2 3),$(DISC_READ_FALLBACK))
$(error DISC_READ_FALLBACK must be 0, 1, 2 or 3)
endif
DISC_FAIL_AFTER_S ?= 0
DISC_FAIL_TEST ?= 0
DVD_READ_SAFE ?= 0
DVD_STUCK_TEST ?= 0
DVD_STUCK_ADDR ?= 0
ifneq ($(DVD_READ_SAFE)$(DVD_STUCK_TEST)$(DISC_READ_FALLBACK)$(DISC_FAIL_TEST)$(DISC_READ_VERIFY)$(DISC_GD_ATOMIC),000000)
ifeq ($(IO_PROBE),1)
$(error DVD_READ_SAFE / DVD_STUCK_TEST / DISC_READ_FALLBACK and IO_PROBE=1 wrap the same cdrom entry points)
endif
GAME_LDFLAGS += -Wl,--wrap=cdrom_stream_start -Wl,--wrap=cdrom_stream_request
ifneq ($(DISC_READ_FALLBACK)$(DISC_FAIL_TEST)$(DISC_READ_VERIFY),000)
GAME_LDFLAGS += -Wl,--wrap=cdrom_read_sectors_ex -Wl,--wrap=cdrom_stream_stop
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_READ_FALLBACK=$(DISC_READ_FALLBACK) -DRE4DC_DISC_FAIL_TEST=$(DISC_FAIL_TEST) -DRE4DC_DISC_READ_VERIFY=$(DISC_READ_VERIFY) -DRE4DC_DISC_FAIL_AFTER_S=$(DISC_FAIL_AFTER_S)
endif
ifneq ($(DISC_READ_FALLBACK),0)
$(OBJDIR)/src/game/snd.o: GAME_CPPFLAGS += -DRE4DC_DISC_READ_FALLBACK=$(DISC_READ_FALLBACK)
endif
# EFFECT_BIND_DIAG=1 (lane discread 10-15, console diagnosis, default 0 = image unchanged): readEmData's MISSING line
# names the native_effect.cpp check that refused the archive, the file, its size and an FNV-1a of the bytes read
# ("enemy effect records chk<line> <file> <bytes>b fnv<hash>"), to tell a damaged disc read from a binding-table fault.
EFFECT_BIND_DIAG ?= 0
ifeq ($(EFFECT_BIND_DIAG),1)
$(OBJDIR)/platform/native_effect.o: PLATFORM_CPPFLAGS += -DRE4DC_EFFECT_BIND_DIAG=1
$(OBJDIR)/src/game/read.o: GAME_CPPFLAGS += -DRE4DC_EFFECT_BIND_DIAG=1
endif
# EFFECT_STATS_LOG=1 (test only, lane ch4found16 2026-10-17; default 0 = image unchanged): logs each new worst decode
# time of a compacted effect record (prepare_enemy_motions.py --compact-effects archives) and a summary every 4096
# compact reads ("effect decode:" lines, native_effect.cpp).
EFFECT_STATS_LOG ?= 0
ifeq ($(EFFECT_STATS_LOG),1)
$(OBJDIR)/platform/native_effect.o: PLATFORM_CPPFLAGS += -DRE4DC_EFFECT_STATS_LOG=1
endif
# DISC_POLL_SPIN_MS=N (with DISC_READ_FALLBACK=2, default 0): a sector read polls its GD command with thd_pass for N ms
# before it sleeps (a KOS sleep ends at the next 10 ms scheduler tick). Lane discread load-time experiment.
DISC_POLL_SPIN_MS ?= 0
# DISC_LAND_SPIN_MS=N (with DISC_READ_FALLBACK=2, default 0 = image unchanged; lane plainread16 2026-10-16): after a DMA
# sector read reports done, wait for the G1 GD-DMA engine to finish with thd_pass for up to N ms before sleeping. A KOS
# sleep lasts until the next 10 ms scheduler tick; on units that report COMPLETED before the data lands (GDEMU, the
# flycast-console gdemu / weak profiles) that made every plain read cost >= 10 ms (r101 entry 7.0 -> 19.4 s, gdemu model).
# Nonzero also bounds that wait by the read's size (1 s + 8 ms a sector) instead of 1 s: on the weak profile (~600 KiB/s)
# a 626-sector read took over 1 s to land, was declared lost and the drive was re-initialised under the DMA.
DISC_LAND_SPIN_MS ?= 0
# STORAGE_BOUNCE_ALIGNED=1 (needs DISC_READ_FALLBACK=2; lane plainread16 2026-10-16, default 0 = image unchanged): the
# shared 16 KiB storage bounce buffer (room/room_storage.cpp: every texture package, tex.pak entry and other read_chunks
# user) becomes 32-byte aligned. It was misaligned on purpose to keep KOS off its stream path; with streams refused
# (plain sector reads) the aligned buffer makes fs_iso9660 read a chunk's whole sectors in one GD command instead of one
# command per sector. Exact: the same bytes in the same places.
STORAGE_BOUNCE_ALIGNED ?= 0
ifneq ($(STORAGE_BOUNCE_ALIGNED),0)
ifneq ($(DISC_READ_FALLBACK),2)
$(error STORAGE_BOUNCE_ALIGNED=1 needs DISC_READ_FALLBACK=2 (an aligned buffer starts KOS cdrom streams otherwise))
endif
$(OBJDIR)/native-reuse/room_storage.o: PLATFORM_CPPFLAGS += -DRE4DC_STORAGE_BOUNCE_ALIGNED=1
endif
ifneq ($(filter $(DISC_READ_FALLBACK),2 3),)
GAME_LDFLAGS += -Wl,--wrap=cdrom_reinit
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_BOOT_LOG=$(DISC_BOOT_LOG) -DRE4DC_DISC_POLL_SPIN_MS=$(DISC_POLL_SPIN_MS) -DRE4DC_DISC_LAND_SPIN_MS=$(DISC_LAND_SPIN_MS)
endif
ifeq ($(DISC_GD_ATOMIC),1)
GAME_LDFLAGS += -Wl,--wrap=syscall_gdrom_check_drive -Wl,--wrap=syscall_gdrom_send_command -Wl,--wrap=syscall_gdrom_check_command -Wl,--wrap=syscall_gdrom_exec_server -Wl,--wrap=syscall_gdrom_abort_command -Wl,--wrap=syscall_gdrom_dma_callback -Wl,--wrap=syscall_gdrom_dma_transfer -Wl,--wrap=syscall_gdrom_dma_check -Wl,--wrap=syscall_gdrom_pio_callback -Wl,--wrap=syscall_gdrom_pio_transfer -Wl,--wrap=syscall_gdrom_pio_check
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_GD_ATOMIC=1
endif
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DVD_READ_SAFE=$(DVD_READ_SAFE) -DRE4DC_DVD_STUCK_TEST=$(DVD_STUCK_TEST) -DRE4DC_DVD_STUCK_ADDR=$(DVD_STUCK_ADDR)
ifeq ($(DISC_READ_METER),1)
ifeq ($(DISC_READ_FALLBACK)$(DISC_FAIL_TEST)$(DISC_READ_VERIFY),000)
GAME_LDFLAGS += -Wl,--wrap=cdrom_read_sectors_ex
endif
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_READ_METER=1
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_DISC_READ_METER=1
$(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_DISC_READ_METER=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_READ_METER=1
$(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_READ_METER=1
endif
# SND_PAD_SKIP=1 (lane doorpause16, 2026-10-16; default 0 = image unchanged; does something only with AICA_AUDIO=1): the
# source queue leaves out the disc reads of a sound block's ARAM part past a build-time converted bank's image. The
# part keeps the GameCube size on the disc (the game's ARAM layout is sized from it) and is zero after the image:
# 0.85 to 2.7 MB of every chapter 1 door's 4 to 11 MB (DOOR-PAUSE-CH1-20261016.md). The skipped pieces still pass
# through the queue's transfer step and re4dc_audio_arq (which copies only the image), so the AICA RAM, the ARAM
# addresses, UseAramSize and the queue's steps are the same; only the reads (and their wait) are gone.
# platform/include/snd_pad_skip.h is forced into dvd.o (the source keeps its line numbers).
SND_PAD_SKIP ?= 0
ifneq ($(filter $(SND_PAD_SKIP),0 1),$(SND_PAD_SKIP))
$(error SND_PAD_SKIP must be 0 or 1)
endif
$(OBJDIR)/src/game/dvd.o: GAME_CPPFLAGS += -include $(CURDIR)/platform/include/snd_pad_skip.h
ifeq ($(SND_PAD_SKIP),1)
$(OBJDIR)/src/game/dvd.o: GAME_CPPFLAGS += -DRE4DC_SND_PAD_SKIP=1
$(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_SND_PAD_SKIP=1
endif
# DOOR_PROBE=1 (lane doorpause16, 2026-10-16; diagnostic, log only, default 0 = image unchanged; needs DISC_READ_METER=1):
# where the door pause goes. platform/door_probe.cpp logs a "DOORPH:" line at each phase mark of a room change (door
# press, door demo, StageSet, the gameRoomInit steps, the first gameMainLoop frame): wall ms, game-thread GD-ROM
# blocked ms / drive calls / KB (DISC_READ_METER's counters) and CPU ms per thread class from KOS's per-thread
# accounting (main, re4-task, other, idle); at the end the files read in the window (fs_open / fs_read wraps:
# "DOORFILE:") and CPU per thread label ("DOORTHD:"). The marks are RE4DC_DOORPH(...) appended to existing source
# lines (main.cpp: the vblank spin waits, "spin=" ms; game.cpp, stage.cpp, sce_at.cpp, ui_bridge.cpp) from the forced header platform/include/door_probe.h, which
# makes them empty statements with the knob off.
DOOR_PROBE ?= 0
ifneq ($(filter $(DOOR_PROBE),0 1),$(DOOR_PROBE))
$(error DOOR_PROBE must be 0 or 1)
endif
DOOR_PROBE_GAME = $(OBJDIR)/src/game/main.o $(OBJDIR)/src/game/game.o $(OBJDIR)/src/game/stage.o $(OBJDIR)/src/game/sce_at.o $(OBJDIR)/ui_bridge.o
$(DOOR_PROBE_GAME): GAME_CPPFLAGS += -include $(CURDIR)/platform/include/door_probe.h
ifeq ($(DOOR_PROBE),1)
ifneq ($(DISC_READ_METER),1)
$(error DOOR_PROBE=1 needs DISC_READ_METER=1)
endif
ifeq ($(IO_PROBE),1)
$(error DOOR_PROBE=1 and IO_PROBE=1 wrap the same fs entry points)
endif
$(DOOR_PROBE_GAME): GAME_CPPFLAGS += -DRE4DC_DOOR_PROBE=1
$(OBJDIR)/platform/door_probe.o $(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DOOR_PROBE=1
GAME_LDFLAGS += -Wl,--wrap=fs_open -Wl,--wrap=fs_read
else
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/door_probe.o,$(PLATFORM_OBJS))
endif
else
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/dvd_read_safe.o,$(PLATFORM_OBJS))
ifeq ($(DISC_READ_METER),1)
$(error DISC_READ_METER=1 needs DVD_READ_SAFE=1 (it counts in the platform/dvd_read_safe.cpp wraps))
endif
endif
.PHONY: io-probe-force
$(OBJDIR)/io-probe.h: io-probe-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_IO_PROBE %s\n' '$(IO_PROBE)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
IO_PROBE_OBJS = $(addprefix $(OBJDIR)/platform/,dvd.o native_motion.o os.o native_ui.o io_probe.o)
$(IO_PROBE_OBJS): $(OBJDIR)/io-probe.h
$(IO_PROBE_OBJS): PLATFORM_CPPFLAGS += -include $(OBJDIR)/io-probe.h
$(OBJDIR)/ui_bridge.o: $(OBJDIR)/io-probe.h
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -include $(OBJDIR)/io-probe.h
ifeq ($(IO_PROBE),1)
# Test-only DVD hold in the source queue step (src/game/dvd.cpp; compiled out when IO_PROBE=0).
$(OBJDIR)/src/game/dvd.o: $(OBJDIR)/io-probe.h
$(OBJDIR)/src/game/dvd.o: GAME_CPPFLAGS += -include $(OBJDIR)/io-probe.h
endif
OBJS = $(NATIVE_REUSE_OBJS) $(GAME_OBJS) $(MODULE_OBJS) $(PLATFORM_OBJS) $(SDK_OBJS)
# NATIVE_MES=1 (default 0: the default image does not change): message text. mes.cpp draw() emits
# each glyph through the GX stub, which sinks it, so no cMes text (prompts, pickups, the picker,
# card and sub screen messages) was visible. With the knob each glyph is a native UI quad in the
# source draw order, textured from a 256x256 PAL4 glyph atlas (32 KiB of VRAM taken before the
# UI_VRAM budget, 64 LRU cells decoded on first use from the font's CI4 sheet). Render only.
# NATIVE_MES_CELLS=128: a 256x512 atlas (64 KiB) for pages with more than 64 distinct glyphs.
NATIVE_MES ?= 0
NATIVE_MES_CELLS ?= 64
.PHONY: native-mes-force
$(OBJDIR)/native-mes.h: native-mes-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_NATIVE_MES %s\n#define RE4DC_NATIVE_MES_CELLS %s\n' '$(NATIVE_MES)' '$(NATIVE_MES_CELLS)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/src/game/mes.o: $(OBJDIR)/native-mes.h
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/native-mes.h
$(OBJDIR)/src/game/mes.o: GAME_CPPFLAGS += -include $(OBJDIR)/native-mes.h
# D367 quality modes (design-lowmode DESIGN.md A). QUALITY=1 (default 0: the default image does
# not change) adds platform/quality.cpp (state, presets, /cd/dc/quality.txt, the RE4DCCFG record
# through re4dc_quality_cfg_load/store, in memory until the VMU layer links them; freeze at game start) and quality_picker.cpp (the once-per-boot "Graphics quality" picker at
# the first title main menu (after Start), in the game's message window: "Standard" (budget-first,
# the default) or "Original" (the faithful look). QUALITY_DEFAULT: mode without a stored record
# or file (1 = Standard, 0 = Original). QUALITY_PICKER=0: no picker. QUALITY_DEBUG=1 (test builds): X or
# L+R+A on the picker opens the per-feature menu. Every switch is render-only.
QUALITY ?= 0
QUALITY_DEFAULT ?= 1
QUALITY_PICKER ?= 1
QUALITY_DEBUG ?= 0
# QUALITY_ASSETS=1 (default 0 = previous image; needs QUALITY=1 TREE_IMPOSTOR=1 MESH_TEXTURES=1
# TEX_RESIDENT=1): in Standard mode each room entry reads native/<room>/low/index.txt
# (D367_ASSET_PIPELINE.md s16) and draws the Standard set: low/<OWNER>.re4mesh packages,
# texlow/ textures, per-mesh cull / impostor / baked-texture records, the room preload
# without the dropped keys. Original never reads low/ or texlow/.
QUALITY_ASSETS ?= 0
ifeq ($(QUALITY_ASSETS),1)
ifneq ($(QUALITY)$(TREE_IMPOSTOR)$(MESH_TEXTURES)$(TEX_RESIDENT),1111)
$(error QUALITY_ASSETS=1 requires QUALITY=1 TREE_IMPOSTOR=1 MESH_TEXTURES=1 TEX_RESIDENT=1)
endif
endif
.PHONY: quality-force
$(OBJDIR)/quality-knobs.h: quality-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_QUALITY %s\n#define RE4DC_QUALITY_DEFAULT %s\n#define RE4DC_QUALITY_PICKER %s\n#define RE4DC_QUALITY_DEBUG %s\n' '$(QUALITY)' '$(QUALITY_DEFAULT)' '$(QUALITY_PICKER)' '$(QUALITY_DEBUG)' > $@.tmp
	@printf '#define RE4DC_QUALITY_ASSETS %s\n' '$(QUALITY_ASSETS)' >> $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
QUALITY_PLATFORM = $(OBJDIR)/platform/quality.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ui.o
QUALITY_GAME = $(OBJDIR)/src/game/title.o $(OBJDIR)/ui_bridge.o $(OBJDIR)/quality_picker.o
$(QUALITY_PLATFORM) $(QUALITY_GAME): $(OBJDIR)/quality-knobs.h
$(QUALITY_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/quality-knobs.h
$(QUALITY_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/quality-knobs.h
ifeq ($(QUALITY),1)
OBJS += $(OBJDIR)/quality_picker.o
else
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/quality.o,$(PLATFORM_OBJS))
endif
ifeq ($(ROUTE_CH13),1)
OBJS += $(OBJDIR)/route_end.o
endif
$(OBJDIR)/route_end.o: route_end.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -MMD -MP -c $< -o $@
$(OBJDIR)/quality_picker.o: quality_picker.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -MMD -MP -c $< -o $@
# Route cutscenes (default off): PS2 prerecorded movies present source events
# (/cd/dc/movie/*.seq, docs/ROUTE_CUTSCENES.md). Default images carry none of it.
ROUTE_MOVIES ?= 0
# ROUTE_MOVIE_YUV=1: full-range movies go through the PVR YUV converter (0: software UYVY path).
# ROUTE_MOVIE_TEXHASH=1: verification builds log the texture FNV of pictures 0/1/30/300.
ROUTE_MOVIE_YUV ?= 1
ROUTE_MOVIE_TEXHASH ?= 0
# ROUTE_MOVIES_CH3=1 (castle lane 2026-10-15; default 0: no effect; needs ROUTE_MOVIES=1 ROUTE_CH31=1): the chapter 3
# castle events are presented by their PS2 movies (BIO4MOV.AFS -> tools/convert_route_movies.py, private dc/movie):
# r201 s00, r203 s00, r204 s00 (3-1 end), r209 s00, r20b s00 (3-2 end), r206 s00 / s10 (3-3 end) / s20 (3-4 end).
# While a room's movies are on the disc no evd is read and the swap module is read at its own size; every gameplay
# effect of the callers runs unchanged and a missing movie falls back to the source event (src/st2/*.cpp).
ROUTE_MOVIES_CH3 ?= 0
ifneq ($(ROUTE_MOVIES_CH3),0)
ifneq ($(ROUTE_MOVIES_CH3)$(ROUTE_MOVIES)$(ROUTE_CH31),111)
$(error ROUTE_MOVIES_CH3 must be 0 or 1 and needs ROUTE_MOVIES=1 ROUTE_CH31=1)
endif
ROUTE_MOVIE_GAME_CH3 = $(OBJDIR)/mod/st2_0/src/st2/r201.o $(OBJDIR)/mod/st2_0/src/st2/r203.o     $(OBJDIR)/mod/st2_1/src/st2/r204.o $(OBJDIR)/mod/st2_1/src/st2/r206.o $(OBJDIR)/mod/st2_1/src/st2/r209.o     $(OBJDIR)/mod/st2_1/src/st2/r20b.o
$(ROUTE_MOVIE_GAME_CH3): GAME_CPPFLAGS += -DRE4DC_ROUTE_MOVIES_CH3=1
endif
# ROUTE_MOVIES_CH4=1 (lane ch4found16 2026-10-16; default 0: no effect; needs ROUTE_MOVIES=1 ROUTE_CH41=1): the chapter 4
# castle events are presented by their PS2 movies (BIO4MOV.AFS -> tools/convert_route_movies.py, private dc/movie):
# r212 s00, r214 s00, r215 s00 (QTE cut 0xA, cancel clip s00c) / s01 / s02 (died demo), r227 s00 (QTE cut 0xB, cancel
# clip s00c) / s01 / s02 (died demo), r228 s00 / s01 / s02. The GameCube r227 entrance events took 2.5 MB of heap 4 at
# room entry; r212s00 r214s00 r215s00..02 r227s02 r228s02 do not pass the event texture converter. Every gameplay effect
# of the callers runs unchanged and a missing movie falls back to the source event (src/st2/*.cpp).
ROUTE_MOVIES_CH4 ?= 0
ifneq ($(ROUTE_MOVIES_CH4),0)
ifneq ($(ROUTE_MOVIES_CH4)$(ROUTE_MOVIES)$(ROUTE_CH41),111)
$(error ROUTE_MOVIES_CH4 must be 0 or 1 and needs ROUTE_MOVIES=1 ROUTE_CH41=1)
endif
ROUTE_MOVIE_GAME_CH4 = $(OBJDIR)/mod/st2_2/src/st2/r212.o $(OBJDIR)/mod/st2_2/src/st2/r214.o $(OBJDIR)/mod/st2_2/src/st2/r215.o     $(OBJDIR)/mod/st2_3/src/st2/r227.o $(OBJDIR)/mod/st2_3/src/st2/r228.o
$(ROUTE_MOVIE_GAME_CH4): GAME_CPPFLAGS += -DRE4DC_ROUTE_MOVIES_CH4=1
endif
# ROUTE_MOVIE_DIAG=1: test builds log the movie loop's per-picture timing and the failing step.
#   2/3/4 are test-only proofs of the route movie VRAM claim (platform/native_ui.cpp; 0 and 1 compile
#   them out): 2 = the movie claim's normal pass releases nothing, so only its fallback (end this
#   frame's scene unpresented, release this frame's uploads) frees the 256 KiB block; 3 = the same
#   without the fallback (the open fails: the pre-fallback outcome on a fragmented pool); 4 = the
#   movie opens inside the interrupted frame's scene, so a later open failure (heap 4 staging)
#   retires the texture with that scene open (re4dc_ui_movie_close discards it).
ROUTE_MOVIE_DIAG ?= 0
# ROUTE_QTE_FRAMES=<n>: test builds hold a route QTE cut (r104 s00 cut 0x1E) for n game frames instead of the
#   event's own (60), so a timed screenshot catches the prompt over the movie. 0 (default) = the event's.
ROUTE_QTE_FRAMES ?= 0
# MOVIE_DISC_QUIET=1 (default 0; ROUTE_MOVIES=1, sound timing only, logic STRICT): while a route movie is open the
#   AICA disc stream reader holds back stream prefills (a stream stopped or claimed then refills after the movie;
#   a playing stream keeps refilling), and a stepped movie that ran dry retries its decode every game frame.
#   r10b s20 lost 279 of 515 pictures (364 ms read) when the boss music's stop raced its close and the prefill
#   seeked the GD mid-movie, then froze at picture 520 for the rest of the QTE (terminal 4).
MOVIE_DISC_QUIET ?= 0
ifneq ($(MOVIE_DISC_QUIET),0)
$(OBJDIR)/platform/native_movie.o $(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_MOVIE_DISC_QUIET=1
endif
# D39: original cabin source events with independently qualified movie output.
# Default zero preserves prior objects/assets; exact carrier staging is a separate reviewed gate.
CABIN_SOURCE ?= 0
CABIN_HANDOFF_DIAG ?= 0
# EVENT_SWAP_RELOAD (lane ch5found16, 10-17; default 0): MemorySwap of an enemy archive against an immutable event file
# (EVENT_FILES=1) reloads the archive region from its disc file afterwards instead of needing a mutable ARAM copy
# (r310 r310s00 with em36). The in-place binds are kept as byte runs and the region's CRC is checked on the way back.
EVENT_SWAP_RELOAD ?= 0
ifneq ($(filter-out 0 1,$(EVENT_SWAP_RELOAD)),)
$(error EVENT_SWAP_RELOAD must be 0 or 1)
endif
ifeq ($(EVENT_SWAP_RELOAD),1)
ifneq ($(EVENT_FILES),1)
$(error EVENT_SWAP_RELOAD needs EVENT_FILES=1)
endif
endif
CABIN_COMPLETE_HANDOFF ?= 0
ifneq ($(filter-out 0 1,$(CABIN_COMPLETE_HANDOFF)),)
$(error CABIN_COMPLETE_HANDOFF must be 0 or 1)
endif
ifeq ($(CABIN_COMPLETE_HANDOFF),1)
ifneq ($(CABIN_SOURCE),1)
$(error CABIN_COMPLETE_HANDOFF requires CABIN_SOURCE=1)
endif
endif
ifneq ($(filter-out 0 1,$(CABIN_HANDOFF_DIAG)),)
$(error CABIN_HANDOFF_DIAG must be 0 or 1)
endif
ifeq ($(CABIN_HANDOFF_DIAG),1)
ifneq ($(CABIN_SOURCE),1)
$(error CABIN_HANDOFF_DIAG requires CABIN_SOURCE=1)
endif
endif
ifneq ($(filter-out 0 1,$(CABIN_SOURCE)),)
$(error CABIN_SOURCE must be 0 or 1)
endif
ifeq ($(CABIN_SOURCE),1)
ifneq ($(ROUTE_CH22):$(ROUTE_MOVIES):$(AICA_AUDIO):$(AICA_STREAMS):$(NATIVE_STATIC),1:1:1:1:1)
$(error CABIN_SOURCE needs ROUTE_CH22=1 ROUTE_MOVIES=1 AICA_AUDIO=1 AICA_STREAMS=1 NATIVE_STATIC=1)
endif
else
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/native_cabin.o,$(PLATFORM_OBJS))
endif
.PHONY: cabin-source-force
$(OBJDIR)/cabin-source.h: cabin-source-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_CABIN_SOURCE %s\n#define RE4DC_CABIN_HANDOFF_DIAG %s\n#define RE4DC_CABIN_COMPLETE_HANDOFF %s\n#define RE4DC_EVENT_SWAP_RELOAD %s\n' '$(CABIN_SOURCE)' '$(CABIN_HANDOFF_DIAG)' '$(CABIN_COMPLETE_HANDOFF)' '$(EVENT_SWAP_RELOAD)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
CABIN_SOURCE_PLATFORM = $(OBJDIR)/platform/native_event_file.o $(OBJDIR)/platform/native_cabin.o $(OBJDIR)/platform/native_movie.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/audio_aica.o
CABIN_SOURCE_GAME = $(OBJDIR)/src/game/datactrl.o $(OBJDIR)/src/game/dvd.o $(OBJDIR)/src/game/read.o $(OBJDIR)/src/game/event.o $(OBJDIR)/src/game/snd_str0.o $(OBJDIR)/src/game/sce_sys.o $(OBJDIR)/src/game/main_mem.o $(OBJDIR)/mod/st1_3/src/st1/r11c.o
$(CABIN_SOURCE_PLATFORM) $(CABIN_SOURCE_GAME) $(OBJDIR)/platform/native_movie_stream.o: $(OBJDIR)/cabin-source.h
$(CABIN_SOURCE_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/cabin-source.h -include platform/include/native_event_file.h
$(CABIN_SOURCE_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/cabin-source.h -include platform/include/native_event_file.h
# D38: exact full blocking r11f10/11f11 movies borrow the retained world cell.
# No resolution/audio changes, source-heap expansion or allocator fallback.
MOVIE_WORLD_ARENA ?= 0
# Bounded Chapter 1 extension: full r100s30 borrows the same retained owner.
MOVIE_WORLD_ARENA_S30 ?= 0
# guards28 (10-28): 1 = derive the borrow layout from the opened package (mesh + sidecar + LUT + gather == the captured
# extent) instead of the hard-coded package sizes, and log every refused eligible borrow (MOVIEARENA refuse ...), so a
# reconverted world can't silently stop the r100 s30 / r11f Mendez movies. 0 = the hard-coded rows (identical image).
MOVIE_LAYOUT_GUARD ?= 0
.PHONY: movie-world-arena-force
$(OBJDIR)/movie-world-arena.h: movie-world-arena-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_MOVIE_WORLD_ARENA %s\n' '$(MOVIE_WORLD_ARENA)' > $@.tmp
	@printf '#define RE4DC_MOVIE_WORLD_ARENA_S30 %s\n' '$(MOVIE_WORLD_ARENA_S30)' >> $@.tmp
	@printf '#define RE4DC_MOVIE_LAYOUT_GUARD %s\n' '$(MOVIE_LAYOUT_GUARD)' >> $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
MOVIE_WORLD_ARENA_PLATFORM = $(OBJDIR)/platform/native_movie.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ps2_world.o
MOVIE_WORLD_ARENA_GAME = $(OBJDIR)/ui_bridge.o $(OBJDIR)/route_movie_bridge.o $(OBJDIR)/src/game/main_mem.o
$(MOVIE_WORLD_ARENA_PLATFORM) $(MOVIE_WORLD_ARENA_GAME) $(OBJDIR)/platform/native_movie_stream.o: $(OBJDIR)/movie-world-arena.h
$(MOVIE_WORLD_ARENA_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/movie-world-arena.h
$(MOVIE_WORLD_ARENA_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/movie-world-arena.h
.PHONY: route-movies-force
$(OBJDIR)/route-movies.h: route-movies-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_ROUTE_MOVIES %s\n#define RE4DC_ROUTE_MOVIE_YUV %s\n#define RE4DC_ROUTE_MOVIE_TEXHASH %s\n#define RE4DC_ROUTE_MOVIE_DIAG %s\n#define RE4DC_ROUTE_QTE_FRAMES %s\n#define RE4DC_ROUTE_CH13 %s\n' '$(ROUTE_MOVIES)' '$(ROUTE_MOVIE_YUV)' '$(ROUTE_MOVIE_TEXHASH)' '$(ROUTE_MOVIE_DIAG)' '$(ROUTE_QTE_FRAMES)' '$(ROUTE_CH13)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
ROUTE_MOVIE_PLATFORM = $(OBJDIR)/platform/native_movie.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/pad.o
ROUTE_MOVIE_GAME = $(OBJDIR)/src/game/game.o $(OBJDIR)/mod/st1_0/src/st1/r100.o $(OBJDIR)/mod/st1_1/src/st1/r101.o $(OBJDIR)/mod/st1_1/src/st1/r102.o $(OBJDIR)/mod/st1_1/src/st1/r104.o $(OBJDIR)/mod/st1_1/src/st1/r105.o $(OBJDIR)/mod/st1_1/src/st1/r106.o $(OBJDIR)/mod/st1_1/src/st1/r10b.o $(OBJDIR)/route_movie_bridge.o $(ROUTE_MOVIE_GAME_CH21) $(ROUTE_MOVIE_GAME_CH22) $(ROUTE_MOVIE_GAME_CH23) $(ROUTE_MOVIE_GAME_CH3) $(ROUTE_MOVIE_GAME_ST3) $(ROUTE_MOVIE_GAME_CH4)
$(ROUTE_MOVIE_PLATFORM) $(ROUTE_MOVIE_GAME): $(OBJDIR)/route-movies.h
$(ROUTE_MOVIE_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/route-movies.h
$(ROUTE_MOVIE_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/route-movies.h
$(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -O3 -fno-exceptions -fno-rtti -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-ipa-cp-clone
ifeq ($(ROUTE_MOVIES),1)
OBJS += $(OBJDIR)/platform/native_movie_stream.o $(OBJDIR)/route_movie_bridge.o
# r100's s03/s20 are presented by their movies, not the deferred evd path.
override R100_DEFER_EVENTS := 0
# Movie cadence (one picture per two fields) needs an asynchronous present.
ifeq ($(filter 1 2,$(PVR_PIPELINE)),)
$(warning ROUTE_MOVIES=1 without PVR_PIPELINE=1/2: the blocking flip halves movie frame rate (docs/ROUTE_CUTSCENES.md))
endif
else
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/native_movie.o,$(PLATFORM_OBJS))
endif
# Isolated recompile of the pinned KOS stream (spike A5): no writes under KOS_BASE.
$(OBJDIR)/platform/native_movie_stream.o: platform/native_movie_stream.c $(OBJDIR)/route-movies.h $(KOS_BASE)/kernel/arch/dreamcast/sound/snd_stream.c
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -Os -include $(OBJDIR)/route-movies.h -include $(OBJDIR)/movie-world-arena.h -include $(OBJDIR)/cabin-source.h -I$(KOS_BASE)/kernel/arch/dreamcast/sound -I$(KOS_BASE)/kernel/arch/dreamcast/include/dc/sound -MMD -MP -c $< -o $@
$(OBJDIR)/route_movie_bridge.o: route_movie_bridge.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -MMD -MP -c $< -o $@

GAME_OPT ?= -O1
# -fpermissive: cManager<T>::arrayPush names Debug_alloc before its
# declaration (a GCC 2.95 two-phase-lookup leniency the sources rely on).
# -w: the sources carry the original's warnings by design; the platform layer
# is compiled with warnings on below.
# -I$(ROOT)/src: a few tool units #include "tools/x.cpp" by that path.
# The prelude declares the libc functions some units use without declaring.
GAME_CPPFLAGS = -std=gnu++20 -fpermissive -w $(GAME_OPT) \
	-include platform/include/re4dc_prelude.h \
	-I$(ROOT)/include -I$(ROOT)/src -Iplatform/include -DRE4DC_GAME
# STAT_ROUTINE_BYTES=1 (lane stat-bytes23 2026-10-23; default 0 = image unchanged): every remaining GameCube
# big-endian store / test of the cModel::stat routine word (STAT_BE in re4dc_prelude.h): player / partner / HUD
# tests, the r100 trap dog (em21 + em2a), El Gigante (em2b), Luis (pl14), the boat (pl0f), the bell / gatling
# objects and the later bosses. em10 / em35 keep their own GANADO_ / EM35_ROUTINE_BYTES knobs.
STAT_ROUTINE_BYTES ?= 0
ifneq ($(STAT_ROUTINE_BYTES),0)
ifneq ($(STAT_ROUTINE_BYTES),1)
$(error STAT_ROUTINE_BYTES must be 0 or 1)
endif
GAME_CPPFLAGS += -DRE4DC_STAT_ROUTINE_BYTES=1
endif
# STAT_DIAG=1 (test / QA discs only; default 0): STATDIAG log lines (player / partner routine-word tests where the
# GameCube meaning and the raw word compare disagree, the r100 trap dog and its trap's routine changes, a self test).
STAT_DIAG ?= 0
ifneq ($(STAT_DIAG),0)
GAME_CPPFLAGS += -DRE4DC_STAT_DIAG=1
endif
PLATFORM_CPPFLAGS = -std=gnu++20 -Wall -Wextra $(GAME_OPT) \
	-Iplatform/include -DRE4DC_GAME

# Immutable qualified EVD file backing; mutable swaps remain explicitly rejected.
# Keep the source reference selectable while the event path is integrated.
EVENT_FILES ?= 0
.PHONY: event-files-force
$(OBJDIR)/event-files.h: event-files-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_EVENT_FILES %s\n' '$(EVENT_FILES)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/src/game/datactrl.o: $(OBJDIR)/event-files.h
$(OBJDIR)/src/game/datactrl.o: GAME_CPPFLAGS += -include $(OBJDIR)/event-files.h
# Only the two reviewed r100 story presentations; source combat/post-event
# continuation remains in r100.cpp. Other events retain the reference path.
R100_DEFER_EVENTS ?= 0
.PHONY: r100-defer-force
$(OBJDIR)/r100-defer.h: r100-defer-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_R100_DEFER_EVENTS %s\n' '$(R100_DEFER_EVENTS)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/mod/st1_0/src/st1/r100.o: $(OBJDIR)/r100-defer.h
$(OBJDIR)/mod/st1_0/src/st1/r100.o: GAME_CPPFLAGS += -include $(OBJDIR)/r100-defer.h
SDK_CFLAGS = -w $(GAME_OPT) -Iplatform/sdk -I$(ROOT)/include
# Nothing uses C++ exceptions or RTTI; their tables are ~362 KB of image, which
# lets the 13 MiB arena request fit (D367: source heap +256 KiB, KOS +~100 KB).
# FP instruction streams are unchanged in all 1,155 FP functions (fmac pairing).
NO_EH ?= 0
ifeq ($(NO_EH),1)
NO_EH_FLAGS = -fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-threadsafe-statics
GAME_CPPFLAGS += $(NO_EH_FLAGS)
PLATFORM_CPPFLAGS += $(NO_EH_FLAGS)
SDK_CFLAGS += -fno-unwind-tables -fno-asynchronous-unwind-tables
endif
# Opt-in game-side CPU knobs and the determinism trace (default off: no effect).
include game30.mk
# Default-off Build29 distinct collision notes; all header consumers share the control.
include atchk_distinct29.mk
# BACKFACE_CONE=1 (backface.mk, lane backface-cone23): the world back-face cone is SCENERY_CONE=1 (scenery19.mk).
ifeq ($(BACKFACE_CONE),1)
override SCENERY_CONE := 1
endif
# behave18 native actor runtime preview (ENGINE_PREVIEW; default off: nothing built).
include engine_preview.mk

# D44 diagnostic only: one four-frame window after an observed r200 card exit.
# Keep the flag local to the three instrumented translation units.
# TRANSITION_GATE_DIAG (test only, lane ch3found16 2026-10-17, never in a recipe): logs which of the five pre-walk checks of
# PS2_WORLD_TRANSITION_OWNER refused (PS2SOURCE_DECLINE reason 14) and the r200 package / scroll pins against the live data.
TRANSITION_GATE_DIAG ?= 0
ifeq ($(TRANSITION_GATE_DIAG),1)
$(OBJDIR)/src/game/trans.o $(OBJDIR)/src/game/scroll.o: GAME_CPPFLAGS += -DRE4DC_TRANSITION_GATE_DIAG=1
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_TRANSITION_GATE_DIAG=1
endif
PS2_WORLD_PREFLIGHT_DIAG ?= 0
ifneq ($(filter-out 0 1,$(PS2_WORLD_PREFLIGHT_DIAG)),)
$(error PS2_WORLD_PREFLIGHT_DIAG must be 0 or 1)
endif
ifeq ($(PS2_WORLD_PREFLIGHT_DIAG),1)
ifneq ($(PS2_WORLD_SOURCE_OWNER)$(PS2_WORLD_SOURCE_TEX_PREP)$(VRAM_PAGES),111)
$(error PS2_WORLD_PREFLIGHT_DIAG needs SOURCE_OWNER=1 SOURCE_TEX_PREP=1 VRAM_PAGES=1)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PS2_WORLD_PREFLIGHT_DIAG=1
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_PREFLIGHT_DIAG=1
endif

# D46: retain only an already-resident, exact native r200 texture during source
# door fades. This does not widen the source-model owner ticket.
PS2_WORLD_TRANSITION_PIN ?= 0
ifneq ($(filter-out 0 1,$(PS2_WORLD_TRANSITION_PIN)),)
$(error PS2_WORLD_TRANSITION_PIN must be 0 or 1)
endif
ifeq ($(PS2_WORLD_TRANSITION_PIN),1)
ifneq ($(PS2_WORLD_SOURCE_OWNER)$(PS2_WORLD_SOURCE_TEX_PREP)$(VRAM_PAGES),111)
$(error PS2_WORLD_TRANSITION_PIN needs SOURCE_OWNER=1 SOURCE_TEX_PREP=1 VRAM_PAGES=1)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PS2_WORLD_TRANSITION_PIN=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_TRANSITION_PIN=1
endif

# D47: exact source callback transaction for pending/entered r200 door images.
PS2_WORLD_TRANSITION_OWNER ?= 0
ifneq ($(filter-out 0 1,$(PS2_WORLD_TRANSITION_OWNER)),)
$(error PS2_WORLD_TRANSITION_OWNER must be 0 or 1)
endif
ifeq ($(PS2_WORLD_TRANSITION_OWNER),1)
ifneq ($(PS2_WORLD_SOURCE_OWNER)$(PS2_WORLD_SOURCE_TEX_PREP)$(PVR_STREAM),111)
$(error PS2_WORLD_TRANSITION_OWNER needs SOURCE_OWNER=1 SOURCE_TEX_PREP=1 PVR_STREAM=1)
endif
ifneq ($(PS2_WORLD_TRANSITION_PIN),0)
$(error PS2_WORLD_TRANSITION_OWNER requires TRANSITION_PIN=0)
endif
$(OBJDIR)/src/game/trans.o $(OBJDIR)/src/game/trans_ot.o $(OBJDIR)/src/game/scroll.o: GAME_CPPFLAGS += -DRE4DC_PS2_WORLD_TRANSITION_OWNER=1
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ps2_world.o: PLATFORM_CPPFLAGS += -DRE4DC_PS2_WORLD_TRANSITION_OWNER=1
endif

KOS_GCCVER_MIN = 12.0.0
include $(KOS_BASE)/Makefile.rules

.PHONY: all clean census

all: $(TARGET)

$(OBJDIR)/%.o: $(ROOT)/%.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -MMD -MP -c $< -o $@

$(OBJDIR)/platform/%.o: platform/%.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -MMD -MP -c $< -o $@

platform/sdk/gen/%.c: $(ROOT)/src/lib/%.c platform/sdk/strip_cw_asm.py
	@mkdir -p $(dir $@)
	python3 platform/sdk/strip_cw_asm.py $< $@

$(OBJDIR)/sdk/%.o: platform/sdk/gen/%.c
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) $(SDK_CFLAGS) -MMD -MP -c $< -o $@

-include $(OBJS:.o=.d) $(CENSUS_OBJS:.o=.d)

.PHONY: module-args-force
$(OBJDIR)/module-args.txt: module-args-force
	@mkdir -p $(dir $@)
	@echo '$(MODULE_ARGS)' > $@.tmp; cmp -s $@.tmp $@ || mv $@.tmp $@; rm -f $@.tmp
$(MODULES_MK): Makefile tools/gen_modules.py $(ROOT)/config/G4BE08/modules.py $(ROOT)/config/G4BE08/modules/*/splits.txt $(ROOT)/src/st1/st1.cpp $(OBJDIR)/module-args.txt
	@mkdir -p $(OBJDIR)
	python3 tools/gen_modules.py $(ROOT)/config/G4BE08/modules $(ROOT) $(OBJDIR) $@ $(MODULE_ARGS)
include $(MODULES_MK)
# D367 W10: platform/gdrom_mount.cpp wraps cdrom_read_toc so /cd mounts track 3
# of a GD-ROM (a GDI on GDEMU, tools/d367/mkgdi.sh). CD-R images are unaffected.
GAME_LDFLAGS += -Wl,--wrap=cdrom_read_toc

# LINK_TIGHT=1 (default 1 with ROUTE_CH21=1, else 0: no effect): link with a copy of KOS's shlelf.xc without its ten
# empty icache-aligned .sub0...sub9 sections. Nothing in the image uses them, but their ALIGN(0x2000) still moves
# .init and everything after it (rodata, data, bss, so _end and the KOS heap) to the next 8 KiB boundary: 0..8 KiB
# of padding, and a jump of 8 KiB whenever .text crosses a boundary (the r119 lane's s30 heap_before cliff). With
# the padding gone, image growth costs heap linearly.
# LINK_OVL_HELPERS=1 (default 1 with ROUTE_CH21=1, else 0: no effect): image code that only one room overlay
# (ROUTE_OVL: pl0f, em2f, em22, em2b) reaches moves into that overlay (tools/link.sh, tools/ovl_helpers.py: the
# .text sections a link without that overlay drops); obj/ovlh/moves.tsv lists them. The sub screen overlay is
# left alone.
ifeq ($(ROUTE_CH21),1)
LINK_TIGHT ?= 1
LINK_OVL_HELPERS ?= 1
else
LINK_TIGHT ?= 0
LINK_OVL_HELPERS ?= 0
endif
LINK_ENV = RE4DC_LINK_OVL_HELPERS=$(LINK_OVL_HELPERS)
ifeq ($(ROUTE_CH21),1)
# pl11 (Ashley, r117 on) reaches the DOL partner class cSubChar (32 KB of code the image otherwise drops): its code
# moves with its vtable and the other read-only data only pl11 reaches (tools/ovl_helpers.py RE4DC_OVL_HELPERS_RO).
LINK_ENV += RE4DC_OVL_HELPERS_RO=.ovl_pl11
endif
ifeq ($(LINK_TIGHT),1)
LINK_KOS_SCRIPT = $(KOS_BASE)/utils/ldscripts/shlelf.xc
ifeq ($(findstring -T$(LINK_KOS_SCRIPT),$(KOS_LDFLAGS)),)
$(error LINK_TIGHT=1: KOS_LDFLAGS does not name -T$(LINK_KOS_SCRIPT))
endif
$(OBJDIR)/shlelf-tight.ld: $(LINK_KOS_SCRIPT) Makefile
	@mkdir -p $(dir $@)
	awk '/Custom sections, aligned to the icache size/{skip=1} !skip{print} skip && /sub9 is bigger than icache size/{skip=0}' $< > $@.tmp
	@! grep -q 'sub[0-9]\|ICACHE_SIZE)' $@.tmp && grep -q '^  \.init' $@.tmp || { echo 'LINK_TIGHT: unexpected shlelf.xc layout' >&2; exit 1; }
	mv $@.tmp $@
$(TARGET): $(OBJDIR)/shlelf-tight.ld
LINK_ENV += KOS_LDFLAGS='$(subst -T$(LINK_KOS_SCRIPT),-T$(abspath $(OBJDIR))/shlelf-tight.ld,$(KOS_LDFLAGS))'
endif
# MOVIE_FENCE_RETRY=1 (timing only; default 1 with ROUTE_CH21=1, else 0: no effect): a route movie retries a
# not-ready render fence (up to 3 more times, logged) before a picture upload instead of failing the movie. One
# LINK_TIGHT image layout ended r119 s30 at its first picture that way (terminal=3, uploaded=0).
ifeq ($(ROUTE_CH21),1)
MOVIE_FENCE_RETRY ?= 1
else
MOVIE_FENCE_RETRY ?= 0
endif
ifeq ($(MOVIE_FENCE_RETRY),1)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_MOVIE_FENCE_RETRY=1
endif
# OVL_ID_GUARD=1 (test 15, robustness): each route overlay names the main image it was linked against. gen_overlay.py
# writes header words 14/15 = FNV-1a of the main image's .text and the .text byte count (RE4DC_OVL_ID=1 in link.sh's
# environment); routeOverlayLoad (platform/modules.cpp) hashes its own .text once and stops with re4dc_missing("route
# overlay built for another program") on a mismatch, instead of relocating another build's overlay into this image (the
# r118 fixture fault, 10-15). swap-program.py copies the overlays with the program, so release discs always match.
# Default 0: the image and the overlays are byte-identical.
OVL_ID_GUARD ?= 0
ifeq ($(filter $(OVL_ID_GUARD),0 1),)
$(error OVL_ID_GUARD must be 0 or 1)
endif
ifeq ($(OVL_ID_GUARD),1)
LINK_ENV += RE4DC_OVL_ID=1
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_OVL_ID_GUARD=1
endif

$(TARGET): $(KOS_BASE)/lib/$(KOS_ARCH)/libkallisti.a $(OBJS) $(GAME30_LINK_INPUTS) tools/link.sh tools/gen_aliases.py tools/gen_missing.py platform/aliases-manual.ld
	@if [ "$(PVR_STREAM)" = 1 ]; then test "$$($(KOS_CC_BASE)/bin/$(KOS_CC_PREFIX)-nm -g --defined-only $(KOS_BASE)/lib/$(KOS_ARCH)/libkallisti.a | grep -Ec ' T _pvr_(set_manual_flip|resolve_frame)$$')" -eq 2 || { echo 'PVR_STREAM requires the pinned manual-flip KOS patch' >&2; exit 1; }; fi
	$(LINK_ENV) GAME_LDFLAGS='$(GAME_LDFLAGS)' bash tools/link.sh $(TARGET) "$(GAME_OPT)" $(OBJS) $(GAME30_LINK_INPUTS)

# Undefined-symbol inventory over every gameplay unit, REL modules included.
census: $(CENSUS_OBJS) $(PLATFORM_OBJS) $(SDK_OBJS)
	@kos-c++ $(GAME_OPT) -o /dev/null $(CENSUS_OBJS) $(PLATFORM_OBJS) $(SDK_OBJS) 2>&1 \
		| grep -o "undefined reference to \`[^']*'" \
		| sed "s/undefined reference to \`//; s/'$$//" \
		| sort | uniq -c | sort -rn > census.txt; \
	echo "undefined symbols: $$(wc -l < census.txt) (census.txt)"

clean:
	rm -rf $(OBJDIR) $(TARGET) census.txt platform/sdk/gen

# Existing native ownership/read/upload implementations; no second texture backend.
$(OBJDIR)/native-reuse/%.o: ../room/%.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -MMD -MP -c $< -o $@
$(OBJDIR)/ui_bridge.o: ui_bridge.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -MMD -MP -c $< -o $@

$(OBJDIR)/motion_bridge.o: motion_bridge.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -MMD -MP -c $< -o $@

$(OBJDIR)/model_bridge.o: model_bridge.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -MMD -MP -c $< -o $@

$(OBJDIR)/model_asset_bridge.o: model_asset_bridge.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -MMD -MP -c $< -o $@

# Select the full source reference by default. A compact core candidate must
# match its report; the source DVD queue rejects oversized input before copying.
CORE_RESIDENT_BYTES ?= 0x234000
OPTION_RESIDENT_BYTES ?= 0x40000
PLAYER_RESIDENT_BYTES ?= 0x118000
WEAPON_RESIDENT_BYTES ?= 0x70000
# Bytes of the fixed 13 MiB source arena left to the KOS heap instead. The KOS
# heap funds native code/staging and had only a few KiB spare at D362; the
# native static candidate's code needs this. Zero keeps the reference layout.
# PC_SAMPLER=1 adds its ring plus 4 KiB of code slack (PC_SAMPLER_KOS_BYTES
# below) so the sampler's .bss/.text never comes out of the KOS heap.
ARENA_KOS_BYTES ?= $(shell expr $(if $(filter 1,$(NATIVE_STATIC)),32768,0) + $(PC_SAMPLER_KOS_BYTES))
# ARENA_FIT=1 (default 0): if the full arena does not fit under the KOS break limit (image too
# large), take the largest that does, leaving ARENA_FIT_KOS_BYTES to KOS, instead of falling back
# a whole 256 KiB step (which heap 4, the arena's top, loses). Each image byte then costs heap 4
# one byte. The PC sampler's ring is .bss (part of the image), so it needs no extra reserve here.
ARENA_FIT ?= 0
ARENA_FIT_KOS_BYTES ?= 131072
# The source's sound region (SND_DATA_TOP, 512 KiB on the GameCube; the arena's bottom). SndInit
# uses ~366 KiB of it with the route's bgm/bio4str.hed and etc/memcard.das (boot log "sound region
# used"); SOUND_REGION_BYTES=0x60000 gives the unused 128 KiB to heap 4. Too small exits at boot.
SOUND_REGION_BYTES ?= 0x80000
# IMAGE_PAD_BYTES=N (default 0: no effect): N bytes of .bss (platform/mem.cpp re4dc_image_pad) so _end, and with it the
# KOS break, the arena and heap 4, start where a reference image's do. The game's own spawn checks read heap-4 free bytes
# (em10 "alloc[..]:free[..]", the texture keep), so with ARENA_FIT a 4 KiB step of heap 4 changes the logic (the combo
# build: UI_OS made the knobs-on image 3,680 bytes smaller, heap 4 +4 KiB, one more r100 Ganado at frame 661). A test
# build pads by the control's _end minus its own so the trace stays STRICT. Multiple of 32.
IMAGE_PAD_BYTES ?= 0
.PHONY: core-budget-force
$(OBJDIR)/core-budget.h: core-budget-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_CORE_RESIDENT_BYTES %s\n' '$(CORE_RESIDENT_BYTES)' > $@.tmp
	@printf '#define RE4DC_OPTION_RESIDENT_BYTES %s\n' '$(OPTION_RESIDENT_BYTES)' >> $@.tmp
	@printf '#define RE4DC_PLAYER_RESIDENT_BYTES %s\n#define RE4DC_WEAPON_RESIDENT_BYTES %s\n' '$(PLAYER_RESIDENT_BYTES)' '$(WEAPON_RESIDENT_BYTES)' >> $@.tmp
	@printf '#define RE4DC_ARENA_KOS_BYTES %s\n' '$(ARENA_KOS_BYTES)' >> $@.tmp
	@printf '#define RE4DC_ARENA_FIT %s\n#define RE4DC_ARENA_FIT_KOS_BYTES %s\n' '$(ARENA_FIT)' '$(ARENA_FIT_KOS_BYTES)' >> $@.tmp
	@printf '#define RE4DC_SOUND_REGION_BYTES %s\n' '$(SOUND_REGION_BYTES)' >> $@.tmp
	@printf '#define RE4DC_IMAGE_PAD_BYTES %s\n' '$(IMAGE_PAD_BYTES)' >> $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/mem.o: $(OBJDIR)/core-budget.h
$(OBJDIR)/platform/mem.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/core-budget.h

# Opt-in backing policy; logical source capacity and cParts layout are unchanged.
PARTS_DEMAND ?= 0
MODELINFO_DEMAND ?= 0
OBJECT_DEMAND ?= 0
ENEMY_DEMAND ?= 0
# HEAP4_PARTS_RESERVE=1 (Phase 2 step 0, default 0; needs PARTS_DEMAND=1): the GameCube allocates the room's whole
# cParts array up front, so a model's parts never fail for heap 4 there; the demand pool's runs come from heap 4 and
# failed at H2 frame 660 (two r100 em10 spawns, e 41 instead of the GameCube's 43) whenever heap 4 was a few KB short.
# In room HEAP4_PARTS_RESERVE_ROOM (stage << 8 | room, default 0x100) the parts pool takes a slab of
# HEAP4_PARTS_RESERVE_BYTES (default 73728: two em10, 2 x 30 runs, 63,808 B with cell headers, + slack) from heap 4 at
# room init; a parts run that heap 4 cannot give (after the dead-run reclaim) comes from the slab. Paid from what the
# PS2_OBJECTS r100 dar frees (315,712 B): without that dar the slab takes the r100 s30 movie's heap.
HEAP4_PARTS_RESERVE ?= 0
HEAP4_PARTS_RESERVE_ROOM ?= 0x100
HEAP4_PARTS_RESERVE_BYTES ?= 73728
# STAGE_OVL=1 (lane ch3found16 2026-10-16, default 0: no effect; needs ROUTE_OVL via ROUTE_CH13=1): every linked stage module
#   (st1_0..st1_3, st2_0..st2_3, st4_0) becomes a room overlay (/cd/dc/<st>.ovl, platform/modules.cpp stage slots): read into
#   heap 3 beside the room REL when linkRelData links it, kept over stopRelData / restartRelData, dropped with heap 3 at the next relink. Only the
#   current stage module is resident; the others' bytes leave the image (heap 4 starts above heap 3).
STAGE_OVL ?= 0
ifneq ($(STAGE_OVL),0)
ifneq ($(STAGE_OVL),1)
$(error STAGE_OVL must be 0 or 1)
endif
STAGE_OVL_NAMES := $(sort $(filter st1_0 st1_1 st1_2 st1_3 st2_0 st2_1 st2_2 st2_3 st4_0 st3_0 st3_1 st3_2 st3_3,$(MODULES)))
MODULES := $(filter-out $(STAGE_OVL_NAMES),$(MODULES)) $(addsuffix :ovl,$(STAGE_OVL_NAMES))
export RE4DC_LINK_OVERLAY += $(addprefix .ovl_,$(STAGE_OVL_NAMES))
export RE4DC_OVL_HELPERS_SAFE += $(addprefix .ovl_,$(STAGE_OVL_NAMES))
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_STAGE_OVL=1
# The st1_1 / st1_3 room code keeps its debug-window menu (cDbgWindow, src/Tools/db_toolbase.cpp: only the Sscrn module
# links a private copy); as a whole kept overlay it now references it, so the image gets the one translation unit.
GAME_SRCS += $(ROOT)/src/Tools/db_toolbase.cpp
$(TARGET): $(OBJDIR)/src/Tools/db_toolbase.o
endif
STAGE_OVL_AUDITED_MODULES = $(if $(filter 1,$(STAGE_OVL)),st1_0:ovl st1_1:ovl st1_2:ovl st1_3:ovl st2_0:ovl st2_1:ovl st2_2:ovl st2_3:ovl st4_0:ovl)
# Direct-slot consumers reviewed for this module set. Audit any newly linked
# module before enabling sparse enemy backing; census/reference remain usable.
# CH23 em3b/em35: guarded default-initialization and sparse scans reviewed; stage st2_0 already audited.
CH23_AUDITED_MODULES = $(if $(filter 1,$(ROUTE_CH23)),em3b:ovl em35:ovl em16)
# Luis preserves its archive pointers and both manager scans use workAt (CH22 guarded adapter).
CH22_AUDITED_MODULES = $(if $(filter 1,$(ROUTE_CH22)),pl14:ovl)
# CH31 (castle lane): st2_1 / em1a / em1b / em14 pass the discover lint (slot-math in r206.cpp and the em1a / em1b /
# em14 _set.cpp value-init rewritten by assets.sh discover --fix); no other direct-slot consumer.
CH31_AUDITED_MODULES = $(if $(filter 1,$(ROUTE_CH31)),st2_1 em1a em1b em14)
# CH32 (castle lane): em2d / em25 / em19 / em3c after assets.sh discover --fix (em2d 4 + em3c 3 slot-math sites,
# value-init in all four); discover reports no other lint for r205 r20a r20c r20f r20d r20e.
CH32_AUDITED_MODULES = $(if $(filter 1,$(ROUTE_CH32)),em2d:ovl em25:ovl em19 em3c:ovl)
CH41_AUDITED_MODULES = $(if $(filter 1,$(ROUTE_CH41)),em1c st2_3 em2c:ovl)
BOSS4_AUDITED_MODULES = $(if $(filter 1,$(ROUTE_BOSS4)),$(if $(filter 1,$(ROUTE_CH41)),,st2_3 em2c:ovl) em38:ovl)
# CH3 st3_0..st3_3 / em1d / em1e: discover --fix value-init and slot-math traps rewritten; em3b as CH23.
CH3_AUDITED_MODULES = $(if $(filter 1,$(ROUTE_CH3)),$(if $(filter 1,$(STAGE_OVL)),st3_0:ovl st3_1:ovl st3_2:ovl st3_3:ovl,st3_0 st3_1 st3_2 st3_3) em1d:ovl em1e:ovl em25:ovl em3b:ovl em36:ovl em1f:ovl em39:ovl em3a:ovl em32:ovl em3d:ovl)
ifeq ($(ENEMY_DEMAND),1)
ifneq ($(filter-out st1_0 st1_1 st1_2 st1_3 wep02 em12 em23 em15 em26 em28 em21 em2a em29 em2e em13 em27 st2_0 st4_0 pl11 st2_2 em1f em18 em17 em24 pl0f em2f pl0f:ovl em2f:ovl em22:ovl em2b:ovl pl11:ovl em11 wep01 wep04 wep04:ovl wep05 wep07 wep09 wep11 wep13 wep19 $(WEP27_AUDITED_MODULES) $(CH23_AUDITED_MODULES) $(CH22_AUDITED_MODULES) $(CH31_AUDITED_MODULES) $(CH32_AUDITED_MODULES) $(CH41_AUDITED_MODULES) $(BOSS4_AUDITED_MODULES) $(STAGE_OVL_AUDITED_MODULES) $(CH3_AUDITED_MODULES),$(MODULES)),)
$(error ENEMY_DEMAND requires a direct-slot consumer audit for the selected MODULES)
endif
endif
.PHONY: parts-budget-force
$(OBJDIR)/parts-budget.h: parts-budget-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_PARTS_DEMAND %s\n' '$(PARTS_DEMAND)' > $@.tmp
	@printf '#define RE4DC_MODELINFO_DEMAND %s\n' '$(MODELINFO_DEMAND)' >> $@.tmp
	@printf '#define RE4DC_OBJECT_DEMAND %s\n' '$(OBJECT_DEMAND)' >> $@.tmp
	@printf '#define RE4DC_ENEMY_DEMAND %s\n' '$(ENEMY_DEMAND)' >> $@.tmp
	@printf '#define RE4DC_HEAP4_PARTS_RESERVE %s\n#define RE4DC_HEAP4_PARTS_RESERVE_ROOM %s\n#define RE4DC_HEAP4_PARTS_RESERVE_BYTES %s\n' '$(HEAP4_PARTS_RESERVE)' '$(HEAP4_PARTS_RESERVE_ROOM)' '$(HEAP4_PARTS_RESERVE_BYTES)' >> $@.tmp
	@cmp -s $@.tmp $@ || cp $@.tmp $@
	@rm -f $@.tmp
# SS_FREEZE_RESERVE=1 (test 12 radio-call HALT, default 0 = image unchanged): parts_bridge.cpp serves the sub screen
# pool freeze copies and the stand-in work from a static SS_FREEZE_RESERVE_BYTES block (bump, reset at thaw, malloc
# fallback) instead of the KOS heap. +SS_FREEZE_RESERVE_BYTES of .bss = that much less heap 4 under ARENA_FIT.
SS_FREEZE_RESERVE ?= 0
SS_FREEZE_RESERVE_BYTES ?= 16384
ifneq ($(filter $(SS_FREEZE_RESERVE),0 1),$(SS_FREEZE_RESERVE))
$(error SS_FREEZE_RESERVE must be 0 or 1)
endif
ifeq ($(SS_FREEZE_RESERVE),1)
$(OBJDIR)/parts_bridge.o: GAME_CPPFLAGS += -DRE4DC_SS_FREEZE_RESERVE=1 -DRE4DC_SS_FREEZE_RESERVE_BYTES=$(SS_FREEZE_RESERVE_BYTES)
endif
$(OBJDIR)/parts_bridge.o: parts_bridge.cpp $(OBJDIR)/parts-budget.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -include $(OBJDIR)/parts-budget.h -MMD -MP -c $< -o $@

# Selectable serial native submission. The original KOS/reference stays usable.
# Only the existing frame owner needs this macro; source end-frame is neutral.
PVR_STREAM ?= 0
.PHONY: pvr-stream-force
$(OBJDIR)/pvr-stream.h: pvr-stream-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_PVR_STREAM %s\n' '$(PVR_STREAM)' > $@.tmp
	@cmp -s $@.tmp $@ || cp $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_ui.o: $(OBJDIR)/pvr-stream.h
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/pvr-stream.h

# D367 frame pipeline (all default off). PVR_FAST_WAKE: reschedule the PVR
# render-done/vblank waiter at once instead of on the next 10 ms tick.
# PVR_PIPELINE (implies FAST_WAKE): resolve/present the finished scene on a
# presenter thread while the next frame runs; fenced before the next scene
# and before any VRAM free/upload. PVR_PIPELINE=2: no presenter thread;
# the decision is applied by the render-done IRQ and flipped in the vblank IRQ
# (needs the KOS async-present patch; with TA_DOUBLEBUF=1 TA input of the next
# frame also overlaps the render). TA_DIRECT: store-queue direct submission
# API for emitters (native_model.h). BRIDGE_LEAN: libcall-free translucent
# view words and borrowed GX lighting per part.
# Hardware (TA/VRAM): TA_VERTBUF_KB per-bank vertex (parameter) buffer,
# TA_DOUBLEBUF, TA_OPB_BINS (16|32 words, OP/TR), TA_OPB_OVERFLOW; defaults
# are the current 1024/0/16/3. TA_GUARD=1: adaptive part budget + overflow
# detection/logging; =2 also never presents an overflowed scene.
# PERF_HUD=1: on-screen frame/CPU/render/wait/TA bars for console tests.
# UI_VRAM=1: native texture cache budget from the actual PVR pool (minus
# UI_VRAM_RESERVE_KB), LRU eviction/fragmentation retry/fail-fast, and 2 KiB
# page placement of VQ codebooks and page-sized textures (texture_package).
# UI_HANDLES=1: direct texture handles; a source image resolves to its cache
# entry once, later draws skip the image_key()/load() scans and hashing.
# UI_HEADERS=1: UI/HUD quad PVR headers compiled once per texture entry and blend.
# TEX_RESIDENT=1: no runtime payload CRC (verified at staging; TEX_PAYLOAD_CRC=1
# restores it), identity sets preloaded at room entry, TEX_SLOTS cache entries (128),
# absent packages remembered and never evict a resident texture.
# TEX_SLOTS=n: texture cache entries (default 192). Above 254 the COPY_LEAN entry hints widen to 16 bits
# (the default image is unchanged). The play recipe (build-r21.sh) uses 448 with EFFECT_ROOM=7: the r101
# fight has ~430-520 unique in-room keys and 192 recycles a slot on every new one (~57 KB .data, 8 KB .bss).
# TEX_KEEP=1 (door load U1, design-doorload): room retirement keeps texture entries resident as
# the oldest (evictable) instead of closing them; the next room's preload finds shared and
# re-entered textures resident and load() evicts the rest LRU. Render-side only.
PVR_FAST_WAKE ?= 0
PVR_PIPELINE ?= 0
TA_DIRECT ?= 0
BRIDGE_LEAN ?= 0
TA_VERTBUF_KB ?= 1024
TA_DOUBLEBUF ?= 0
TA_OPB_BINS ?= 16
TA_OPB_OVERFLOW ?= 3
TA_GUARD ?= 0
PERF_HUD ?= 0
UI_VRAM ?= 0
UI_VRAM_RESERVE_KB ?= 64
# UI_FRAG_LATCH=1: a texture refused for fragmentation is not retried (and nothing is evicted for it)
# for 120 frames or until the next room preload (the r101 scope-view evict/reload lockup).
# UI_OVERLAY_SLAB_KB=n: an n KiB contiguous block held from init for a large overlay that finds no
# contiguous block in play (taken before anything is evicted, returned when it closes). Needs TEX_RESIDENT.
UI_FRAG_LATCH ?= 0
# UI_FRAG_RESERVE=1 (needs UI_FRAG_LATCH=1, TEX_RESIDENT=1, MOVIE_WINDOW=1; default 0): a texture refused for
# fragmentation while every resident upload is used by the frame gets its block reserved at the next frame start
# (previous render fenced, the cheapest window of unpinned uploads released, then held), and the block is handed
# to that texture when the scene asks for it again. Was: refused to the end of the room (r11b 7506e95f after the
# chapter end: 15 refusals, 2.2 MB free, largest hole ~508 KiB; r118 em22 after r119). Render only.
# PT_BLEND_FIX=1: alpha blending for PS2 world / impostor punch-through headers.
# Hardware candidate: alpha-zero texels must preserve the destination. Default 0 retains old headers.
PT_BLEND_FIX ?= 0
UI_FRAG_RESERVE ?= 0
ifeq ($(UI_FRAG_RESERVE),1)
ifneq ($(UI_FRAG_LATCH)$(TEX_RESIDENT)$(MOVIE_WINDOW),111)
$(error UI_FRAG_RESERVE needs UI_FRAG_LATCH=1 TEX_RESIDENT=1 MOVIE_WINDOW=1)
endif
endif
UI_OVERLAY_SLAB_KB ?= 0
# UI_FRAG_WINDOW=1|2 (t11 lane vr, render only, default 0; needs UI_VRAM=1 UI_FRAG_LATCH=1 TEX_RESIDENT=1 MOVIE_WINDOW=1):
# a texture upload refused for fragmentation first releases the cheapest page-aligned window of uploads idle for 30
# frames or more (movie_window_release: one hole of the size) instead of evicting least recently used uploads one by
# one until a hole appears (r105 results 495x150: 7 retries evicted everything evictable, 1.36 MB free and no 256 KiB
# hole; r119: 410 retries, ~2,000 reloads). With no such window, the old LRU retry runs. (A window of recently drawn
# uploads was reloaded the next frame and failed again: r101 bell fight effect textures, 2.4x the knob-off loads,
# vr-bell-v4.) =2 also: when the LRU retry finds no hole either and the upload is at least 128 KiB (the hole is
# blocked by uploads this frame already took: its draws, or the room preload's picks), the cheapest window including
# this frame's uploads is released (close_entry waits for the render in flight, as every eviction does), the texture
# uploads now, and this frame's scene is closed unrendered at its present: the previous picture stays on screen one
# more frame. The rest of the frame draws as usual (released uploads reload on first sight; no model part is refused,
# so no actor falls back to its source model in that frame; an earlier version aborted the stream and Leon fell back
# in the unshown frame, LEONGC FAIL vr-ch12-v2). At most once per 120 frames; otherwise the latch.
# Was: the texture was refused for that frame (texchk FAIL, "no contiguous block ... latched") and UI_FRAG_RESERVE
# handed it a block one frame later (r105 results picture; Leon's 512x512 body at the r105 / r10b preloads, where
# LEON-GC showed the source model for that frame).
# =3 (test 13 RC, 10-15): =1 only for uploads of at least 128 KiB (kFragDropBytes; the r105 results pictures need 256
# KiB); smaller refused uploads keep the LRU retry. =1 in the r100 s20 fight released windows of effect textures for
# 8..89 KiB uploads and the thrash guard dropped 11 effect sprites (H2, guard_p 0 -> 11). No frame drop (that is =2).
UI_FRAG_WINDOW ?= 0
# TEX_REF_SELFKEY=1 (t11 lane vr, render only, default 0): a texture descriptor whose pixels are an R4NREF record (the
# native package reference a .drs/.dat keeps in place of the texels: magic, crc, fnv, width, height, format) that no
# registered identity table covers takes the record's own key instead of a hash of the record bytes. Was: the r101 bell
# fight after a sub screen (vr-bell-on, frame 7026 on): an em12/em13/em15 128x128 CMPR record at 0x8cd0d760 hashed to a
# key that changes per build (8e66a119-a8c9b754 here, 926d9ee7-cbd1c81a in test 10), "open failed", ~30 texchk fails a
# frame until the room ends. Its own key 51f07c2d-e1b0ac5d is in tex.pak. Non-indexed records only; the width, height
# and format must equal the descriptor's.
TEX_REF_SELFKEY ?= 0
ifneq ($(filter-out 0 1,$(TEX_REF_SELFKEY)),)
$(error TEX_REF_SELFKEY must be 0 or 1)
endif
ifneq ($(filter-out 0 1 2 3,$(UI_FRAG_WINDOW)),)
$(error UI_FRAG_WINDOW must be 0, 1, 2 or 3)
endif
ifneq ($(UI_FRAG_WINDOW),0)
ifneq ($(UI_VRAM)$(UI_FRAG_LATCH)$(TEX_RESIDENT)$(MOVIE_WINDOW),1111)
$(error UI_FRAG_WINDOW needs UI_VRAM=1 UI_FRAG_LATCH=1 TEX_RESIDENT=1 MOVIE_WINDOW=1)
endif
endif
# TEX_CHECK=1|2 (test only, default 0 = play image unchanged): texture presence check (native_ui.cpp texchk::, lane
# texchk). Logs every failed / refused texture lookup and any change of a resident texture's metadata or VRAM sample
# ("texchk:" lines; gate tools/d367/texchk/texchk.sh). 2 also fills free texture RAM with magenta (with VRAM_PAGES=1).
TEX_CHECK ?= 0
ifneq ($(filter-out 0 1 2,$(TEX_CHECK)),)
$(error TEX_CHECK must be 0, 1 or 2)
endif
ifeq ($(TEX_CHECK),2)
$(OBJDIR)/platform/vram_pages.o: PLATFORM_CPPFLAGS += -DRE4DC_TEX_CHECK=2
endif
ifneq ($(TEX_CHECK),0)
$(OBJDIR)/platform/native_lake.o: PLATFORM_CPPFLAGS += -DRE4DC_TEX_CHECK=$(TEX_CHECK)
endif
# MOVIE_WINDOW=1 (needs VRAM_PAGES=1 and TEX_RESIDENT=1): a route movie's VRAM claim releases the cheapest
# page-aligned window of room textures instead of LRU uploads until a hole appears (r100 s44: 0.5-1.1 MB and
# 160-240 reloads per movie), and the movie texture is only the picture's rows (288x192: 192 KiB, not 256).
# A held 256 KiB block (tried 2026-10-02) fixed the bridge but cost the r101 fight 80% -> 50% game speed.
MOVIE_WINDOW ?= 0
# VRAM_PAGES=1: platform/vram_pages.cpp replaces KOS's weak pvr_mem_* (dlmalloc, in-VRAM block
# headers) with a best-fit allocator whose bookkeeping is in main RAM; >= 2 KiB blocks start on a
# 2 KiB page and smaller ones never straddle one, so UI_VRAM's VQ page placement no longer pads
# each texture by 2 KiB (r100: ~160 KB of texture RAM). VRAM_CENSUS=1 (test only): texture RAM
# census (blocks, free extents, largest, size histogram) every 120 frames and after each preload.
VRAM_PAGES ?= 0
VRAM_CENSUS ?= 0
# VRAM_PAGES_VQ_ONLY=1 (lane vram101 2026-10-17, render only, default 0; needs VRAM_PAGES=1 UI_VRAM=1): the page allocator
#   (platform/vram_pages.cpp) starts a texture of more than one 2 KiB page on a page boundary only when it is VQ (the
#   codebook must sit on a page). A larger twiddled / palettised texture needs no page (texture_package.cpp
#   allocate_texture accepts it anywhere), but was page-aligned anyway: a PAL4 128x128 package is 8,192 texels + its
#   32-byte palette = 8,224 B, so the next texture of a page or more skipped 2,016 B. r101 holds 118 of them: about
#   230 KB of 2 KB holes: a preload upload found no contiguous block, the retry evicted 22 pictures, no free block over
#   10 KB (largest 10,368 B; the bell gate then loaded 7 pictures in play). Placement only: the same textures, bytes and
#   draws. Doc: VRAM101-20261017.md (lane notes).
VRAM_PAGES_VQ_ONLY ?= 0
# VRAM_ROOM_ARENA=1 (lane mipmap22 2026-10-22, render only, default 0 = image unchanged; needs VRAM_PAGES=1, UI_VRAM=1
# and ROOM_CHANGE_EVICT): two-ended texture RAM. Core keys, the glyph atlas and the overlay slab fill from the top;
# room textures from the bottom (first fit); dynamic allocations (movie, door, lake) keep best fit in between. At a
# room change every unpinned, non-core texture of the old room closes (the listed keys of the new room are pinned),
# so the new room's preload fills one hole-free region (r101 -> r100 x3 had 14 KB largest blocks and 82 evictions).
VRAM_ROOM_ARENA ?= 0
# TEX_ARENA_CURRENT_KEY=1 (console regression fix, default 0): classify a texture
# by its incoming key, not the previous occupant of its cache slot. Requires the
# room arena; also corrects the optional arena upload ring's texture identity.
TEX_ARENA_CURRENT_KEY ?= 0
# TEX_FINAL_REFUSAL_LOG=1 (diagnostic, default 0): one TEX-REFUSE line for every
# final load() refusal, including early guards, with incoming key (kv=0 when no
# key is available), reason, room/frame and free/largest VRAM. Successful retries
# are not refusals. Independent of the fix for matching A/B diagnostics; this
# can produce many lines and is intended for short console reproduction runs.
TEX_FINAL_REFUSAL_LOG ?= 0
ifneq ($(words $(TEX_ARENA_CURRENT_KEY)),1)
$(error TEX_ARENA_CURRENT_KEY must be 0 or 1)
endif
ifneq ($(filter-out 0 1,$(TEX_ARENA_CURRENT_KEY)),)
$(error TEX_ARENA_CURRENT_KEY must be 0 or 1)
endif
ifneq ($(words $(TEX_FINAL_REFUSAL_LOG)),1)
$(error TEX_FINAL_REFUSAL_LOG must be 0 or 1)
endif
ifneq ($(filter-out 0 1,$(TEX_FINAL_REFUSAL_LOG)),)
$(error TEX_FINAL_REFUSAL_LOG must be 0 or 1)
endif
ifeq ($(TEX_ARENA_CURRENT_KEY),1)
ifneq ($(VRAM_ROOM_ARENA)$(VRAM_PAGES)$(UI_VRAM),111)
$(error TEX_ARENA_CURRENT_KEY=1 needs VRAM_ROOM_ARENA=1 VRAM_PAGES=1 UI_VRAM=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_TEX_ARENA_CURRENT_KEY=1
endif
ifeq ($(TEX_FINAL_REFUSAL_LOG),1)
ifneq ($(VRAM_PAGES)$(UI_VRAM),11)
$(error TEX_FINAL_REFUSAL_LOG=1 needs VRAM_PAGES=1 UI_VRAM=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_TEX_FINAL_REFUSAL_LOG=1
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_TEX_FINAL_REFUSAL_LOG=1   # defines re4dc_room_id_now (build-d3)
endif
# VRAM_ROOM_ARENA_NO_TOP=1 (arena23 console experiment, default 0): long-lived
# class 2 allocations use best fit below a47f2000 instead of top placement. The
# final 56 KiB stays available to room/dynamic allocations. Room residency stays on.
VRAM_ROOM_ARENA_NO_TOP ?= 0
# CACHE_LINEWISE=1 (lane arena23, default 0 = image unchanged): DC* data-cache ops, route overlay load/release and the
# sub screen code sync write back line by line (ocbwb) instead of KOS's whole-cache address-array path for ranges
# >= 65560 bytes (platform/cache_lines.h). Cause candidate for the console-only 0x0c8a8001 st1_1 overlay fault.
CACHE_LINEWISE ?= 0
# FOLIAGE_MIP24=1 (lane mip-finish24 2026-10-24, render only, default 0 = image unchanged; needs WORLD_RECT21=1 and the
# fol24 data set after mip22b): the rect21 scoped table binds the 86 foliage / cut-out rows that fol24 re-encodes with
# coverage-preserving alpha mip chains (tools/d367/foliagemip22). Without fol24 those keys refuse the rect21 adapter.
FOLIAGE_MIP24 ?= 0
ifneq ($(filter-out 0 1,$(FOLIAGE_MIP24)),)
$(error FOLIAGE_MIP24 must be 0 or 1)
endif
ifeq ($(FOLIAGE_MIP24),1)
ifneq ($(WORLD_RECT21),1)
$(error FOLIAGE_MIP24=1 needs WORLD_RECT21=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FOLIAGE_MIP24=1
endif
ifneq ($(CACHE_LINEWISE),0)
$(OBJDIR)/platform/misc.o $(OBJDIR)/platform/modules.o $(OBJDIR)/platform/subscreen_backing.o: PLATFORM_CPPFLAGS += -DRE4DC_CACHE_LINEWISE=1
endif
ifneq ($(filter-out 0 1,$(VRAM_ROOM_ARENA_NO_TOP)),)
$(error VRAM_ROOM_ARENA_NO_TOP must be 0 or 1)
endif
ifeq ($(VRAM_ROOM_ARENA_NO_TOP),1)
ifneq ($(VRAM_ROOM_ARENA)$(VRAM_PAGES)$(UI_VRAM),111)
$(error VRAM_ROOM_ARENA_NO_TOP=1 needs VRAM_ROOM_ARENA=1 VRAM_PAGES=1 UI_VRAM=1)
endif
$(OBJDIR)/platform/vram_pages.o: PLATFORM_CPPFLAGS += -DRE4DC_VRAM_ROOM_ARENA_NO_TOP=1
endif
# CRASH_OVL_LINE=1 (lane mipfault22, diagnostic, default 0 = image unchanged): the crash screen lists each loaded
# route overlay as name@image+bytes, so a console fault pc / pr in an overlay can be symbolized.
CRASH_OVL_LINE ?= 0
# OVL_WATCH=1 (lane mipfault22, diagnostic only): log every changed word of a loaded route overlay (after each
# texture upload and close, and at release).
OVL_WATCH ?= 0
# OVL_GUARD=1 (lane mipfault22, console diagnostic only): stop on the first changed word of a loaded route overlay's
# code (checked per UI frame and texture upload / close); =2: instead, the SH-4 UBC on the st1_1 literal word that the
# console fault read (st1_1+0x6114), reported from the next UI frame (see platform/modules.cpp).
OVL_GUARD ?= 0
# =3 (D4): both checks, plus a ring of the last 12 texture-RAM operations (alloc / free / upload) shown on the crash screen.
# LOG_TRIM=N (diagnostic, default 0): the RAM boot log is N bytes shorter (mem.cpp / crash_screen.cpp), so a
# diagnostic build can keep the reference image's _end (with IMAGE_PAD_BYTES) and so its heap and overlay addresses.
# ARENA_RING=1 (lane mipfault22, diagnostic, default 0): the ring of the last 12 texture-RAM operations (A alloc / F free:
# VRAM offset, bytes, arena class, caller; U upload: key crc, VRAM bytes, main-RAM package) on the crash screen.
# OVL_GUARD=3 turns it on too.
ARENA_RING ?= 0
ifneq ($(filter 3,$(OVL_GUARD))$(filter-out 0,$(ARENA_RING)),)
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/vram_pages.o $(OBJDIR)/platform/crash_screen.o: PLATFORM_CPPFLAGS += -DRE4DC_ARENA_RING=1
endif
# DVD_BUFF_KB=N (lane heap-margin25 2026-10-25, default 0 = the GameCube's 128 KB; N = 16..64, a power of two):
# the DVD staging area (platform mem.cpp re4dc_dvd_buff) is N KB. src/game/dvd.cpp chunks every transfer through it:
# sound / archive pieces of N KB (was 128 KB), memory swap and event swap reload through the N/2 halves. No read is
# refused; smaller pieces only mean more disc requests during loads. The image (heap 4 at r100 s30) is 128-N KB smaller.
DVD_BUFF_KB ?= 0
ifneq ($(DVD_BUFF_KB),0)
ifeq ($(filter 16 32 64,$(DVD_BUFF_KB)),)
$(error DVD_BUFF_KB must be 0, 16, 32 or 64)
endif
GAME_CPPFLAGS += -DRE4DC_DVD_BUFF_BYTES=$(DVD_BUFF_KB)*1024
PLATFORM_CPPFLAGS += -DRE4DC_DVD_BUFF_BYTES=$(DVD_BUFF_KB)*1024
endif
# DVD_BORROW=1 (lane heap-margin25, default 0; needs DVD_BUFF_KB): load-time staging borrow (src/game/dvd.cpp): during
# boot / new game / room loads a transfer larger than the static area reads through DVD_BORROW_KB (default 128) carved
# from the top of heap 4, only while DVD_BORROW_SPARE_KB (default 512) more stays free; returned at the transfer's end.
DVD_BORROW ?= 0
DVD_BORROW_KB ?= 128
DVD_BORROW_SPARE_KB ?= 512
ifneq ($(DVD_BORROW),0)
ifneq ($(DVD_BORROW),1)
$(error DVD_BORROW must be 0 or 1)
endif
ifeq ($(DVD_BUFF_KB),0)
$(error DVD_BORROW=1 needs DVD_BUFF_KB)
endif
$(OBJDIR)/src/game/dvd.o $(OBJDIR)/src/game/game.o: GAME_CPPFLAGS += -DRE4DC_DVD_BORROW=1 -DRE4DC_DVD_BORROW_BYTES=$(DVD_BORROW_KB)*1024U -DRE4DC_DVD_BORROW_SPARE=$(DVD_BORROW_SPARE_KB)*1024U
endif
# LOG_PLAY_KB=N (lane heap-margin25 2026-10-25, default 0: no effect): in a play image (DBG_WARP=0 and QA_MENU=0 only)
# the RAM log ring is N KB (LOG_TRIM = 64 KB - N KB) with a 32-byte size header before it (mem.cpp RE4DC_LOG_RING_HDR;
# read_log.py reads it, 64 KB when absent). The crash screen shows the ring's newest lines, which N >= 8 covers. Test,
# warp and QA images keep 64 KB. The image (heap 4 at r100 s30) is 64 - N KB smaller, less the 32-byte header.
LOG_PLAY_KB ?= 0
# LOG_CRASH_TEST=N (test only, default 0): fault after the N-th log append (platform/mem.cpp), for the crash screen check.
LOG_CRASH_TEST ?= 0
ifneq ($(LOG_CRASH_TEST),0)
$(OBJDIR)/platform/mem.o: PLATFORM_CPPFLAGS += -DRE4DC_LOG_CRASH_TEST=$(LOG_CRASH_TEST)
endif
ifneq ($(LOG_PLAY_KB),0)
ifeq ($(filter 8 16 32,$(LOG_PLAY_KB)),)
$(error LOG_PLAY_KB must be 0, 8, 16 or 32)
endif
ifeq ($(filter-out 0,$(DBG_WARP))$(filter-out 0,$(QA_MENU)),)
LOG_TRIM := $(shell echo $$((65536 - $(LOG_PLAY_KB) * 1024)))
$(OBJDIR)/platform/mem.o: PLATFORM_CPPFLAGS += -DRE4DC_LOG_RING_HDR=1
endif
endif
LOG_TRIM ?= 0
ifneq ($(LOG_TRIM),0)
$(OBJDIR)/platform/mem.o $(OBJDIR)/platform/crash_screen.o: PLATFORM_CPPFLAGS += -DRE4DC_LOG_TRIM=$(LOG_TRIM)
$(OBJDIR)/qa_menu.o: GAME_CPPFLAGS += -DRE4DC_LOG_TRIM=$(LOG_TRIM)
endif
ifneq ($(OVL_GUARD),0)
$(OBJDIR)/platform/modules.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/vram_pages.o $(OBJDIR)/platform/crash_screen.o: PLATFORM_CPPFLAGS += -DRE4DC_OVL_GUARD=$(OVL_GUARD)
endif
# HDR_ALIGN_PROBE=1 (lane mipfault22, diagnostic, default 0): log each caller that compiles a PVR header into a dst that is
# not 32-byte aligned (KOS compiles with movca.l). Needs TEX_MIP_DADJ (the wrapper it lives in).
HDR_ALIGN_PROBE ?= 0
ifneq ($(HDR_ALIGN_PROBE),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_HDR_ALIGN_PROBE=1
endif
ifneq ($(OVL_WATCH),0)
$(OBJDIR)/platform/modules.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_OVL_WATCH=1
endif
ifneq ($(CRASH_OVL_LINE),0)
$(OBJDIR)/platform/modules.o $(OBJDIR)/platform/crash_screen.o: PLATFORM_CPPFLAGS += -DRE4DC_CRASH_OVL_LINE=1
endif
ifneq ($(VRAM_ROOM_ARENA),0)
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/vram_pages.o: PLATFORM_CPPFLAGS += -DRE4DC_VRAM_ROOM_ARENA=1
endif
ifneq ($(filter-out 0 1,$(VRAM_PAGES_VQ_ONLY)),)
$(error VRAM_PAGES_VQ_ONLY must be 0 or 1)
endif
ifeq ($(VRAM_PAGES_VQ_ONLY),1)
ifneq ($(VRAM_PAGES)$(UI_VRAM),11)
$(error VRAM_PAGES_VQ_ONLY=1 needs VRAM_PAGES=1 UI_VRAM=1)
endif
endif
# VRAM_ROOM_LOG=1 (lane vram12 D4, render/log only, default 0 = image unchanged; needs UI_VRAM=1 VRAM_PAGES=1): the
# per-room VRAM report of the CLAUDE.md graphics memory rule (native_ui.cpp: "vram room:" pinned / dynamic / other /
# free / largest free block, "vram gaps:" refusals, thrash-guard skips, no contiguous block, GameCube effect pictures,
# dropped parts, silent sound blocks) at each room-entry preload, every 600 frames and at the room change. Gates:
# tools/d367/vram/vram_gate.py, fullplay/fp_check.py.
# KOS_WATCH=1 (diagnostic, default 0 = image unchanged): native_ui.cpp logs "kos watch:" KOS malloc headroom (free
# chunks + sbrk room below the kernel stack) every 60 frames and at each new low (2 KiB steps). Test 12 bell HALT
# ("Out of memory. Requested sbrk_base 0x8cff0000") accounting.
KOS_WATCH ?= 0
ifneq ($(filter $(KOS_WATCH),0 1),$(KOS_WATCH))
$(error KOS_WATCH must be 0 or 1)
endif
ifeq ($(KOS_WATCH),1)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_KOS_WATCH=1
endif
# KOS_SQUEEZE=1 (diagnostic, test builds only, default 0 = image unchanged; 2026-10-15 console out-of-memory gate):
# right after OSInit carves the source arena (ARENA_FIT leaves ARENA_FIT_KOS_BYTES to KOS), hold KOS_SQUEEZE_BYTES of
# KOS malloc for the whole run: one block (KOS_SQUEEZE_FRAG=0), or 4 KiB pieces each followed by a 4 KiB block that is
# freed again (KOS_SQUEEZE_FRAG=1: the same bytes held, the space above them broken into 4 KiB holes). It makes Flycast's
# KOS heap as small, or as broken up, as a console's: preview 2 had 7-8.5 KB minimum headroom in the Flycast r101 fight
# and ran out of KOS on the console; preview 1's first radio call could not get 12,248 B on the console. A line
# "squeeze <bytes> [frag]" in /cd/dc/warp.txt overrides both at run time (one warp twin serves every level). Logs
# "kos squeeze:" (held bytes, pieces, headroom before / after); with KOS_WATCH=1 the "kos watch:" lines also give
# top= (the largest block: sbrk room + the top chunk) and holes= (free chunks below the top).
KOS_SQUEEZE ?= 0
KOS_SQUEEZE_BYTES ?= 0
KOS_SQUEEZE_FRAG ?= 0
ifneq ($(filter $(KOS_SQUEEZE),0 1),$(KOS_SQUEEZE))
$(error KOS_SQUEEZE must be 0 or 1)
endif
ifneq ($(filter $(KOS_SQUEEZE_FRAG),0 1),$(KOS_SQUEEZE_FRAG))
$(error KOS_SQUEEZE_FRAG must be 0 or 1)
endif
ifeq ($(KOS_SQUEEZE),1)
$(OBJDIR)/platform/os.o: PLATFORM_CPPFLAGS += -DRE4DC_KOS_SQUEEZE=1 -DRE4DC_KOS_SQUEEZE_BYTES=$(KOS_SQUEEZE_BYTES) -DRE4DC_KOS_SQUEEZE_FRAG=$(KOS_SQUEEZE_FRAG)
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_KOS_SQUEEZE=1
endif
VRAM_ROOM_LOG ?= 0
ifneq ($(filter-out 0 1,$(VRAM_ROOM_LOG)),)
$(error VRAM_ROOM_LOG must be 0 or 1)
endif
ifeq ($(VRAM_ROOM_LOG),1)
ifneq ($(UI_VRAM)$(VRAM_PAGES),11)
$(error VRAM_ROOM_LOG=1 needs UI_VRAM=1 VRAM_PAGES=1)
endif
endif
# TEX_META_EVICT=1 (lane vram12 D5, render only, default 0; needs UI_VRAM=1 TEX_RESIDENT=1): the KOS heap that
# ARENA_FIT_KOS_BYTES leaves (~138 KB at r101 entry; heap 4 cannot give more: the spawn checks read its free bytes)
# holds every open texture package's descriptor, so with VRAM no longer the limit it is. A streamed package takes
# one KOS block (descriptor + pointer table + flags: 160 B for one texture, was three blocks, 184 B); the cache keeps
# 8 KiB of KOS heap free (pack sector reads, motion file opens) by evicting least recently used uploads, and a
# refused descriptor evicts and opens again instead of failing the load every frame; the native model slab
# (64 KiB) is allocated before the first room-entry preload, not after it. Logs kos= headroom (VRAM_ROOM_LOG).
TEX_META_EVICT ?= 0
# RETIRE_KOS_FLOOR=<bytes> (test 12.2, render only, default 0 = image unchanged; needs TEX_KEEP=1 TEX_META_EVICT=1):
# TEX_KEEP keeps every texture entry resident across a room change, and with TEX_META_EVICT each open package holds a
# KOS block (144-184 B). Leaving r101 after the fight kept ~345 of them (~60 KB) plus the 64 KiB model slab into the
# next room's start (12.1 "room lifecycle: phase=enter drift kos=-128808"), and the next room's own KOS allocations ran
# out under a 48 KiB KOS squeeze (the console's smaller KOS; tools/d367/fullplay/kos_squeeze.sh leave100 / leave103).
# At room retirement (after the fence, before the next room allocates) the kept entries are closed least recently used
# first, sparing actor-leased and room-pinned ones, until KOS headroom is at least RETIRE_KOS_FLOOR; textures the next
# room shares reload from tex.pak during its load. Logs "native UI: room retire KOS floor:".
RETIRE_KOS_FLOOR ?= 0
ifneq ($(shell echo '$(RETIRE_KOS_FLOOR)' | grep -Ex '[0-9]+'),$(RETIRE_KOS_FLOOR))
$(error RETIRE_KOS_FLOOR must be a byte count)
endif
ifneq ($(RETIRE_KOS_FLOOR),0)
ifneq ($(TEX_KEEP)$(TEX_META_EVICT),11)
$(error RETIRE_KOS_FLOOR needs TEX_KEEP=1 TEX_META_EVICT=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_RETIRE_KOS_FLOOR=$(RETIRE_KOS_FLOOR)U
endif
# ROOM_CHANGE_EVICT=<frames> (test 13, render only, default 0 = image unchanged; needs TEX_KEEP=1): VRAM graphics memory
# rule. TEX_KEEP marked every kept entry "oldest" (frame 0) at room retirement, so the next room's preload and first
# frames evicted among the previous room's leftovers in table order, not LRU: r101 -> r103 kept 209 entries (1.5 MB),
# reused 23, evicted the common set (Leon, HUD) and kept r101-only scenery; the common set then reloaded in r103's first
# frames into a 3.5 KB largest block, and the evictions armed the EFFECT_ROOM thrash guard (door103 full row: 6-18
# guard_p refusals, in 12.1 and 12.2). With it, retirement keeps each entry's last-drawn frame (LRU order across the
# change), and the next room's first preload pass, once its own listed textures are marked, closes every kept entry not
# drawn in the old room's last <frames> frames and not leased or pinned. The new room's set loads into the freed pool;
# the common set the old room drew to the end stays. Logs "native UI: room change evict:".
ROOM_CHANGE_EVICT ?= 0
ifneq ($(shell echo '$(ROOM_CHANGE_EVICT)' | grep -Ex '[0-9]+'),$(ROOM_CHANGE_EVICT))
$(error ROOM_CHANGE_EVICT must be a frame count)
endif
ifneq ($(ROOM_CHANGE_EVICT),0)
ifneq ($(TEX_KEEP),1)
$(error ROOM_CHANGE_EVICT needs TEX_KEEP=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ROOM_CHANGE_EVICT=$(ROOM_CHANGE_EVICT)U
endif
# SS11_ROOM_EVICT=1 (lane lake20 2026-10-20, #43; render only, default 0 = image unchanged; needs ROOM_CHANGE_EVICT,
# ROOM_REENTRY_EVICT=1 and SS11_PRELOAD=1 on the command line): a room change made behind the chapter-end screens (Del
# Lago r10b -> the night shore r11b) arms the room-change evict at the SS heap 11 preload pass and closes every unpinned
# entry of the old room, so the new room's preload finds contiguous blocks (Test 20: three 256x256 r11b pictures latched
# ~2 s, 1 guard refusal).
SS11_ROOM_EVICT ?= 0
ifeq ($(SS11_ROOM_EVICT),1)
ifneq ($(if $(filter-out 0,$(ROOM_CHANGE_EVICT)),1)$(ROOM_REENTRY_EVICT)$(SS11_PRELOAD),111)
$(error SS11_ROOM_EVICT=1 needs ROOM_CHANGE_EVICT, ROOM_REENTRY_EVICT=1 and SS11_PRELOAD=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_SS11_ROOM_EVICT=1
endif
# FRAME_QUEUE_DIAG=1 (lane fix18 #39, log only, default 0 = image unchanged): one FQDIAG line per frame whose frame
# queue refused translucent parts or effect sprites: counts, bytes asked for, the peak, and the queue at the drop.
FRAME_QUEUE_DIAG ?= 0
ifneq ($(filter-out 0 1,$(FRAME_QUEUE_DIAG)),)
$(error FRAME_QUEUE_DIAG must be 0 or 1)
endif
ifeq ($(FRAME_QUEUE_DIAG),1)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FRAME_QUEUE_DIAG=1
endif
# FRAME_QUEUE_SPILL_KB=<n> (lane fix18 #39, render only, default 0 = image unchanged = 8 KiB): the frame queue's deferred
# spill (carved from the model slab, which grows by n-8 KiB of KOS heap). r200 f1104-1135 needs 11,264 B past 8 KiB: 20.
FRAME_QUEUE_SPILL_KB ?= 0
ifneq ($(FRAME_QUEUE_SPILL_KB),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FRAME_QUEUE_SPILL_KB=$(FRAME_QUEUE_SPILL_KB)
endif
# ROOM_LEFTOVER_FIT=1 (lane fix18 #39, render only, default 0 = image unchanged; needs ROOM_CHANGE_EVICT): after each
# preload pass, while the texture budget has less than 512 KB free, close the previous room's leftovers (last drawn at or
# before the room change; not pinned, leased or core), oldest first. r10f -> r200 kept 54 r10f world pictures (611 KB)
# beside r200's set: 72 KB free, 20 thrash-guard refusals, 366 effect sprites dropped, fa6fe38c without a block.
# Logs "native UI: room leftover fit:".
ROOM_LEFTOVER_FIT ?= 0
ifneq ($(filter-out 0 1,$(ROOM_LEFTOVER_FIT)),)
$(error ROOM_LEFTOVER_FIT must be 0 or 1)
endif
ifeq ($(ROOM_LEFTOVER_FIT),1)
ifeq ($(ROOM_CHANGE_EVICT),0)
$(error ROOM_LEFTOVER_FIT needs ROOM_CHANGE_EVICT)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ROOM_LEFTOVER_FIT=1
endif
# ROOM_REENTRY_EVICT=1 (test 14 RC, render only, default 0 = image unchanged; needs ROOM_CHANGE_EVICT): when the room
# entered is the room just left (Continue after a death, r101 -> r101), the room-change evict closes every kept entry
# the new room's first preload pass did not pin, instead of keeping what the old visit drew in its last frames. Without
# it the r101 death / Continue re-entry kept 57 entries (526 KB) beside the 190-key resident list and three 256x256
# textures found no contiguous block (crash suite death, test 14 RC 10-15). Logs "native UI: room re-entry evict:".
ROOM_REENTRY_EVICT ?= 0
ifneq ($(filter-out 0 1,$(ROOM_REENTRY_EVICT)),)
$(error ROOM_REENTRY_EVICT must be 0 or 1)
endif
ifeq ($(ROOM_REENTRY_EVICT),1)
ifeq ($(ROOM_CHANGE_EVICT),0)
$(error ROOM_REENTRY_EVICT needs ROOM_CHANGE_EVICT)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ROOM_REENTRY_EVICT=1
endif
# PRELOAD_LARGE_FIRST=1 (lane vram12 D5, render only, default 0; needs TEX_RESIDENT=1): the room-entry preload loads its
# picks of 16 KiB or more first, then the rest (two forward sweeps in disc order), so small packages do not fragment
# the pool ahead of the large ones.
PRELOAD_LARGE_FIRST ?= 0
# ROOM_RESIDENT=1 (lane vram12 D5, render only, default 0; needs TEX_RESIDENT=1): the room-entry preload also loads
# the room's list in dc/resident.bin (tools/d367/vram/resident_keys.py: the textures its scenes otherwise load on
# first sight), so the room's set is resident from its entry. Without the file the preload is as before.
ROOM_RESIDENT ?= 0
# RESIDENT_LIST_CACHE=1: retain bounded copied current-room/core list metadata between owner admissions.
# New owner identities and missing textures still use the original preload; no payload reserve changes.
RESIDENT_LIST_CACHE ?= 0
ifneq ($(filter-out 0 1,$(RESIDENT_LIST_CACHE)),)
$(error RESIDENT_LIST_CACHE must be 0 or 1)
endif
ifeq ($(RESIDENT_LIST_CACHE)$(ROOM_RESIDENT),10)
$(error RESIDENT_LIST_CACHE=1 needs ROOM_RESIDENT=1)
endif
ifneq ($(filter-out 0 1,$(ROOM_RESIDENT)),)
$(error ROOM_RESIDENT must be 0 or 1)
endif
ifeq ($(ROOM_RESIDENT)$(TEX_RESIDENT),10)
$(error ROOM_RESIDENT=1 needs TEX_RESIDENT=1)
endif
ifneq ($(filter-out 0 1,$(PRELOAD_LARGE_FIRST)),)
$(error PRELOAD_LARGE_FIRST must be 0 or 1)
endif
ifeq ($(PRELOAD_LARGE_FIRST)$(TEX_RESIDENT),10)
$(error PRELOAD_LARGE_FIRST=1 needs TEX_RESIDENT=1)
endif
ifneq ($(filter-out 0 1,$(TEX_META_EVICT)),)
$(error TEX_META_EVICT must be 0 or 1)
endif
ifeq ($(TEX_META_EVICT),1)
ifneq ($(UI_VRAM)$(TEX_RESIDENT),11)
$(error TEX_META_EVICT=1 needs UI_VRAM=1 TEX_RESIDENT=1)
endif
endif
ifneq ($(VRAM_PAGES),1)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/vram_pages.o,$(PLATFORM_OBJS))
endif
UI_HANDLES ?= 0
UI_HEADERS ?= 0
TEX_RESIDENT ?= 0
TEX_RESIDENT_RESERVE_KB ?= 256
TEX_SLOTS ?= 192
TEX_PAYLOAD_CRC ?= 0
TEX_KEEP ?= 0
.PHONY: pipeline30-force
$(OBJDIR)/pipeline30.h: pipeline30-force
	@mkdir -p $(dir $@)
	@if [ "$(PVR_PIPELINE)" = 2 ]; then test "$$($(KOS_CC_BASE)/bin/$(KOS_CC_PREFIX)-nm -g --defined-only $(KOS_BASE)/lib/$(KOS_ARCH)/libkallisti.a | grep -Ec ' T _pvr_present_(async|wait|pending)$$')" -eq 3 || { echo 'PVR_PIPELINE=2 requires the KOS async-present patch' >&2; exit 1; }; fi
	@printf '#define RE4DC_PVR_FAST_WAKE %s\n#define RE4DC_PVR_PIPELINE %s\n#define RE4DC_TA_DIRECT %s\n#define RE4DC_BRIDGE_LEAN %s\n' '$(PVR_FAST_WAKE)' '$(PVR_PIPELINE)' '$(TA_DIRECT)' '$(BRIDGE_LEAN)' > $@.tmp
	@printf '#define RE4DC_TA_VERTBUF_KB %s\n#define RE4DC_TA_DOUBLEBUF %s\n#define RE4DC_TA_OPB_BINS %s\n#define RE4DC_TA_OPB_OVERFLOW %s\n#define RE4DC_TA_GUARD %s\n#define RE4DC_PERF_HUD %s\n' '$(TA_VERTBUF_KB)' '$(TA_DOUBLEBUF)' '$(TA_OPB_BINS)' '$(TA_OPB_OVERFLOW)' '$(TA_GUARD)' '$(PERF_HUD)' >> $@.tmp
	@printf '#define RE4DC_UI_VRAM %s\n#define RE4DC_UI_VRAM_RESERVE_KB %s\n' '$(UI_VRAM)' '$(UI_VRAM_RESERVE_KB)' >> $@.tmp
	@printf '#define RE4DC_UI_FRAG_LATCH %s\n#define RE4DC_UI_OVERLAY_SLAB_KB %s\n' '$(UI_FRAG_LATCH)' '$(UI_OVERLAY_SLAB_KB)' >> $@.tmp
	@printf '#define RE4DC_UI_FRAG_RESERVE %s\n' '$(UI_FRAG_RESERVE)' >> $@.tmp
	@printf '#define RE4DC_UI_FRAG_WINDOW %s\n' '$(UI_FRAG_WINDOW)' >> $@.tmp
	@printf '#define RE4DC_TEX_REF_SELFKEY %s\n' '$(TEX_REF_SELFKEY)' >> $@.tmp
	@printf '#define RE4DC_PT_BLEND_FIX %s\n' '$(PT_BLEND_FIX)' >> $@.tmp
	@printf '#define RE4DC_TEX_CHECK %s\n' '$(TEX_CHECK)' >> $@.tmp
	@printf '#define RE4DC_VRAM_PAGES %s\n#define RE4DC_VRAM_CENSUS %s\n' '$(VRAM_PAGES)' '$(VRAM_CENSUS)' >> $@.tmp
	@printf '#define RE4DC_VRAM_PAGES_VQ_ONLY %s\n' '$(VRAM_PAGES_VQ_ONLY)' >> $@.tmp
	@printf '#define RE4DC_VRAM_ROOM_LOG %s\n' '$(VRAM_ROOM_LOG)' >> $@.tmp
	@printf '#define RE4DC_TEX_META_EVICT %s\n' '$(TEX_META_EVICT)' >> $@.tmp
	@printf '#define RE4DC_PRELOAD_LARGE_FIRST %s\n' '$(PRELOAD_LARGE_FIRST)' >> $@.tmp
	@printf '#define RE4DC_ROOM_RESIDENT %s\n' '$(ROOM_RESIDENT)' >> $@.tmp
	@printf '#define RE4DC_RESIDENT_LIST_CACHE %s\n' '$(RESIDENT_LIST_CACHE)' >> $@.tmp
	@printf '#define RE4DC_UI_HANDLES %s\n#define RE4DC_UI_HEADERS %s\n' '$(UI_HANDLES)' '$(UI_HEADERS)' >> $@.tmp
	@printf '#define RE4DC_TEX_RESIDENT %s\n#define RE4DC_TEX_RESIDENT_RESERVE_KB %s\n#define RE4DC_TEX_PAYLOAD_CRC %s\n#define RE4DC_TEX_SLOTS %s\n' '$(TEX_RESIDENT)' '$(TEX_RESIDENT_RESERVE_KB)' '$(TEX_PAYLOAD_CRC)' '$(TEX_SLOTS)' >> $@.tmp
	@printf '#define RE4DC_TEX_KEEP %s\n#define RE4DC_PVR_LATCH %s\n' '$(TEX_KEEP)' '$(PVR_LATCH)' >> $@.tmp
	@printf '#define RE4DC_MOVIE_WINDOW %s\n' '$(MOVIE_WINDOW)' >> $@.tmp
	@printf '#define RE4DC_DOOR_FREEZE %s\n' '$(DOOR_FREEZE)' >> $@.tmp
	@printf '#define RE4DC_PVR_READY_STRICT %s\n#define RE4DC_PVR_RECOVER %s\n' '$(PVR_READY_STRICT)' '$(PVR_RECOVER)' >> $@.tmp
	@printf '#define RE4DC_PVR_MID_FENCE %s\n#define RE4DC_TA_HEADROOM %s\n' '$(PVR_MID_FENCE)' '$(TA_HEADROOM)' >> $@.tmp
	@if [ "$(MOVIE_WINDOW)" = 1 ] && { [ "$(VRAM_PAGES)" != 1 ] || [ "$(TEX_RESIDENT)" != 1 ]; }; then echo 'MOVIE_WINDOW=1 needs VRAM_PAGES=1 TEX_RESIDENT=1' >&2; exit 1; fi
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/model_bridge.o: $(OBJDIR)/pipeline30.h
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/pipeline30.h
ifneq ($(filter 1 2,$(PVR_LATCH) $(PVR_READY_STRICT)),)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -I$(KOS_BASE)/kernel/arch/dreamcast/hardware/pvr
endif
ifeq ($(PVR_READY_STRICT),1)
GAME_LDFLAGS += -Wl,--wrap=pvr_list_begin -Wl,--wrap=pvr_set_presort_mode
endif
ifeq ($(UI_OS),1)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -Os
endif
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -include $(OBJDIR)/pipeline30.h
$(OBJDIR)/native-reuse/texture_package.o: $(OBJDIR)/pipeline30.h
$(OBJDIR)/native-reuse/texture_package.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/pipeline30.h
$(OBJDIR)/platform/vram_pages.o: $(OBJDIR)/pipeline30.h
$(OBJDIR)/platform/vram_pages.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/pipeline30.h

# Both renderer arms retain the full source arena. Reuse a smaller native I/O
# bounce (same reader, short-read/CRC/unaligned-small-file contracts), reclaiming
# 48 KiB of redundant staging rather than funding metadata from gameplay RAM.
$(OBJDIR)/native-reuse/room_storage.o: PLATFORM_CPPFLAGS += -DRE4DC_STORAGE_BOUNCE_BYTES=16384

# Exact source-position reuse, scoped to one native part. 0 is the reference path.
# Shared room/character strip assembly in recovered source models. Selectable
# until matched target timing and appearance qualification are complete.
D349_RENDERER_STACK ?= 0
ifeq ($(D349_RENDERER_STACK),1)
override MODEL_ROOM_STRIPS = 1
override MODEL_DRAW_PLANS = 1
override MODEL_POSITION_CACHE = 1
ifneq ($(PVR_STREAM),1)
$(error D349_RENDERER_STACK requires the existing PVR_STREAM=1 frame owner)
endif
endif
.PHONY: d349-stack-force
$(OBJDIR)/d349-stack.h: d349-stack-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_D349_RENDERER_STACK %s\n' '$(D349_RENDERER_STACK)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
D349_NATIVE_OBJS = $(OBJDIR)/native-reuse/source_lighting.o $(OBJDIR)/native-reuse/pvr_geometry.o $(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/gx_stub.o
$(D349_NATIVE_OBJS): $(OBJDIR)/d349-stack.h
$(D349_NATIVE_OBJS): PLATFORM_CPPFLAGS += -include $(OBJDIR)/d349-stack.h
$(OBJDIR)/src/game/trans.o: $(OBJDIR)/d349-stack.h
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -include $(OBJDIR)/d349-stack.h
$(OBJDIR)/ui_bridge.o $(OBJDIR)/model_bridge.o $(OBJDIR)/model_asset_bridge.o: $(OBJDIR)/d349-stack.h
$(OBJDIR)/ui_bridge.o $(OBJDIR)/model_bridge.o $(OBJDIR)/model_asset_bridge.o: GAME_CPPFLAGS += -include $(OBJDIR)/d349-stack.h
# Bounded diagnostic attribution; both A/B arms use the same enabled policy.
NATIVE_RENDER_PROFILE ?= 0
.PHONY: native-profile-force
$(OBJDIR)/native-profile.h: native-profile-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_NATIVE_RENDER_PROFILE %s\n' '$(NATIVE_RENDER_PROFILE)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
# Default-off: DEBUG_PAD=1 lets platform/pad.cpp pass the source's debug pad chords
# (L+START debug menu, Z item-make / puzzle debug in the sub screen) through.
DEBUG_PAD ?= 0
.PHONY: debug-pad-force
$(OBJDIR)/debug-pad.h: debug-pad-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_DEBUG_PAD %s\n' '$(DEBUG_PAD)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/pad.o: $(OBJDIR)/debug-pad.h
$(OBJDIR)/platform/pad.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/debug-pad.h
# Default-off, bounded source-view/reuse audit through the existing RAM log.
NATIVE_REUSE_AUDIT ?= 0
.PHONY: native-reuse-audit-force
$(OBJDIR)/native-reuse-audit.h: native-reuse-audit-force
	@printf '#define RE4DC_NATIVE_REUSE_AUDIT %s\n' '$(NATIVE_REUSE_AUDIT)' > $@.tmp
	@cmp -s $@.tmp $@ || cp $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_model.o: $(OBJDIR)/native-reuse-audit.h platform/include/native_reuse_audit.hpp
$(OBJDIR)/platform/native_model.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/native-reuse-audit.h

$(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/native-reuse/pvr_geometry.o: $(OBJDIR)/native-profile.h platform/include/native_render_profile.hpp
$(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/native-reuse/pvr_geometry.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/native-profile.h
# Default-off statistical PC sampler: TMU1 interrupt -> fixed RAM ring
# (re4dc_pcs) streamed out by the harness. Off: platform/pc_sampler.cpp is an
# empty unit and the OSInit/end-frame hooks are empty inlines.
# PC_SAMPLER_BYTES is a power of two (8-byte records); see ARENA_KOS_BYTES.
PC_SAMPLER ?= 0
PC_SAMPLER_HZ ?= 1000
PC_SAMPLER_BYTES ?= 16384
PC_SAMPLER_KOS_BYTES = $(if $(filter 1,$(PC_SAMPLER)),$(shell expr $(PC_SAMPLER_BYTES) + 4096),0)
.PHONY: pc-sampler-force
$(OBJDIR)/pc-sampler.h: pc-sampler-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_PC_SAMPLER %s\n#define RE4DC_PC_SAMPLER_HZ %s\n#define RE4DC_PC_SAMPLER_BYTES %s\n' '$(PC_SAMPLER)' '$(PC_SAMPLER_HZ)' '$(PC_SAMPLER_BYTES)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
PC_SAMPLER_OBJS = $(OBJDIR)/platform/pc_sampler.o $(OBJDIR)/platform/os.o $(OBJDIR)/platform/native_ui.o
$(PC_SAMPLER_OBJS): $(OBJDIR)/pc-sampler.h platform/include/pc_sampler.h
$(PC_SAMPLER_OBJS): PLATFORM_CPPFLAGS += -include $(OBJDIR)/pc-sampler.h
# With NATIVE_RENDER_PROFILE=1 each sample also carries the active render stage.
$(OBJDIR)/platform/pc_sampler.o: $(OBJDIR)/native-profile.h
$(OBJDIR)/platform/pc_sampler.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/native-profile.h
# Historical native-only kernel policy; source gameplay retains its current flags.
ifeq ($(D349_RENDERER_STACK),1)
$(OBJDIR)/platform/native_model.o $(OBJDIR)/native-reuse/source_lighting.o $(OBJDIR)/native-reuse/pvr_geometry.o: PLATFORM_CPPFLAGS += -O3 -fno-predictive-commoning
endif

MODEL_ROOM_STRIPS ?= 0
.PHONY: model-room-strips-force
$(OBJDIR)/model-room-strips.h: model-room-strips-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_MODEL_ROOM_STRIPS %s\n' '$(MODEL_ROOM_STRIPS)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_model.o: $(OBJDIR)/model-room-strips.h ../room/pvr_geometry.hpp platform/include/native_model.h
$(OBJDIR)/platform/native_model.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/model-room-strips.h
$(OBJDIR)/native-reuse/pvr_geometry.o: ../room/pvr_geometry.hpp

MODEL_POSITION_CACHE ?= 1
.PHONY: model-position-force
$(OBJDIR)/model-position.h: model-position-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_MODEL_POSITION_CACHE %s\n' '$(MODEL_POSITION_CACHE)' > $@.tmp
	@cmp -s $@.tmp $@ || cp $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_model.o: $(OBJDIR)/crash-screen.h
$(OBJDIR)/platform/native_model.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/crash-screen.h
$(OBJDIR)/platform/native_model.o: $(OBJDIR)/model-position.h
$(OBJDIR)/platform/native_model.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/model-position.h

# Compact structural plans share the existing native packet slab. No source
# heap reservation and no copied display-list corners.
MODEL_DRAW_PLANS ?= 0
# Converted actor streams keep their meshlet decoder after fallback skinning.
MODEL_STREAM_FIX ?= 0
ifneq ($(filter-out 0 1,$(MODEL_STREAM_FIX)),)
$(error MODEL_STREAM_FIX must be 0 or 1)
endif
ifeq ($(MODEL_STREAM_FIX),1)
ifneq ($(NATIVE_ACTOR)$(NATIVE_ACTOR_FAST),11)
$(error MODEL_STREAM_FIX requires NATIVE_ACTOR=1 and NATIVE_ACTOR_FAST=1)
endif
endif
.PHONY: model-draw-plan-force
$(OBJDIR)/model-draw-plan.h: model-draw-plan-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_MODEL_DRAW_PLANS %s\n' '$(MODEL_DRAW_PLANS)' > $@.tmp
	@printf '#define RE4DC_MODEL_STREAM_FIX %s\n' '$(MODEL_STREAM_FIX)' >> $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_draw_plan_owner.o: $(OBJDIR)/model-draw-plan.h
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_draw_plan_owner.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/model-draw-plan.h

# Recovered scroll objects draw keyed v4 static room packages from
# /cd/dc/native/<room>/<owner>.re4room (platform/native_static.cpp). Opt-in until
# matched target visual/timing acceptance. NATIVE_STATIC_OWNERS is a mask:
# bit 0 main scenario, bit n+1 source block n.
NATIVE_STATIC ?= 0
NATIVE_STATIC_OWNERS ?= 1
# NATIVE_MESH=1 draws instanced per-BIN meshes (<owner>.re4mesh, COMMON.re4mesh)
# instead of placement-baked packages; owner mask bit 6 is the room's common set.
NATIVE_MESH ?= 0
# NATIVE_PKG_HIGH=1 carves native static/mesh packages from the top of the highest heap-4 free cell
# that fits (OSAlloc's first fit hands out the lowest). The packages then stack at the high end and a
# retired area's hole joins the free space below it instead of being split by the game's later
# allocations (r100: FILE_01 414 KB failed to reload walking west with 552 KB free in two cells).
NATIVE_PKG_HIGH ?= 0
# MESH_LOD=1 also accepts R4IM v2 packages (convert_room_bins.py --lod) and draws,
# per visible cluster, the coarsest level within MESH_LOD_PX projected pixels.
MESH_LOD ?= 0
MESH_LOD_PX ?= 3
# NATIVE_FOG=1: GXSetFog -> PVR table fog on model headers, ramped to 100% at the
# source View far plane, which also rejects scenery clusters/meshlets beyond it.
# FOG_FAR (source units, 0 = off) pulls that far plane in when it is shorter.
NATIVE_FOG ?= 0
FOG_FAR ?= 0
ifeq ($(NATIVE_FOG),1)
ifneq ($(NATIVE_STATIC),1)
$(error NATIVE_FOG requires NATIVE_STATIC=1 (platform/native_static.cpp owns the fog state))
endif
endif
ifeq ($(NATIVE_PKG_HIGH),1)
ifneq ($(NATIVE_STATIC),1)
$(error NATIVE_PKG_HIGH requires NATIVE_STATIC=1)
endif
endif
ifeq ($(NATIVE_STATIC),1)
ifneq ($(D349_RENDERER_STACK),1)
$(error NATIVE_STATIC requires the D349_RENDERER_STACK=1 packet/deferral owner)
endif
# The fixed 13 MiB source arena leaves the KOS heap only a few KiB (D367); an
# image that grows by more exhausts it at r100 thread creation. Keep this small.
$(OBJDIR)/native-reuse/room_package.o $(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -Os
endif
.PHONY: native-static-force
$(OBJDIR)/native-static.h: native-static-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_NATIVE_STATIC %s\n#define RE4DC_NATIVE_STATIC_OWNERS %sU\n#define RE4DC_NATIVE_MESH %s\n' '$(NATIVE_STATIC)' '$(NATIVE_STATIC_OWNERS)' '$(NATIVE_MESH)' > $@.tmp
	@printf '#define RE4DC_MESH_LOD %s\n#define RE4DC_MESH_LOD_PX %s\n#define RE4DC_NATIVE_FOG %s\n#define RE4DC_FOG_FAR %s\n' '$(MESH_LOD)' '$(MESH_LOD_PX)' '$(NATIVE_FOG)' '$(FOG_FAR)' >> $@.tmp
	@printf '#define RE4DC_NATIVE_PKG_HIGH %s\n' '$(NATIVE_PKG_HIGH)' >> $@.tmp
	@printf '#define RE4DC_FOG_TA_DOUBLEBUF %s\n' '$(TA_DOUBLEBUF)' >> $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
NATIVE_STATIC_PLATFORM = $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_ui.o \
	$(OBJDIR)/platform/gx_stub.o
NATIVE_STATIC_GAME = $(OBJDIR)/model_bridge.o $(OBJDIR)/ui_bridge.o $(OBJDIR)/src/game/scroll.o
$(NATIVE_STATIC_PLATFORM) $(NATIVE_STATIC_GAME): $(OBJDIR)/native-static.h platform/include/native_static.h
$(NATIVE_STATIC_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/native-static.h
$(NATIVE_STATIC_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/native-static.h
$(OBJDIR)/platform/native_static.o: $(OBJDIR)/d349-stack.h ../room/room_package.hpp ../room/static_room_prepare.hpp ../room/instanced_mesh.hpp
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/d349-stack.h

# Non-scenery parts through platform/native_actor.cpp. Its ~14 KiB of -O2 code
# comes out of the source heap after the arena; build with NO_EH=1 to fund it.
ifeq ($(NATIVE_ACTOR),1)
ifneq ($(D349_RENDERER_STACK),1)
$(error NATIVE_ACTOR requires the D349_RENDERER_STACK=1 packet/deferral owner)
endif
$(OBJDIR)/platform/native_actor.o: PLATFORM_CPPFLAGS += -O2 -include $(OBJDIR)/d349-stack.h
$(OBJDIR)/platform/native_actor.o: $(OBJDIR)/d349-stack.h ../room/pvr_geometry.hpp platform/include/native_actor.hpp platform/include/native_model.h
endif
.PHONY: native-actor-force
$(OBJDIR)/native-actor.h: native-actor-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_NATIVE_ACTOR %s\n#define RE4DC_NATIVE_ACTOR_FAST %s\n#define RE4DC_NATIVE_ACTOR_SKIN %s\n#define RE4DC_ACTOR_DIRECT %s\n#define RE4DC_NATIVE_ACTOR_SKIN_LAZY %s\n' '$(NATIVE_ACTOR)' '$(NATIVE_ACTOR_FAST)' '$(NATIVE_ACTOR_SKIN)' '$(NATIVE_ACTOR_DIRECT)' '$(NATIVE_ACTOR_SKIN_LAZY)' > $@.tmp
	@printf '#define RE4DC_ACTOR_LOD_PX ((float)(%s))\n#define RE4DC_ACTOR_LOD_BUDGET %sU\n#define RE4DC_ACTOR_PRELIT %s\n#define RE4DC_ACTOR_UV16 %s\n#define RE4DC_ACTOR_LOG %s\n' '$(if $(filter 1,$(NATIVE_ACTOR_LOD)),$(NATIVE_ACTOR_LOD_PX),0)' '$(if $(filter 1,$(NATIVE_ACTOR_LOD)),$(NATIVE_ACTOR_LOD_BUDGET),0)' '$(NATIVE_ACTOR_PRELIT)' '$(NATIVE_ACTOR_UV16)' '$(NATIVE_ACTOR_LOG)' >> $@.tmp
	@printf '#define RE4DC_ACTOR_CROWD %s\n#define RE4DC_ACTOR_CROWD_NEAR %sU\n#define RE4DC_ACTOR_CROWD_NEAR_M ((float)(%s))\n#define RE4DC_ACTOR_CROWD_MID_M ((float)(%s))\n#define RE4DC_ACTOR_CROWD_MID_PX ((float)(%s))\n' '$(CROWD_LOD)' '$(CROWD_NEAR)' '$(CROWD_NEAR_M)' '$(CROWD_MID_M)' '$(CROWD_MID_PX)' >> $@.tmp
	@printf '#define RE4DC_ACTOR_CROWD_FLAT %s\n' '$(CROWD_FLAT)' >> $@.tmp
	@printf '#define RE4DC_ACTOR_SKIN_FTRV %s\n' '$(ACTOR_SKIN_FTRV)' >> $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_model.o $(OBJDIR)/model_bridge.o: $(OBJDIR)/native-actor.h
$(OBJDIR)/platform/native_model.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/native-actor.h
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -include $(OBJDIR)/native-actor.h
$(OBJDIR)/platform/native_ui.o: $(OBJDIR)/native-actor.h
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/native-actor.h
ifeq ($(NATIVE_ACTOR_FAST),1)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -O2 -include $(OBJDIR)/d349-stack.h -include $(OBJDIR)/native-actor.h
$(OBJDIR)/platform/native_actor_fast.o: $(OBJDIR)/d349-stack.h $(OBJDIR)/native-actor.h ../room/pvr_geometry.hpp platform/include/native_actor.hpp platform/include/native_model.h
ifeq ($(NATIVE_ACTOR_DIRECT),1)
ifneq ($(TA_DIRECT),1)
$(error NATIVE_ACTOR_DIRECT=1 requires TA_DIRECT=1 (pipeline30 direct TA API))
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/pipeline30.h
$(OBJDIR)/platform/native_actor_fast.o: $(OBJDIR)/pipeline30.h platform/include/ta_direct.hpp
endif
endif
$(OBJDIR)/src/game/trans.o: $(OBJDIR)/native-actor.h
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -include $(OBJDIR)/native-actor.h
# D367 frontend30 knobs (COPY_LEAN, FRONT_LEAN, MESH_DIRECT; default off: no effect).
include frontend30.mk
# D367 W11 knobs (SUBSCREEN, W11_FIXTURE; default off: no effect).
include subscreen.mk

include vmusave.mk
# D367 test warp rig (DBG_WARP; default off: no effect).
include dbgwarp.mk
# D367 safe cuts (FX_LEAN; default off: no effect).
include safecuts.mk
# D367 effects30 (EFFECT_LEAN, EFFECT_SPRITES; default off: no effect).
include effects30.mk
# PVR_RTT (lane castlerender19 2026-10-19): PVR render-to-texture for TexRenderMng targets (default off: no effect).
include pvr_rtt.mk
# HW_FOG_HAZE (lane hwfog 2026-10-14): the distant camera haze as PVR table fog
include hwfog.mk
# gcleft26 (MODEL_PART_DUMP diagnostic; default 0: no effect).
include partdump.mk
# D367 scenery30 (PLAN_ADMIT_LEAN, SCENERY_GATE, MODEL_SLAB_LATCH; default off: no effect).
include scenery30.mk
# D367 records30 (FRONT_TEXOBJ; default off: no effect).
include records30.mk
# D367 Blender scenery knobs (TREE_IMPOSTOR; default off: no effect).
include blender30.mk
# D367 TA_HASH (test builds; default off: no effect).
include tahash.mk
# D367 machine checks (MCHECK_PT, MCHECK_SAFE; test builds; default off: no effect).
include mcheck.mk
include backface.mk
# D367 lane barn28 (r103 barn model cost; default off: no effect).
include barn28.mk
# D367 PS2 world holes (WORLD_HOLE_DIAG; test 11 item E; default off: no effect).
include worldhole.mk
# D367 effect sprite trimming (FX_SPRITE_TRIM; test 11; default off: no effect).
include fxtrim.mk
# D367 frame pacing (PACE_CATCHUP; default off: no effect).
include pace.mk
# Frozen source candidate controls, after all prerequisite defaults.
include demo_candidate.mk
# D367 post30 (Filter00 contrast pass / dither; default off: no effect).
include post30.mk
# D367 lane crowd (CROWD_CULL, CROWD_CENSUS, CROWD_DRAW_MAX / _M; default off: no effect).
include crowd.mk
include g1parts.mk
include actor_ganado_ps2_stump.mk
# D367 generic native models (NATIVE_MODEL_REGISTRY; default off: no effect).
include native_model_registry.mk
# Lane actorplan17: ACTOR_PLAN (character draw plan) and ACTOR_PROF (diagnostic profiler); default off: no effect.
include actorplan.mk
# Lane qws19: QUICK_WEAPON (X + D-pad weapon shortcuts; default off: no effect).
include quickweapon.mk
# D367 charbake (CHARBAKE_HAIR, CHARBAKE_TOGGLE; default off: no effect).
include charbake.mk
# D367 ps2leon (PS2_LEON test arms; default off: no effect).
include ps2leon.mk
include vmu_context.mk
# Lane t2exact (GC_CENSUS_TRIM ...; default off: no effect).
include t2exact.mk
# Lane scenery19 (SCENERY_CHUNK; default off: no effect).
include scenery19.mk
include scenery_data_variants.mk
include scenery_record_split.mk
include scenery_n256.mk
include worldopt26.mk
# Lane chardraw19 (CHAR_CHUNK; default off: no effect).
include chardraw19.mk
# Lane logiclod20 (LOGIC_LOD_EM, ESP_LOD; default off: no effect).
include logiclod20.mk
# Lane rigid20 (RIGID_CENSUS, RIGID_CHUNK; default off: no effect).
include rigid20.mk
include shotfx20.mk
# Lane cache20 (GAME_SHZ_MEMSET, SQ_OUT, PREF_WALK; default off: no effect).
include cache20.mk
# Lane bodysvc20 (BODY_CORPSE, BODY_IK, BODY_ROUTE, BODY_POSE; default off: no effect). BODY_GRID is in engine_preview.mk.
include bodysvc20.mk
# Resolved knobs for tools/d367/build-r21.sh (re4dc-knobs; builds nothing).
include knobs.mk
include esppool.mk
include mendezfx.mk

# Validate after all knob defaults and included recipes are available.
ifneq ($(MOVIE_WORLD_ARENA_S30),0)
ifneq ($(MOVIE_WORLD_ARENA),1)
$(error MOVIE_WORLD_ARENA_S30 needs MOVIE_WORLD_ARENA=1)
endif
endif
ifeq ($(MOVIE_WORLD_ARENA),1)
ifneq ($(ROUTE_MOVIES)$(ROUTE_MOVIE_YUV)$(PS2_WORLD_DRAW)$(PS2_WORLD_MESH)$(IO_ALIGNED)$(MOVIE_HEAP_EVICT)$(D349_RENDERER_STACK)$(PVR_STREAM),11111111)
$(error MOVIE_WORLD_ARENA=1 needs ROUTE_MOVIES/ROUTE_MOVIE_YUV/PS2_WORLD_DRAW/PS2_WORLD_MESH/IO_ALIGNED/MOVIE_HEAP_EVICT/D349_RENDERER_STACK/PVR_STREAM=1)
endif
ifeq ($(filter 2 3,$(PS2_WORLD_ROOMS)),)
$(error MOVIE_WORLD_ARENA=1 needs PS2_WORLD_ROOMS>=2)
endif
endif

# BENCHMARK=1: the public benchmark disc (bench.mk; default 0: nothing compiled, image unchanged)
include bench.mk
# QA_MENU=1: the tester QA disc menu (qamenu.mk; default 0: nothing compiled, image unchanged)
include qamenu.mk
# QA_LINK=1 (lane qalink27; QA discs only): the QA remote link over the modem (qalink.mk)
include qalink.mk

# Isolated bounded A/B/C memory experiment; default 0.
include worldscratch.mk

# Pinned KOS whole-cache writeback repair; default 0, shared KOS untouched.
include kos_cache_p2.mk

# World programme Gate 0, diagnostic only; default 0.
include world_census24.mk
include world_census24_errors.mk
include perf_phase_miss.mk
include draw_setup_audit.mk
include draw_fallback_audit.mk
include fallback_audit29.mk
# Default-off bounded continuation for the existing ordered line collision walk.
include line_resume29.mk
include fallback_audit35.mk
include fallback_scan29.mk
include world_plan29.mk
include actor_format32.mk
include static_obj_batch33.mk
# GC-ASSET diagnostics: default 0, no linked object/flags when off.
include gc_asset_gate.mk
# WEAPON_WEP04_OVL (above): the Blacktail overlay section goes last, after every other overlay (route, stage, sub screen).
ifeq ($(WEAPON_WEP04_OVL),1)
export RE4DC_LINK_OVERLAY += .ovl_wep04
endif
