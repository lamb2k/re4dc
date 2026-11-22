# game_settings.mk: the game settings the engine and the PC reference build the original code with (lane eng-fix1,
# H-026; docs/engine/CORRECTIONS_20261121.md section 3). Settings are the owner's product choices, each with who
# decided it and when. The corrections (the original made right on this CPU and compiler) are not here: they are in
# host/corrections.h and game/hosted_corrections.mk. The guards are in host/corrections.h, counted by
# host/guard_hooks.cpp.
#
# ---- departures from the GameCube version, chosen by the owner ----
#   1. At most 4 Ganados alive at once, Novistadors in the same 4; extra sends held and released one at a time, the
#      farthest off-screen parked when more are alive anyway (owner 2026-10-15 "cap"; 2026-10-17 "lets do cap 4 for the
#      zombies"; 2026-10-18 Novistadors "Ok").
#   2. The PS2 version's enemy spawns, per chapter, enemy lists and room code as one unit (owner 2026-10-15 "i want the
#      ps2 logic holistically for enemy spawns in chapter 1"; chapter 2 the same, test 15 / 16).
#   3. No ambient farm animals in stage 1: cows, chickens, the farm dog (owner 2026-10-17 "Get rid of them asap").
#   4. Quick weapon select: hold X and press the D-pad (owner 2026-11-21 "i want to keep quiock weapon switch"). Not in
#      the GameCube game. Its code is in units the engine does not host yet (sscrn.cpp: the sub screen and the weapon
#      list; the X + D-pad chord in the pad path): host/guard_hooks.cpp counts it as a stub in every scene summary until
#      the lane that hosts the items brings them.
# ---- open (not set: off, as the engine has them) ----
#   LIGHT_CUT_HOLD (cam_ctrl, r11f barn light cut): settled by a still pair, engine renderer against a GameCube capture.
#   SS_MENU_ANIM_RT (ss_pzzl, inventory menu flash per elapsed tick): settled by whether the engine's sub screen can
#      draw below 30 Hz on console.
#
# Read by: game/Makefile (one include line, after every image's hosted list is final): each hosted unit takes its
# SET_<dir>_<name>; engine/hostref/Makefile: HOSTREF_SETTINGS (the settings its units name), with CORRECTIONS=1.
# Values: the Test 27.2 release's own, per unit (its Disc 1 program, chapters 1-1 to 2-3), read from the release build's
# preprocessed units; PS2_ENEMY_ROOMS at the release's 0x3ff (integrator H-026). PS2_CH2_ENEMY needs the PS2 chapter 2
# list data (ps2_enemy_ch22_data.inc in PS2_ENEMY_CH22_DIR): set only where it exists.

# 1 and 3 (and r10c's ambush through the cap, ROUTE_CH21_FULL), the units the reference hosts:
HOSTREF_SETTINGS := -DRE4DC_ALIVE_CAP=4 -DRE4DC_ALIVE_CAP_N=4 -DRE4DC_ALIVE_CAP_PARK=1 -DRE4DC_ALIVE_CAP_R101=1 \
	-DRE4DC_ANIMALS_OFF=1 -DRE4DC_ROUTE_CH21_FULL=1 -DRE4DC_QUICK_WEAPON=1

