# fix_switches.mk: PROPOSED switch set (lane eng-fix1, 2026-11-21; docs/engine/FIX_SWITCHES_20261121.md). NOT INCLUDED
# BY ANY MAKEFILE. The integrator rules on switching it on and which lane wires it.
#
# What it is: the old port's class (a) fixes - behaviour fixes inside src/ that the released game (Test 27.2, source
# 6e86de745, recipe tools/d367/test27.2/release-knobs*.txt over build-r21.sh) builds on and the engine images and the
# PC reference build off. Values are the release's own, per unit, read from the release build's preprocessed units
# (make -n of both disc programs, then -E -dM of every src/ unit with its own command line). FIX_<unit> holds the Disc 1
# program's values (chapters 1-1 to 2-3); FIX_CASTLE_<unit> the Disc 2 program's additions (chapters 3-4), for later.
#
# Not in this file: class (b) (old drawing path, memory limits, speed switches, approximations), class (c) (platform
# fixes that belong to an engine service) and class (d) (unknown). See the document.
#
# ---------------------------------------------------------------------------------------------------------------------
# Proposed lines for engine/game/Makefile (after fight.mk / boss.mk are included, so HOSTED_SRCS is final):
#
#   include $(ENG)/game/fix_switches.mk
#   ORIG_INC += -I$(ENG)/host/fixstub          # holds an EMPTY actor_lifetime.h: model.h includes it under RE4DC_GAME
#   $(foreach u,$(HOSTED_SRCS),$(eval $(OUT)/h/$(u).o: ORIG_FLAGS += $(FIX_ALL) $(FIX_$(subst /,_,$(u))) \
#       $(if $(filter $(u),$(FIX_NO_GAME)),,$(FIX_GAME))))
#   (castle images later: the same with $(FIX_CASTLE_$(subst /,_,$(u))) added; em_set then includes the old port's
#   alive_cap_r202_gate.h, which the engine must carry, and stage.cpp needs the PS2 chapter 3 / 4 list data)
#
#   and in the engine (one engine source file, not src/): re4dc_log (printf-style; cManager.h createBack, em_set,
#   emtree, pl_sub, wep02 call it under RE4DC_GAME) and re4dc_em_sleep(int frames) (em_set's EM_MUST retry under
#   EM_READ_RETRY; on the engine a module read does not fail, so a logged no-op is enough). Measured by compiling every
#   hosted unit of the default, FIGHT=1 and BOSS=1 images with these flags (objects only, s/ecc.py): every unit compiles
#   except game/game.cpp (old-port headers native_ui.h, native_motion.h, native_primitive.h), and the only new
#   undefined symbols are re4dc_log, re4dc_em_sleep and (r119) re4dc_emSetMust / re4dc_em_must_end, which em_set.cpp
#   itself defines under EM_READ_RETRY. fight.mk's E2_CAP lines give the same values as below (duplicates are harmless).
#
# Proposed lines for engine/hostref/Makefile (a reference change: its cause is in the source, and FIX_REF=0 keeps the
# old reference as a control build for svc/refctl.sh):
#
#   include ../game/fix_switches.mk
#   FIX_REF ?= 1
#   REF_VARIANT := $(REF_VARIANT)-fix$(FIX_REF)         # a build folder holds one reference only
#   ifeq ($(FIX_REF),1)
#   GAMEINC += $(FIX_HOSTREF)
#   endif
#
#   GAMEINC reaches every game unit of the reference (plain, fma, odump, native and the svc.mk weak copies); each macro in
#   FIX_HOSTREF is referenced only by the unit the release sets it in (em10, pl_sub, em_set), so one flag set is the
#   release's per-unit set. RE4DC_GAME and STAT_ROUTINE_BYTES=1 are already in the reference's GAMEINC.
#   EM_READ_RETRY is left out of FIX_HOSTREF until hostref answers re4dc_em_sleep (host_stubs.cpp, the hostref owner):
#   with it the reference does not link; no reference unit uses EM_OK / EM_MUST (only room code does), so its outcome
#   effect on the reference is none.
# ---------------------------------------------------------------------------------------------------------------------

