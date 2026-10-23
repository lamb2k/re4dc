# mendezfx.mk (lane fix-mendez-fx23, 2026-10-23; every knob default 0 = no effect, image unchanged).
# Issue #55 item 5 (Mendez fight, r11f barn: see-through layers, lighting switching on and off, freeze) and #41 (r200
# effect sprites skipped at the castle gate).
# LIGHT_CUT_LOG=1 (test only): logs each light-cut change of cLightMgr::update (camera area, cut, its environment:
#   ambients, TEV scale, filter, light count, then every light of the cut) and Leon's position, once per change.
LIGHT_CUT_LOG ?= 0
ifeq ($(filter $(LIGHT_CUT_LOG),0 1),)
$(error LIGHT_CUT_LOG must be 0 or 1)
endif
ifeq ($(LIGHT_CUT_LOG),1)
GAME_CPPFLAGS += -DRE4DC_LIGHT_CUT_LOG=1
endif
