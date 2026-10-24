# Pinned KOS whole-cache writeback repair. Default off: no commands or objects
# change. See docs/KOS_CACHE_AUDIT_20261023.md. Use a fresh OBJDIR per arm.
KOS_CACHE_P2 ?= 0
ifneq ($(KOS_CACHE_P2),0)
ifneq ($(KOS_CACHE_P2),1)
$(error KOS_CACHE_P2 must be 0 or 1)
endif
endif
# Test-only observer; no object/flag/helper changes when it is zero.
KOS_CACHE_P2_DIAG ?= 0
ifneq ($(KOS_CACHE_P2_DIAG),0)
ifneq ($(KOS_CACHE_P2_DIAG),1)
$(error KOS_CACHE_P2_DIAG must be 0 or 1)
endif
endif
ifeq ($(KOS_CACHE_P2_DIAG),1)
ifneq ($(KOS_CACHE_P2),1)
$(error KOS_CACHE_P2_DIAG=1 requires KOS_CACHE_P2=1)
endif
endif
# PLATFORM_OBJS is a wildcard: keep the new diagnostic TU absent when off.
PLATFORM_OBJS := $(filter-out $(OBJDIR)/platform/kos_cache_p2_diag.o,$(PLATFORM_OBJS))
ifeq ($(KOS_CACHE_P2),1)
KOSCACHE := $(OBJDIR)/koscache-p2
KOSCACHE_TOOLS := $(CURDIR)/../tools/d367/kos_cache_audit
KOSCACHE_PATCH := $(CURDIR)/../patches/kos-804b319-cache-p2.patch
KOSCACHE_HEADER := $(KOSCACHE)/tree/kernel/arch/dreamcast/include/arch/cache.h
KOSCACHE_ASM := $(KOSCACHE)/tree/kernel/arch/dreamcast/kernel/cache_p2.S
KOSCACHE_CHECK := $(KOSCACHE)/require_p2.h
KOSCACHE_CPPFLAGS := -DKOS_CACHE_P2=1 -I$(abspath $(KOSCACHE))/tree/kernel/arch/dreamcast/include -include $(abspath $(KOSCACHE_CHECK))
KOSCACHE_OBJS := $(addprefix $(KOSCACHE)/,exec.o dmac.o g1ata.o broadband_adapter.o cache_p2.o)
KOSCACHE_DIAG_ARG :=
ifeq ($(KOS_CACHE_P2_DIAG),1)
KOSCACHE_DIAG_ARG := --diagnostics
KOSCACHE_OBJS += $(OBJDIR)/platform/kos_cache_p2_diag.o
$(OBJDIR)/platform/kos_cache_p2_diag.o: PLATFORM_CPPFLAGS += -DRE4DC_KOS_CACHE_P2_DIAG=1
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_KOS_CACHE_P2_DIAG=1
$(OBJDIR)/platform/kos_cache_p2_diag.o $(OBJDIR)/ui_bridge.o: platform/include/kos_cache_p2_diag.h
KOSCACHE_INPUTS_DIAG := $(KOS_BASE)/kernel/arch/dreamcast/kernel/timer.c \
    $(KOS_BASE)/kernel/arch/dreamcast/include/arch/timer.h $(KOS_BASE)/include/kos/timer.h
endif
KOSCACHE_INPUTS := $(KOS_BASE)/Makefile $(KOS_BASE)/kernel/arch/dreamcast/kernel/Makefile \
	$(KOS_BASE)/include/kos/cache.h $(KOS_BASE)/kernel/arch/dreamcast/include/arch/cache.h \
	$(KOS_BASE)/kernel/arch/dreamcast/kernel/exec.c \
	$(KOS_BASE)/kernel/arch/dreamcast/hardware/dmac.c \
	$(KOS_BASE)/kernel/arch/dreamcast/hardware/g1ata.c \
	$(KOS_BASE)/kernel/arch/dreamcast/hardware/network/broadband_adapter.c

