# E1 game image (lane eng-e1): engine core + services + the hosted original player/camera behaviour.
# One image: engine plus the hosted list (SHELL_MAP section 5, build layout). The bench image stays engine only.
#
#   make -C port/dreamcast/engine/game OUT=<dir>            -> <dir>/e1.elf
#
# Hosted files are compiled from src/ unchanged with the reference build's code-generation flags (the old game's
# GAME_CPPFLAGS without any RE4DC_ define): same FP contraction (off), -fwrapv, -O2, so their arithmetic matches the
# reference trace's. Engine C++ that ports original service arithmetic (services/) uses the same flags.
OUT ?= build
ROOT := $(abspath ../../../..)
ENG := $(abspath ..)
SHZ := $(ROOT)/port/dreamcast/game/third_party/sh4zam/include
include hosted.mk

ORIG_FLAGS := -ffunction-sections -fdata-sections -std=gnu++20 -fpermissive -w -O2 -ffp-contract=off -fwrapv -fno-strict-aliasing \
	-fno-delete-null-pointer-checks -fno-isolate-erroneous-paths-dereference \
	-fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-threadsafe-statics -fno-rtti
# Lane eng-e2d (the split check, tools/engine/split_check.py): every object compiled with ORIG_FLAGS writes the
# compiler's own inlining report beside it (<object>.inl.txt) and records its flags in the object (.GCC.command.line);
# check_link.py runs the split check on every hosted object of the map and refuses one without its report. Neither
# option changes the code. ORIG_FLAGS becomes a recursive variable so that $@ is the object being built.
#   A hosted unit some of whose functions the engine replaces (made weak, so the engine's strong body is linked) is
# compiled without the interprocedural optimisations (SPLIT_NOIPA: no inlining of non-inline functions, no partial
# inlining, no clones, and no caller trusting what it saw of a callee: its clobbered registers, purity, memory effects,
# value ranges). The units: SPLIT_NOIPA_UNITS (here and in fight.mk); the split check refuses a unit with a replaced
# function that lacks any of these flags (read from its .GCC.command.line), so a unit missing from the list fails.
SPLIT_REPORT = -fopt-info-inline-optimized=$@.inl.txt -frecord-gcc-switches
SPLIT_NOIPA := -fno-inline-functions -fno-inline-small-functions -fno-partial-inlining -fno-ipa-cp -fno-ipa-sra \
	-fno-ipa-icf -fno-ipa-ra -fno-ipa-pure-const -fno-ipa-modref -fno-ipa-reference -fno-ipa-vrp -fno-ipa-bit-cp
# (the camera units and objWep, pl_debug: functions made weak; pl_sub, pl_npc, wep02, em_set, game and the boss image's
# em2b, emtree, emtorch, obj20: manager members the engine pool defines under the original's names; em_sub, dmg in the
# fight and boss images; em10, sce_com, sce_at: fight.mk)
SPLIT_NOIPA_UNITS := game/objWep game/pl_debug game/cam_ctrl game/cam_qfps game/cam_extra game/pl_sub game/pl_npc \
	wep02/wep02 game/em_sub game/dmg game/em_set game/game em2b/em2b game/emtree game/emtorch game/obj20
# (lane eng-e2c's r119: its three thunder functions made weak by services/boss/r119_weak.h, the engine's in
# services/boss/r119_thunder.cpp; game/r119_split_check.py also runs on the object in boss.mk)
SPLIT_NOIPA_UNITS += st1/r119
# (lane eng-mem1: the waived sound driver's game/snd, whose SndRoomStrStop, SndStop and the fade calls the fight and boss
# images' sound stubs replace: the split check found them inlined, H-025.1's group)
SPLIT_NOIPA_UNITS += game/snd
# dmg's cDmg::beginEvent destroys its volume through the manager's destroy, which the shared header declares inline:
# GCC inlined the original's body there, which the engine's table (services/volumes/dmg_vol.cpp) replaces. dmg is
# built with no inlining at all, so the call reaches the engine's.
SPLIT_NOINLINE_UNITS := game/dmg
ORIG_FLAGS_BASE := $(ORIG_FLAGS)
SPLIT_UNIT = $(patsubst $(OUT)/h/%.o,%,$@)
ORIG_FLAGS = $(ORIG_FLAGS_BASE) $(SPLIT_REPORT) \
	$(if $(filter $(SPLIT_UNIT),$(filter-out $(SPLIT_IPA),$(SPLIT_NOIPA_UNITS))),$(SPLIT_NOIPA)) \
	$(if $(filter $(SPLIT_UNIT),$(filter-out $(SPLIT_IPA),$(SPLIT_NOINLINE_UNITS))),-fno-inline)
