# svc.mk (lane eng-svc), included by hostref/Makefile. The service builds of re4ref (docs/engine/SERVICES.md):
#
#   make census   -> $(BUILD)/census/re4ref   the reference (plain) with the service census: every call across the
#                    service boundary counted (--wrap trampolines, svc/gen_wraps.py), and with RE4_SVC_TRACE=1 every
#                    guest-memory access of each tick traced (svc/svc_trace.cpp). RE4_SVC_OUT=<dir> gets the tables.
#
# The census build links exactly the plain build's objects; only the link adds the trampolines and the census.

# lane eng-svc2: every svc build hosts the original cloth (game/pendulum.cpp; the plain build keeps host_stubs.cpp's
# PenClothSet / PenClothMove / PenClothMove3 stubs, which the svc builds link weakened).
PEN_STUBS := PenClothSet PenClothMove PenClothMove3
# Random numbers are split (owner 2026-11-19): the cloth is presentation and draws from the engine's presentation
# generator, never from the behaviour's Rnd. The hosted original's fRand0_1 / fRand1_1 are renamed to pen_fRand*
# (svc_cloth_glue.cpp: a presentation stream of its own), so both builds leave the behaviour's Rnd untouched.
PEN_RAND := fRand0_1=pen_fRand0_1 fRand1_1=pen_fRand1_1
$(BUILD)/svc/ref/pendulum.o: $(BUILD)/plain/game/pendulum.o svc/svc.mk
	@mkdir -p $(dir $@)
	objcopy $(foreach s,$(PEN_RAND),--redefine-sym $(s)) $< $@
SVC_HG_OBJS := $(filter-out $(BUILD)/plain/host/host_stubs.o,$(plain_HG_OBJS)) $(BUILD)/svc/host_stubs.o $(BUILD)/svc/svc_cloth_glue.o
$(BUILD)/svc/svc_cloth_glue.o: svc/svc_cloth_glue.cpp hostref.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -c $< -o $@
SVC_REF_GAME := $(plain_GAME_OBJS) $(BUILD)/svc/ref/pendulum.o
# lane eng-skel1:
# The chain object (kind 0x1D): the reference builds (odump, census) link the original game/obj1d.cpp, the native builds
# services/cloth/chain.cpp; the plain build's generated stubs of its entry points are weak in the svc builds (svc/ copy).
CHAIN_STUBS := _Z8SetChainPvS_P3VecS1_ _ZN9cObjChain8setChainEP8PenCloth _ZN9cObjChain9setParentEP6cModeliP3Veci
$(BUILD)/svc/host_actor_stubs.o: $(BUILD)/plain/host/host_actor_stubs.o svc/svc.mk
	@mkdir -p $(dir $@)
	objcopy $(foreach s,$(CHAIN_STUBS),--weaken-symbol=$(s)) $< $@
SVC_HG_OBJS := $(filter-out $(BUILD)/plain/host/host_actor_stubs.o,$(SVC_HG_OBJS)) $(BUILD)/svc/host_actor_stubs.o
$(BUILD)/svc/ref/obj1d.o: $(BUILD)/gen/obj1d.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(GAMEFLAGS) -c $< -o $@
SVC_REF_GAME += $(BUILD)/svc/ref/obj1d.o
$(BUILD)/svc/host_stubs.o: $(BUILD)/plain/host/host_stubs.o svc/svc.mk
	@mkdir -p $(dir $@)
	objcopy $(foreach s,$(PEN_STUBS),--weaken-symbol=$(s)) $< $@

CEN := $(BUILD)/census
CENSUS_S_UNITS := model motion cMotBase ik shape pl_cloth atari at_mod at_sub at_sub2 atariInfo route_ck area
CENSUS_M_UNITS := math_sub sub2
CENSUS_OBJS := $(plain_PC_OBJS) $(SVC_HG_OBJS) $(SVC_REF_GAME) $(plain_SDK_OBJS) $(plain_LIBM_OBJS)

$(CEN)/wraps.flags: $(SVC_REF_GAME) $(plain_SDK_OBJS) $(plain_LIBM_OBJS) svc/gen_wraps.py
	@mkdir -p $(CEN)
	$(PY) svc/gen_wraps.py $(CEN)/wraps.S $(CEN)/wrapnames.cpp $@ \
	    $(foreach u,$(CENSUS_S_UNITS),S:$(BUILD)/plain/game/$(u).o) S:$(BUILD)/svc/ref/pendulum.o \
	    $(foreach u,$(CENSUS_M_UNITS),M:$(BUILD)/plain/game/$(u).o) \
	    $(foreach o,$(plain_SDK_OBJS) $(plain_LIBM_OBJS),M:$(o))
$(CEN)/wraps.S $(CEN)/wrapnames.cpp: $(CEN)/wraps.flags
$(CEN)/wraps.o: $(CEN)/wraps.S
	$(CC) -m32 -c $< -o $@
$(CEN)/wrapnames.o: $(CEN)/wrapnames.cpp
	$(CXX) -m32 -c $< -o $@
$(CEN)/svc_trace.o: svc/svc_trace.cpp svc/svc_census.h hostref.h
	@mkdir -p $(CEN)
	$(CXX) $(COMMON) $(FP_plain) $(PCFLAGS) -c $< -o $@
$(CEN)/svc_glue.o: svc/svc_glue.cpp svc/svc_census.h hostref.h
	@mkdir -p $(CEN)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -c $< -o $@
$(BUILD)/plant/svc_plant.o: svc/svc_plant.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(GAMEFLAGS) -c $< -o $@
$(CEN)/re4ref: $(CENSUS_OBJS) $(CEN)/wraps.o $(CEN)/wrapnames.o $(CEN)/svc_trace.o $(CEN)/svc_glue.o $(BUILD)/plant/svc_plant.o aliases.ld
	$(CC) -o $@ $(plain_PC_OBJS) $(SVC_HG_OBJS) $(CEN)/svc_trace.o $(CEN)/svc_glue.o $(BUILD)/plant/svc_plant.o $(CEN)/wraps.o $(CEN)/wrapnames.o \
	    $(SVC_REF_GAME) $(plain_SDK_OBJS) $(plain_LIBM_OBJS) aliases.ld $(LDFLAGS) \
	    $$(cat $(CEN)/wraps.flags) -Wl,--wrap=host_fixed -Wl,-Map=$(CEN)/re4ref.map

