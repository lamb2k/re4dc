# Build 27: recovered civilian / Government / Thompson weapon modules.
# Existing module generator/localization/state handling is used unchanged.
WEP_MODULES_27 ?= 0
ifneq ($(words $(WEP_MODULES_27)),1)
$(error WEP_MODULES_27 must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(WEP_MODULES_27)),)
$(error WEP_MODULES_27 must be 0 or 1)
endif
ifeq ($(WEP_MODULES_27),1)
ifeq ($(filter wep05,$(MODULES)),)
MODULES += wep05
endif
MODULES += wep06 wep12
# cObjMgr initializes its work before these constructors and assigns id/serial
# afterwards; no cEm direct-slot consumers. See the Build 27 source audit.
WEP27_AUDITED_MODULES = wep06 wep12
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -DRE4DC_WEP_MODULES_27=1
$(OBJDIR)/src/game/read.o $(OBJDIR)/src/game/pl_wep.o $(OBJDIR)/src/game/item.o $(OBJDIR)/src/game/sscrn.o $(OBJDIR)/src/game/t_option.o: GAME_CPPFLAGS += -DRE4DC_WEP_MODULES_27=1
endif