# 4: quick weapon select (sscrn.cpp; not hosted yet).
SET_game_sscrn := -DRE4DC_QUICK_WEAPON=1
# 1, 2, 3 per unit:
SET_game_em_set := -DRE4DC_ALIVE_CAP=4 -DRE4DC_ALIVE_CAP_N=4 -DRE4DC_ALIVE_CAP_PARK=1 -DRE4DC_ALIVE_CAP_R101=1 -DRE4DC_ANIMALS_OFF=1 -DRE4DC_ROUTE_CH21_FULL=1
SET_game_sce_com := -DRE4DC_ALIVE_CAP=4
SET_game_sce_sys := -DRE4DC_ALIVE_CAP=4
SET_game_stage := $(if $(wildcard $(PS2_ENEMY_CH22_DIR)/ps2_enemy_ch22_data.inc),-DRE4DC_PS2_CH2_ENEMY=1) -DRE4DC_PS2_ENEMY_ROOMS=0x3ff -DRE4DC_PS2_ENEMY_RULES=1
SET_st_em_wrap := -DRE4DC_ALIVE_CAP_ON=1
SET_st1_r100 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
SET_st1_r101 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff -DRE4DC_PS2_ENEMY_RULES=1 -DRE4DC_R101_ALIVE_CAP=4 -DRE4DC_R101_CAP_N=4 -DRE4DC_R101_CAP_WAVES=1
SET_st1_r102 := -DRE4DC_ALIVE_CAP_ON=1
SET_st1_r104 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
SET_st1_r105 := -DRE4DC_ALIVE_CAP_ON=1
SET_st1_r106 := -DRE4DC_ALIVE_CAP_ON=1
SET_st1_r107 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_RULES=1
SET_st1_r108 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
SET_st1_r10a := -DRE4DC_ALIVE_CAP_ON=1
SET_st1_r10c := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_ROUTE_CH21_FULL=1
SET_st1_r10f := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_RULES=1
SET_st1_r111 := -DRE4DC_PS2_ENEMY_RULES=1
SET_st1_r113 := -DRE4DC_PS2_ENEMY_RULES=1
SET_st1_r117 := -DRE4DC_ALIVE_CAP_ON=1
SET_st1_r118 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
SET_st1_r11a := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
SET_st1_r11b := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff
SET_st1_r11c := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff -DRE4DC_PS2_ENEMY_RULES=1
SET_st1_r11d := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_ROOMS=0x3ff -DRE4DC_PS2_ENEMY_RULES=1
SET_st1_r11e := -DRE4DC_ALIVE_CAP_ON=1
SET_st1_r11f := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_RULES=1
SET_st2_r200 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_RULES=1
SET_st2_r201 := -DRE4DC_ALIVE_CAP_ON=1
SET_st2_r202 := -DRE4DC_ALIVE_CAP_ON=1
SET_st2_r203 := -DRE4DC_ALIVE_CAP_ON=1
SET_st2_r207 := -DRE4DC_ALIVE_CAP_ON=1
SET_st2_r208 := -DRE4DC_ALIVE_CAP_ON=1
SET_st2_r222 := -DRE4DC_ALIVE_CAP_ON=1

# ---- later: the Disc 2 (castle) settings, chapters 3-4 (not wired; em_set then includes the old port's
# alive_cap_r202_gate.h, and stage.cpp needs the PS2 chapter 3 / 4 list data) ----
# SET_CASTLE_game_em_set := -DRE4DC_ALIVE_CAP_DEFER_FLAGS=1 -DRE4DC_ALIVE_CAP_DEFER_GOTO_R207=1 -DRE4DC_ALIVE_CAP_NOVIS=1 -DRE4DC_ALIVE_CAP_R202_GATE=1 -DRE4DC_PS2_CH3_ENEMY=1 -DRE4DC_PS2_CH4_ENEMY=1
# SET_CASTLE_game_stage := -DRE4DC_PS2_CH3_ENEMY=1 -DRE4DC_PS2_CH4_ENEMY=1
# SET_CASTLE_st_em_wrap := -DRE4DC_ALIVE_CAP_DEFER_FLAGS=1 -DRE4DC_ALIVE_CAP_DEFER_GOTO_R207=1
# SET_CASTLE_st2_r204 := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r205 := -DRE4DC_ALIVE_CAP_NOVIS=1 -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r206 := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r207 := -DRE4DC_ALIVE_CAP_DEFER_GOTO_R207=1
# SET_CASTLE_st2_r208 := -DRE4DC_PS2_ENEMY_CASTLE=0xe7
# SET_CASTLE_st2_r209 := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r20b := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_CASTLE=0xe7
# SET_CASTLE_st2_r20c := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r20d := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r20e := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r20f := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r211 := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r212 := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r213 := -DRE4DC_ALIVE_CAP_NOVIS=1 -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r214 := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r216 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_CASTLE=0xe7
# SET_CASTLE_st2_r217 := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r218 := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r21a := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r21b := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r21d := -DRE4DC_ALIVE_CAP_NOVIS=1 -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r221 := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r223 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_CASTLE=0xe7
# SET_CASTLE_st2_r224 := -DRE4DC_ALIVE_CAP_ON=1
# SET_CASTLE_st2_r226 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_CASTLE=0xe7
# SET_CASTLE_st2_r227 := -DRE4DC_ALIVE_CAP_ON=1 -DRE4DC_PS2_ENEMY_CASTLE=0xe7
# SET_CASTLE_st2_r228 := -DRE4DC_ALIVE_CAP_ON=1

# ---- wiring (engine images only) ----
ifdef HOSTED_SRCS
$(foreach u,$(HOSTED_SRCS),$(eval $(OUT)/h/$(u).o: ORIG_FLAGS += $(SET_$(subst /,_,$(u)))))
$(foreach u,$(HOSTED_SRCS),$(eval $(OUT)/h/$(u).o: $(ENG)/game/game_settings.mk))
endif