# Every hosted unit (the release builds it on in every unit: include/types.h EM_OK / EM_MUST).
FIX_ALL := -DRE4DC_EM_READ_RETRY=1

# RE4DC_GAME: the non-PowerPC source paths (GCC / ABI correctness fixes: cam_ctrl's destroyed camera extras, the enemy
# modules' placement construction, pl11, and the blocks that em10 / em35 / em3b / r117's knobs sit in). Every hosted
# unit takes it except the units whose RE4DC_GAME blocks call the old port's platform layer. Extend FIX_NO_GAME when a
# new unit is hosted and its RE4DC_GAME blocks name old-port functions (compile it with FIX_GAME first, as s/ecc.py).
FIX_GAME := -DRE4DC_GAME=1
FIX_NO_GAME := game/game st1/r100

# Route knobs whose blocks in these units only are ABI / construction fixes (elsewhere they are route gating, class b):
FIX_pl14_pl14 := -DRE4DC_ROUTE_CH22=1
FIX_em35_em35 := -DRE4DC_EM35_ROUTINE_BYTES=1 -DRE4DC_ROUTE_CH23=1
FIX_em3b_em3b := -DRE4DC_ROUTE_CH23=1

# The PC reference (see above): the class (a) macros its units reference.
FIX_HOSTREF := -DRE4DC_GANADO_ROUTINE_BYTES=1 -DRE4DC_SUB_EM_FUNC=1 -DRE4DC_ALIVE_CAP=4 -DRE4DC_ALIVE_CAP_N=4 \
	-DRE4DC_ALIVE_CAP_PARK=1 -DRE4DC_ALIVE_CAP_R101=1 -DRE4DC_ANIMALS_OFF=1 -DRE4DC_ROUTE_CH21_FULL=1

# Per unit (src/<dir>/<name> -> FIX_<dir>_<name>), the release's values (generated by s/gen_fix.py from the release
# build; EM_READ_RETRY is in FIX_ALL). The em10 line covers every copy of em10.cpp: the released Disc 2 compiles a
# second copy for em1f without GANADO_ROUTINE_BYTES (see the document: a gap in the release itself).
FIX_Sscrn_ss_pzzl := -DRE4DC_SS_MSG_FIELDS=1
FIX_em10_em10 := -DRE4DC_GANADO_ROUTINE_BYTES=1
FIX_game_card := -DRE4DC_SAVE_ROW_FIX=1
FIX_game_em_set := -DRE4DC_ALIVE_CAP=4 -DRE4DC_ALIVE_CAP_N=4 -DRE4DC_ALIVE_CAP_PARK=1 -DRE4DC_ALIVE_CAP_R101=1 -DRE4DC_ANIMALS_OFF=1 -DRE4DC_ROUTE_CH21_FULL=1
FIX_game_id_sys := -DRE4DC_ID_ALPHA_SAT=1
FIX_game_pl_sub := -DRE4DC_SUB_EM_FUNC=1
FIX_game_sce_com := -DRE4DC_ALIVE_CAP=4
FIX_game_sce_sys := -DRE4DC_ALIVE_CAP=4
FIX_game_stage := -DRE4DC_PS2_CH2_ENEMY=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff -DRE4DC_PS2_ENEMY_RULES=1
FIX_st_em_wrap := -DRE4DC_ALIVE_CAP_ON=1
FIX_st1_r100 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
FIX_st1_r101 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff -DRE4DC_PS2_ENEMY_RULES=1 -DRE4DC_R101_ALIVE_CAP=4 -DRE4DC_R101_CAP_N=4 -DRE4DC_R101_CAP_WAVES=1
FIX_st1_r102 := -DRE4DC_ALIVE_CAP_ON=1
FIX_st1_r104 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
FIX_st1_r105 := -DRE4DC_ALIVE_CAP_ON=1
FIX_st1_r106 := -DRE4DC_ALIVE_CAP_ON=1
FIX_st1_r107 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_RULES=1
FIX_st1_r108 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
FIX_st1_r10a := -DRE4DC_ALIVE_CAP_ON=1
FIX_st1_r10c := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_R10C_SPAWN_LIVE_GUARD=1 -DRE4DC_ROUTE_CH21_FULL=1
FIX_st1_r10f := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_RULES=1
FIX_st1_r111 := -DRE4DC_PS2_ENEMY_RULES=1
FIX_st1_r113 := -DRE4DC_PS2_ENEMY_RULES=1
FIX_st1_r117 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_R117_EFFECT_FAILURE_SAFE=1
FIX_st1_r118 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
FIX_st1_r11a := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
FIX_st1_r11b := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
FIX_st1_r11c := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff -DRE4DC_PS2_ENEMY_RULES=1
FIX_st1_r11d := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff -DRE4DC_PS2_ENEMY_RULES=1
FIX_st1_r11e := -DRE4DC_ALIVE_CAP_ON=1
FIX_st1_r11f := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_RULES=1
FIX_st2_r200 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_RULES=1
FIX_st2_r201 := -DRE4DC_ALIVE_CAP_ON=1
FIX_st2_r202 := -DRE4DC_ALIVE_CAP_ON=1
FIX_st2_r203 := -DRE4DC_ALIVE_CAP_ON=1
FIX_st2_r207 := -DRE4DC_ALIVE_CAP_ON=1
FIX_st2_r208 := -DRE4DC_ALIVE_CAP_ON=1
FIX_st2_r222 := -DRE4DC_ALIVE_CAP_ON=1