census: $(CEN)/re4ref
.PHONY: census

# ---- odump / native (lane eng-svc): the per-tick direct comparison of the original units with the native services
#
#   make odump    -> $(BUILD)/odump/re4ref    the reference (plain objects) + svc_dump: palettes and collision queries
#   make native   -> $(BUILD)/native/re4ref   the native skeleton (services/skeleton) and collision (services/collision)
#                    in place of the original units, + svc_dump. The build switch is the binary: no runtime switch.
#
# native: game/ik.o is not linked; game/motion.o, model.o and atari.o are linked with the functions the native services
# replace made weak (objcopy --weaken-symbol), so every call, from any unit, reaches the native body.
SVC_ENG := $(ROOT)/port/dreamcast/engine/services
SHZ := $(GAME)/third_party/sh4zam
SVC_WRAP_COL := _ZN7cSatMgr8getFloorEP3VecffPmi _ZN7cSatMgr8hitCheckEP3VecS1_S1_S1_ii _ZN7cSatMgr9hitCheck2EP3VecS1_S1_Pmii \
                _ZN7cSatMgr12polySphereCkEP3VecS1_fiS1_i _ZN7cSatMgr5checkEP6cModeli _ZN7cSatMgr8checkAirEP6cModeli
# lane eng-svc4: the round-4 boundary log (svc4_dump.cpp), the same entry points in both builds
SVC4_WRAP := EmAtCheck EmHitCheck ObjHitCheck ObaLineHitChk AtSphereCapsuleCk AtBoxCapsuleCk3 At_box_sphere_ck EatGetEffectType
SVC4_WRAP += At_poly_line_ck YarareInit YarareAdd _ZN10cAtariInfo4moveEv _ZN10cAtariInfo3setEiff _ZN10cAtariInfo11setPriorityEi
SVC4_WRAP += RouteCkToPos RouteCkToEm RouteCkEscEm RouteCkPosToPos RouteCkPosToPosDis RouteCkGetDist RouteCkConnectPosCk getNearPoint getNearInfo RouteCk
SVC4_WRAP += _ZN8cMotBase4moveEv _ZN8cMotBase6adjustEv _ZN8cMotBase3setEP9cMotModelP3VecS3_h
SVC4_WRAP += _ZN6cModel9modelInitEPvS0_ _ZN6cModel9initJointEPv _ZN6cModel13makePartsListEi _ZN6cModel4pushEv
SVC4_WRAP += _ZN6cModel8addModelEP10cModelInfo _ZN6cModel15deleteModelInfoEP10cModelInfo ModelInfoSetTrans
SVC4_WRAP += _ZN6cModel13swapModelInfoEP9ModelDataP10cModelInfo _ZN11cModInfoMgr6createEPvS0_
SVC4_WRAP += _ZN4VIEW15initPerspectiveEffff CameraMove _ZN12CameraMotion4moveEv HermiteInterpolation
SVC4_WRAP += CameraSetOrientationRoll CameraSetOrientationUp _ZN22CameraAttachedToMotion4moveEv
SVC4_WRAP += _ZN13CameraControl13HermiteExportEP9CameraCutPh _Z7BSplineP13CameraBSplineP6Camerai
SVC4_WRAP += _Z11ParametrizeP9CameraCutP13CameraBSpline
SVC4_WRAP += PadRead VibSet KeyStop
SVC4_WRAP += _ZN10cAtariInfo6getPosEP6cModelP3Vec _ZN10cAtariInfo14getSpeedVectorEP6cModelP3VecS3_ _ZN7cEatMgr10getEffInfoEi
# lane eng-e2a: the enemy hit geometry's boundary log (e2_dump.cpp): em_sub.cpp's service entry points and the effect
# starts made inside them
E2_WRAP := emLinePolyCrossCk emLineCubeCrossCk emLineCapsuleCrossCk emLineAtCk emSphereAtCk EmGetDmPos EmAtkHitCk2 	EmAtkHitSubCk2 EmAtkHitCk EmAtkLineHitCk EmRackCk CheckInWater EmCatchMotionMove EmYarareDisp EmDmBloodSet2 	EmPlBloodSet2 EmSubBloodSet PlBombHitCk GetWepTargetListBomb EstSet
# and the damage volumes (dmg_vol.cpp): the point test, the two registrations (hosted in both builds) and the tick
E2_WRAP += _ZN7cDmgMgr8hitCheckEP3VecS1_ _ZN7cDmgMgr3setEiiP3Vecff _ZN7cDmgMgr3setEiiP3Vecf _ZN7cDmgMgr4moveEv
# and the scenario areas (area_vol.cpp)
E2_WRAP += _Z12AreaHitCheckPvP3Vec areaHitCheck_xz4 areaHitCheck_Cylinder AreaViewCheck AreaGetCenterPos AreaGetInsidePos AreaDataInit
# lane eng-e2b: em10's service functions' boundary log (e2b_dump.cpp): the sound entry points (SndCall, SndStop, the
# ctrl11 voice slots under both names, the ctrl12 locks) and the effect table lookups the Ganado's presentation calls
E2B_WRAP := _Z7SndCallttP3VeciiP5cUnit _Z7SndStopmi _Z11Ctrl11SetSeP5cCtrlP6cModelsti _Z12Ctrl11SetSe2P5cCtrlP6cModelstit \
	Ctrl11SetSe2__FP5cCtrlP6cModelsUsiUs _Z18Ctrl11StopAndSetSeP5cCtrlP6cModelsti _Z8Ctrl12CkP5cCtrli _Z9Ctrl12SetP5cCtrlit \
	Ctrl12Set__FP5cCtrliUs EspGetEstAddr EspEstSetSelect
