# Build29 collision line continuation. Include after game30.mk so GAME_LINE_WALK
# has its resolved value. Only atari.o consumes the control; absent and zero
# select the existing assembly gather and recursive fallback unchanged.
GAME_LINE_RESUME ?= 0
ifeq ($(filter $(GAME_LINE_RESUME),0 1),)
$(error GAME_LINE_RESUME must be 0 or 1)
endif
ifeq ($(GAME_LINE_RESUME),1)
ifeq ($(GAME_LINE_WALK),0)
$(error GAME_LINE_RESUME=1 needs GAME_LINE_WALK=1 or 2)
endif
$(OBJDIR)/src/game/atari.o: GAME_CPPFLAGS += -DRE4DC_LINE_RESUME=1
endif
