# hostref: a PC (host) build of Leon's original player and camera code that replays recorded pad input
# and writes a per-tick state trace. It is the reference the engine is checked against
# (ENGINE_PLAN.md section 8 "Plays right"; docs/engine/PLAYS_RIGHT.md).
#
#   make            -> $(BUILD)/plain/re4ref   (SSE single precision, no fused multiply-add)
#   make fma        -> $(BUILD)/fma/re4ref     (-mfma -ffp-contract=fast: a*b+c fused, like SH-4 fmac;
#                                              GCC forms FMAs only with -fexpensive-optimizations)
#   make clean
#
# i386 (-m32) code, run on x86-64 Linux: the game's structures, its data files and its u32 pointer casts
# are 32-bit. -malign-double keeps u64/f64 members 8-aligned as on the SH-4 and the GameCube.
# No RE4DC_ knob is defined; RE4DC_GAME only selects the non-PowerPC source paths (the build target).
# The original sources are compiled as they are; prep.py writes host copies (see there for why).

ROOT   := $(abspath ../../../..)
GAME   := $(ROOT)/port/dreamcast/game
BUILD  ?= $(ROOT)/build/hostref
PY     := python3
CXX    := g++
CC     := gcc

# The E1 closure, variant B (SHELL_MAP.md section 5): 19 player and camera files plus rnd.cpp
# (rnd.cpp goes through prep.py rnd: a call counter and a state reader, no result changed).
SEEDS := src/game/player.cpp src/game/pl_class.cpp src/game/pl_body.cpp src/game/pl_sub.cpp \
         src/game/pl_leon.cpp src/game/pl_wep.cpp src/game/pl_dmg.cpp src/game/pl_push.cpp \
         src/game/pl_knife.cpp src/game/pl_debug.cpp src/game/pl_event.cpp src/game/cam_ctrl.cpp \
         src/game/cam_sys.cpp src/game/cam_qfps.cpp src/game/cam_extra.cpp src/game/cam_motion.cpp \
         src/game/camera.cpp src/game/view.cpp src/wep/pl_handgun.cpp

# Host versions of the engine interface that the reference takes from the original code itself
# (skeleton and pose, collision, math, pad, room counts, the weapon object): the reference must be
# the original behaviour, so the services under the player are the original's too.
SERVICES := src/game/model.cpp src/game/motion.cpp src/game/cMotBase.cpp src/game/ik.cpp \
            src/game/math_sub.cpp src/game/sub2.cpp src/game/atari.cpp src/game/at_mod.cpp \
            src/game/at_sub.cpp src/game/at_sub2.cpp src/game/atariInfo.cpp src/game/shape.cpp \
            src/game/pl_cloth.cpp src/game/cons.cpp src/game/pad.cpp src/game/foot_shadow_tbl.cpp \
            src/game/objWep.cpp
# The equipped handgun's module (weapon 2, the new-game default): its REL entry fills Leon's footwork
# motion table (cObjRuger::setMotion), so the player cannot stand or walk without it.
WEAPON := src/wep/objRuger.cpp
WEAPON02 := src/wep02/wep02.cpp src/wep02/objMauser.cpp

# Parts of files whose other functions reach behaviour outside E1 (prep.py extract, verbatim):
# em.cpp the character base and manager (construct: host_em.cpp), obj.cpp the object manager
# (construct: host_em.cpp), read.cpp the tagged-archive lookup (the loaders: host_glue.cpp).
EM_FUNCS := cEm::cEm cEm::setStatus cEm::clearStatus cEm::checkStatus cEm::checkThrow cEm::setItem \
            cEm::setNoItem cEm::move cEm::initWork cDmgInfo::cDmgInfo cDmgInfo::set cDmgInfo::clear \
            cDmgInfo::move cEmMgr::cEmMgr cEmMgr::arrayAlloc cEmMgr::destroy cEmMgr::isBattle cEmMgr::log battleCheck
OBJ_FUNCS := cObjMgr::cObjMgr cObjMgr::log cObjMgr::move objMove cObjMgr::destroy cObj::cObj
READ_FUNCS := GetDataExt

