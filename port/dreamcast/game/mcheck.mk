# D367 machine checks (test 9; test builds only, default 0: nothing compiled, identical image). Each knob adds one
# log line that a host script turns into PASS / FAIL (tools/d367/mcheck/):
# MCHECK_PT=1 (needs TA_HASH >= 1, whose hooks see every TA burst): "pt_audit:" per scene: punch-through polygon /
#   sprite headers (PCW list type 4) and those whose blend is not SRCALPHA / INVSRCALPHA (ONE / ZERO draws the
#   cut-out texels as solid on PVR hardware: the test 8 branch-tip cards; PT_BLEND_FIX). pt_check.py.
# MCHECK_SAFE=1 (needs RENDER_OPTION=1): "safe_area:" the speed display's screen rectangle, the render size and the
#   tile rows LETTERBOX_CLIP cleared in that scene (issue #26: tile row 0 lost the counter on consoles; Flycast
#   draws it anyway). safe_check.py.
MCHECK_PT ?= 0
MCHECK_SAFE ?= 0
ifeq ($(MCHECK_PT),1)
ifeq ($(TA_HASH),0)
$(error MCHECK_PT=1 needs TA_HASH=1, 2 or 3)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_MCHECK_PT=1
endif
ifeq ($(MCHECK_SAFE),1)
ifneq ($(RENDER_OPTION),1)
$(error MCHECK_SAFE=1 needs RENDER_OPTION=1 (the speed display))
endif
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/letterbox_clip.o: PLATFORM_CPPFLAGS += -DRE4DC_MCHECK_SAFE=1
endif
# MCHECK_LEONGC=1 (issue #26, 2026-10-13; needs ACTOR_TRANSACTION=1): "LEONGC" when the player's model is left to the
#   source (GameCube) path instead of the owner path (user: GC Leon is a bug, never a fallback): the transaction's last
#   decline, the role-binding event, the material certificate error / role and the hand infos; "LEONGC armed" at the
#   first transaction. leongc_check.py: PASS only with the armed line and zero LEONGC lines.
MCHECK_LEONGC ?= 0
ifeq ($(MCHECK_LEONGC),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error MCHECK_LEONGC=1 needs ACTOR_TRANSACTION=1)
endif
$(OBJDIR)/coarse_actor.o $(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_MCHECK_LEONGC=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_MCHECK_LEONGC=1  # SKINACQ lines: why the skin lease declined
endif
# MODEL_WALK_CHECK=1 (test 11 radio-call fault, 2026-10-14; debug only, default 0): "MWC bad" when an OT chain holds a
#   node, cModel or model info outside main RAM or misaligned (model_asset_bridge.cpp walkcheck), checked at the main
#   loop's steps (main.cpp top / clear / tasks / trans / watch / mes / fade / otag / itask / rdone / end), after each
#   task slot (scheduler.cpp taskN), in sscrn.cpp SubScreenExitCore (ssexit0 / ssexit1, with the OT entries listed for
#   a few steps after the close) and before the draw-plan walk (which then skips a broken table). Gate: zero "MWC bad".
#   =2 (console locator disc): the first bad link stops the game with "MWC <where> t<table> <what> ..." as the stop
#   screen's reason, so a photograph names the step that broke the chain.
MODEL_WALK_CHECK ?= 0
ifneq ($(filter $(MODEL_WALK_CHECK),0 1 2),$(MODEL_WALK_CHECK))
$(error MODEL_WALK_CHECK must be 0, 1 or 2)
endif
ifneq ($(MODEL_WALK_CHECK),0)
$(OBJDIR)/model_asset_bridge.o $(OBJDIR)/src/game/main.o $(OBJDIR)/src/game/sscrn.o $(OBJDIR)/src/game/scheduler.o: GAME_CPPFLAGS += -DRE4DC_MODEL_WALK_CHECK=$(MODEL_WALK_CHECK)
endif
# SS_CLOSE_POISON=1 (test 11 radio-call fault; debug only, default 0): sub screen close fills the window bytes it does
#   not restore (free-cell payloads skipped at open: the screen's heap 12) with 0xA5 (sscrn_bridge.cpp), so a stale
#   reference into the closed screen faults or shows as "MWC bad" on Flycast as well.
#   =2 also fills the dead stack below the closing thread's stack pointer (the frames the restore used, the packed
#   stream's read buffer among them) with 0xA5 after the restore, so a later read of an uninitialised local or a
#   reference into that dead stack shows on Flycast (whose stream bytes differ from the console's).
# DEAD_STACK_POISON=1 (test 11 radio-call fault; debug only, default 0, needs MODEL_WALK_CHECK): every task's dead stack
#   (below its saved stack pointer, after each slot of TaskScheduler) and 6 KiB of the main thread's (at the "top" and
#   "rdone" checkpoints) are filled with 0xA5, so an uninitialised local that reaches an OT entry shows as "MWC bad".
DEAD_STACK_POISON ?= 0
ifneq ($(filter $(DEAD_STACK_POISON),0 1),$(DEAD_STACK_POISON))
$(error DEAD_STACK_POISON must be 0 or 1)
endif
ifeq ($(DEAD_STACK_POISON),1)
ifeq ($(MODEL_WALK_CHECK),0)
$(error DEAD_STACK_POISON=1 needs MODEL_WALK_CHECK=1 or 2)
endif
$(OBJDIR)/model_asset_bridge.o $(OBJDIR)/src/game/scheduler.o: GAME_CPPFLAGS += -DRE4DC_DEAD_STACK_POISON=1
$(OBJDIR)/platform/os.o: PLATFORM_CPPFLAGS += -DRE4DC_DEAD_STACK_POISON=1
endif
SS_CLOSE_POISON ?= 0
ifneq ($(filter $(SS_CLOSE_POISON),0 1 2),$(SS_CLOSE_POISON))
$(error SS_CLOSE_POISON must be 0, 1 or 2)
endif
ifneq ($(SS_CLOSE_POISON),0)
$(OBJDIR)/sscrn_bridge.o: GAME_CPPFLAGS += -DRE4DC_SS_CLOSE_POISON=$(SS_CLOSE_POISON)
$(OBJDIR)/platform/subscreen_backing.o: PLATFORM_CPPFLAGS += -DRE4DC_SS_CLOSE_POISON=$(SS_CLOSE_POISON)
endif
# SS_CLOSE_HOLD=1 (test only, default 0; lane land17 2026-10-17): equalised sub screen close for STRICT pairs. The close
# lands on wall/thread timing (radio voice end, sub screen threads), so a render-cost change can move it by a tick (h2,
# FOLIAGE_NEAR_FIX). A "sshold <frame>..." line in the w11.txt fixture slot (one source frame per close) holds SubScreenExit before
# SubScreenExitCore until that frame on both arms; logs "sshold:" lines. Trace discs only (DBG_WARP fixture reader).
SS_CLOSE_HOLD ?= 0
ifneq ($(filter $(SS_CLOSE_HOLD),0 1),$(SS_CLOSE_HOLD))
$(error SS_CLOSE_HOLD must be 0 or 1)
endif
ifeq ($(SS_CLOSE_HOLD),1)
ifneq ($(DBG_WARP),1)
$(error SS_CLOSE_HOLD=1 needs DBG_WARP=1)
endif
$(OBJDIR)/sscrn_bridge.o $(OBJDIR)/src/game/sscrn.o: GAME_CPPFLAGS += -DRE4DC_SS_CLOSE_HOLD=1
endif
