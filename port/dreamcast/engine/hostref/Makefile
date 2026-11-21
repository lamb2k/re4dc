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

# Actors (lane eng-host2; PLAYS_RIGHT.md "Actors"; closures in closure-map-actors.tsv):
# Ashley as the partner: cSubChar (pl_npc.cpp) and the pl11 module's cSubAshley (enemy id 3, em/pl11).
# One Ganado: the shared Ganado library em10.cpp with the per-type set files of the village square's
# Ganado (em15, the bell fight), the farm's (em12, the hay-fork view) and the hill's with Ashley (em16, r11d), the spawn list (em_set.cpp), the
# enemy helpers (em_sub.cpp) and the damage records (dmg.cpp). Each module's REL entry (_prolog) is linked
# in under its own name (MODNAME_prolog: the -D renames below; no source change), as wep02's is.
ACTOR_GAME := src/game/pl_npc.cpp src/game/em_set.cpp src/game/em_sub.cpp src/game/dmg.cpp src/game/em_dm_val.cpp
ACTOR_MODS := src/pl11/pl11.cpp src/em10/em10.cpp src/em12/em12_set.cpp src/em15/em15_set.cpp src/em16/em16_set.cpp
# The original services the actors reach that E1 did not (collision, routes, skeleton, math): the reference
# keeps the original behaviour under the actors, as it does under the player.
ACTOR_SERVICES := src/game/route_ck.cpp src/game/area.cpp

# Parts of files whose other functions reach behaviour outside E1 (prep.py extract, verbatim):
# em.cpp the character base and manager (construct: host_em.cpp), obj.cpp the object manager
# (construct: host_em.cpp), read.cpp the tagged-archive lookup (the loaders: host_glue.cpp).
EM_FUNCS := cEm::cEm cEm::setStatus cEm::clearStatus cEm::checkStatus cEm::checkThrow cEm::setItem \
            cEm::setNoItem cEm::move cEm::initWork cDmgInfo::cDmgInfo cDmgInfo::set cDmgInfo::clear \
            cDmgInfo::move cEmMgr::cEmMgr cEmMgr::arrayAlloc cEmMgr::destroy cEmMgr::isBattle cEmMgr::log battleCheck \
            cEmMgr::move emMove@host_em_move cEmMgr::getEmPtr killEm cEmMgr::destroyAll
OBJ_FUNCS := cObjMgr::cObjMgr cObjMgr::log cObjMgr::move objMove cObjMgr::destroy cObj::cObj
READ_FUNCS := GetDataExt

# The game's own libm (recovered fdlibm) and the SDK's C matrix library (CodeWarrior asm stripped).
FDLIBM := sf_sin sf_cos kf_sin kf_cos ef_rem_pio2 kf_rem_pio2 sf_scalbn sf_floor sf_fabs ef_acos ef_asin \
          ef_sqrt ef_atan2 sf_atan sf_tan kf_tan sf_copysign
SDKLIB := mtx mtxvec vec quat mtx44 Padclamp

# Host files: PC side (system C library) and game side (the game's headers, with their own libc).
HOST_PC   := host_rt.cpp host_mem.cpp host_data.cpp host_trace.cpp host_io.cpp
HOST_GAME := host_memapi.cpp host_globals.cpp host_mgr.cpp host_stubs.cpp host_glue.cpp host_em.cpp \
             host_math.cpp host_actors.cpp host_actor_stubs.cpp replay.cpp host_present.cpp

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
LDFLAGS := -m32 -no-pie -Wl,--gc-sections -Wl,-z,start-stop-gc -lm -Wl,--wrap=Rnd,--wrap=fRand0_1,--wrap=fRand1_1

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
$(BUILD)/gen/pl11_%.cpp: $(ROOT)/src/pl11/%.cpp prep.py
	@mkdir -p $(dir $@)
	$(PY) prep.py copy $< $@
$(BUILD)/gen/em10_%.cpp: $(ROOT)/src/em10/%.cpp prep.py
	@mkdir -p $(dir $@)
	$(PY) prep.py copy $< $@
$(BUILD)/gen/em12_%.cpp: $(ROOT)/src/em12/%.cpp prep.py
	@mkdir -p $(dir $@)
	$(PY) prep.py copy $< $@
$(BUILD)/gen/em16_%.cpp: $(ROOT)/src/em16/%.cpp prep.py
	@mkdir -p $(dir $@)
	$(PY) prep.py copy $< $@
$(BUILD)/gen/em15_%.cpp: $(ROOT)/src/em15/%.cpp prep.py
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

