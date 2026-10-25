# ACTOR_GANADO_PS2_STUMP=1 (default 0; render only): the exact PS2 lost-head stumps of all five Ganado cast appearances
# and the hand poses 449 / 450 / 454 / 455 (lane stump17 10-17; Codex 10-13: appearance 2 only). The private dir holds
# tools/d367/ps2_ganado_stump.py's ganado_ps2_stump_runtime.h (layout and digests only); the meshes are data set stump17.
ACTOR_GANADO_PS2_STUMP ?= 0
ACTOR_GANADO_PS2_STUMP_DIR ?=
# ACTOR_GANADO_PS2_GRIP=1 (lane purge-cast24 10-24, GC purge; default 0; render only; needs ACTOR_GANADO_PS2_STUMP=1):
# em10HandSet's grip hands (BIN 451 / 456: a held weapon or torch; r108 r118 r11a) draw their PS2 meshes from the variant
# package instead of the GameCube geometry (ganado_extra). ACTOR_GANADO_PS2_STUMP_DIR must then hold the 11-geometry
# runtime header of ps2_ganado_stump.py --grip, and the disc the matching ganado_var.re4gv (data set grip24).
ACTOR_GANADO_PS2_GRIP ?= 0
ifeq ($(filter $(ACTOR_GANADO_PS2_GRIP),0 1),)
$(error ACTOR_GANADO_PS2_GRIP must be 0 or 1)
endif
ifeq ($(ACTOR_GANADO_PS2_GRIP)$(ACTOR_GANADO_PS2_STUMP),10)
$(error ACTOR_GANADO_PS2_GRIP needs ACTOR_GANADO_PS2_STUMP=1)
endif
ifeq ($(filter $(ACTOR_GANADO_PS2_STUMP),0 1),)
$(error ACTOR_GANADO_PS2_STUMP must be 0 or 1)
endif
ifeq ($(ACTOR_GANADO_PS2_STUMP),1)
ifneq ($(ACTOR_TRANSACTION)$(COARSE_SKIN_FTRV)$(PS2_GANADO),111)
$(error ACTOR_GANADO_PS2_STUMP needs ACTOR_TRANSACTION=1 COARSE_SKIN_FTRV=1 PS2_GANADO=1)
endif
ifeq ($(wildcard $(ACTOR_GANADO_PS2_STUMP_DIR)/ganado_ps2_stump_runtime.h),)
$(error ACTOR_GANADO_PS2_STUMP_DIR must contain the qualified ganado_ps2_stump_runtime.h)
endif
$(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_GANADO_PS2_STUMP=1
ifeq ($(ACTOR_GANADO_PS2_GRIP),1)
$(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_GANADO_PS2_GRIP=1
# compose-test24 (10-24, s30 heap 4): every route movie borrows the variant cell before heap_before (native_movie.cpp).
$(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_GANADO_VAR_MOVIE_LEND=1
endif
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -I$(ACTOR_GANADO_PS2_STUMP_DIR)
$(OBJDIR)/coarse_ganado.o: $(ACTOR_GANADO_PS2_STUMP_DIR)/ganado_ps2_stump_runtime.h
# lane stump17 (10-17): the variant meshes are the disc package dc/native/ganado/ganado_var.re4gv (data set stump17),
# a heap-4 room cell: ui_bridge.cpp frees it at room leave, native_movie.cpp lends it to a movie that does not fit.
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_GANADO_VAR=1
$(OBJDIR)/platform/native_movie.o: PLATFORM_CPPFLAGS += -DRE4DC_GANADO_VAR=1
endif