SVC_WRAP_FLAGS := $(foreach s,$(SVC_WRAP_COL) $(SVC4_WRAP) $(E2_WRAP) $(E2B_WRAP),-Wl,--wrap=$(s)) -Wl,--wrap=PenClothSet
WEAK_motion := HermiteInterpolation _Z13MotionSetCoreP6cModelPvS1_iiii MotionMove MotionMoveCore MotionMoveSub MotionHokan MotionClear PartsWorldPosCalc \
               MotionGetSpeed MotionGetPosition MotionAddSpeed MotionSequenceCtrl MotionBlendOff MotionPause FcvGetMaxFrame \
               MotionGetMaxFrame MotionGetCurrentFrame MotionCheckCrossFrame MotionGetState
WEAK_model := _ZN6cModel11getPartsPtrEi _ZN6cModel12partsMatCalcEv _ZN6cModel14partsWorldCalcEv _ZN6cModel8matBlendEf \
              _ZN6cModel9matUpdateEv _ZN6cModel12updateOldPosEv _ZN6cModel6setPosEP3Vec _ZN6cModel14partsFixMemoryEi \
              _ZN6cModel14partsFixAdjustEv _ZN6cModel9setParentEPS_P3VecS2_ _ZN6cModel9setParentEPS_iP3VecS2_ \
              _ZN6cModel14setPartsOffsetEPv _ZN6cModel16releasePartsListEi GetPartsAddr
WEAK_atari := _ZN7cSatMgr9hitCheck2EP3VecS1_S1_Pmii _ZN7cSatMgr8hitCheckEP3VecS1_S1_S1_ii _ZN7cSatMgr12polySphereCkEP3VecS1_fiS1_i \
              _Z11at_pos_calcP6cModelP3Vec
NAT := $(BUILD)/native
ODU := $(BUILD)/odump
NATIVE_REPLACED := $(BUILD)/plain/game/motion.o $(BUILD)/plain/game/model.o $(BUILD)/plain/game/atari.o $(BUILD)/plain/game/ik.o
# lane eng-svc2: the native cloth (services/cloth) gives PenClothSet / Move / Move3 / FixSet / FixClear engine bodies;
# pendulum.o is linked with those five renamed pen_orig_* (the fallback for a chain the service cannot resolve), so
# its volume tests, PenClothMove2 and the wind stay original.
PEN_ORIG := PenClothSet=pen_orig_Set PenClothMove=pen_orig_Move PenClothMove3=pen_orig_Move3 \
            PenClothFixSet=pen_orig_FixSet PenClothFixClear=pen_orig_FixClear
# lane eng-svc4: the native versions of the service units the E1 audit found linked (services/<area>/, SERVICES.md
# sections 23 on). SVC4_OBJS are compiled with the hosted units' flags; every global symbol they define is made weak in
# the original units of SVC4_UNITS (weak4/), so each call reaches the native body; svc4/svc4_units.sh reports which
# original functions of those units the native link still keeps.
# lane eng-svc5 (round 5): the math helpers (services/math: math_sub, sub2) and the garments (services/cloth/garment:
# pl_cloth), linked the same way (SERVICES.md sections 32, 33)
SVC5_SRCS := math/math_svc.cpp cloth/garment.cpp math/sdk_math.cpp
SVC5_UNITS := math_sub sub2 pl_cloth
SVC4_SRCS := volumes/volumes.cpp collision/col_model.cpp routes/routes.cpp motion/follow.cpp model/model_svc.cpp camera/camera_svc.cpp input/input.cpp              $(SVC5_SRCS)
# lane eng-e1h: the Ganado's dissolving-corpse squash on the native skeleton (em10ScaleCompress; em10's own made weak in
# weak6/ below)
SVC4_SRCS += skeleton/em_compress.cpp
# lane eng-e1j (H-016.1): the camera service's evaluation under the controller (services/camera/cam_eval.cpp)
SVC4_SRCS += camera/cam_eval.cpp
# lane eng-e2a: the enemy hit geometry (services/aim/em_hit.cpp: em_sub.cpp's service functions; em_sub is split below)
SVC4_SRCS += aim/em_hit.cpp
# lane eng-e2a: the damage volumes (services/volumes/dmg_vol.cpp: the table on the engine pool, its tick and the point
# tests; dmg is split below, its set / beginEvent stay the behaviour's, and the native file constructs DmgMgr itself)
SVC4_SRCS += volumes/dmg_vol.cpp
# lane eng-e2a item 3: the scenario areas (services/volumes/area_vol.cpp: every area query; area is a replaced unit)
SVC4_SRCS += volumes/area_vol.cpp
# lane eng-e2b: em10's service functions (services/em10/: the presentation and the cut-in cameras; em10 is linked with
# their bodies weak in weak6/ below)
SVC4_SRCS += em10/em10_pres.cpp em10/em10_cam.cpp em10/em10_model.cpp
SVC4_OBJS := $(addprefix $(NAT)/svc4/,$(notdir $(SVC4_SRCS:.cpp=.o)))
# lane eng-e1j: cam_sys is camera maths throughout (the camera service has every function): a replaced unit
SVC4_UNITS := at_mod at_sub atariInfo atari route_ck cMotBase model view camera cam_motion cam_sys motion pad $(SVC5_UNITS) area
# SVC4_SPLIT: behaviour units whose evaluation functions are native (the camera's: cam_ctrl's blend, smoothing, area
# tests, probe, rail and data relocation, cam_qfps's frame, offsets and wall probe, cam_extra's attached camera;
# svc4_split.txt names them): the same weak copy, and svc4_units.sh checks only the named functions
SVC4_SPLIT := cam_ctrl cam_qfps cam_extra
# lane eng-e2a: em_sub (the enemies' shared helpers): its hit geometry is the engine's (svc4_split.txt names it)
SVC4_SPLIT += em_sub dmg
SVC4_ALL := $(SVC4_UNITS) $(SVC4_SPLIT)
SVC4_INC := $(foreach d,$(sort $(dir $(SVC4_SRCS))),-I$(SVC_ENG)/$(d)) -I$(SHZ)/include
# SH4ZAM's headers include <math.h>: the C++ wrapper needs the target-neutral c++config.h of the 64-bit tree (as PCFLAGS)
SVC4_INC += -isystem /usr/include/x86_64-linux-gnu/c++/13
define SVC4_RULE
$(NAT)/svc4/$(notdir $(1:.cpp=.o)): $(SVC_ENG)/$(1) $(wildcard $(SVC_ENG)/$(dir $(1))*.h)
	@mkdir -p $$(dir $$@)
	$(CXX) $(COMMON) $(FP_plain) $$(SVC_GAMEFLAGS) $$(SVC4_INC) -c $$< -o $$@
