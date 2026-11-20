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
	game/sce_com game/sce_at game/area game/game
HOSTED_SRCS += $(FIGHT_SRCS)
SVC_ORIG_SRCS += game/route_ck
HOSTED_OBJS := $(addprefix $(OUT)/h/,$(addsuffix .o,$(HOSTED_SRCS) $(SVC_ORIG_SRCS)))
ENG_CPP := $(filter-out $(ENG)/core/route.cpp,$(ENG_CPP)) $(wildcard $(ENG)/fight/*.cpp) $(wildcard $(ENG)/services/effects/*.cpp)
ENG_HDRS += $(wildcard $(ENG)/fight/*.h) $(wildcard $(ENG)/services/effects/*.h)
ENG_FLAGS += -DE2_BOSS=1 -DE2_FIGHT=1 -I$(ENG)/fight -I$(ENG)/boss -I$(ENG)/services/effects
REND_FLAGS += -DE2_BOSS=1 -DE2_FIGHT=1 -I$(ENG)/services/effects

E2_CAP := -DRE4DC_ALIVE_CAP=4 -DRE4DC_ALIVE_CAP_R101=1 -DRE4DC_ALIVE_CAP_LOG=0
$(OUT)/h/game/em_set.o: ORIG_FLAGS += $(E2_CAP) -DRE4DC_ALIVE_CAP_N=4 -DRE4DC_ALIVE_CAP_PARK=1 -DRE4DC_ANIMALS_OFF=1
$(OUT)/h/game/sce_com.o: ORIG_FLAGS += $(E2_CAP)
$(OUT)/h/st1/r101.o: ORIG_FLAGS += -DRE4DC_R101_ALIVE_CAP=4 -DRE4DC_R101_CAP_N=4 -DRE4DC_R101_CAP_LOG=1 \
	-DRE4DC_R101_CAP_WAVES=1 -DRE4DC_PS2_ENEMY_RULES=1 -DRE4DC_PS2_ENEMY_ROOMS=0x33f -DRE4DC_ALIVE_CAP_ON=1 \
	-D_prolog=r101_prolog -D_epilog=r101_epilog -D_unresolved=r101_unresolved
# src/game/game.cpp names the old port's door-phase probe unconditionally: an empty macro here (knob off).
$(OUT)/h/game/game.o $(OUT)/h/game/sce_at.o: ORIG_FLAGS += "-DRE4DC_DOORPH(x)="
# The Ganado module's REL entry under its own name (em15_set.cpp defines _prolog: EmInitFunc = the em10 init).
$(OUT)/h/em15/em15_set.o: ORIG_FLAGS += -D_prolog=em15_prolog -D_epilog=em15_epilog -D_unresolved=em15_unresolved
# Controls / arms: make FIGHT=1 FIGHT_EXTRA=-DE1_CONTROL_SHIFT=1 (every pad action one frame late) ...
ENG_FLAGS += $(FIGHT_EXTRA)
