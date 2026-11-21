# E2 fight slice (lane eng-e2): the village square fight (r101) at cap 4 on the E1 shell.
#   make -C port/dreamcast/engine/game FIGHT=1 OUT=<dir>   -> <dir>/e1.elf
#
# Hosted behaviour (src/ unchanged): the Ganado library (em10) and the village square's set file (em15), the enemy list
# and creator (em_set), the enemy helpers and weapon targeting (em_sub), damage records (dmg, em_dm_val), the room
# script (st1/r101), the scenario helpers the room script calls (sce_com, sce_at, area) and the difficulty points
# (game). Engine side under engine/fight/ (room set-up, enemy table move, scenario tasks, route, trace) and the native
# effect service (services/effects/). The boss slice's E2 hooks in core/ are reused (E2_BOSS=1): engine/boss/ is not
# built in this image.
#
# Behaviour knobs: the release recipe's enemy rules, which ARE the game's behaviour now (owner rule: cap 4; chapter 1
# PS2 spawn lists and room code, one unit): ALIVE_CAP=4 with r101 through its own hold (R101_ALIVE_CAP=4, the reset
# waves capped), ALIVE_CAP_PARK=1, PS2_ENEMY_RULES=1, PS2_ENEMY_ROOMS=0x33f, ANIMALS_OFF=1. Every other RE4DC_ knob
# stays off (render, platform and old-port hooks compile out).
.DEFAULT_GOAL := all
FIGHT_SRCS := em10/em10 em15/em15_set game/em_set game/em_sub game/dmg game/em_dm_val st1/r101 \
	game/sce_com game/sce_at game/game st/em_wrap
# lane eng-e2d item 3: game/libgpu is not hosted: the three calls the image used (ClearOTagR, AddPrim, DelPrim) are the
# scene attachments' list, the engine's (services/scene/at_list.cpp), with sce_at's two walkers. Control build only:
# ATLIST_ORIG=1 hosts libgpu and keeps sce_at's walkers (the engine's copies left out; the link check must FAIL).
# Lane eng-e2d item 3: the logged stubs of engine/fight/fight_svc_stubs.cpp (the binocular's widget and the focus blur,
# the save file's storage, the scenario debug print; DebugTrg the engine's 0): the hosted bodies made weak. (The header
# inlines IDApplication::init and IdBinocular's destructors are taken from the engine's by name.) Control build only:
# FIGHT_STUBS_ORIG=1 keeps them all original (the link check must FAIL).
ifneq ($(FIGHT_STUBS_ORIG),1)
WEAKEN_game/cam_extra += __ZN11IdBinocular4initEP6CameraPvS2_ __ZN11IdBinocular4moveEPv __ZN11IdBinocular4quitEPv \
	__ZN14FocusAnimation4initEi __ZN14FocusAnimation4moveEi __ZN14FocusAnimation4quitEv
WEAKEN_game/game += __ZN9cGameSave4loadEPv __ZN9cGameSave9checkAddrEP12GameSaveData \
	__ZN9cGameSave10calcOffsetEP12GameSaveDataPv __ZN9cGameSave8calcAddrEP12GameSaveData save__9cGameSavePv
WEAKEN_game/sce_com += _SceDebugDisp __Z8DebugTrgi
else
ENG_CPP_OUT += $(ENG)/fight/fight_svc_stubs.cpp
endif
ifeq ($(ATLIST_ORIG),1)
FIGHT_SRCS += game/libgpu
ENG_CPP_OUT += $(ENG)/services/scene/at_list.cpp
else
WEAKEN_game/sce_at += _sceAtSetOtStart _sceAtGetOtAddr
endif
# Lane eng-e2f item 2: sce_at's service functions are the engine's (services/scene/sce_at_svc.cpp: the room set-up, the
# area geometry, the hit, sight and screen tests, the item models and glows, the shadow area's handler; itemZoom and
# releaseModel logged stubs). sce_at's bodies are made weak; its file statics (the system record SceAtSys and its pointer
# pS) and the static shadow handler are made weak globals by services/scene/sce_at_weak.h, force-included (no source
# change, only the symbols' binding): the engine's SceAtInit points pS at the record and its handler takes the table's
# entry. tools/engine/split_check.py checks the object (SCEAT_WEAK_SYMS weak, no section-relative reference to a
# replaced body). Control build only: SCEAT_ORIG=1 keeps sce_at's bodies (the link check must FAIL, 17 back).
SCEAT_NATIVE := _InScreenCheck _SceAtHitCheck _SceAtInit _SceAtItemHitCheck _SceAtItemModelPtr \
	__Z17SceAtSetItemModelP9SceAtWorkP6cModel _itemZoom _releaseModel _sceAtCheckItemEffectCol _sceAtCheckItemModelParent \
	_sceAtGetArea _sceAtGetLadderPos _sceAtHitCheck _sceAtItemEffDelete _sceAtItemEffSet _sceAtSetItemModelParent
