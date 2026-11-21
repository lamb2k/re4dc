# E2 boss slice (lane eng-boss): the E1 shell plus El Gigante (src/em2b) and its arena script (src/st1/r119), the
# enemy-body behaviour they reach (variant B of s/closure_boss.py: em_sub, em_set, dmg, em_dm_val, emtree, emtorch)
# and the engine pieces under engine/boss/ (route, room set-up, enemy table move, scenario tasks, effect service).
#   make -C port/dreamcast/engine/game BOSS=1 OUT=<dir>   -> <dir>/e1.elf
.DEFAULT_GOAL := all
# Lane eng-e2c: game/obj20 (the oba collision objects) is not hosted: services/boss/oba_obj.cpp has the whole unit.
# Control build only: OBA_ORIG=1 hosts game/obj20 again in place of the engine's (the link check must FAIL). Never a default.
BOSS_SRCS := em2b/em2b st1/r119 game/em_sub game/em_set game/dmg game/em_dm_val game/emtree game/emtorch game/game
ifeq ($(OBA_ORIG),1)
BOSS_SRCS += game/obj20
endif
HOSTED_SRCS += $(BOSS_SRCS)
# Lane eng-e2c: El Gigante's service entry points are the engine's (services/boss/; docs/engine/lanes/eng-e2c.md):
# presentation and view (em2b_pres: the event cameras, the quake, the foot landing, the on-screen test), pose
# (em2b_skel: the neck, the blends, the squash), lifetime (em2b_life: the giant's, the tree's and the torch's
# destructors) and the collision bodies (oba_obj: the oba objects, the giants' push-apart). Compiled with the hosted
# units' flags and linked before the hosted objects; every global symbol they define is made weak in em2b.o (below),
# so the hosted calls reach the engine bodies and --gc-sections drops the original's. The tree's and the torch's
# destructors are the compiler's inline (weak) copies in emtree.o and emtorch.o: the engine's strong ones take their place.
# Control build only (E2C_ORIG=<symbol>, the SH-ELF name, e.g. __Z12em2bNeckMoveP5cEm2b): that original stays linked and
# the engine's copy is made weak (the link check must FAIL on it). Never a default.
BOSSVC_SRCS := em2b_pres em2b_skel em2b_life em2b_setup
ifneq ($(OBA_ORIG),1)
BOSSVC_SRCS += oba_obj
endif
# Lane eng-e2c (integrator ruling 2026-11-21): the room's thunder (services/boss/r119_thunder.cpp). r119.cpp's three
# thunder functions are static: the hosted unit is compiled with services/boss/r119_weak.h force-included (they become
# weak symbols, referenced by symbol), and game/r119_split_check.py must pass on the object (no section reference, no
# copy inlined elsewhere) or the build stops. Control build only: R119_ORIG=1 builds r119 as it was and links no engine
# thunder (the link check must FAIL on the three). Never a default.
ifneq ($(R119_ORIG),1)
BOSSVC_SRCS += r119_thunder
R119_WEAK := -include $(ENG)/services/boss/r119_weak.h
endif
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
$(OUT)/h/st1/r119.o: $(ROOT)/src/st1/r119.cpp $(ENG)/host/e1_prelude.h $(ENG)/services/boss/r119_weak.h $(ENG)/game/r119_split_check.py
	@mkdir -p $(dir $@)
	kos-c++ $(ORIG_FLAGS) $(ORIG_INC) $(R119_WEAK) -c $< -o $@.tmp.o
	sh-elf-objcopy --redefine-sym __prolog=_r119_prolog --redefine-sym __epilog=_r119_epilog \
		--redefine-sym __unresolved=_r119_unresolved $@.tmp.o $@
	rm -f $@.tmp.o
	$(if $(R119_WEAK),python3 $(ENG)/game/r119_split_check.py $@ > $@.split.txt || { cat $@.split.txt; rm -f $@; exit 1; })
# src/game/game.cpp names the old port's door-phase probe unconditionally: an empty macro here (knob off).
$(OUT)/h/game/game.o: ORIG_FLAGS += "-DRE4DC_DOORPH(x)="
# Controls / arms of the boss image: make BOSS=1 BOSS_EXTRA=-DE1_CONTROL_SHIFT=1 (every pad action one frame late).
ENG_FLAGS += $(BOSS_EXTRA)
