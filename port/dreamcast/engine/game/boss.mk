# E2 boss slice (lane eng-boss): the E1 shell plus El Gigante (src/em2b) and its arena script (src/st1/r119), the
# enemy-body behaviour they reach (variant B of s/closure_boss.py: em_sub, em_set, dmg, em_dm_val, emtree, emtorch)
# and the engine pieces under engine/boss/ (route, room set-up, enemy table move, scenario tasks, effect service).
#   make -C port/dreamcast/engine/game BOSS=1 OUT=<dir>   -> <dir>/e1.elf
.DEFAULT_GOAL := all
BOSS_SRCS := em2b/em2b st1/r119 game/em_sub game/em_set game/dmg game/em_dm_val game/emtree game/emtorch game/obj20 game/game
HOSTED_SRCS += $(BOSS_SRCS)
# Lane eng-e2c: El Gigante's service entry points are the engine's (services/boss/; docs/engine/lanes/eng-e2c.md):
# presentation and view (em2b_pres: the event cameras, the quake, the foot landing, the on-screen test) and pose
# (em2b_skel: the neck, the blends, the squash). Compiled with the hosted units' flags and linked before the hosted
# objects; every global symbol they define is made weak in em2b.o (below), so the hosted calls reach the engine bodies
# and --gc-sections drops the original's.
# Control build only (E2C_ORIG=<symbol>, the SH-ELF name, e.g. __Z12em2bNeckMoveP5cEm2b): that original stays linked and
# the engine's copy is made weak (the link check must FAIL on it). Never a default.
BOSSVC_SRCS := em2b_pres em2b_skel
BOSSVC_OBJS := $(addprefix $(OUT)/n/boss_,$(addsuffix .o,$(BOSSVC_SRCS)))
HOSTED_OBJS := $(BOSSVC_OBJS) $(addprefix $(OUT)/h/,$(addsuffix .o,$(HOSTED_SRCS) $(SVC_ORIG_SRCS)))
$(OUT)/n/boss_%.o: $(ENG)/services/boss/%.cpp $(wildcard $(ENG)/services/boss/*.h) $(ENG)/services/camera/cam_math.h $(ENG)/host/e1_prelude.h
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(NATIVE_INC) -I$(ENG)/services/boss -c $< -o $@
	$(if $(E2C_ORIG),sh-elf-objcopy $(foreach f,$(E2C_ORIG),--weaken-symbol=$(f)) $@)
$(OUT)/n/boss_syms.txt: $(BOSSVC_OBJS)
	sh-elf-nm -g --defined-only $^ | awk 'NF == 3 {print $$3}' | sort -u | grep -v -x -F -e - $(foreach f,$(E2C_ORIG),-e $(f)) > $@
ENG_CPP := $(filter-out $(ENG)/core/route.cpp,$(ENG_CPP)) $(wildcard $(ENG)/boss/*.cpp)
ENG_HDRS += $(wildcard $(ENG)/boss/*.h)
ENG_FLAGS += -DE2_BOSS=1 -I$(ENG)/boss
REND_FLAGS += -DE2_BOSS=1
# Module entry points of the hosted overlays are renamed so they link into one image (the old port links each
# module apart): em2b's _prolog / _epilog / _unresolved become em2b_prolog ...
$(OUT)/h/em2b/em2b.o: $(ROOT)/src/em2b/em2b.cpp $(ENG)/host/e1_prelude.h $(OUT)/n/boss_syms.txt
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) -c $< -o $@.tmp.o
	sh-elf-objcopy --redefine-sym __prolog=_em2b_prolog --redefine-sym __epilog=_em2b_epilog \
		--redefine-sym __unresolved=_em2b_unresolved $$(sed 's/^/--weaken-symbol=/' $(OUT)/n/boss_syms.txt) $@.tmp.o $@
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
