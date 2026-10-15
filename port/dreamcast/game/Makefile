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
PLATFORM_SRCS = $(wildcard platform/*.cpp)
ifneq ($(VMU_CONTEXT),1)
PLATFORM_SRCS := $(filter-out platform/vmu_lcd.cpp,$(PLATFORM_SRCS))
endif
# SDK units compiled from the game's src/lib with the CodeWarrior asm bodies
# stripped (platform/sdk/strip_cw_asm.py) over the shim headers in platform/sdk.
SDK_UNITS = mtx mtxvec mtx44 vec quat OSAlloc
SDK_GEN = $(addprefix platform/sdk/gen/,$(addsuffix .c,$(SDK_UNITS)))

OBJDIR = obj

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
# PS2_ENEMY_RULES=1 (test 9 lane PS2EN, default 0; changes gameplay by design): the PS2 USA enemy rules of the
# chapter 1 rooms. Enemy list emleon00 gets the PS2 start-alive bits / flags (stage.cpp, at list read); r101 sends
# its reset waves when fewer than 5 Ganados are alive (GameCube: after 5 / 10 kills) and holds two villagers back
# as reinforcements (fewer than 9 alive, PS2 area 0x21); r107 holds three Ganados and five fish until PS2 areas
# 6 / 7 / 8. r103 (3 cows, 3 chickens) and r10a (2 snakes) only lose list entries the PS2 never spawns.
PS2_ENEMY_RULES ?= 0
ifneq ($(PS2_ENEMY_RULES),0)
$(OBJDIR)/src/game/stage.o $(OBJDIR)/mod/st1_1/src/st1/r101.o $(OBJDIR)/mod/st1_1/src/st1/r107.o: GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_RULES=$(PS2_ENEMY_RULES)
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
ifneq ($(ALIVE_CAP),0)
ALIVE_CAP_R101 := $(shell [ $$(( ($(PS2_ENEMY_ROOMS)) & 2 )) -ne 0 ] && echo 1 || echo 0)
ifneq ($(filter-out 0 $(ALIVE_CAP),$(R101_ALIVE_CAP)),)
$(error ALIVE_CAP=$(ALIVE_CAP) with R101_ALIVE_CAP=$(R101_ALIVE_CAP): set ALIVE_CAP only (it sets r101's cap too))
endif
ifeq ($(ALIVE_CAP_R101),1)
R101_ALIVE_CAP := $(ALIVE_CAP)
endif
$(OBJDIR)/src/game/em_set.o $(OBJDIR)/src/game/sce_com.o $(OBJDIR)/src/game/sce_sys.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP=$(ALIVE_CAP) -DRE4DC_ALIVE_CAP_R101=$(ALIVE_CAP_R101) -DRE4DC_ALIVE_CAP_LOG=$(ALIVE_CAP_LOG)
ifneq ($(or $(ALIVE_CAP_PARK),0),0)
$(OBJDIR)/src/game/em_set.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_PARK=1
endif
# Room modules that call the shared PS2 far delete (include/em_far_delete.h: r301 / r327) see the cap's held
# entries (RE4DC_ALIVE_CAP_ON; only that header tests it).
$(OBJDIR)/mod/%.o: GAME_CPPFLAGS += -DRE4DC_ALIVE_CAP_ON=1
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
$(OBJDIR)/mod/st1_1/src/st1/r101.o: GAME_CPPFLAGS += -DRE4DC_R101_ALIVE_CAP=$(R101_ALIVE_CAP) -DRE4DC_R101_CAP_LOG=$(R101_CAP_LOG)
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
$(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_STR_ENT_MAX=32
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
ifeq ($(PS2_ENEMY_RULES),1)
ifeq ($(wildcard $(PS2_ENEMY_CH22_DIR)/ps2_enemy_ch22_data.inc),)
$(error ROUTE_CH22 with PS2_ENEMY_RULES needs qualified PS2_ENEMY_CH22_DIR/ps2_enemy_ch22_data.inc)
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
ifneq ($(ROUTE_CH23),0)
ifneq ($(ROUTE_CH23)$(ROUTE_CH21)$(ROUTE_OVL),111)
$(error ROUTE_CH23 must be 0 or 1 and needs ROUTE_CH21=1 ROUTE_OVL=1)
endif
MODULES += em3b:ovl em35:ovl st2_0
export RE4DC_LINK_OVERLAY += .ovl_em3b .ovl_em35
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH23=1
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH23=1
ROUTE_CH23_ROOM_OBJS = $(OBJDIR)/mod/st1_3/src/st1/r10f.o $(OBJDIR)/mod/st1_3/src/st1/r11d.o \
    $(OBJDIR)/mod/st1_3/src/st1/r11e.o $(OBJDIR)/mod/st1_3/src/st1/r11f.o $(OBJDIR)/mod/st2_0/src/st2/r200.o
$(ROUTE_CH23_ROOM_OBJS) $(OBJDIR)/src/game/stage.o $(OBJDIR)/mod/em3b/src/em3b/em3b.o $(OBJDIR)/mod/em35/src/em35/em35.o: GAME_CPPFLAGS += -DRE4DC_ROUTE_CH23=1
# These room-local callbacks need the same generated movie policy as earlier chapters.
ROUTE_MOVIE_GAME_CH23 = $(OBJDIR)/mod/st1_3/src/st1/r11f.o $(OBJDIR)/mod/st2_0/src/st2/r200.o
# Existing export alias needed by r200, without enabling the unrelated world-test module set.
$(OBJDIR)/src/game/EtcModel.o: GAME_CPPFLAGS += -DRE4DC_WORLD_STAGE_MODULES=1
ifeq ($(PS2_ENEMY_RULES),1)
ifeq ($(wildcard $(PS2_ENEMY_CH23_DIR)/ps2_enemy_ch23_data.inc),)
$(error ROUTE_CH23 with PS2_ENEMY_RULES needs qualified PS2_ENEMY_CH23_DIR/ps2_enemy_ch23_data.inc)
endif
$(ROUTE_CH23_ROOM_OBJS): GAME_CPPFLAGS += -DRE4DC_PS2_ENEMY_RULES=1
$(OBJDIR)/platform/ps2_enemy_ch23.o: PLATFORM_CPPFLAGS += -DRE4DC_ROUTE_CH23=1 -DRE4DC_PS2_ENEMY_RULES=1 -I$(PS2_ENEMY_CH23_DIR)
$(OBJDIR)/platform/ps2_enemy_ch23.o: $(PS2_ENEMY_CH23_DIR)/ps2_enemy_ch23_data.inc
endif
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
MODULES += st3_0 st3_1 st3_2 st3_3 em1d:ovl em1e:ovl em25:ovl
export RE4DC_LINK_OVERLAY += .ovl_em1d .ovl_em1e .ovl_em25
# em36 (85: r306..r310, r326) and em1f (109: r304 / r30b / r30c / r30f / r311 / r321 / r330 Ganados) room overlays.
MODULES += em36:ovl em1f:ovl
export RE4DC_LINK_OVERLAY += .ovl_em36 .ovl_em1f
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
ROUTE_MOVIE_GAME_CH3 = $(OBJDIR)/mod/st3_0/src/st3/r300.o
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
# WEAPON_HEAP4=1 (option 3 of issue lamb2k/re4dc#1, default 0: no effect): a weapon body larger than the resident
# weapon block (WEAPON_RESIDENT_BYTES; the r104 merchant's rifle 398,144 / with scope 404,608, rocket launcher
# 382,688, TMP 289,248 / with stock 299,200) is read into heap 4, the room heap, as Krauser's body goes to
# Game.pWepBuf (read.cpp ReadWepData); bodies that fit keep the resident block. Released before each room heap
# rebuild and read again by the next room's player constructor (one extra GD read per door while it is equipped).
# Heap 4 short after one motion-key eviction pass: the equip is reverted to the previously loaded weapon (or bare
# hands), item state included ("weapon heap4 alloc failed"). A route movie short of heap 4 borrows the body and
# returns it after the movie. WEAPON_HEAP4_FAILTEST=1 (test only): every heap-4 weapon allocation fails.
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
WORLD_ROOM_MODULES ?= 0
ifneq ($(WORLD_ROOM_MODULES),0)
ifneq ($(WORLD_ROOM_MODULES)$(WORLD_STAGE_MODULES),11)
$(error WORLD_ROOM_MODULES must be 0 or 1, and 1 needs WORLD_STAGE_MODULES=1)
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
EM10_GROUP = $(filter em12 em15 em13 em17 em11 $(if $(filter 1,$(EM1F_SHARED)),em1f),$(MODULES))
MODULE_ARGS = $(if $(and $(filter 1,$(EM10_SHARED)),$(strip $(EM10_GROUP))),$(filter-out $(EM10_GROUP),$(MODULES)) em10g=$(subst $(eval) ,+,$(strip $(EM10_GROUP))),$(MODULES))
MODULE_OBJS =
MODULES_MK = $(OBJDIR)/modules.mk
GAME_OBJS = $(patsubst $(ROOT)/%.cpp,$(OBJDIR)/%.o,$(GAME_SRCS))
CENSUS_OBJS = $(patsubst $(ROOT)/%.cpp,$(OBJDIR)/%.o,$(CENSUS_SRCS))
PLATFORM_OBJS = $(patsubst %.cpp,$(OBJDIR)/%.o,$(PLATFORM_SRCS))
ifneq ($(ROUTE_CH22)$(PS2_ENEMY_RULES),11)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/ps2_enemy_ch22.o,$(PLATFORM_OBJS))
endif
ifneq ($(ROUTE_CH23)$(PS2_ENEMY_RULES),11)
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/ps2_enemy_ch23.o,$(PLATFORM_OBJS))
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
DISC_READ_FALLBACK ?= 0
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
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_READ_FALLBACK=$(DISC_READ_FALLBACK) -DRE4DC_DISC_FAIL_TEST=$(DISC_FAIL_TEST) -DRE4DC_DISC_READ_VERIFY=$(DISC_READ_VERIFY)
endif
ifeq ($(DISC_READ_FALLBACK),1)
$(OBJDIR)/src/game/snd.o: GAME_CPPFLAGS += -DRE4DC_DISC_READ_FALLBACK=1
endif
ifeq ($(DISC_GD_ATOMIC),1)
GAME_LDFLAGS += -Wl,--wrap=syscall_gdrom_check_drive -Wl,--wrap=syscall_gdrom_send_command -Wl,--wrap=syscall_gdrom_check_command -Wl,--wrap=syscall_gdrom_exec_server -Wl,--wrap=syscall_gdrom_abort_command -Wl,--wrap=syscall_gdrom_dma_callback -Wl,--wrap=syscall_gdrom_dma_transfer -Wl,--wrap=syscall_gdrom_dma_check -Wl,--wrap=syscall_gdrom_pio_callback -Wl,--wrap=syscall_gdrom_pio_transfer -Wl,--wrap=syscall_gdrom_pio_check
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DISC_GD_ATOMIC=1
endif
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_DVD_READ_SAFE=$(DVD_READ_SAFE) -DRE4DC_DVD_STUCK_TEST=$(DVD_STUCK_TEST) -DRE4DC_DVD_STUCK_ADDR=$(DVD_STUCK_ADDR)
else
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/dvd_read_safe.o,$(PLATFORM_OBJS))
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
	@printf '#define RE4DC_CABIN_SOURCE %s\n#define RE4DC_CABIN_HANDOFF_DIAG %s\n#define RE4DC_CABIN_COMPLETE_HANDOFF %s\n' '$(CABIN_SOURCE)' '$(CABIN_HANDOFF_DIAG)' '$(CABIN_COMPLETE_HANDOFF)' > $@.tmp
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
.PHONY: movie-world-arena-force
$(OBJDIR)/movie-world-arena.h: movie-world-arena-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_MOVIE_WORLD_ARENA %s\n' '$(MOVIE_WORLD_ARENA)' > $@.tmp
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
ROUTE_MOVIE_GAME = $(OBJDIR)/src/game/game.o $(OBJDIR)/mod/st1_0/src/st1/r100.o $(OBJDIR)/mod/st1_1/src/st1/r101.o $(OBJDIR)/mod/st1_1/src/st1/r102.o $(OBJDIR)/mod/st1_1/src/st1/r104.o $(OBJDIR)/mod/st1_1/src/st1/r105.o $(OBJDIR)/mod/st1_1/src/st1/r106.o $(OBJDIR)/mod/st1_1/src/st1/r10b.o $(OBJDIR)/route_movie_bridge.o $(ROUTE_MOVIE_GAME_CH21) $(ROUTE_MOVIE_GAME_CH22) $(ROUTE_MOVIE_GAME_CH23) $(ROUTE_MOVIE_GAME_CH3)
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

# D44 diagnostic only: one four-frame window after an observed r200 card exit.
# Keep the flag local to the three instrumented translation units.
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
# Direct-slot consumers reviewed for this module set. Audit any newly linked
# module before enabling sparse enemy backing; census/reference remain usable.
# CH23 em3b/em35: guarded default-initialization and sparse scans reviewed; stage st2_0 already audited.
CH23_AUDITED_MODULES = $(if $(filter 1,$(ROUTE_CH23)),em3b:ovl em35:ovl)
# Luis preserves its archive pointers and both manager scans use workAt (CH22 guarded adapter).
CH22_AUDITED_MODULES = $(if $(filter 1,$(ROUTE_CH22)),pl14:ovl)
# CH3 st3_0..st3_3 / em1d / em1e: discover --fix value-init and slot-math traps rewritten; em3b as CH23.
CH3_AUDITED_MODULES = $(if $(filter 1,$(ROUTE_CH3)),st3_0 st3_1 st3_2 st3_3 em1d:ovl em1e:ovl em25:ovl em3b:ovl em36:ovl em1f:ovl)
ifeq ($(ENEMY_DEMAND),1)
ifneq ($(filter-out st1_0 st1_1 st1_2 st1_3 wep02 em12 em23 em15 em26 em28 em21 em2a em29 em2e em13 em27 st2_0 st4_0 pl11 st2_2 em1f em18 em17 em24 pl0f em2f pl0f:ovl em2f:ovl em22:ovl em2b:ovl pl11:ovl em11 wep01 wep07 wep09 wep11 wep13 wep19 $(CH23_AUDITED_MODULES) $(CH22_AUDITED_MODULES) $(CH3_AUDITED_MODULES),$(MODULES)),)
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
ifneq ($(filter-out 0 1 2,$(UI_FRAG_WINDOW)),)
$(error UI_FRAG_WINDOW must be 0, 1 or 2)
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
# PRELOAD_LARGE_FIRST=1 (lane vram12 D5, render only, default 0; needs TEX_RESIDENT=1): the room-entry preload loads its
# picks of 16 KiB or more first, then the rest (two forward sweeps in disc order), so small packages do not fragment
# the pool ahead of the large ones.
PRELOAD_LARGE_FIRST ?= 0
# ROOM_RESIDENT=1 (lane vram12 D5, render only, default 0; needs TEX_RESIDENT=1): the room-entry preload also loads
# the room's list in dc/resident.bin (tools/d367/vram/resident_keys.py: the textures its scenes otherwise load on
# first sight), so the room's set is resident from its entry. Without the file the preload is as before.
ROOM_RESIDENT ?= 0
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
	@printf '#define RE4DC_VRAM_ROOM_LOG %s\n' '$(VRAM_ROOM_LOG)' >> $@.tmp
	@printf '#define RE4DC_TEX_META_EVICT %s\n' '$(TEX_META_EVICT)' >> $@.tmp
	@printf '#define RE4DC_PRELOAD_LARGE_FIRST %s\n' '$(PRELOAD_LARGE_FIRST)' >> $@.tmp
	@printf '#define RE4DC_ROOM_RESIDENT %s\n' '$(ROOM_RESIDENT)' >> $@.tmp
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
# HW_FOG_HAZE (lane hwfog 2026-10-14): the distant camera haze as PVR table fog
include hwfog.mk
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
include actor_ganado_ps2_stump.mk
# D367 generic native models (NATIVE_MODEL_REGISTRY; default off: no effect).
include native_model_registry.mk
# D367 charbake (CHARBAKE_HAIR, CHARBAKE_TOGGLE; default off: no effect).
include charbake.mk
# D367 ps2leon (PS2_LEON test arms; default off: no effect).
include ps2leon.mk
include vmu_context.mk
# Resolved knobs for tools/d367/build-r21.sh (re4dc-knobs; builds nothing).
include knobs.mk

# Validate after all knob defaults and included recipes are available.
ifeq ($(MOVIE_WORLD_ARENA),1)
ifneq ($(ROUTE_MOVIES)$(ROUTE_MOVIE_YUV)$(PS2_WORLD_DRAW)$(PS2_WORLD_MESH)$(IO_ALIGNED)$(MOVIE_HEAP_EVICT)$(D349_RENDERER_STACK)$(PVR_STREAM),11111111)
$(error MOVIE_WORLD_ARENA=1 needs ROUTE_MOVIES/ROUTE_MOVIE_YUV/PS2_WORLD_DRAW/PS2_WORLD_MESH/IO_ALIGNED/MOVIE_HEAP_EVICT/D349_RENDERER_STACK/PVR_STREAM=1)
endif
ifeq ($(filter 2 3,$(PS2_WORLD_ROOMS)),)
$(error MOVIE_WORLD_ARENA=1 needs PS2_WORLD_ROOMS>=2)
endif
endif
