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
ORIG_INC := -include $(ENG)/host/e1_prelude.h -I$(ROOT)/include -I$(ROOT)/src -I$(ENG)/host
# Engine C++ (core, host adapters, services): the original headers for the record layouts, warnings on.
ENG_FLAGS := -ffunction-sections -fdata-sections -std=gnu++20 -fpermissive -O2 -ffp-contract=off -fwrapv -fno-strict-aliasing -Wall -Wno-unused \
	-fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-threadsafe-statics -fno-rtti -g
# Renderer (C, from the E0 bench): the bench's flags.
REND_FLAGS := -g -std=gnu11 -Wall -Wdouble-promotion -fno-strict-aliasing -ffast-math -mfsca -mfsrra -DNDEBUG \
	-I$(ENG)/render -I$(SHZ) -DRE4DC_ACTOR_LIGHT_N16=1 -DM1_NATIVE -O2

HOSTED_OBJS := $(addprefix $(OUT)/h/,$(addsuffix .o,$(HOSTED_SRCS) $(SVC_ORIG_SRCS)))
SDK_UNITS := mtx mtxvec mtx44 vec quat OSAlloc
SDK_OBJS := $(addprefix $(OUT)/sdk/,$(addsuffix .o,$(SDK_UNITS)))
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
WRAPS := $(foreach s,$(WRAP_SYMS),-Wl,--wrap=$(s)) -Wl,--wrap=cdrom_read_toc
all: $(OUT)/e1.elf

# rnd.cpp with its read-only trace accessor (re4dc_rnd_state: returns the generator state, changes nothing).
$(OUT)/h/game/rnd.o: ORIG_FLAGS += -DRE4DC_LOGIC_TRACE=1
# The partner module's REL entry under its own name (wep02's keeps _prolog).
$(OUT)/h/pl11/pl11.o: ORIG_FLAGS += -D_prolog=pl11_prolog -D_epilog=pl11_epilog -D_unresolved=pl11_unresolved
$(OUT)/h/%.o: $(ROOT)/src/%.cpp $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) -c $< -o $@
	$(if $(PRESENT_$*),sh-elf-objcopy $(foreach f,$(PRESENT_$*),--rename-section .text.$(f)=e1_present) $@)
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
# SDK math (mtx, mtxvec, vec) and OSAlloc (the behaviour arena's allocator), generated from src/lib as the reference
# build does (CodeWarrior asm stripped) and compiled with its flags; mtx.c with the reference's exact sincos and
# normalise forms (RE4DC_SINCOS, RE4DC_VEC_NORM_INLINE: bit-identical by construction).
SDK_STRIP := $(ROOT)/port/dreamcast/game/platform/sdk/strip_cw_asm.py
SDK_CF := -w -O2 -ffp-contract=off -fwrapv -fno-strict-aliasing -fno-delete-null-pointer-checks 	-fno-isolate-erroneous-paths-dereference -fschedule-insns -fsched-pressure -ffunction-sections -fdata-sections 	-I$(ROOT)/port/dreamcast/game/platform/sdk -I$(ROOT)/include
$(OUT)/sdk/%.c: $(ROOT)/src/lib/%.c
	@mkdir -p $(dir $@)
	python3 $(SDK_STRIP) $< $@
$(OUT)/sdk/mtx.o: SDK_CF += -DRE4DC_SINCOS=1 -DRE4DC_VEC_NORM_INLINE=1
$(OUT)/sdk/%.o: $(OUT)/sdk/%.c
	kos-cc $(SDK_CF) -c $< -o $@
