# E2 boss slice (lane eng-boss): the E1 shell plus El Gigante (src/em2b) and its arena script (src/st1/r119), the
# enemy-body behaviour they reach (variant B of s/closure_boss.py: em_sub, em_set, dmg, em_dm_val, emtree, emtorch)
# and the engine pieces under engine/boss/ (route, room set-up, enemy table move, scenario tasks, effect service).
#   make -C port/dreamcast/engine/game BOSS=1 OUT=<dir>   -> <dir>/e1.elf
.DEFAULT_GOAL := all
BOSS_SRCS := em2b/em2b st1/r119 game/em_sub game/em_set game/dmg game/em_dm_val game/emtree game/emtorch game/obj20 game/route_ck game/game
HOSTED_SRCS += $(BOSS_SRCS)
HOSTED_OBJS := $(addprefix $(OUT)/h/,$(addsuffix .o,$(HOSTED_SRCS) $(SVC_ORIG_SRCS)))
ENG_CPP := $(filter-out $(ENG)/core/route.cpp,$(ENG_CPP)) $(wildcard $(ENG)/boss/*.cpp)
ENG_HDRS += $(wildcard $(ENG)/boss/*.h)
ENG_FLAGS += -DE2_BOSS=1 -I$(ENG)/boss
REND_FLAGS += -DE2_BOSS=1
# Module entry points of the hosted overlays are renamed so they link into one image (the old port links each
# module apart): em2b's _prolog / _epilog / _unresolved become em2b_prolog ...
$(OUT)/h/em2b/em2b.o: $(ROOT)/src/em2b/em2b.cpp $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) -c $< -o $@.tmp.o
	sh-elf-objcopy --redefine-sym __prolog=_em2b_prolog --redefine-sym __epilog=_em2b_epilog \
		--redefine-sym __unresolved=_em2b_unresolved $@.tmp.o $@
	rm -f $@.tmp.o
$(OUT)/h/st1/r119.o: $(ROOT)/src/st1/r119.cpp $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) -c $< -o $@.tmp.o
	sh-elf-objcopy --redefine-sym __prolog=_r119_prolog --redefine-sym __epilog=_r119_epilog \
		--redefine-sym __unresolved=_r119_unresolved $@.tmp.o $@
	rm -f $@.tmp.o
# src/game/game.cpp names the old port's door-phase probe unconditionally: an empty macro here (knob off).
$(OUT)/h/game/game.o: ORIG_FLAGS += "-DRE4DC_DOORPH(x)="
# Controls / arms of the boss image: make BOSS=1 BOSS_EXTRA=-DE1_CONTROL_SHIFT=1 (every pad action one frame late).
ENG_FLAGS += $(BOSS_EXTRA)