endef
$(foreach s,$(SVC4_SRCS),$(eval $(call SVC4_RULE,$(s))))
$(NAT)/svc4/syms.txt: $(SVC4_OBJS)
	nm -g --defined-only $(SVC4_OBJS) | awk 'NF == 3 {print "--weaken-symbol=" $$3}' | sort -u > $@
# SVC4_NOINIT: units whose global objects the native file defines and constructs itself: the original's static
# initialiser (.init_array) is taken out of the copy, so --gc-sections drops its constructor calls too.
SVC4_NOINIT := model atari view camera dmg
NOINIT_FLAGS := --remove-section=.init_array --remove-section=.rel.init_array
# lane eng-e1n (H-017.1): cam_extra's camera bodies reach their matrix maths through the camera service, as in the image
# (game/Makefile CAM_UNIT_MATH_game/cam_extra): the unit's references bound to the service's entry points
CAM_UNIT_MATH_cam_extra := PSMTXInverse=cam_mtx_inverse PSMTXMultVec=cam_mtx_point PSMTXMultVecSR=cam_mtx_dir \
	PSMTXIdentity=cam_mtx_identity MtxRotAxisPosRad=cam_mtx_turn_about
$(NAT)/weak4/%.o: $(BUILD)/plain/game/%.o $(NAT)/svc4/syms.txt
	@mkdir -p $(dir $@)
	objcopy $$(cat $(NAT)/svc4/syms.txt) $(foreach s,$(WEAK_$*),--weaken-symbol=$(s)) \
	    $(foreach r,$(CAM_UNIT_MATH_$*),--redefine-sym $(r)) \
	    $(if $(filter $*,$(SVC4_NOINIT)),$(NOINIT_FLAGS)) $< $@
# ---- lane eng-svc5: the native SDK math in re4ref native (services/math/sdk_math.cpp): the SDK's C objects and the old
# port's PS* forwarders (plain/sdk) are linked with every symbol the native objects define made weak (weak5/), as weak4/
# does for the game units, so every PS* / C_* call reaches the engine body and --gc-sections drops the original's.
NAT_SDK_OBJS := $(patsubst $(BUILD)/plain/sdk/%,$(NAT)/weak5/%,$(plain_SDK_OBJS))
$(NAT)/weak5/%.o: $(BUILD)/plain/sdk/%.o $(NAT)/svc4/syms.txt
	@mkdir -p $(dir $@)
	objcopy $$(cat $(NAT)/svc4/syms.txt) $< $@

SVC4_REPLACED := $(addprefix $(BUILD)/plain/game/,$(addsuffix .o,$(SVC4_ALL)))
# the native objects first: a header inline (manager methods, destructors) both define is taken from them
NATIVE_GAME_OBJS := $(SVC4_OBJS) $(filter-out $(NATIVE_REPLACED) $(SVC4_REPLACED),$(plain_GAME_OBJS)) \
                    $(filter-out $(addprefix $(NAT)/weak/,$(addsuffix .o,$(SVC4_ALL))),$(NAT)/weak/motion.o $(NAT)/weak/model.o $(NAT)/weak/atari.o) \
                    $(NAT)/pen.o $(addprefix $(NAT)/weak4/,$(addsuffix .o,$(SVC4_ALL)))
# lane eng-e1h: em10 (the Ganado library) linked with em10ScaleCompress weak, so the native squash
# (services/skeleton/em_compress.cpp, skel_compress_y) is the one reached
WEAK_em10 := _Z17em10ScaleCompressP5cEm10
# lane eng-e2b: and with every em10 service function the engine has (services/em10/) weak, as in the image (game/fight.mk
# EM10_NATIVE). em10 is compiled again from the same host copy for this build, without the interprocedural optimisations
# that could keep a copy of a weakened function in a caller (EM10_NOIPA, as the image), and game/em10_split_check.py
# refuses the object when a clone or an inlined copy of one of em10's service functions is reported.
EM10_NATIVE_PC := Em10SetSeTbl em10CallVoiceSe _Z16em10CallVoiceSe2P5cEm10ii _Z12em10BreathSeP5cEm10 em10CsawSignSe \
	_Z18em10SetDamageVoiceP5cEm10ii em10BehindSeCk _Z10em10FootSeP5cEm10 em10WepSeEffSet _Z12em10BloodSetP5cEm10i \
	_Z12em1cBloodSetP5cEm10i _Z15em10KickHitMarkP5cEm10 _Z17em10SetDmWaterEffP5cEm10i _Z15em10SetWaterEffP5cEm10 \
	em10CamMove _Z12em10CamMove2P5cEm10 em10CamMoveCri em10CamMoveAshley em10CamMoveTakeaway em10SetCampos2 em10ScreenInCk \
	em10SetAccesory em10ClothPartsSet em10GoodsPartsSet em10SackSet em10BlendMotSet _Z11em10HandSetP5cEm10i \
	_Z11em10HeadSetP5cEm10i _Z13em10ModelInitP5cEm10 _ZN5cEm10D0Ev _ZN5cEm10D1Ev _ZN5cEm10D2Ev
WEAK_em10 += $(EM10_NATIVE_PC)
EM10_NOIPA_PC := -fno-inline-functions -fno-inline-small-functions -fno-partial-inlining -fno-ipa-cp -fno-ipa-sra \
	-fno-ipa-icf -fno-ipa-ra -fno-ipa-pure-const -fno-ipa-modref -fno-ipa-reference -fno-ipa-vrp -fno-ipa-bit-cp
$(NAT)/weak6/em10_em10.o: $(BUILD)/gen/em10_em10.cpp svc/svc.mk ../game/em10_split_check.py
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(GAMEFLAGS) $(EM10_NOIPA_PC) -fopt-info-inline-optimized=$@.inl.txt -c $< -o $@.raw.o
	objcopy $(EM10_POSTCC) $(foreach s,$(WEAK_em10),--weaken-symbol=$(s)) $@.raw.o $@
	rm -f $@.raw.o
	$(PY) ../game/em10_split_check.py --nm nm --obj $@ --inline $@.inl.txt --weak $(WEAK_em10)
