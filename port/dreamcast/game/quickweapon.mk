# QUICK_WEAPON=1 (lane qws19, default 0; a feature not in the original game): hold X and press the D-pad to equip
# a weapon by kind (up handguns, right shotguns, down grenades, left rifles / TMP / launchers; pressing the same
# direction again cycles to the next owned weapon of that kind). The equip is the case's own: cItemMgr::arm, then
# the weapon part of SubScreenExit (weaponRelease / weaponLoad / weaponInit) in the sub screen's task slot, with
# the game frozen while the weapon module reads from disc. Gate = the case's (subScrCheck + SubScreenCall's
# conditions) plus not shooting / reloading / carrying Ashley. With X up the D-pad maps exactly as before.
# Files: platform/pad.cpp (the chord), src/game/sscrn.cpp (re4dc_qw_frame / qwTask).
QUICK_WEAPON ?= 0
ifeq ($(filter $(QUICK_WEAPON),0 1),)
$(error QUICK_WEAPON must be 0 or 1)
endif
ifneq ($(QUICK_WEAPON),0)
$(OBJDIR)/platform/pad.o: PLATFORM_CPPFLAGS += -DRE4DC_QUICK_WEAPON=1
$(OBJDIR)/src/game/sscrn.o: GAME_CPPFLAGS += -DRE4DC_QUICK_WEAPON=1
endif
