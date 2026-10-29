# GAME_ATCHK_DISTINCT29=1: coalesce collision eligibility notes by distinct
# cAtariInfo address, with separate enemy/object pending state and conservative
# per-reader overflow. Requires the existing ordered candidate cache. Default 0
# keeps GAME_ATCHK_CACHE's original ring and object code unchanged.
# Include after game30.mk defines GAME_ATCHK, GAME_ATCHK_LIST and GAME_ATCHK_CACHE.
GAME_ATCHK_DISTINCT29 ?= 0
ifeq ($(filter $(GAME_ATCHK_DISTINCT29),0 1),)
$(error GAME_ATCHK_DISTINCT29 must be 0 or 1)
endif
ifeq ($(GAME_ATCHK_DISTINCT29),1)
ifeq ($(GAME_ATCHK),0)
$(error GAME_ATCHK_DISTINCT29 needs GAME_ATCHK=1)
endif
ifeq ($(GAME_ATCHK_LIST),0)
$(error GAME_ATCHK_DISTINCT29 needs GAME_ATCHK_LIST=1)
endif
ifeq ($(GAME_ATCHK_CACHE),0)
$(error GAME_ATCHK_DISTINCT29 needs GAME_ATCHK_CACHE=1 or 2)
endif
# The wrappers live in atariInfo.h and can be inlined from every game/room
# and platform unit; use the same affected TU flags as GAME_ATCHK_CACHE.
GAME_CPPFLAGS += -DRE4DC_ATCHK_DISTINCT29=1
PLATFORM_CPPFLAGS += -DRE4DC_ATCHK_DISTINCT29=1
endif