NATIVE_GAME_OBJS := $(filter-out $(BUILD)/plain/game/em10_em10.o,$(NATIVE_GAME_OBJS)) $(NAT)/weak6/em10_em10.o
SVC_GAMEFLAGS := $(GAMEFLAGS) -I$(SVC_ENG)/skeleton -I$(SVC_ENG)/collision -I$(SVC_ENG)/cloth
$(NAT)/pen.o: $(BUILD)/plain/game/pendulum.o svc/svc.mk
	@mkdir -p $(dir $@)
	objcopy $(foreach s,$(PEN_ORIG) $(PEN_RAND),--redefine-sym $(s)) $< $@
$(NAT)/cloth.o: $(SVC_ENG)/cloth/cloth.cpp $(SVC_ENG)/cloth/cloth.h $(SVC_ENG)/cloth/cloth_kernel.h $(SVC_ENG)/cloth/pres_rng.h $(SVC_ENG)/skeleton/skel.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(SVC_GAMEFLAGS) -c $< -o $@

$(NAT)/weak/%.o: $(BUILD)/plain/game/%.o svc/svc.mk
	@mkdir -p $(dir $@)
	objcopy $(foreach s,$(WEAK_$*),--weaken-symbol=$(s)) $< $@
$(NAT)/skel.o: $(SVC_ENG)/skeleton/skel.cpp $(SVC_ENG)/skeleton/skel.h $(SVC_ENG)/skeleton/skel_mk.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(SVC_GAMEFLAGS) -c $< -o $@
# COL_DEFS: measurement builds of the cell grid's shape (lane eng-svc3: -DCOL_MASK64, -DCOL_GRID_X=..)
$(NAT)/col.o: $(SVC_ENG)/collision/col.cpp $(SVC_ENG)/collision/col.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(SVC_GAMEFLAGS) $(COL_DEFS) -c $< -o $@
$(NAT)/cloth_kernel.o: $(SVC_ENG)/cloth/cloth_kernel.c $(SVC_ENG)/cloth/cloth_kernel.h $(SVC_ENG)/cloth/pres_rng.h
	@mkdir -p $(dir $@)
	$(CC) $(COMMON) $(FP_plain) -std=gnu11 -Wall -I$(SHZ)/include -c $< -o $@
$(NAT)/skel_xm.o: $(SVC_ENG)/skeleton/skel_xm.c $(SVC_ENG)/skeleton/skel_xm.h
	@mkdir -p $(dir $@)
	$(CC) $(COMMON) $(FP_plain) -std=gnu11 -Wall -I$(SHZ)/include -c $< -o $@
$(NAT)/shz_xmtrx_sw.o: $(SHZ)/source/sw/shz_xmtrx_sw.c
	@mkdir -p $(dir $@)
	$(CC) $(COMMON) $(FP_plain) -std=gnu11 -w -I$(SHZ)/include -c $< -o $@
# svc_dump (game side) and svc_io (PC side): one copy, linked by both odump and native
$(BUILD)/svc/svc_dump.o: svc/svc_dump.cpp $(SVC_ENG)/skeleton/skel.h $(SVC_ENG)/collision/col.h $(SVC_ENG)/cloth/cloth.h hostref.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -c $< -o $@
$(BUILD)/svc/svc_io.o: svc/svc_io.cpp hostref.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(PCFLAGS) -c $< -o $@
$(BUILD)/svc/svc4_dump.o: svc/svc4_dump.cpp $(wildcard $(SVC_ENG)/*/*.h) hostref.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -c $< -o $@
$(BUILD)/svc/svc5_dump.o: svc/svc5_dump.cpp $(wildcard $(SVC_ENG)/*/*.h) hostref.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -c $< -o $@
$(BUILD)/svc/e2_dump.o: svc/e2_dump.cpp hostref.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -c $< -o $@
$(BUILD)/svc/e2b_dump.o: svc/e2b_dump.cpp hostref.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -c $< -o $@
SVC_HOST_OBJS := $(BUILD)/svc/svc_dump.o $(BUILD)/svc/svc_io.o $(BUILD)/svc/svc4_dump.o $(BUILD)/svc/svc5_dump.o $(BUILD)/svc/e2_dump.o \
	$(BUILD)/svc/e2b_dump.o
# lane eng-skel1: the skeleton's bone entries and the chain object against the original (skent_dump.cpp; skent_check.sh)
$(BUILD)/svc/skent_dump.o: svc/skent_dump.cpp $(SVC_ENG)/skeleton/skel.h hostref.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -c $< -o $@
SVC_HOST_OBJS += $(BUILD)/svc/skent_dump.o $(BUILD)/svc/skchain_kind.o
$(BUILD)/svc/skchain_kind.o: svc/skchain_kind.cpp hostref.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(GAMEFLAGS) -c $< -o $@
$(NAT)/chain.o: $(SVC_ENG)/cloth/chain.cpp $(SVC_ENG)/skeleton/skel.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(SVC_GAMEFLAGS) -c $< -o $@
NATIVE_GAME_OBJS += $(NAT)/chain.o
# lane eng-skel2: the room's collision in the baked form in the native builds (svc/colb_host.cpp: host_room_post; the
# bake step RE4_COLB_BAKE, svc/colbake.sh; the map entry's check RE4_COLMAP, svc/colmap_check.sh)
$(NAT)/colb_host.o: svc/colb_host.cpp $(SVC_ENG)/collision/col.h hostref.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) -isystem /usr/include/x86_64-linux-gnu/c++/13 $(HOSTFLAGS) -c $< -o $@
NATIVE_GAME_OBJS += $(NAT)/colb_host.o

$(ODU)/re4ref: $(CENSUS_OBJS) $(SVC_HOST_OBJS) aliases.ld
	@mkdir -p $(dir $@)
	$(CC) -o $@ $(plain_PC_OBJS) $(SVC_HG_OBJS) $(SVC_HOST_OBJS) $(SVC_REF_GAME) $(plain_SDK_OBJS) $(plain_LIBM_OBJS) \
	    aliases.ld $(LDFLAGS) $(SVC_WRAP_FLAGS)
