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
SVC_WRAP_FLAGS := $(foreach s,$(SVC_WRAP_COL) $(SVC4_WRAP),-Wl,--wrap=$(s)) -Wl,--wrap=PenClothSet
WEAK_motion := _Z13MotionSetCoreP6cModelPvS1_iiii MotionMove MotionMoveCore MotionMoveSub MotionHokan MotionClear PartsWorldPosCalc \
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
# lane eng-svc5 (round 5): the math helpers (services/math: math_sub, sub2), linked the same way (SERVICES.md section 32)
SVC5_SRCS := math/math_svc.cpp
SVC5_UNITS := math_sub sub2
SVC4_SRCS := volumes/volumes.cpp collision/col_model.cpp routes/routes.cpp motion/follow.cpp model/model_svc.cpp camera/camera_svc.cpp input/input.cpp              $(SVC5_SRCS)
SVC4_OBJS := $(addprefix $(NAT)/svc4/,$(notdir $(SVC4_SRCS:.cpp=.o)))
SVC4_UNITS := at_mod at_sub atariInfo atari route_ck cMotBase model view camera cam_motion motion pad $(SVC5_UNITS)
# SVC4_SPLIT: behaviour units whose evaluation functions are native (the camera's: cam_ctrl's rail spline,
# cam_sys's orientation matrices, cam_extra's attached camera; svc4_split.txt names them): the same weak copy, and
# svc4_units.sh checks only the named functions
SVC4_SPLIT := cam_ctrl cam_sys cam_extra
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
SVC4_NOINIT := model atari view camera
NOINIT_FLAGS := --remove-section=.init_array --remove-section=.rel.init_array
$(NAT)/weak4/%.o: $(BUILD)/plain/game/%.o $(NAT)/svc4/syms.txt
	@mkdir -p $(dir $@)
	objcopy $$(cat $(NAT)/svc4/syms.txt) $(foreach s,$(WEAK_$*),--weaken-symbol=$(s)) \
	    $(if $(filter $*,$(SVC4_NOINIT)),$(NOINIT_FLAGS)) $< $@
SVC4_REPLACED := $(addprefix $(BUILD)/plain/game/,$(addsuffix .o,$(SVC4_ALL)))
# the native objects first: a header inline (manager methods, destructors) both define is taken from them
NATIVE_GAME_OBJS := $(SVC4_OBJS) $(filter-out $(NATIVE_REPLACED) $(SVC4_REPLACED),$(plain_GAME_OBJS)) \
                    $(filter-out $(addprefix $(NAT)/weak/,$(addsuffix .o,$(SVC4_ALL))),$(NAT)/weak/motion.o $(NAT)/weak/model.o $(NAT)/weak/atari.o) \
                    $(NAT)/pen.o $(addprefix $(NAT)/weak4/,$(addsuffix .o,$(SVC4_ALL)))
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
SVC_HOST_OBJS := $(BUILD)/svc/svc_dump.o $(BUILD)/svc/svc_io.o $(BUILD)/svc/svc4_dump.o $(BUILD)/svc/svc5_dump.o

$(ODU)/re4ref: $(CENSUS_OBJS) $(SVC_HOST_OBJS) aliases.ld
	@mkdir -p $(dir $@)
	$(CC) -o $@ $(plain_PC_OBJS) $(SVC_HG_OBJS) $(SVC_HOST_OBJS) $(SVC_REF_GAME) $(plain_SDK_OBJS) $(plain_LIBM_OBJS) \
	    aliases.ld $(LDFLAGS) $(SVC_WRAP_FLAGS)
$(NAT)/re4ref: $(plain_PC_OBJS) $(SVC_HG_OBJS) $(NATIVE_GAME_OBJS) $(plain_SDK_OBJS) $(plain_LIBM_OBJS) $(SVC_HOST_OBJS) \
               $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/shz_xmtrx_sw.o aliases.ld
	$(CC) -o $@ $(plain_PC_OBJS) $(SVC_HG_OBJS) $(SVC_HOST_OBJS) $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/cloth_kernel.o $(NAT)/shz_xmtrx_sw.o \
	    $(NATIVE_GAME_OBJS) $(plain_SDK_OBJS) $(plain_LIBM_OBJS) aliases.ld $(LDFLAGS) $(SVC_WRAP_FLAGS) -Wl,-Map=$(NAT)/re4ref.map

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
