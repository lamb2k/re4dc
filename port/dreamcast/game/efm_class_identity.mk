# GAME_EFM_CLASS_IDENTITY=1: EfmDelete's existing 64-slot class index follows object
# construction and mapping incarnations. An ordinary deletion keeps the index.
# This fragment is included after game30.mk by the shared Make owner.
GAME_EFM_CLASS_IDENTITY ?= 0
ifneq ($(words $(GAME_EFM_CLASS_IDENTITY)),1)
$(error GAME_EFM_CLASS_IDENTITY must be exactly 0 or 1)
endif
ifneq ($(filter-out 0 1,$(GAME_EFM_CLASS_IDENTITY)),)
$(error GAME_EFM_CLASS_IDENTITY must be 0 or 1)
endif
ifneq ($(GAME_EFM_CLASS_IDENTITY),0)
ifeq ($(GAME_FX_SCAN),0)
$(error GAME_EFM_CLASS_IDENTITY needs GAME_FX_SCAN=1 or 2)
endif
ifeq ($(GAME_ATCHK_LIST),0)
$(error GAME_EFM_CLASS_IDENTITY needs GAME_ATCHK_LIST=1)
endif
ifeq ($(GAME_WORKAT_INLINE),0)
$(error GAME_EFM_CLASS_IDENTITY needs GAME_WORKAT_INLINE=1)
endif
GAME_CPPFLAGS += -DRE4DC_EFM_CLASS_IDENTITY=$(GAME_EFM_CLASS_IDENTITY)
PLATFORM_CPPFLAGS += -DRE4DC_EFM_CLASS_IDENTITY=$(GAME_EFM_CLASS_IDENTITY)
endif