$(NAT)/re4ref: $(plain_PC_OBJS) $(SVC_HG_OBJS) $(NATIVE_GAME_OBJS) $(NAT_SDK_OBJS) $(plain_LIBM_OBJS) $(SVC_HOST_OBJS) \
               $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/shz_xmtrx_sw.o aliases.ld
	$(CC) -o $@ $(plain_PC_OBJS) $(SVC_HG_OBJS) $(SVC_HOST_OBJS) $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/shz_xmtrx_sw.o \
	    $(NATIVE_GAME_OBJS) $(NAT_SDK_OBJS) $(plain_LIBM_OBJS) aliases.ld $(LDFLAGS) $(SVC_WRAP_FLAGS) -Wl,-Map=$(NAT)/re4ref.map

odump: $(ODU)/re4ref
native: $(NAT)/re4ref
.PHONY: odump native

# ---- ncensus: the native build with the census (calls, memory and fields, as make census for the reference) ----
NCEN := $(BUILD)/ncensus
NCENSUS_S := $(NAT)/weak/model.o $(NAT)/weak/motion.o $(NAT)/weak/atari.o $(NAT)/skel.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/pen.o \
             $(foreach u,cMotBase shape pl_cloth at_mod at_sub at_sub2 atariInfo route_ck area,$(BUILD)/plain/game/$(u).o)
$(NCEN)/wraps.flags: $(NATIVE_GAME_OBJS) $(NAT)/skel.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/skel_xm.o $(plain_SDK_OBJS) $(plain_LIBM_OBJS) svc/gen_wraps.py
	@mkdir -p $(NCEN)
	$(PY) svc/gen_wraps.py $(NCEN)/wraps.S $(NCEN)/wrapnames.cpp $@ $(foreach o,$(NCENSUS_S),S:$(o)) \
	    $(foreach u,$(CENSUS_M_UNITS),M:$(BUILD)/plain/game/$(u).o) M:$(NAT)/skel_xm.o \
	    $(foreach o,$(plain_SDK_OBJS) $(plain_LIBM_OBJS),M:$(o))
$(NCEN)/wraps.S $(NCEN)/wrapnames.cpp: $(NCEN)/wraps.flags
$(NCEN)/wraps.o: $(NCEN)/wraps.S
	$(CC) -m32 -c $< -o $@
$(NCEN)/wrapnames.o: $(NCEN)/wrapnames.cpp
	$(CXX) -m32 -c $< -o $@
$(NCEN)/re4ref: $(plain_PC_OBJS) $(SVC_HG_OBJS) $(NATIVE_GAME_OBJS) $(plain_SDK_OBJS) $(plain_LIBM_OBJS) $(NAT)/skel.o $(NAT)/cloth.o \
                $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/shz_xmtrx_sw.o $(CEN)/svc_trace.o $(CEN)/svc_glue.o $(BUILD)/svc/svc_io.o \
                $(NCEN)/wraps.o $(NCEN)/wrapnames.o $(BUILD)/plant/svc_plant.o aliases.ld
	$(CC) -o $@ $(plain_PC_OBJS) $(SVC_HG_OBJS) $(CEN)/svc_trace.o $(CEN)/svc_glue.o $(BUILD)/svc/svc_io.o $(NCEN)/wraps.o \
	    $(NCEN)/wrapnames.o $(BUILD)/plant/svc_plant.o $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/shz_xmtrx_sw.o $(NATIVE_GAME_OBJS) \
	    $(plain_SDK_OBJS) $(plain_LIBM_OBJS) aliases.ld $(LDFLAGS) $$(cat $(NCEN)/wraps.flags) -Wl,--wrap=host_fixed \
	    -Wl,-Map=$(NCEN)/re4ref.map
ncensus: $(NCEN)/re4ref
.PHONY: ncensus

# ---- cloth_ktest (lane eng-svc3): the cloth kernel's test and benchmark (services/cloth/cloth_kernel_test.c) ----
KT := $(BUILD)/ktest
KT_SDK := $(BUILD)/plain/sdk/sdk_vec.o $(BUILD)/plain/sdk/sdk_mtx.o $(BUILD)/plain/sdk/sdk_mtxvec.o
$(KT)/cloth_kernel_t.o: $(SVC_ENG)/cloth/cloth_kernel.c $(SVC_ENG)/cloth/cloth_kernel.h $(SVC_ENG)/cloth/pres_rng.h
	@mkdir -p $(dir $@)
	$(CC) $(COMMON) $(FP_plain) -std=gnu11 -Wall -DCLOTH_K_TEST -I$(SHZ)/include -c $< -o $@
$(KT)/cloth_kernel_test.o: $(SVC_ENG)/cloth/cloth_kernel_test.c $(SVC_ENG)/cloth/cloth_kernel.h
	@mkdir -p $(dir $@)
	$(CC) $(COMMON) $(FP_plain) -std=gnu11 -Wall -I$(SHZ)/include -c $< -o $@
$(KT)/cloth_ktest: $(KT)/cloth_kernel_t.o $(KT)/cloth_kernel_test.o $(KT_SDK) $(plain_LIBM_OBJS)
	$(CC) -o $@ $^ $(LDFLAGS) -lm
cloth_ktest: $(KT)/cloth_ktest
	$(KT)/cloth_ktest
.PHONY: cloth_ktest

# ---- mathtest (lane eng-svc5): the native math helpers against math_sub.cpp / sub2.cpp on random inputs, bit for bit ----
# The original objects are linked with every global symbol they define renamed orig_<symbol> (references included), so
# the two run side by side in one program. RE4_SVC_CONTROL=mathsin|mathmuku sets the native control (must FAIL).
MT := $(BUILD)/mathtest
MT_UNITS := math_sub sub2
$(MT)/orig.syms: $(foreach u,$(MT_UNITS),$(BUILD)/plain/game/$(u).o) svc/svc.mk
	@mkdir -p $(MT)
	nm -g --defined-only $(foreach u,$(MT_UNITS),$(BUILD)/plain/game/$(u).o) | awk 'NF == 3 {print $$3 " orig_" $$3}' | sort -u > $@
