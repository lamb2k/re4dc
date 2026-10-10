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
# SDK units compiled from the game's src/lib with the CodeWarrior asm bodies
# stripped (platform/sdk/strip_cw_asm.py) over the shim headers in platform/sdk.
SDK_UNITS = mtx mtxvec mtx44 vec quat OSAlloc
SDK_GEN = $(addprefix platform/sdk/gen/,$(addsuffix .c,$(SDK_UNITS)))

OBJDIR = obj
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
ROUTE_MOVIE_GAME_CH21 = $(OBJDIR)/mod/st1_2/src/st1/r11b.o $(OBJDIR)/mod/st1_2/src/st1/r119.o
endif
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
EM10_GROUP = $(filter em12 em15 em13 em17 $(if $(filter 1,$(EM1F_SHARED)),em1f),$(MODULES))
MODULE_ARGS = $(if $(filter 1,$(EM10_SHARED)),$(filter-out $(EM10_GROUP),$(MODULES)) em10g=$(subst $(eval) ,+,$(strip $(EM10_GROUP))),$(MODULES))
MODULE_OBJS =
MODULES_MK = $(OBJDIR)/modules.mk
GAME_OBJS = $(patsubst $(ROOT)/%.cpp,$(OBJDIR)/%.o,$(GAME_SRCS))
CENSUS_OBJS = $(patsubst $(ROOT)/%.cpp,$(OBJDIR)/%.o,$(CENSUS_SRCS))
PLATFORM_OBJS = $(patsubst %.cpp,$(OBJDIR)/%.o,$(PLATFORM_SRCS))
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
.PHONY: crash-screen-force
$(OBJDIR)/crash-screen.h: crash-screen-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_CRASH_SCREEN %s\n#define RE4DC_PVR_LATCH %s\n' '$(CRASH_SCREEN)' '$(PVR_LATCH)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/fault.o $(OBJDIR)/platform/crash_screen.o $(OBJDIR)/platform/os.o: $(OBJDIR)/crash-screen.h
$(OBJDIR)/platform/fault.o $(OBJDIR)/platform/crash_screen.o $(OBJDIR)/platform/os.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/crash-screen.h
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
.PHONY: route-movies-force
$(OBJDIR)/route-movies.h: route-movies-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_ROUTE_MOVIES %s\n#define RE4DC_ROUTE_MOVIE_YUV %s\n#define RE4DC_ROUTE_MOVIE_TEXHASH %s\n#define RE4DC_ROUTE_MOVIE_DIAG %s\n#define RE4DC_ROUTE_QTE_FRAMES %s\n#define RE4DC_ROUTE_CH13 %s\n' '$(ROUTE_MOVIES)' '$(ROUTE_MOVIE_YUV)' '$(ROUTE_MOVIE_TEXHASH)' '$(ROUTE_MOVIE_DIAG)' '$(ROUTE_QTE_FRAMES)' '$(ROUTE_CH13)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
ROUTE_MOVIE_PLATFORM = $(OBJDIR)/platform/native_movie.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/pad.o
ROUTE_MOVIE_GAME = $(OBJDIR)/src/game/game.o $(OBJDIR)/mod/st1_0/src/st1/r100.o $(OBJDIR)/mod/st1_1/src/st1/r101.o $(OBJDIR)/mod/st1_1/src/st1/r102.o $(OBJDIR)/mod/st1_1/src/st1/r104.o $(OBJDIR)/mod/st1_1/src/st1/r105.o $(OBJDIR)/mod/st1_1/src/st1/r106.o $(OBJDIR)/mod/st1_1/src/st1/r10b.o $(OBJDIR)/route_movie_bridge.o $(ROUTE_MOVIE_GAME_CH21)
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
	kos-cc $(KOS_CFLAGS) -Os -include $(OBJDIR)/route-movies.h -I$(KOS_BASE)/kernel/arch/dreamcast/sound -I$(KOS_BASE)/kernel/arch/dreamcast/include/dc/sound -MMD -MP -c $< -o $@
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
.PHONY: core-budget-force
$(OBJDIR)/core-budget.h: core-budget-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_CORE_RESIDENT_BYTES %s\n' '$(CORE_RESIDENT_BYTES)' > $@.tmp
	@printf '#define RE4DC_OPTION_RESIDENT_BYTES %s\n' '$(OPTION_RESIDENT_BYTES)' >> $@.tmp
	@printf '#define RE4DC_PLAYER_RESIDENT_BYTES %s\n#define RE4DC_WEAPON_RESIDENT_BYTES %s\n' '$(PLAYER_RESIDENT_BYTES)' '$(WEAPON_RESIDENT_BYTES)' >> $@.tmp
	@printf '#define RE4DC_ARENA_KOS_BYTES %s\n' '$(ARENA_KOS_BYTES)' >> $@.tmp
	@printf '#define RE4DC_ARENA_FIT %s\n#define RE4DC_ARENA_FIT_KOS_BYTES %s\n' '$(ARENA_FIT)' '$(ARENA_FIT_KOS_BYTES)' >> $@.tmp
	@printf '#define RE4DC_SOUND_REGION_BYTES %s\n' '$(SOUND_REGION_BYTES)' >> $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/mem.o: $(OBJDIR)/core-budget.h