GEN_GAME := $(patsubst src/game/%.cpp,$(BUILD)/gen/%.cpp,$(filter src/game/%,$(SEEDS) $(SERVICES) $(ACTOR_GAME) $(ACTOR_SERVICES))) \
            $(patsubst src/wep/%.cpp,$(BUILD)/gen/wep_%.cpp,$(filter src/wep/%,$(SEEDS) $(WEAPON))) \
            $(patsubst src/wep02/%.cpp,$(BUILD)/gen/w02_%.cpp,$(WEAPON02)) \
            $(foreach f,$(ACTOR_MODS),$(BUILD)/gen/$(word 2,$(subst /, ,$(f)))_$(notdir $(f))) \
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
	$(CXX) $(COMMON) $(FP_$(1)) $(GAMEFLAGS) $$(MODFLAGS) -c $$< -o $$@
	$$(POSTCC)
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

# Module entry points under their own names (each module's file defines _prolog/_epilog/_unresolved).
modname = -D_prolog=$(1)_prolog -D_epilog=$(1)_epilog -D_unresolved=$(1)_unresolved
$(BUILD)/%/game/pl11_pl11.o: MODFLAGS = $(call modname,pl11)
$(BUILD)/%/game/em12_em12_set.o: MODFLAGS = $(call modname,em12)
$(BUILD)/%/game/em15_em15_set.o: MODFLAGS = $(call modname,em15)
$(BUILD)/%/game/em16_em16_set.o: MODFLAGS = $(call modname,em16)
# em_sub.cpp declares AtSphereCapsuleCk under its C name with the float arguments first (the atari_init.h
# idiom): fine where int and float arguments travel in separate registers, wrong on the i386 stack. Its
# object's reference is renamed to the adapter that passes them on in at_sub.cpp's order (host_actors.cpp).
$(BUILD)/%/game/em_sub.o: POSTCC = objcopy --redefine-sym AtSphereCapsuleCk=host_AtSphereCapsuleCkF $@

# lane eng-e1d: random numbers split as in the engine image (host_present.cpp): the presentation functions (the engine's
# game/Makefile PRESENT_* list) are moved to the section re4ref_present, whose draws host_present.cpp answers.
$(BUILD)/%/game/pl_class.o: POSTCC = objcopy --rename-section .text._ZN7cPlayer13moveEyeNormalEv=re4ref_present $@
$(BUILD)/%/game/pl_sub.o: POSTCC = objcopy --rename-section .text.PlSetDamageSe=re4ref_present $@
$(BUILD)/%/game/pl_wep.o: POSTCC = objcopy --rename-section .text.wepSetWaterShot=re4ref_present $@
$(BUILD)/%/game/cam_extra.o: POSTCC = objcopy --rename-section .text._ZN11CameraScope4moveEv=re4ref_present --rename-section .text._ZN12CameraLookAtC2EP6Camera=re4ref_present $@
$(BUILD)/%/game/wep_objRuger.o: POSTCC = objcopy --rename-section .text._ZN9cObjRuger12setCartridgeEv=re4ref_present $@
$(BUILD)/%/game/pl_npc.o: POSTCC = objcopy --rename-section .text._ZN8cSubChar8moveFaceEv=re4ref_present $@
# lane eng-svc4: rumble is presentation (E1 audit section 3): the random-strength rumble (VibControl) draws from the
# presentation generator in the reference too, as the native input service does (services/input, eng_pres_u8)
$(BUILD)/%/game/pad.o: POSTCC = objcopy --rename-section .text.VibControl=re4ref_present $@
# lane eng-e1k: the Ganado's presentation callers, as the engine's fight image splits them (game/fight.mk PRESENT_em10):
# its voice, breath and chainsaw sound timers, its blood-effect choice and its camera moves. Without them the reference's
# Ganado drew its voice timer from the behaviour generator (two draws at tick 135 of shot-ganado) and the engine's did not.
PRESENT_EM10 := _Z12em10BloodSetP5cEm10i _Z12em10BreathSeP5cEm10 _Z12em10CamMove2P5cEm10 _Z12em1cBloodSetP5cEm10i \
	_Z16em10CallVoiceSe2P5cEm10ii _Z18em10SetDamageVoiceP5cEm10ii em10CallVoiceSe em10CamMove em10CamMoveAshley \
	em10CamMoveCri em10CamMoveTakeaway em10CsawSignSe plem10KickCamMove
$(BUILD)/%/game/em10_em10.o: POSTCC = objcopy $(foreach f,$(PRESENT_EM10),--rename-section .text.$(f)=re4ref_present) $@

# lane eng-svc: the service census build and the native skeleton and collision services (svc/svc.mk)
include svc/svc.mk

.SECONDARY:
.PHONY: all fma clean
clean:
	rm -rf $(BUILD)