$(MT)/orig_%.o: $(BUILD)/plain/game/%.o $(MT)/orig.syms
	objcopy --redefine-syms=$(MT)/orig.syms $< $@
$(MT)/mathtest.o: svc/mathtest.cpp $(SVC_ENG)/math/math_svc.h hostref.h
	@mkdir -p $(MT)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -isystem /usr/include/x86_64-linux-gnu/c++/13 -c $< -o $@
$(MT)/mathtest: $(MT)/mathtest.o $(NAT)/svc4/math_svc.o $(foreach u,$(MT_UNITS),$(MT)/orig_$(u).o) $(plain_SDK_OBJS) $(plain_LIBM_OBJS)
	$(CC) -o $@ $^ $(LDFLAGS)
mathtest: $(MT)/mathtest
.PHONY: mathtest

# ---- garmenttest (lane eng-svc5): the native garments against pl_cloth.cpp, every character and costume, with the
# cloth service's entry points logged (stubs) and Ashley's lapel pose on a synthetic model; the original object's global
# symbols renamed orig_<symbol>. RE4_SVC_CONTROL=garmenthair|garmentskirt|lapelrate sets the native control (must FAIL).
GT := $(BUILD)/garmenttest
$(GT)/orig.syms: $(BUILD)/plain/game/pl_cloth.o svc/svc.mk
	@mkdir -p $(GT)
	nm -g --defined-only $< | awk 'NF == 3 {print $$3 " orig_" $$3}' | sort -u > $@
$(GT)/orig_pl_cloth.o: $(BUILD)/plain/game/pl_cloth.o $(GT)/orig.syms
	objcopy --redefine-syms=$(GT)/orig.syms $< $@
$(GT)/garmenttest.o: svc/garmenttest.cpp $(SVC_ENG)/cloth/garment.h hostref.h
	@mkdir -p $(GT)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -isystem /usr/include/x86_64-linux-gnu/c++/13 -c $< -o $@
$(GT)/garmenttest: $(GT)/garmenttest.o $(NAT)/svc4/garment.o $(NAT)/svc4/math_svc.o $(GT)/orig_pl_cloth.o $(plain_SDK_OBJS) $(plain_LIBM_OBJS)
	$(CC) -o $@ $^ $(LDFLAGS)
garmenttest: $(GT)/garmenttest
.PHONY: garmenttest

# ---- aimchk (lane eng-e1g): the native weapon-target query (services/aim/aim.cpp) against the original on the same
# calls. The native build plus aim.o (GetWepTargetPos renamed eng_GetWepTargetPos) and svc/aimcheck.cpp, which wraps
# GetWepTargetPos: both answer every call, the answers are compared (aim.txt, aim-diff.txt), and RE4_AIM_USE=native
# hands the behaviour the native answer. RE4_AIM_CONTROL=grow is the native control (must differ). Lane eng-e1k: the
# shot's target list too (GetWepTargetList2 renamed eng_GetWepTargetList2; aimlist.txt, aimlist-diff.txt).
AIM := $(BUILD)/aimchk
# (Lane eng-e1h: the reference's magazine is the new game's 10 rounds (host_stubs.cpp) and its rumble table is read in
# the PC's order (host_glue.cpp), so this build no longer replaces the magazine stubs or wraps VibSetData.)
AIM_HG_OBJS := $(SVC_HG_OBJS)
$(AIM)/aim.o: $(SVC_ENG)/aim/aim.cpp
	@mkdir -p $(AIM)
	$(CXX) $(COMMON) $(FP_plain) $(SVC_GAMEFLAGS) $(SVC4_INC) -c $< -o $@.raw.o
	objcopy --redefine-sym GetWepTargetPos=eng_GetWepTargetPos --redefine-sym GetWepTargetList2=eng_GetWepTargetList2 $@.raw.o $@
	rm -f $@.raw.o
$(AIM)/aimcheck.o: svc/aimcheck.cpp hostref.h
	@mkdir -p $(AIM)
	$(CXX) $(COMMON) $(FP_plain) $(HOSTFLAGS) -c $< -o $@
$(AIM)/re4ref: $(plain_PC_OBJS) $(AIM_HG_OBJS) $(NATIVE_GAME_OBJS) $(NAT_SDK_OBJS) $(plain_LIBM_OBJS) $(SVC_HOST_OBJS) \
               $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/shz_xmtrx_sw.o \
               $(AIM)/aim.o $(AIM)/aimcheck.o aliases.ld
	$(CC) -o $@ $(plain_PC_OBJS) $(AIM_HG_OBJS) $(SVC_HOST_OBJS) $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/shz_xmtrx_sw.o \
	    $(AIM)/aim.o $(AIM)/aimcheck.o $(NATIVE_GAME_OBJS) $(NAT_SDK_OBJS) $(plain_LIBM_OBJS) aliases.ld $(LDFLAGS) $(SVC_WRAP_FLAGS) \
	    -Wl,--wrap=GetWepTargetPos -Wl,--wrap=GetWepTargetList2 -Wl,-Map=$(AIM)/re4ref.map
aimchk: $(AIM)/re4ref
.PHONY: aimchk

# ---- sdktest (lane eng-svc5): the native SDK math against src/lib mtx.c, mtxvec.c, mtx44.c, vec.c, quat.c (renamed
# orig_<symbol>) on random inputs, bit for bit. RE4_SVC_CONTROL=sdkconcat sets the native control (must FAIL).
ST := $(BUILD)/sdktest
ST_UNITS := sdk_mtx sdk_mtxvec sdk_mtx44 sdk_vec sdk_quat
$(ST)/orig.syms: $(foreach u,$(ST_UNITS),$(BUILD)/plain/sdk/$(u).o) svc/svc.mk
	@mkdir -p $(ST)
	nm -g --defined-only $(foreach u,$(ST_UNITS),$(BUILD)/plain/sdk/$(u).o) | awk 'NF == 3 {print $$3 " orig_" $$3}' | sort -u > $@