# The game's own libm (recovered fdlibm) and the SDK's C matrix library (CodeWarrior asm stripped).
FDLIBM := sf_sin sf_cos kf_sin kf_cos ef_rem_pio2 kf_rem_pio2 sf_scalbn sf_floor sf_fabs ef_acos ef_asin \
          ef_sqrt ef_atan2 sf_atan sf_tan kf_tan sf_copysign
SDKLIB := mtx mtxvec vec quat mtx44 Padclamp

# Host files: PC side (system C library) and game side (the game's headers, with their own libc).
HOST_PC   := host_rt.cpp host_mem.cpp host_data.cpp host_trace.cpp host_io.cpp
HOST_GAME := host_memapi.cpp host_globals.cpp host_mgr.cpp host_stubs.cpp host_glue.cpp host_em.cpp \
             host_math.cpp replay.cpp

ARCH   := -m32 -msse2 -mfpmath=sse -malign-double -fno-pie -fno-stack-protector
COMMON := $(ARCH) -O1 -g -fno-strict-aliasing -ffunction-sections -fdata-sections
GAMEINC := -include $(GAME)/platform/include/re4dc_prelude.h -I$(ROOT)/include -I$(ROOT)/src \
           -I$(ROOT)/src/game -I$(ROOT)/src/wep -I$(GAME)/platform/include -DRE4DC_GAME
GAMEFLAGS := -std=gnu++20 -fpermissive -w -fno-exceptions -fno-rtti -fno-threadsafe-statics $(GAMEINC)
HOSTFLAGS := -std=gnu++20 -fpermissive -Wall -Wno-unused-function -Wno-register -fno-exceptions -fno-rtti \
             -fno-threadsafe-statics $(GAMEINC) -I.
# No 32-bit libstdc++ is installed: the C++ wrappers of the C headers need the target-neutral
# c++config.h, taken from the 64-bit tree; nothing links against libstdc++ (host_rt.cpp).
PCFLAGS := -isystem /usr/include/x86_64-linux-gnu/c++/13 -std=gnu++20 -Wall -fno-exceptions -fno-rtti \
           -fno-threadsafe-statics -I.
LDFLAGS := -m32 -no-pie -Wl,--gc-sections -lm

FP_plain := -ffp-contract=off '-DHOST_FP_NAME="plain"'
FP_fma   := -mfma -ffp-contract=fast -fexpensive-optimizations '-DHOST_FP_NAME="fma"'

all: $(BUILD)/plain/re4ref
fma: $(BUILD)/fma/re4ref

# Host copies (prep.py): shared by both variants.
$(BUILD)/gen/%.cpp: $(ROOT)/src/game/%.cpp prep.py
	@mkdir -p $(dir $@)
	$(PY) prep.py copy $< $@
$(BUILD)/gen/wep_%.cpp: $(ROOT)/src/wep/%.cpp prep.py
	@mkdir -p $(dir $@)
	$(PY) prep.py copy $< $@
$(BUILD)/gen/w02_%.cpp: $(ROOT)/src/wep02/%.cpp prep.py
	@mkdir -p $(dir $@)
	$(PY) prep.py copy $< $@
$(BUILD)/gen/x_rnd.cpp: $(ROOT)/src/game/rnd.cpp prep.py
	@mkdir -p $(dir $@)
	$(PY) prep.py rnd $< $@
$(BUILD)/gen/x_em.cpp: $(ROOT)/src/game/em.cpp prep.py Makefile
	@mkdir -p $(dir $@)
	$(PY) prep.py extract $< $@ $(EM_FUNCS)
$(BUILD)/gen/x_obj.cpp: $(ROOT)/src/game/obj.cpp prep.py Makefile
	@mkdir -p $(dir $@)
	$(PY) prep.py extract $< $@ $(OBJ_FUNCS)
$(BUILD)/gen/x_read.cpp: $(ROOT)/src/game/read.cpp prep.py Makefile
	@mkdir -p $(dir $@)
	$(PY) prep.py extract $< $@ $(READ_FUNCS)
$(BUILD)/gen/sdk_%.c: $(ROOT)/src/lib/%.c $(GAME)/platform/sdk/strip_cw_asm.py
	@mkdir -p $(dir $@)
	$(PY) $(GAME)/platform/sdk/strip_cw_asm.py $< $@ > /dev/null