$(OBJDIR)/platform/mem.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/core-budget.h

# Opt-in backing policy; logical source capacity and cParts layout are unchanged.
PARTS_DEMAND ?= 0
MODELINFO_DEMAND ?= 0
OBJECT_DEMAND ?= 0
ENEMY_DEMAND ?= 0
# Direct-slot consumers reviewed for this module set. Audit any newly linked
# module before enabling sparse enemy backing; census/reference remain usable.
ifeq ($(ENEMY_DEMAND),1)
ifneq ($(filter-out st1_0 st1_1 st1_2 st1_3 wep02 em12 em23 em15 em26 em28 em21 em2a em29 em2e em13 em27 st2_0 st4_0 pl11 st2_2 em1f em18 em17 em24 pl0f em2f pl0f:ovl em2f:ovl em22:ovl em2b:ovl wep01 wep07 wep09 wep11 wep13 wep19,$(MODULES)),)
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
	@cmp -s $@.tmp $@ || cp $@.tmp $@
	@rm -f $@.tmp
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
UI_OVERLAY_SLAB_KB ?= 0
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
	@printf '#define RE4DC_VRAM_PAGES %s\n#define RE4DC_VRAM_CENSUS %s\n' '$(VRAM_PAGES)' '$(VRAM_CENSUS)' >> $@.tmp
	@printf '#define RE4DC_UI_HANDLES %s\n#define RE4DC_UI_HEADERS %s\n' '$(UI_HANDLES)' '$(UI_HEADERS)' >> $@.tmp
	@printf '#define RE4DC_TEX_RESIDENT %s\n#define RE4DC_TEX_RESIDENT_RESERVE_KB %s\n#define RE4DC_TEX_PAYLOAD_CRC %s\n#define RE4DC_TEX_SLOTS %s\n' '$(TEX_RESIDENT)' '$(TEX_RESIDENT_RESERVE_KB)' '$(TEX_PAYLOAD_CRC)' '$(TEX_SLOTS)' >> $@.tmp
	@printf '#define RE4DC_TEX_KEEP %s\n#define RE4DC_PVR_LATCH %s\n' '$(TEX_KEEP)' '$(PVR_LATCH)' >> $@.tmp
	@printf '#define RE4DC_MOVIE_WINDOW %s\n' '$(MOVIE_WINDOW)' >> $@.tmp
	@printf '#define RE4DC_PVR_READY_STRICT %s\n' '$(PVR_READY_STRICT)' >> $@.tmp
	@if [ "$(MOVIE_WINDOW)" = 1 ] && { [ "$(VRAM_PAGES)" != 1 ] || [ "$(TEX_RESIDENT)" != 1 ]; }; then echo 'MOVIE_WINDOW=1 needs VRAM_PAGES=1 TEX_RESIDENT=1' >&2; exit 1; fi
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/model_bridge.o: $(OBJDIR)/pipeline30.h
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/pipeline30.h
ifneq ($(filter 1,$(PVR_LATCH) $(PVR_READY_STRICT)),)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -I$(KOS_BASE)/kernel/arch/dreamcast/hardware/pvr
endif
ifeq ($(PVR_READY_STRICT),1)
GAME_LDFLAGS += -Wl,--wrap=pvr_list_begin -Wl,--wrap=pvr_set_presort_mode
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
$(OBJDIR)/platform/native_model.o: $(OBJDIR)/model-position.h
$(OBJDIR)/platform/native_model.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/model-position.h

# Compact structural plans share the existing native packet slab. No source
# heap reservation and no copied display-list corners.
MODEL_DRAW_PLANS ?= 0
.PHONY: model-draw-plan-force
$(OBJDIR)/model-draw-plan.h: model-draw-plan-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_MODEL_DRAW_PLANS %s\n' '$(MODEL_DRAW_PLANS)' > $@.tmp
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
# D367 scenery30 (PLAN_ADMIT_LEAN, SCENERY_GATE, MODEL_SLAB_LATCH; default off: no effect).
include scenery30.mk
# D367 records30 (FRONT_TEXOBJ; default off: no effect).
include records30.mk
# D367 Blender scenery knobs (TREE_IMPOSTOR; default off: no effect).
include blender30.mk
# D367 TA_HASH (test builds; default off: no effect).
include tahash.mk
# D367 frame pacing (PACE_CATCHUP; default off: no effect).
include pace.mk
# Frozen source candidate controls, after all prerequisite defaults.
include demo_candidate.mk
# D367 post30 (Filter00 contrast pass / dither; default off: no effect).
include post30.mk
# D367 lane crowd (CROWD_CULL, CROWD_CENSUS, CROWD_DRAW_MAX / _M; default off: no effect).
include crowd.mk
# D367 generic native models (NATIVE_MODEL_REGISTRY; default off: no effect).
include native_model_registry.mk
# Resolved knobs for tools/d367/build-r21.sh (re4dc-knobs; builds nothing).
include knobs.mk
