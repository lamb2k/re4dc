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
SVC_WRAP_FLAGS := $(foreach s,$(SVC_WRAP_COL),-Wl,--wrap=$(s)) -Wl,--wrap=PenClothSet
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
NATIVE_GAME_OBJS := $(filter-out $(NATIVE_REPLACED),$(plain_GAME_OBJS)) $(NAT)/weak/motion.o $(NAT)/weak/model.o $(NAT)/weak/atari.o \
                    $(NAT)/pen.o
SVC_GAMEFLAGS := $(GAMEFLAGS) -I$(SVC_ENG)/skeleton -I$(SVC_ENG)/collision -I$(SVC_ENG)/cloth
$(NAT)/pen.o: $(BUILD)/plain/game/pendulum.o svc/svc.mk
	@mkdir -p $(dir $@)
	objcopy $(foreach s,$(PEN_ORIG) $(PEN_RAND),--redefine-sym $(s)) $< $@
$(NAT)/cloth.o: $(SVC_ENG)/cloth/cloth.cpp $(SVC_ENG)/cloth/cloth.h $(SVC_ENG)/skeleton/skel.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(SVC_GAMEFLAGS) -c $< -o $@

$(NAT)/weak/%.o: $(BUILD)/plain/game/%.o svc/svc.mk
	@mkdir -p $(dir $@)
	objcopy $(foreach s,$(WEAK_$*),--weaken-symbol=$(s)) $< $@
$(NAT)/skel.o: $(SVC_ENG)/skeleton/skel.cpp $(SVC_ENG)/skeleton/skel.h $(SVC_ENG)/skeleton/skel_mk.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(SVC_GAMEFLAGS) -c $< -o $@
$(NAT)/col.o: $(SVC_ENG)/collision/col.cpp $(SVC_ENG)/collision/col.h
	@mkdir -p $(dir $@)
	$(CXX) $(COMMON) $(FP_plain) $(SVC_GAMEFLAGS) -c $< -o $@
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
SVC_HOST_OBJS := $(BUILD)/svc/svc_dump.o $(BUILD)/svc/svc_io.o

$(ODU)/re4ref: $(CENSUS_OBJS) $(SVC_HOST_OBJS) aliases.ld
	@mkdir -p $(dir $@)
	$(CC) -o $@ $(plain_PC_OBJS) $(SVC_HG_OBJS) $(SVC_HOST_OBJS) $(SVC_REF_GAME) $(plain_SDK_OBJS) $(plain_LIBM_OBJS) \
	    aliases.ld $(LDFLAGS) $(SVC_WRAP_FLAGS)
$(NAT)/re4ref: $(plain_PC_OBJS) $(SVC_HG_OBJS) $(NATIVE_GAME_OBJS) $(plain_SDK_OBJS) $(plain_LIBM_OBJS) $(SVC_HOST_OBJS) \
               $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/shz_xmtrx_sw.o aliases.ld
	$(CC) -o $@ $(plain_PC_OBJS) $(SVC_HG_OBJS) $(SVC_HOST_OBJS) $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/shz_xmtrx_sw.o \
	    $(NATIVE_GAME_OBJS) $(plain_SDK_OBJS) $(plain_LIBM_OBJS) aliases.ld $(LDFLAGS) $(SVC_WRAP_FLAGS) -Wl,-Map=$(NAT)/re4ref.map

odump: $(ODU)/re4ref
native: $(NAT)/re4ref
.PHONY: odump native

# ---- ncensus: the native build with the census (calls, memory and fields, as make census for the reference) ----
NCEN := $(BUILD)/ncensus
NCENSUS_S := $(NAT)/weak/model.o $(NAT)/weak/motion.o $(NAT)/weak/atari.o $(NAT)/skel.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/pen.o \
             $(foreach u,cMotBase shape pl_cloth at_mod at_sub at_sub2 atariInfo route_ck area,$(BUILD)/plain/game/$(u).o)
$(NCEN)/wraps.flags: $(NATIVE_GAME_OBJS) $(NAT)/skel.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/skel_xm.o $(plain_SDK_OBJS) $(plain_LIBM_OBJS) svc/gen_wraps.py
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
	    $(NCEN)/wrapnames.o $(BUILD)/plant/svc_plant.o $(NAT)/skel.o $(NAT)/skel_xm.o $(NAT)/col.o $(NAT)/cloth.o $(NAT)/shz_xmtrx_sw.o $(NATIVE_GAME_OBJS) \
	    $(plain_SDK_OBJS) $(plain_LIBM_OBJS) aliases.ld $(LDFLAGS) $$(cat $(NCEN)/wraps.flags) -Wl,--wrap=host_fixed \
	    -Wl,-Map=$(NCEN)/re4ref.map
ncensus: $(NCEN)/re4ref
.PHONY: ncensus