$(ST)/orig_%.o: $(BUILD)/plain/sdk/%.o $(ST)/orig.syms
	objcopy --redefine-syms=$(ST)/orig.syms $< $@
$(ST)/sdktest.o: svc/sdktest.c
	@mkdir -p $(ST)
	$(CC) $(COMMON) $(FP_plain) -Wall -Wno-unused -c $< -o $@
$(ST)/sdktest: $(ST)/sdktest.o $(NAT)/svc4/sdk_math.o $(foreach u,$(ST_UNITS),$(ST)/orig_$(u).o) $(plain_LIBM_OBJS)
	$(CC) -o $@ $^ $(LDFLAGS)
sdktest: $(ST)/sdktest
.PHONY: sdktest

# ---- alloctest (lane eng-svc5): the native heap service (services/memory/heap.cpp) against src/lib/OSAlloc.c (the SDK
# allocator the image links today; renamed orig_<symbol>) on random sequences. RE4_SVC_CONTROL=heapsplit (must FAIL).
AT := $(BUILD)/alloctest
$(AT)/OSAlloc.o: $(BUILD)/gen/sdk_OSAlloc.c
	@mkdir -p $(AT)
	$(CC) $(COMMON) $(FP_plain) -w -I$(GAME)/platform/sdk -I$(ROOT)/include -c $< -o $@.raw.o
	nm -g --defined-only $@.raw.o | awk 'NF == 3 {print $$3 " orig_" $$3}' > $@.syms
	objcopy --redefine-syms=$@.syms $@.raw.o $@
	rm -f $@.raw.o
$(AT)/heap.o: $(SVC_ENG)/memory/heap.cpp $(SVC_ENG)/memory/heap.h
	@mkdir -p $(AT)
	$(CXX) $(COMMON) $(FP_plain) $(SVC_GAMEFLAGS) -I$(SVC_ENG)/memory -c $< -o $@
$(AT)/alloctest.o: svc/alloctest.c
	@mkdir -p $(AT)
	$(CC) $(COMMON) $(FP_plain) -Wall -Wno-unused -c $< -o $@
$(AT)/alloctest: $(AT)/alloctest.o $(AT)/heap.o $(AT)/OSAlloc.o
	$(CC) -o $@ $^ $(LDFLAGS)
alloctest: $(AT)/alloctest
.PHONY: alloctest

# ---- pooltest (lane eng-e1h): the engine's record pool (services/model/pool.h: create, createBack, create at a slot,
# destroy, the sweep) on a test record type: full tables and double frees refused, the list intact.
# RE4_POOL_CONTROL=1|2 turns a refusal off (must FAIL).
PT := $(BUILD)/pooltest
$(PT)/pooltest: svc/pooltest.cpp $(SVC_ENG)/model/pool.h $(ROOT)/include/cManager.h
	@mkdir -p $(PT)
	$(CXX) $(ARCH) -O1 -g -std=gnu++20 -fpermissive -w -fno-exceptions -fno-rtti -fno-threadsafe-statics \
	    -isystem /usr/include/x86_64-linux-gnu/c++/13 -I$(ROOT)/include -I$(SVC_ENG)/model -c $< -o $(PT)/pooltest.o
	$(CC) -m32 -no-pie -o $@ $(PT)/pooltest.o
pooltest: $(PT)/pooltest
.PHONY: pooltest

# ---- libmtest (lane eng-svc5): the engine's float math library, the toolchain's newlib 4.6.0 libm (its sources
# compiled for the PC by svc/newlib_libm.sh into build/ext/nlobj, symbols prefixed nl_), against the game's fdlibm
# (src/lib, which re4ref links), bit for bit. LIBMTEST_CONTROL=sinulp (must FAIL).
NLOBJ := $(ROOT)/build/ext/nlobj
LT := $(BUILD)/libmtest
$(LT)/libmtest.o: svc/libmtest.c
	@mkdir -p $(LT)
	$(CC) $(COMMON) $(FP_plain) -Wall -Wno-unused -fno-builtin -c $< -o $@
$(LT)/libmtest: $(LT)/libmtest.o $(plain_LIBM_OBJS)
	@test -f $(NLOBJ)/sf_sin.o || { echo "libmtest: run svc/newlib_libm.sh first (newlib's sources into build/ext)"; exit 1; }
	$(CC) -o $@ $^ $(wildcard $(NLOBJ)/*.o) $(LDFLAGS)
libmtest: $(LT)/libmtest
.PHONY: libmtest

# ---- nlnative (lane eng-e1g): the native build with the engine's float library, the toolchain's newlib float functions
# (svc/newlib_libm.sh's unprefixed objects, build/ext/nlraw) in place of the game's fdlibm. libmtest shows the two are
# not bit-identical (sinf, cosf, tanf on large arguments, atan2f, asinf); this build judges the swap by outcome on the
# fixtures (native against nlnative: outcome.py and plays_right.py; svc/nl_outcome.sh).
NLRAW := $(ROOT)/build/ext/nlraw
NLN := $(BUILD)/nlnative
$(NLN)/nl_glue.o: svc/nl_glue.c
	@mkdir -p $(NLN)
	$(CC) $(COMMON) $(FP_plain) -c $< -o $@
$(NLN)/re4ref: $(plain_PC_OBJS) $(SVC_HG_OBJS) $(NATIVE_GAME_OBJS) $(NAT_SDK_OBJS) $(SVC_HOST_OBJS) $(NLN)/nl_glue.o                $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/shz_xmtrx_sw.o aliases.ld
	@test -f $(NLRAW)/sf_sin.o || { echo "nlnative: run svc/newlib_libm.sh first"; exit 1; }
	$(CC) -o $@ $(plain_PC_OBJS) $(SVC_HG_OBJS) $(SVC_HOST_OBJS) $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/shz_xmtrx_sw.o 	    $(NATIVE_GAME_OBJS) $(NAT_SDK_OBJS) $(wildcard $(NLRAW)/*.o) $(NLN)/nl_glue.o aliases.ld $(LDFLAGS) $(SVC_WRAP_FLAGS) -Wl,-Map=$(NLN)/re4ref.map
nlnative: $(NLN)/re4ref
.PHONY: nlnative