# Disc 2 (castle, chapters 3-4) additions: add them when the castle is hosted (em_set then needs the old port's
# alive_cap_r202_gate.h and the PS2 chapter 3 / 4 list data; see the document).
FIX_CASTLE_game_em_set := -DRE4DC_ALIVE_CAP_DEFER_FLAGS=1 -DRE4DC_ALIVE_CAP_DEFER_GOTO_R207=1 -DRE4DC_ALIVE_CAP_NOVIS=1 -DRE4DC_ALIVE_CAP_R202_GATE=1 -DRE4DC_PS2_CH3_ENEMY=1 -DRE4DC_PS2_CH4_ENEMY=1
FIX_CASTLE_game_stage := -DRE4DC_PS2_CH3_ENEMY=1 -DRE4DC_PS2_CH4_ENEMY=1
FIX_CASTLE_st_em_wrap := -DRE4DC_ALIVE_CAP_DEFER_FLAGS=1 -DRE4DC_ALIVE_CAP_DEFER_GOTO_R207=1
FIX_CASTLE_st2_r204 := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r205 := -DRE4DC_ALIVE_CAP_NOVIS=1 -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r206 := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r207 := -DRE4DC_ALIVE_CAP_DEFER_GOTO_R207=1
FIX_CASTLE_st2_r208 := -DRE4DC_PS2_ENEMY_CASTLE=0xe7
FIX_CASTLE_st2_r209 := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r20b := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_CASTLE=0xe7
FIX_CASTLE_st2_r20c := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r20d := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r20e := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r20f := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r211 := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r212 := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r213 := -DRE4DC_ALIVE_CAP_NOVIS=1 -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r214 := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r216 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_CASTLE=0xe7
FIX_CASTLE_st2_r217 := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r218 := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r21a := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r21b := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r21d := -DRE4DC_ALIVE_CAP_NOVIS=1 -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r221 := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r223 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_CASTLE=0xe7
FIX_CASTLE_st2_r224 := -DRE4DC_ALIVE_CAP_ON=1
FIX_CASTLE_st2_r226 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_CASTLE=0xe7
FIX_CASTLE_st2_r227 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_CASTLE=0xe7
FIX_CASTLE_st2_r228 := -DRE4DC_ALIVE_CAP_ON=1