# The game's recovered fdlibm (src/lib/fdlibm, newlib 1.8.2), as the reference links it (GAME_FDLIBM=1; its
# sinf / cosf are game30_trig.c, bit-identical to sf_sin / sf_cos by construction).
FD_UNITS := ef_acos ef_asin ef_atan2 ef_rem_pio2 ef_sqrt kf_cos kf_rem_pio2 kf_sin kf_tan sf_atan sf_tan sf_sin sf_cos
FD_OBJS := $(addprefix $(OUT)/fd/,$(addsuffix .o,$(FD_UNITS)))
$(OUT)/fd/%.o: $(ROOT)/src/lib/fdlibm/%.c
	@mkdir -p $(dir $@)
	kos-cc -O1 -ffp-contract=off -fwrapv -fno-strict-aliasing -fno-delete-null-pointer-checks 		-fno-isolate-erroneous-paths-dereference -fschedule-insns -fsched-pressure -ffunction-sections -fdata-sections 		-I$(ROOT)/include -c $< -o $@
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
ifeq ($(BOSS)$(FIGHT),)
NATIVE_INC += -I$(SVC_DIR)/cloth
NATIVE_OBJS += $(OUT)/n/cloth.o $(OUT)/n/cloth_kernel.o
endif
CLOTH_DEPS := $(SVC_DIR)/cloth/cloth.h $(SVC_DIR)/cloth/cloth_kernel.h $(SVC_DIR)/cloth/pres_rng.h $(ENG)/host/e1_pres_rng.h
$(OUT)/n/cloth.o: $(SVC_DIR)/cloth/cloth.cpp $(CLOTH_DEPS) $(SVC_DIR)/skeleton/skel.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -include $(ENG)/host/e1_pres_rng.h -c $< -o $@
$(OUT)/n/cloth_kernel.o: $(SVC_DIR)/cloth/cloth_kernel.c $(CLOTH_DEPS)
	@mkdir -p $(dir $@)
	kos-cc -O2 -std=gnu11 -Wall -ffp-contract=off -ffunction-sections -fdata-sections -I$(SHZ) -I$(SVC_DIR)/cloth \
		-include $(ENG)/host/e1_pres_rng.h -c $< -o $@
$(OUT)/n/skel.o: $(SVC_DIR)/skeleton/skel.cpp $(SVC_DIR)/skeleton/skel.h $(SVC_DIR)/skeleton/skel_xm.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -c $< -o $@
$(OUT)/n/col.o: $(SVC_DIR)/collision/col.cpp $(SVC_DIR)/collision/col.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -c $< -o $@
$(OUT)/n/skel_xm.o: $(SVC_DIR)/skeleton/skel_xm.c $(SVC_DIR)/skeleton/skel_xm.h
	@mkdir -p $(dir $@)
	kos-cc -O2 -std=gnu11 -Wall -ffp-contract=off -ffunction-sections -fdata-sections -I$(SHZ) -c $< -o $@
# The original units the native services replace in part: every replaced function made weak (the lists of
# hostref/svc/svc.mk, with the SH symbol prefix), so each call reaches the native body and --gc-sections drops the
# original's. ik.cpp is not linked (hosted.mk).
WEAK_motion := _Z13MotionSetCoreP6cModelPvS1_iiii MotionMove MotionMoveCore MotionMoveSub MotionHokan MotionClear PartsWorldPosCalc \
               MotionGetSpeed MotionGetPosition MotionAddSpeed MotionSequenceCtrl MotionBlendOff MotionPause FcvGetMaxFrame \
               MotionGetMaxFrame MotionGetCurrentFrame MotionCheckCrossFrame MotionGetState
WEAK_model := _ZN6cModel11getPartsPtrEi _ZN6cModel12partsMatCalcEv _ZN6cModel14partsWorldCalcEv _ZN6cModel8matBlendEf \
              _ZN6cModel9matUpdateEv _ZN6cModel12updateOldPosEv _ZN6cModel6setPosEP3Vec _ZN6cModel14partsFixMemoryEi \
              _ZN6cModel14partsFixAdjustEv _ZN6cModel9setParentEPS_P3VecS2_ _ZN6cModel9setParentEPS_iP3VecS2_ \
              _ZN6cModel14setPartsOffsetEPv _ZN6cModel16releasePartsListEi GetPartsAddr
WEAK_atari := _ZN7cSatMgr9hitCheck2EP3VecS1_S1_Pmii _ZN7cSatMgr8hitCheckEP3VecS1_S1_S1_ii _ZN7cSatMgr12polySphereCkEP3VecS1_fiS1_i \
              _Z11at_pos_calcP6cModelP3Vec
$(OUT)/h/game/motion.o $(OUT)/h/game/model.o $(OUT)/h/game/atari.o: $(OUT)/h/game/%.o: $(ROOT)/src/game/%.cpp $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) -c $< -o $@.orig.o
	sh-elf-objcopy $(foreach s,$(WEAK_$*),--weaken-symbol=_$(s)) $@.orig.o $@
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
$(OUT)/e1.elf: $(HOSTED_OBJS) $(SDK_OBJS) $(FD_OBJS) $(ENG_OBJS) $(REND_OBJS) $(NATIVE_OBJS) $(CL_SEND_OBJS)
	bash link.sh $@ -g -Wl,-Map=$(OUT)/e1.map -Wl,--gc-sections -Wl,-z,start-stop-gc \
		-Wl,--wrap=malloc,--wrap=calloc,--wrap=memalign,--wrap=realloc,--wrap=free $(WRAPS) $(CL_SEND_LDFLAGS) -lm -- $^