ifneq ($(SCEAT_ORIG),1)
WEAKEN_game/sce_at += $(SCEAT_NATIVE)
$(OUT)/h/game/sce_at.o: ORIG_FLAGS += -include $(ENG)/services/scene/sce_at_weak.h
$(OUT)/h/game/sce_at.o: $(ENG)/services/scene/sce_at_weak.h
else
ENG_CPP_OUT += $(ENG)/services/scene/sce_at_svc.cpp
endif
# lane eng-e2a item 3: the scenario areas are the engine's (services/volumes/area_vol.cpp, game/Makefile AREAVOL_OBJ);
# game/area is not hosted (AREA_ORIG=1, a control build only, hosts it again)
ifeq ($(AREA_ORIG),1)
FIGHT_SRCS += game/area
endif
HOSTED_SRCS += $(FIGHT_SRCS)
# Lane eng-e2f item 3: the village square's Ganado voices before the fight (r101_callGanadoVoice, a static task of the
# room script) are the engine's presentation loop (fight/r101_voice.cpp): fight/r101_weak.h, force-included into the
# hosted r101.cpp, makes the static a weak global (no source change, only its binding) and the engine's strong body
# takes its place; r101 is built without the interprocedural optimisations (the split check requires it of a unit with
# a replaced function). Control build only: R101_VOICE_ORIG=1 keeps the original (the link check must FAIL, 1 back).
SPLIT_NOIPA_UNITS += st1/r101
# Lane eng-e2f item 4: cam_extra is built without inlining in this image (SPLIT_NOINLINE_UNITS, as dmg): the binocular
# widget's in-class constructor and destructor (IdBinocular, drawing: the widget's stubs, fight/fight_svc_stubs.cpp) were
# inlined into CameraBinocular's (split problems); out of line, CameraBinocular's calls reach the engine's by symbol.
# Control build only: CAMX_INLINE=1 inlines again (the split check must FAIL, 2 problems).
ifneq ($(CAMX_INLINE),1)
SPLIT_NOINLINE_UNITS += game/cam_extra
endif
ifneq ($(R101_VOICE_ORIG),1)
$(OUT)/h/st1/r101.o: ORIG_FLAGS += -include $(ENG)/fight/r101_weak.h
$(OUT)/h/st1/r101.o: $(ENG)/fight/r101_weak.h
else
ENG_CPP_OUT += $(ENG)/fight/r101_voice.cpp
endif
# route_ck: the native routes service (services/routes, lane eng-e1e), not the original unit
HOSTED_OBJS := $(addprefix $(OUT)/h/,$(addsuffix .o,$(HOSTED_SRCS) $(SVC_ORIG_SRCS)))
ENG_CPP := $(filter-out $(ENG)/core/route.cpp,$(ENG_CPP)) $(filter-out $(ENG_CPP_OUT),$(wildcard $(ENG)/fight/*.cpp)) \
	$(wildcard $(ENG)/services/effects/*.cpp)
ENG_HDRS += $(wildcard $(ENG)/fight/*.h) $(wildcard $(ENG)/services/effects/*.h)
# Lane eng-e2d: the scenario layer's services (services/scene/: the event walk over the record tables, sce_at's
# service functions); sce_com and sce_at are SPLIT_NOIPA_UNITS (their calls reach the engine's bodies)
ENG_CPP += $(filter-out $(ENG_CPP_OUT),$(wildcard $(ENG)/services/scene/*.cpp))
ENG_HDRS += $(wildcard $(ENG)/services/scene/*.h)
SPLIT_NOIPA_UNITS += game/sce_com game/sce_at
ENG_FLAGS += -DE2_BOSS=1 -DE2_FIGHT=1 -I$(ENG)/fight -I$(ENG)/boss -I$(ENG)/services/effects
REND_FLAGS += -DE2_BOSS=1 -DE2_FIGHT=1 -I$(ENG)/services/effects -I$(ENG)/fight
REND_DEPS += $(wildcard $(ENG)/fight/*.inc) $(ENG)/services/effects/fx.h

E2_CAP := -DRE4DC_ALIVE_CAP=4 -DRE4DC_ALIVE_CAP_R101=1 -DRE4DC_ALIVE_CAP_LOG=0
$(OUT)/h/game/em_set.o: ORIG_FLAGS += $(E2_CAP) -DRE4DC_ALIVE_CAP_N=4 -DRE4DC_ALIVE_CAP_PARK=1 -DRE4DC_ANIMALS_OFF=1
$(OUT)/h/game/sce_com.o: ORIG_FLAGS += $(E2_CAP)
$(OUT)/h/st1/r101.o: ORIG_FLAGS += -DRE4DC_R101_ALIVE_CAP=4 -DRE4DC_R101_CAP_N=4 -DRE4DC_R101_CAP_LOG=0 \
	-DRE4DC_R101_CAP_WAVES=1 -DRE4DC_PS2_ENEMY_RULES=1 -DRE4DC_PS2_ENEMY_ROOMS=0x33f -DRE4DC_ALIVE_CAP_ON=1 \
	-D_prolog=r101_prolog -D_epilog=r101_epilog -D_unresolved=r101_unresolved
# src/game/game.cpp names the old port's door-phase probe unconditionally: an empty macro here (knob off).
$(OUT)/h/game/game.o $(OUT)/h/game/sce_at.o: ORIG_FLAGS += "-DRE4DC_DOORPH(x)="
# The Ganado module's REL entry under its own name (em15_set.cpp defines _prolog: EmInitFunc = the em10 init).
$(OUT)/h/em15/em15_set.o: ORIG_FLAGS += -D_prolog=em15_prolog -D_epilog=em15_epilog -D_unresolved=em15_unresolved
# Service accounting of the Ganado paths and the native effect service (fight/fight_wraps.cpp), with E1's wraps.
FIGHT_WRAP_SYMS := At_box_sphere_ck AtBoxCapsuleCk3 RouteCkToEm RouteCkEscEm 	RouteCkToPos RouteCkConnectPosCk RouteCkPosToPosDis RouteCkGetNearPoint EstSet
$(OUT)/e1.elf: WRAPS += $(foreach s,$(FIGHT_WRAP_SYMS),-Wl,--wrap=$(s))
# Controls / arms: make FIGHT=1 FIGHT_EXTRA=-DE1_CONTROL_SHIFT=1 (every pad action one frame late) ...
ENG_FLAGS += $(FIGHT_EXTRA)
# Presentation randomness (owner 2026-11-19 "Split it"; lane eng-e1c's e1_present section): the Ganado's voice, breath
# and chainsaw sound timers, its blood-effect choice and its camera moves draw from the engine generator, not Rnd.
PRESENT_em10/em10 := _Z12em10BloodSetP5cEm10i _Z12em10BreathSeP5cEm10 _Z12em10CamMove2P5cEm10 _Z12em1cBloodSetP5cEm10i \
	_Z16em10CallVoiceSe2P5cEm10ii _Z18em10SetDamageVoiceP5cEm10ii em10CallVoiceSe em10CamMove em10CamMoveAshley \
	em10CamMoveCri em10CamMoveTakeaway em10CsawSignSe plem10KickCamMove

# Lane eng-e2b (item 1): em10's service functions are the engine's (services/em10/: em10_pres.cpp the sound numbers,
# voices, breath, chainsaw tell, footsteps, the weapon's sound set, blood, the kick's mark, water; em10_cam.cpp the cut-in
# cameras and the on-screen check; em10_model.cpp the model parts, accessories, the aiming blend and the destructor;
# docs/engine/lanes/eng-e2b.md). em10's own bodies are made weak (EM10_NATIVE, SH-ELF
# names without the leading underscore) so the engine's are linked and --gc-sections drops the originals. em10.o is
# compiled without the interprocedural optimisations that let a caller keep an inlined, cloned or register-assumed copy
# of a function that is later made weak (EM10_NOIPA: -fipa-ra in particular lets a caller trust the clobbers of the
# body it saw), and game/em10_split_check.py refuses the object when the compiler reports a clone or an inlining of any
# of em10's 40 service functions, or a symbol of the list is not weak.
# Control builds only, never a default: EM10_ORIG=<name> keeps that original body linked (its engine copy made weak; the
# link check must FAIL); EM10_IPA=1 compiles em10.o with the interprocedural optimisations (the split check must FAIL).
EM10SVC_OBJS := $(OUT)/n/em10_pres.o $(OUT)/n/em10_cam.o $(OUT)/n/em10_model.o
EM10_NATIVE := Em10SetSeTbl em10CallVoiceSe _Z16em10CallVoiceSe2P5cEm10ii _Z12em10BreathSeP5cEm10 em10CsawSignSe \
	_Z18em10SetDamageVoiceP5cEm10ii em10BehindSeCk _Z10em10FootSeP5cEm10 em10WepSeEffSet _Z12em10BloodSetP5cEm10i \
	_Z12em1cBloodSetP5cEm10i _Z15em10KickHitMarkP5cEm10 _Z17em10SetDmWaterEffP5cEm10i _Z15em10SetWaterEffP5cEm10 \
	em10CamMove _Z12em10CamMove2P5cEm10 em10CamMoveCri em10CamMoveAshley em10CamMoveTakeaway em10SetCampos2 em10ScreenInCk \
	em10SetAccesory em10ClothPartsSet em10GoodsPartsSet em10SackSet em10BlendMotSet _Z11em10HandSetP5cEm10i \
	_Z11em10HeadSetP5cEm10i _Z13em10ModelInitP5cEm10 _ZN5cEm10D0Ev _ZN5cEm10D1Ev _ZN5cEm10D2Ev
EM10_WEAK := $(addprefix _,$(filter-out $(EM10_ORIG),$(EM10_NATIVE)))
# Lane eng-e2d: em10.o is one of game/Makefile's SPLIT_NOIPA_UNITS (the interprocedural optimisations off, as lane
# eng-e2b's EM10_NOIPA was) and the general split check (tools/engine/split_check.py, per object here and per image in
# check_link.py) replaces game/em10_split_check.py. EM10_IPA=1 (control only) is SPLIT_IPA=em10/em10.
SPLIT_NOIPA_UNITS += em10/em10
ifeq ($(EM10_IPA),1)
SPLIT_IPA += em10/em10
endif
# (WEAKEN_em10/em10, em10ScaleCompress's, is set by game/Makefile after this file is read: the recipe expands it then.)
$(OUT)/h/em10/em10.o: $(ROOT)/src/em10/em10.cpp $(ENG)/host/e1_prelude.h $(ROOT)/port/dreamcast/tools/engine/split_check.py $(ENG)/game/fight.mk
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) -c $< -o $@
	sh-elf-objcopy $(foreach f,$(PRESENT_em10/em10),--rename-section .text.$(f)=e1_present) \
		$(foreach f,$(WEAKEN_em10/em10) $(EM10_WEAK),--weaken-symbol=$(f)) $@
	python3 $(ROOT)/port/dreamcast/tools/engine/split_check.py --obj $@ --unit em10/em10 --weak $(WEAKEN_em10/em10) $(EM10_WEAK)
# (em_sub and dmg, whose service functions lane eng-e2a made weak, are SPLIT_NOIPA_UNITS in game/Makefile: lane eng-e2b's
# -fno-ipa-ra there is part of that set.)
$(OUT)/n/em10_%.o: $(ENG)/services/em10/em10_%.cpp $(ENG)/services/camera/cam_math.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -I$(ENG)/services/camera -c $< -o $@
	$(if $(EM10_ORIG),sh-elf-objcopy $(foreach f,$(EM10_ORIG),--weaken-symbol=_$(f)) $@)