GEN_GAME := $(patsubst src/game/%.cpp,$(BUILD)/gen/%.cpp,$(filter src/game/%,$(SEEDS) $(SERVICES))) \
            $(patsubst src/wep/%.cpp,$(BUILD)/gen/wep_%.cpp,$(filter src/wep/%,$(SEEDS) $(WEAPON))) \
            $(patsubst src/wep02/%.cpp,$(BUILD)/gen/w02_%.cpp,$(WEAPON02)) \
            $(BUILD)/gen/x_rnd.cpp $(BUILD)/gen/x_em.cpp $(BUILD)/gen/x_obj.cpp $(BUILD)/gen/x_read.cpp
GEN_SDK  := $(addprefix $(BUILD)/gen/sdk_,$(addsuffix .c,$(SDKLIB)))

# $(1) variant
define VARIANT
$(1)_GAME_OBJS := $(patsubst $(BUILD)/gen/%.cpp,$(BUILD)/$(1)/game/%.o,$(GEN_GAME))
$(1)_SDK_OBJS  := $(patsubst $(BUILD)/gen/%.c,$(BUILD)/$(1)/sdk/%.o,$(GEN_SDK)) $(BUILD)/$(1)/sdk/pmtx.o
$(1)_LIBM_OBJS := $(addprefix $(BUILD)/$(1)/libm/,$(addsuffix .o,$(FDLIBM)))
$(1)_PC_OBJS   := $(addprefix $(BUILD)/$(1)/host/,$(HOST_PC:.cpp=.o))
$(1)_HG_OBJS   := $(addprefix $(BUILD)/$(1)/host/,$(HOST_GAME:.cpp=.o))

$(BUILD)/$(1)/game/%.o: $(BUILD)/gen/%.cpp
	@mkdir -p $$(dir $$@)
	$(CXX) $(COMMON) $(FP_$(1)) $(GAMEFLAGS) -c $$< -o $$@
$(BUILD)/$(1)/sdk/%.o: $(BUILD)/gen/%.c
	@mkdir -p $$(dir $$@)
	$(CC) $(COMMON) $(FP_$(1)) -w -I$(GAME)/platform/sdk -I$(ROOT)/include -c $$< -o $$@
$(BUILD)/$(1)/sdk/pmtx.o: $(GAME)/platform/mtx.cpp
	@mkdir -p $$(dir $$@)
	$(CXX) $(COMMON) $(FP_$(1)) -w -fno-exceptions -fno-rtti -c $$< -o $$@
$(BUILD)/$(1)/libm/%.o: $(ROOT)/src/lib/%.cpp
	@mkdir -p $$(dir $$@)
	$(CXX) $(COMMON) $(FP_$(1)) -w -fno-exceptions -fno-rtti -I$(ROOT)/include -c $$< -o $$@
$$($(1)_PC_OBJS): $(BUILD)/$(1)/host/%.o: %.cpp hostref.h
	@mkdir -p $$(dir $$@)
	$(CXX) $(COMMON) $(FP_$(1)) $(PCFLAGS) -c $$< -o $$@
$$($(1)_HG_OBJS): $(BUILD)/$(1)/host/%.o: %.cpp hostref.h
	@mkdir -p $$(dir $$@)
	$(CXX) $(COMMON) $(FP_$(1)) $(HOSTFLAGS) -c $$< -o $$@
$(BUILD)/$(1)/re4ref: $$($(1)_GAME_OBJS) $$($(1)_SDK_OBJS) $$($(1)_LIBM_OBJS) $$($(1)_PC_OBJS) $$($(1)_HG_OBJS) aliases.ld
	$(CC) -o $$@ $$($(1)_PC_OBJS) $$($(1)_HG_OBJS) $$($(1)_GAME_OBJS) $$($(1)_SDK_OBJS) $$($(1)_LIBM_OBJS) aliases.ld $(LDFLAGS)
endef
$(eval $(call VARIANT,plain))
$(eval $(call VARIANT,fma))

.SECONDARY:
.PHONY: all fma clean
clean:
	rm -rf $(BUILD)