# Control build only, never a default: SPLIT_IPA=<unit>... compiles those units with the interprocedural optimisations
# back on (the split check must FAIL on each one that has a replaced function).
ORIG_INC := -include $(ENG)/host/e1_prelude.h -I$(ROOT)/include -I$(ROOT)/src -I$(ENG)/host
# Engine C++ (core, host adapters, services): the original headers for the record layouts, warnings on.
ENG_FLAGS := -ffunction-sections -fdata-sections -std=gnu++20 -fpermissive -O2 -ffp-contract=off -fwrapv -fno-strict-aliasing -Wall -Wno-unused \
	-fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-threadsafe-statics -fno-rtti -g
# Renderer (C, from the E0 bench): the bench's flags.
REND_FLAGS := -g -std=gnu11 -Wall -Wdouble-promotion -fno-strict-aliasing -ffast-math -mfsca -mfsrra -DNDEBUG \
	-I$(ENG)/render -I$(SHZ) -DRE4DC_ACTOR_LIGHT_N16=1 -DM1_NATIVE -O2

HOSTED_OBJS := $(addprefix $(OUT)/h/,$(addsuffix .o,$(HOSTED_SRCS) $(SVC_ORIG_SRCS)))
# Lane eng-e1g (eng-svc5 round 5 linked): the SDK math and allocator are the engine's services (services/math/sdk_math,
# services/memory/heap, below); the float functions are the toolchain's newlib (-lm). No src/lib unit is linked, and
# host/e1_math.cpp (the PS* forwarders to the SDK's C bodies) is deleted.
ENG_CPP := $(wildcard $(ENG)/core/*.cpp $(ENG)/host/*.cpp $(ENG)/services/*.cpp)
ENG_C := $(wildcard $(ENG)/core/*.c)
# E2 boss slice (lane eng-boss): BOSS=1 builds the El Gigante arena image (game/boss.mk).
ifeq ($(BOSS),1)
include boss.mk
endif
# E2 fight slice (lane eng-e2): FIGHT=1 builds the village square fight image (game/fight.mk).
ifeq ($(FIGHT),1)
include fight.mk
endif
ENG_OBJS := $(patsubst $(ENG)/%.cpp,$(OUT)/e/%.o,$(ENG_CPP)) $(patsubst $(ENG)/%.c,$(OUT)/e/%.o,$(ENG_C))
REND_OBJS := $(OUT)/r/render_e1.o $(OUT)/r/replay_pack.o $(OUT)/r/native_world.o $(OUT)/r/avk_sh4.o $(OUT)/r/stage_sh4.o
ENG_HDRS := $(wildcard $(ENG)/host/*.h $(ENG)/core/*.h $(ENG)/services/*.h)
REND_DEPS := $(wildcard $(ENG)/render/*.inc $(ENG)/render/*.h $(ENG)/services/*.inc)

.PHONY: all
# Service-boundary accounting (host/e1_wraps.cpp): generator draws and service time at the behaviour's entry points.
# Lane eng-e1c: every entry point of the skeleton and collision services the behaviour can call (groups in
# host/e1_wraps.cpp: motion, cloth, parts and palette, collision), the same list for the original units and the native.
WRAP_SYMS := Rnd fRand1_1 fRand0_1 \
    _Z13MotionSetCoreP6cModelPvS1_iiii _ZN6cModel10motionMoveEv MotionMove MotionClear MotionHokan \
    _ZN8cMotBase4moveEv _ZN8cMotBase6adjustEv InverseKinematics ShapeMove \
    _Z15PlClothMoveLeonP6cModelP7PlClothS2_S2_ _Z15PlClothMoveGirlP6cModelP7PlClothS2_S2_ PenClothMove PenClothMove3 \
    PartsWorldPosCalc _ZN6cModel14partsWorldCalcEv _ZN6cModel12partsMatCalcEv _ZN6cModel8matBlendEf \
    _ZN6cModel14partsFixAdjustEv _ZN6cModel12updateOldPosEv _ZN6cModel9matUpdateEv _ZN6cModel11getPartsPtrEi GetPartsAddr \
    _ZN6cModel9setParentEPS_P3VecS2_ _ZN6cModel9setParentEPS_iP3VecS2_ \
    _ZN7cSatMgr5checkEP6cModeli _ZN7cSatMgr8checkAirEP6cModeli _ZN7cSatMgr8getFloorEP3VecffPmi \
    _ZN7cSatMgr8hitCheckEP3VecS1_S1_S1_ii _ZN7cSatMgr9hitCheck2EP3VecS1_S1_Pmii _ZN7cSatMgr12polySphereCkEP3VecS1_fiS1_i \
    EmAtCheck _ZN10cAtariInfo4moveEv \
    _ZN7cPlNeck4moveEv _ZN7cPlBody4moveEv _ZN7cPlayer7moveEyeEv _ZN7cPlayer10shadowCtrlEv _ZN7cPlayer9seqSeCtrlEv \
    _ZN7cPlayer11visibleCtrlEv _ZN6cPlWep4moveEv _ZN7cPlayer8dmgCheckEv _ZN7cPlayer9keyConfigEv \
    _ZN7cPlayer13moveBinocularEv _ZN7cPlayer16subCharLiveCheckEv _ZN7cPlayer9debugMoveEv pl_R0_Move
# lane eng-e1e: the route service's entry points in the services row (host/e1_wraps.cpp; fight.mk wraps them itself)
ifneq ($(FIGHT),1)
WRAP_SYMS += RouteCkToEm RouteCkToPos RouteCkEscEm RouteCkPosToPosDis
endif
# lane eng-e1o (H-017.7): every file open goes through core/play_files.c, which counts the opens during play; lane
# eng-e1p (H-018.4): and the reads on disc-backed handles (fs_read, fs_close drops a handle's mark) and the CD drive's read
# commands the ISO filesystem issues (cdrom_read_sectors_ex, cdrom_stream_start, cdrom_stream_request; cdrom_read_sectors;
# the TOC reads through core/boot.c)
WRAPS := $(foreach s,$(WRAP_SYMS),-Wl,--wrap=$(s)) -Wl,--wrap=cdrom_read_toc -Wl,--wrap=fs_open -Wl,--wrap=fs_read \
	-Wl,--wrap=fs_close -Wl,--wrap=cdrom_read_sectors -Wl,--wrap=cdrom_read_sectors_ex -Wl,--wrap=cdrom_stream_start \
	-Wl,--wrap=cdrom_stream_request
all: $(OUT)/e1.elf

# rnd.cpp with its read-only trace accessor (re4dc_rnd_state: returns the generator state, changes nothing).
$(OUT)/h/game/rnd.o: ORIG_FLAGS += -DRE4DC_LOGIC_TRACE=1
# The partner module's REL entry under its own name (wep02's keeps _prolog).
$(OUT)/h/pl11/pl11.o: ORIG_FLAGS += -D_prolog=pl11_prolog -D_epilog=pl11_epilog -D_unresolved=pl11_unresolved
$(OUT)/h/%.o: $(ROOT)/src/%.cpp $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) -c $< -o $@
	$(if $(PRESENT_$*),sh-elf-objcopy $(foreach f,$(PRESENT_$*),--rename-section .text.$(f)=e1_present) $@)
	$(if $(WEAKEN_$*),sh-elf-objcopy $(foreach f,$(WEAKEN_$*),--weaken-symbol=$(f)) $@)
# Presentation functions (lane eng-e1c, owner 2026-11-19: presentation randomness from an engine-owned generator):
# their code goes to the section e1_present, whose draws host/e1_wraps.cpp answers from the engine generator.
PRESENT_game/pl_class := _ZN7cPlayer13moveEyeNormalEv
PRESENT_game/pl_sub := PlSetDamageSe
# Lane eng-e1d: the aim sway PlWepLockRand is behaviour (it moves Leon and his shots): back on the original generator.
PRESENT_game/pl_wep := wepSetWaterShot
# Diagnostic arm (not a default): AIMSWAY_PRESENT=1 puts the aim sway back on the presentation generator, as images
# before lane eng-e1d drew it (to compare with their traces).
ifeq ($(AIMSWAY_PRESENT),1)
PRESENT_game/pl_wep += PlWepLockRand
endif
PRESENT_game/cam_extra := _ZN11CameraScope4moveEv _ZN12CameraLookAtC2EP6Camera
PRESENT_wep/objRuger := _ZN9cObjRuger12setCartridgeEv
PRESENT_game/pl_npc := _ZN8cSubChar8moveFaceEv
# (Lane eng-e1g: the src/lib SDK units and the game's fdlibm are no longer built here; services/math/sdk_math.cpp,
# services/memory/heap.cpp and the toolchain's newlib float functions stand in. SERVICES.md sections 35-38.)
$(OUT)/e/%.o: $(ENG)/%.cpp $(ENG_HDRS) $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ENG_FLAGS) $(ORIG_INC) -I$(ENG)/render -I$(ENG)/core -I$(ENG)/services $(NATIVE_INC) -c $< -o $@

# ---- Native skeleton and collision services (lane eng-e1c; docs/engine/SERVICES.md section 7) ----
# skel.cpp and col.cpp port the original arithmetic in its order: the hosted units' flags (contraction off). skel_xm.c
# is the bone-chain kernel on SH4ZAM's XMTRX (SH-4 back-end: FTRV).
SVC_DIR := $(ENG)/services
NATIVE_INC := -I$(SVC_DIR)/skeleton -I$(SVC_DIR)/collision -I$(ROOT)/port/dreamcast/game/platform/include
NATIVE_OBJS := $(OUT)/n/skel.o $(OUT)/n/skel_xm.o $(OUT)/n/col.o
# Lane eng-e1d: the native cloth (services/cloth, round 3: cloth.cpp + the SH4ZAM chain kernel cloth_kernel.c; SERVICES.md
# sections 12, 17 and 21), not in the boss image. Its presentation generator is the engine's: host/e1_pres_rng.h is
# force-included and stands in for services/cloth/pres_rng.h (same four functions, same include guard), drawing from
# the engine generator of host/e1_wraps.cpp. pendulum.cpp is not linked (host/e1_svc_stubs.cpp: the wind globals, the
# fallback stubs).
# Lane eng-skel1: the cloth and the native chain object (services/cloth/chain.cpp: SetChain, cObjChain, object kind
# 0x1D) are linked wherever CLOTH_SVC is 1: the default image and the boss image (El Gigante's rope and arm chains, Leon's
# garments). The fight image's lines are lane eng-e2d's: CLOTH_SVC := 1 in fight.mk, and the SetChain / cObjChain stubs out
# of fight/fight_gen_stubs.cpp. host/e1_svc_mem.cpp and host/e1_svc_stubs.cpp follow E1_CLOTH_SVC.
ifneq ($(FIGHT),1)
CLOTH_SVC := 1
endif
ifeq ($(CLOTH_SVC),1)
NATIVE_INC += -I$(SVC_DIR)/cloth
NATIVE_OBJS += $(OUT)/n/cloth.o $(OUT)/n/cloth_kernel.o $(OUT)/n/chain.o
ENG_FLAGS += -DE1_CLOTH_SVC=1
endif
$(OUT)/n/chain.o: $(SVC_DIR)/cloth/chain.cpp $(SVC_DIR)/skeleton/skel.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -c $< -o $@
CLOTH_DEPS := $(SVC_DIR)/cloth/cloth.h $(SVC_DIR)/cloth/cloth_kernel.h $(SVC_DIR)/cloth/pres_rng.h $(ENG)/host/e1_pres_rng.h
$(OUT)/n/cloth.o: $(SVC_DIR)/cloth/cloth.cpp $(CLOTH_DEPS) $(SVC_DIR)/skeleton/skel.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -include $(ENG)/host/e1_pres_rng.h -c $< -o $@
$(OUT)/n/cloth_kernel.o: $(SVC_DIR)/cloth/cloth_kernel.c $(CLOTH_DEPS)
	@mkdir -p $(dir $@)
	kos-cc -O2 -std=gnu11 -Wall -ffp-contract=off -ffunction-sections -fdata-sections -I$(SHZ) -I$(SVC_DIR)/cloth \
		-include $(ENG)/host/e1_pres_rng.h -c $< -o $@
# SKEL_PAL_DRAW (lane eng-e1e): the palette published in the renderer's skinning layout (quantum and sphere scale).
$(OUT)/n/skel.o: $(SVC_DIR)/skeleton/skel.cpp $(SVC_DIR)/skeleton/skel.h $(SVC_DIR)/skeleton/skel_xm.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -DSKEL_PAL_DRAW=1 -c $< -o $@
$(OUT)/n/col.o: $(SVC_DIR)/collision/col.cpp $(SVC_DIR)/collision/col.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -c $< -o $@
$(OUT)/n/skel_xm.o: $(SVC_DIR)/skeleton/skel_xm.c $(SVC_DIR)/skeleton/skel_xm.h
	@mkdir -p $(dir $@)
	kos-cc -O2 -std=gnu11 -Wall -ffp-contract=off -ffunction-sections -fdata-sections -I$(SHZ) -c $< -o $@
# ---- Round-4 native services (lane eng-svc4, wired by lane eng-e1e; docs/engine/SERVICES.md sections 23-31) ----
# Actor volumes, collision response and managers, routes, the root-motion follower, model records and pools, the
# camera (frustum, tracks, orientation) and input/rumble. Compiled with the hosted units' flags (they port the original
# arithmetic in its order) and linked BEFORE the hosted objects, so a header inline both define is taken from them.
# The original units they retire are not linked at all (hosted.mk): model, motion, cMotBase, atari, atariInfo, at_mod,
# at_sub, pad, route_ck, view, camera, cam_motion, cam_sys. The split behaviour units cam_ctrl, cam_qfps and cam_extra stay
# hosted with every global symbol the native objects define made weak in them (SPLIT_UNITS below), so each call
# reaches the native body and --gc-sections drops the original's.
SVC4_SRCS := volumes/volumes collision/col_model routes/routes motion/follow model/model_svc camera/camera_svc input/input
# lane eng-e1j (H-016.1): the camera service's evaluation under the controller (services/camera/cam_eval.cpp)
SVC4_SRCS += camera/cam_eval
# lane eng-e1h (H-014.4): the character and light tables on the engine's record pool (services/model/mgr_pool.cpp)
SVC4_SRCS += model/mgr_pool
# lane eng-e1h: the Ganado's dissolving-corpse squash on the native skeleton (services/skeleton/em_compress.cpp; the
# hosted em10's body made weak below)
SVC4_SRCS += skeleton/em_compress
SVC4_OBJS := $(addprefix $(OUT)/n/,$(addsuffix .o,$(notdir $(SVC4_SRCS))))
SVC4_INC := $(foreach d,$(sort $(dir $(SVC4_SRCS))),-I$(SVC_DIR)/$(d))
# lane eng-e1j: the camera service is on SH4ZAM's types (services/camera/cam_math.h)
NATIVE_INC += $(SVC4_INC) -I$(SHZ)
define SVC4_RULE
$(OUT)/n/$(notdir $(1)).o: $(SVC_DIR)/$(1).cpp $(wildcard $(SVC_DIR)/$(dir $(1))*.h) $(SVC_DIR)/model/pool.h $(ENG)/host/e1_prelude.h
	@mkdir -p $$(dir $$@)
	kos-c++ $$(ORIG_FLAGS) $$(ORIG_INC) $$(NATIVE_INC) -c $$< -o $$@
endef
$(foreach s,$(SVC4_SRCS),$(eval $(call SVC4_RULE,$(s))))
# Control build only (lane eng-e1g): PAD_EXTRA=-DE1_PAD_NOCLAMP=1 takes the pad clamp out of the input service (the
# village plays-right comparison must then split from the reference at tick 424). Never a default.
$(OUT)/n/input.o: ORIG_FLAGS += $(PAD_EXTRA)
# Control build only (lane eng-e1h): MGR_EXTRA=-DE1_MGR_ORIG_CREATEBACK=1 leaves cManager<cEm>::createBack to pl_sub's
# original template copy (the link check must then FAIL on it). Never a default.
# -fno-inline: the table's header inlines (cEmMgr::memClear) are emitted in this object, which links before the hosted
# units, so the table's vtable reaches the engine's copy (services/model/mgr_pool.cpp).
$(OUT)/n/mgr_pool.o: ORIG_FLAGS += -fno-inline $(MGR_EXTRA)
# ---- The native weapon-target query (lanes eng-e1f, eng-e1g; services/aim/aim.cpp: GetWepTargetPos, the laser's end,
# target and surface) in every image. Where em_sub is hosted (FIGHT=1, BOSS=1) its own GetWepTargetPos is made weak
# (WEAKEN_<unit> in the hosted rule) so the native body is linked and --gc-sections drops the original's.
AIM_OBJ := $(OUT)/n/aim.o
$(AIM_OBJ): $(SVC_DIR)/aim/aim.cpp $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -I$(SHZ) -c $< -o $@
WEAKEN_game/em_sub := _GetWepTargetPos _GetWepTargetList2   # SH-ELF symbol names carry the leading underscore
# (lane eng-e1k: GetWepTargetList2, the shot's target list, is the native one in every image too)
# Lane eng-e2a: em_sub's hit geometry, attack checks, damage position, blast list, rack and water tests, caught-actor
# follow, debug boxes and blood placement are the engine's (services/aim/em_hit.cpp)
EMSUB_NATIVE := emLinePolyCrossCk emLineCubeCrossCk emLineCapsuleCrossCk emLineAtCk emSphereAtCk EmGetDmPos EmAtkHitCk2 \
	EmAtkHitSubCk2 EmAtkHitCk EmAtkLineHitCk EmRackCk CheckInWater EmCatchMotionMove EmYarareDisp EmDmBloodSet2 \
	EmPlBloodSet2 EmSubBloodSet PlBombHitCk GetWepTargetListBomb
# Control build only (EMSUB_ORIG=<name>): that original em_sub function stays linked, the engine's copy made weak (the
# link check must FAIL on it). Never a default.
WEAKEN_game/em_sub += $(addprefix _,$(filter-out $(EMSUB_ORIG),$(EMSUB_NATIVE)))
ifneq ($(BOSS)$(FIGHT),)
EMHIT_OBJ := $(OUT)/n/em_hit.o
# Lane eng-e2a item 2: the damage volumes (services/volumes/dmg_vol.cpp: the table on the engine pool, its tick, the
# records and the point tests, and DmgMgr itself). dmg.cpp stays hosted for its decisions (set, beginEvent): every
# global symbol the native object defines is made weak in it and its static initialiser is taken out, so DmgMgr is the
# engine's and --gc-sections drops the original bodies. Control build only: DMG_ORIG=1 links dmg.cpp whole (the native
# object left out; the link check must FAIL).
ifneq ($(DMG_ORIG),1)
DMGVOL_OBJ := $(OUT)/n/dmg_vol.o
$(OUT)/h/game/dmg.o: $(ROOT)/src/game/dmg.cpp $(ENG)/host/e1_prelude.h $(DMGVOL_OBJ)
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) -c $< -o $@.orig.o
	sh-elf-objcopy $$(sh-elf-nm -g --defined-only $(DMGVOL_OBJ) | awk 'NF == 3 {print "--weaken-symbol=" $$3}' | sort -u) \
		--remove-section=.init_array --remove-section=.rela.init_array --remove-section=.ctors --remove-section=.rela.ctors \
		$@.orig.o $@
	rm -f $@.orig.o
endif
endif
# Lane eng-e2a item 3: the scenario areas (services/volumes/area_vol.cpp) in the fight image, which no longer hosts
# game/area at all (fight.mk). Control build only: AREA_ORIG=1 hosts game/area again (the link check must FAIL).
ifeq ($(FIGHT),1)
ifneq ($(AREA_ORIG),1)
AREAVOL_OBJ := $(OUT)/n/area_vol.o
endif
endif
$(OUT)/n/area_vol.o: $(SVC_DIR)/volumes/area_vol.cpp $(SVC_DIR)/camera/area_edge.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -c $< -o $@
$(OUT)/n/dmg_vol.o: $(SVC_DIR)/volumes/dmg_vol.cpp $(SVC_DIR)/model/pool.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -c $< -o $@
$(OUT)/n/em_hit.o: $(SVC_DIR)/aim/em_hit.cpp $(SVC_DIR)/aim/hit_shape.h $(SVC_DIR)/camera/cam_math.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -I$(SHZ) -c $< -o $@
	$(if $(EMSUB_ORIG),sh-elf-objcopy $(foreach f,$(EMSUB_ORIG),--weaken-symbol=_$(f)) $@)
# Lane eng-e1h (H-014.3): the laser sight's drawing is the engine's (services/laser.cpp: the setters the renderer's
# laser pass reads); objWep's GX bodies are made weak so --gc-sections drops them. drawLaserSight stays hosted.
WEAKEN_game/objWep := _drawPoint _Draw_line3d_local_222 _Draw_line3d_222
# Lane eng-e1h: em10ScaleCompress's squash is the skeleton service's (services/skeleton/em_compress.cpp)
WEAKEN_em10/em10 := __Z17em10ScaleCompressP5cEm10
# Lane eng-e1j: pl_debug's scrHitCheck (a debug ray drawn as lines) is a logged stub (host/e1_stubs.cpp); without partial
# inlining cPlayer::debugMove calls the symbol (not a local clone), so the stub is reached and the body dropped.
WEAKEN_game/pl_debug := __Z11scrHitCheckP7cPlayer
$(OUT)/h/game/pl_debug.o: ORIG_FLAGS += -fno-partial-inlining
# ---- Round-5 native services (lane eng-svc5, linked by lane eng-e1g; SERVICES.md sections 32-38) in every image: the
# math helpers (math_sub, sub2), the garments (pl_cloth's chain set-up and pose), the SDK matrix / vector math and the
# allocator. Compiled with the hosted units' flags (the original's arithmetic in its order) and linked before the
# hosted objects. The garments call the cloth service (PenCloth*): native in the default image, logged stubs in the
# fight and boss images (host/e1_svc_stubs.cpp).
SVC5_SRCS := math/math_svc math/sdk_math cloth/garment memory/heap
SVC5_OBJS := $(addprefix $(OUT)/n/,$(addsuffix .o,$(notdir $(SVC5_SRCS))))
SVC5_INC := -I$(SVC_DIR)/math -I$(SVC_DIR)/cloth -I$(SVC_DIR)/memory -I$(SHZ)
define SVC5_RULE
$(OUT)/n/$(notdir $(1)).o: $(SVC_DIR)/$(1).cpp $(wildcard $(SVC_DIR)/$(dir $(1))*.h) $(ENG)/host/e1_prelude.h
	@mkdir -p $$(dir $$@)
	kos-c++ $$(ORIG_FLAGS) $$(ORIG_INC) $$(NATIVE_INC) $$(SVC5_INC) -c $$< -o $$@
endef
$(foreach s,$(SVC5_SRCS),$(eval $(call SVC5_RULE,$(s))))
$(OUT)/n/svc4_syms.txt: $(SVC4_OBJS)
	sh-elf-nm -g --defined-only $(SVC4_OBJS) | awk 'NF == 3 {print "--weaken-symbol=" $$3}' | sort -u > $@
# lane eng-e1j: cam_qfps is split too (its frame, offset blend, wall probe and offset correction are the camera
# service's); cam_sys is not hosted at all (every function is the service's: hosted.mk)
SPLIT_UNITS := game/cam_ctrl game/cam_qfps game/cam_extra
# Lane eng-e1n (H-017.1): cam_qfps's CameraQuasiFPS::move is the camera service's (services/camera/cam_eval.cpp: it
# calls the unit's decisions and the service's follow), so the unit's copy is weak like the others. cam_extra's camera
# bodies keep their decisions (the push-object camera's door and side) and reach their matrix maths through the camera
# service: the unit's references to the five matrix functions are bound to the service's entry points
# (CAM_UNIT_MATH_<unit>, objcopy --redefine-sym); the link check refuses the unit referencing the SDK's
# (allowed_original.txt "-" lines, read from the map's cross reference).
CAM_UNIT_MATH_game/cam_extra := PSMTXInverse=cam_mtx_inverse PSMTXMultVec=cam_mtx_point PSMTXMultVecSR=cam_mtx_dir \
	PSMTXIdentity=cam_mtx_identity MtxRotAxisPosRad=cam_mtx_turn_about
# Control builds only, never a default: CAM_PUSH_ORIG=1 leaves cam_extra calling the SDK's matrix functions (the link
# check must FAIL on the cross reference); CAM_EXTRA=-DE1_CAM_ORIG_QFPS_MOVE=1 links cam_qfps's own CameraQuasiFPS::move
# (the link check must FAIL on its size ceiling).
ifeq ($(CAM_PUSH_ORIG),1)
CAM_UNIT_MATH_game/cam_extra :=
endif
$(OUT)/n/cam_eval.o: ORIG_FLAGS += $(CAM_EXTRA)
$(addprefix $(OUT)/h/,$(addsuffix .o,$(SPLIT_UNITS))): $(OUT)/h/%.o: $(ROOT)/src/%.cpp $(ENG)/host/e1_prelude.h $(OUT)/n/svc4_syms.txt
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) -c $< -o $@.orig.o
	sh-elf-objcopy $$(cat $(OUT)/n/svc4_syms.txt) $(if $(PRESENT_$*),$(foreach f,$(PRESENT_$*),--rename-section .text.$(f)=e1_present)) \
		$(foreach r,$(CAM_UNIT_MATH_$*),--redefine-sym _$(subst =,=_,$(r))) $(foreach f,$(WEAKEN_$*),--weaken-symbol=$(f)) \
		$@.orig.o $@
	rm -f $@.orig.o
$(OUT)/e/%.o: $(ENG)/%.c $(ENG_HDRS)
	@mkdir -p $(dir $@)
	kos-cc $(REND_FLAGS) -I$(ENG)/core -I$(ENG)/host -I$(ENG)/services -c $< -o $@
$(OUT)/r/render_e1.o: $(ENG)/services/render_e1.c $(REND_DEPS)
	@mkdir -p $(dir $@)
	kos-cc $(REND_FLAGS) -I$(ENG)/services -c $< -o $@
$(OUT)/r/replay_pack.o: $(ENG)/render/replay_pack.c $(REND_DEPS)
	@mkdir -p $(dir $@)
	kos-cc $(REND_FLAGS) -Os -c $< -o $@
$(OUT)/r/native_world.o: $(ENG)/render/native_world.c $(REND_DEPS)
	@mkdir -p $(dir $@)
	kos-cc $(REND_FLAGS) -c $< -o $@
$(OUT)/r/avk_sh4.o: $(ROOT)/port/dreamcast/game/platform/avk_sh4.S
	@mkdir -p $(dir $@)
	kos-cc -c $< -o $@
$(OUT)/r/stage_sh4.o: $(ENG)/render/stage_sh4.S
	@mkdir -p $(dir $@)
	kos-cc -c $< -o $@

# lane eng-loop2: SENDABLE=1 links the console loop's client (loader/sendable.mk) for the console disc and the loader
ifeq ($(SENDABLE),1)
include $(ENG)/loader/sendable.mk
.DEFAULT_GOAL := all
endif
include $(ENG)/game/hosted_corrections.mk $(ENG)/game/game_settings.mk   # lane eng-fix1 (H-026): corrections, settings
include sound.mk
$(OUT)/e1.elf: $(SVC4_OBJS) $(SVC5_OBJS) $(AIM_OBJ) $(EMHIT_OBJ) $(DMGVOL_OBJ) $(AREAVOL_OBJ) $(EM10SVC_OBJS) $(HOSTED_OBJS) $(ENG_OBJS) $(REND_OBJS) $(NATIVE_OBJS) $(CL_SEND_OBJS)
	bash link.sh $@ -g -Wl,-Map=$(OUT)/e1.map -Wl,--cref -Wl,--gc-sections -Wl,-z,start-stop-gc \
		-Wl,--wrap=malloc,--wrap=calloc,--wrap=memalign,--wrap=realloc,--wrap=free $(WRAPS) $(CL_SEND_LDFLAGS) -lm -- $^
