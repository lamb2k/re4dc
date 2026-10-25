# SCENERY_N256=1 (lane scenery-cut25, Test 25, render only, default 0): the r101 / r103 PS2 worlds ship re-exported with
# meshlets of up to 256 vertices (data set n256w25: ps2-world.re4mesh + r101 ps2-world.r4sg; R4PW / ids / r4tc unchanged).
# Fewer, larger world pieces: less per-piece setup, select and header work. The knob only adds the two packages'
# WORLD_RECT21 provenance certificates (texture_rect21/provenance_certificates_n256.inc), so the certified policy crc,
# and with it R4ID / R4TC / area-hide binding, holds for the re-exported packages. Without the knob a disc carrying
# n256w25 loses those sidecars (the 10-24 b13-n256 trap); without n256w25 the knob changes nothing.
# Never in KSETS (knob-off discs) and never without n256w25.
SCENERY_N256 ?= 0
ifneq ($(filter-out 0 1,$(SCENERY_N256)),)
$(error SCENERY_N256 must be 0 or 1)
endif
ifeq ($(SCENERY_N256),1)
ifneq ($(WORLD_RECT21),1)
$(error SCENERY_N256=1 needs WORLD_RECT21=1 (it only adds rect21 certificates))
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_N256=1
endif
