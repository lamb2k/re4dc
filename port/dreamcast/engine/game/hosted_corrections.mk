# hosted_corrections.mk: the corrections that must be given per unit (lane eng-fix1, H-026;
# docs/engine/CORRECTIONS_20261121.md). The others are in host/corrections.h, included by the prelude of every unit.
# Not options: nothing here can be turned off in the engine build. Read by game/Makefile (one include line, after every
# image's hosted list is final).
#
# RE4DC_GAME selects the original's non-PowerPC paths. In the hosted units they are GCC / ABI corrections: cam_ctrl's
# destroyed camera extras forgotten (a second delete met a 0x09090909 vtable), the enemy modules' placement
# construction (no value-initialisation: it zeroed the archive cEmMgr::construct set), pl11, and the blocks em10, em35
# and r117's corrections sit in. Per unit because:
#   - game/game.cpp and st1/r100.cpp have RE4DC_GAME blocks that call the old port's platform layer (native_ui.h,
#     native_motion.h, native_primitive.h; r100's event-file glue), not corrections;
#   - the prelude is also force-included by engine C++ and the native services, where RE4DC_GAME names reference-only
#     hooks (services/model/model_svc.cpp re4dc_model_assets_changed).
# model.h includes the old port's actor_lifetime.h under RE4DC_GAME; the engine's (host/oldport/) is empty: its
# declarations serve the old drawing path's actor transactions.
# ROUTE_CH22 (pl14) and ROUTE_CH23 (em35, em3b): in these units only, their blocks are corrections (Luis's asm-label
# calls forwarded to cEm off the GameCube; the placement construction that keeps the archive). Elsewhere they are the
# old discs' route gating and stay off.
$(foreach u,$(filter-out game/game st1/r100,$(HOSTED_SRCS)),$(eval $(OUT)/h/$(u).o: ORIG_FLAGS += -DRE4DC_GAME=1 \
	-I$(ENG)/host/oldport))
$(OUT)/h/pl14/pl14.o: ORIG_FLAGS += -DRE4DC_ROUTE_CH22=1
$(OUT)/h/em35/em35.o $(OUT)/h/em3b/em3b.o: ORIG_FLAGS += -DRE4DC_ROUTE_CH23=1
$(foreach u,$(HOSTED_SRCS),$(eval $(OUT)/h/$(u).o: $(ENG)/game/hosted_corrections.mk $(ENG)/host/corrections.h))