# The original header in KOS_BASE remains untouched. prepare.py checks the pin,
# exact input bytes and complete KOS inline-call inventory before applying.
$(KOSCACHE_HEADER) $(KOSCACHE_ASM) $(KOSCACHE_CHECK) &: $(KOSCACHE_INPUTS) $(KOSCACHE_PATCH) $(KOSCACHE_TOOLS)/prepare.py $(KOSCACHE_TOOLS)/cache_diag.py $(KOSCACHE_INPUTS_DIAG)
	python3 $(KOSCACHE_TOOLS)/prepare.py --kos-root $(KOS_BASE) --output $(KOSCACHE) --patch $(KOSCACHE_PATCH) $(KOSCACHE_DIAG_ARG)

# All game-side writeback APIs pass through these three translation units.
# Explicit prerequisites make the header available before parallel compiles.
$(OBJDIR)/platform/misc.o $(OBJDIR)/platform/modules.o $(OBJDIR)/platform/subscreen_backing.o: $(KOSCACHE_HEADER) $(KOSCACHE_CHECK)
$(OBJDIR)/platform/misc.o $(OBJDIR)/platform/modules.o $(OBJDIR)/platform/subscreen_backing.o: PLATFORM_CPPFLAGS += $(KOSCACHE_CPPFLAGS)

# KOS's cache functions are inline: replacing only the three port users misses
# DMA -> dma_map_src and the other KOS callers. Recompile every pinned user.
$(KOSCACHE)/exec.o: $(KOS_BASE)/kernel/arch/dreamcast/kernel/exec.c $(KOSCACHE_HEADER) $(KOSCACHE_CHECK)
	kos-cc $(KOS_CFLAGS) $(KOSCACHE_CPPFLAGS) -O2 -MMD -MP -c $< -o $@
$(KOSCACHE)/dmac.o: $(KOS_BASE)/kernel/arch/dreamcast/hardware/dmac.c $(KOSCACHE_HEADER) $(KOSCACHE_CHECK)
	kos-cc $(KOS_CFLAGS) $(KOSCACHE_CPPFLAGS) -O2 -MMD -MP -c $< -o $@
$(KOSCACHE)/g1ata.o: $(KOS_BASE)/kernel/arch/dreamcast/hardware/g1ata.c $(KOSCACHE_HEADER) $(KOSCACHE_CHECK)
	kos-cc $(KOS_CFLAGS) $(KOSCACHE_CPPFLAGS) -O2 -MMD -MP -c $< -o $@
$(KOSCACHE)/broadband_adapter.o: $(KOS_BASE)/kernel/arch/dreamcast/hardware/network/broadband_adapter.c $(KOSCACHE_HEADER) $(KOSCACHE_CHECK)
	kos-cc $(KOS_CFLAGS) $(KOSCACHE_CPPFLAGS) -O2 -MMD -MP -c $< -o $@
$(KOSCACHE)/cache_p2.o: $(KOSCACHE_ASM)
	kos-cc $(KOS_CFLAGS) -DKOS_CACHE_P2=1 -c $< -o $@

# Normal objects are passed before the KOS archive by tools/link.sh. Check that
# every replacement actually refers to the new routine, and keep its symbol out
# of the generated-stub path. The archive's matching members then stay unpulled.
.PHONY: kos-cache-p2-check
kos-cache-p2-check: $(KOSCACHE_OBJS)
	python3 $(KOSCACHE_TOOLS)/check_objects.py --prefix $(KOS_CC_BASE)/bin/$(KOS_CC_PREFIX)- --directory $(KOSCACHE) --kos-root $(KOS_BASE)
$(TARGET): $(KOSCACHE_OBJS) | kos-cache-p2-check
OBJS += $(KOSCACHE_OBJS)
-include $(KOSCACHE_OBJS:.o=.d)
endif
