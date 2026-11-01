# barn28.mk (lane barn28, 2026-10-28). Absent/0 adds no CPP flags.
# BARN28_EMDUMP=1 (diagnostic, warp builds): every alivelog line also lists each enemy work's id and position.
BARN28_EMDUMP ?= 0
ifeq ($(BARN28_EMDUMP),1)
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_BARN28_EMDUMP=1
endif
# BARN28_DIAG=1 (diagnostic): B28L lines (actor parts off the fast light fold, by model and reason) and, with
# DRAW_SETUP_AUDIT=1, every DSA24 page row in the log.
BARN28_DIAG ?= 0
ifeq ($(BARN28_DIAG),1)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_BARN28_DIAG=1
$(OBJDIR)/draw_setup_audit.o: PLATFORM_CPPFLAGS += -DRE4DC_BARN28_DIAG=1
$(OBJDIR)/platform/native_model.o: PLATFORM_CPPFLAGS += -DRE4DC_BARN28_DIAG=1
endif
ifeq ($(BARN28_DIAG),1)
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_BARN28_DIAG=1
endif
# ACTOR_LIGHT_CAP=1 (render only, approximation, default 0; needs GIGANTE_LIGHTS; user 10-28 no per-vertex fallback): no
# actor part takes the exact per-vertex evaluator: >3 lights fold the 3 strongest (all models), per-vertex-colour and
# diffuse/scale records fold as an approximation, anything left draws one flat colour (native_actor_fast.cpp).
# r103 barn interior: exact light pass 1.6 hw ms MODELLED -> 0.
ACTOR_LIGHT_CAP ?= 0
ifneq ($(ACTOR_LIGHT_CAP),0)
ifeq ($(filter $(ACTOR_LIGHT_CAP),1),)
$(error ACTOR_LIGHT_CAP must be 0 or 1)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_LIGHT_CAP=1
endif
