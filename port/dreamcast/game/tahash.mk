# D367 TA_HASH (test builds only; default 0 compiles it out: identical image). TA_HASH=1 folds every
# 32-byte TA store-queue burst of the game frame (stream packets, direct headers, re4dc_ta_put /
# re4dc_ta_vertex bursts) into an FNV-1a hash per display list and logs one line per scene:
#   ta_hash: frame=<native frame> present=<0|1> op=<hash>/<words> tr=.. pt=.. mod=<op mod>,<tr mod>
# Two builds that must submit the same geometry compare these lines frame by frame.
# TA_HASH=2: the same with polygon / sprite header words 4..7 left out (KOS leaves them as stack garbage), so
# two different builds' lines compare.
# TA_HASH=3: as 2, and a header counts only once a vertex follows it (header-only polygons, which draw nothing,
# are left out).
# TA_BIN_DIAG=1 (issue 9, test builds only; needs TA_HASH=1): replaces the ta_hash line with a model of the hardware
# tiler per scene ("tabin:" object pointer blocks against the KOS overflow pool, deepest tile per list, translucent
# triangles in the busiest tile, an ISP/TSP parameter estimate). platform/native_ui.cpp namespace tabin.
TA_HASH ?= 0
TA_BIN_DIAG ?= 0
# Per-texture/source submitted-area observer; diagnostic only, default image unchanged.
TA_MATERIAL_DIAG ?= 0
ifeq ($(TA_MATERIAL_DIAG),1)
ifneq ($(TA_BIN_DIAG),1)
$(error TA_MATERIAL_DIAG=1 needs TA_BIN_DIAG=1)
endif
# Each material/source record is one bounded log call. Use the existing atomic
# RAM-ring append so AICA and vblank writers cannot split diagnostic rows.
ifneq ($(LOGIC_TRACE),1)
$(OBJDIR)/platform/mem.o: PLATFORM_CPPFLAGS += -DRE4DC_LOG_ATOMIC=1
endif
endif
# LBX_CENSUS=1 (lane lbcull 2026-10-15, test only; needs TA_HASH>=1 and LETTERBOX_CLIP>=1): "lbx census:" per 60
# scenes: strips / vertices / header runs of the OP, TR and PT lists in the visible band, wholly under the letterbox
# bars, or wholly off screen (native_ui.cpp lbxc). Measures what a band cull could drop.
LBX_CENSUS ?= 0
ifeq ($(LBX_CENSUS),1)
ifeq ($(TA_HASH),0)
$(error LBX_CENSUS=1 needs TA_HASH=1, 2 or 3)
endif
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/letterbox_clip.o: PLATFORM_CPPFLAGS += -DRE4DC_LBX_CENSUS=1
endif
ifeq ($(TA_BIN_DIAG),1)
ifneq ($(TA_HASH),1)
$(error TA_BIN_DIAG=1 needs TA_HASH=1)
endif
endif
.PHONY: tahash-force
$(OBJDIR)/tahash.h: tahash-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_TA_HASH %s\n#define RE4DC_TA_BIN_DIAG %s\n#define RE4DC_TA_MATERIAL_DIAG %s\n' '$(TA_HASH)' '$(TA_BIN_DIAG)' '$(TA_MATERIAL_DIAG)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
TAHASH_PLATFORM = $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_actor_fast.o
$(TAHASH_PLATFORM): $(OBJDIR)/tahash.h
$(TAHASH_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/tahash.h
ifeq ($(TA_BIN_DIAG),1)
# The translucent fill split (native_ui.cpp tabin "fill"): esp_sub.cpp tags haze / mist sheet sprites.
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_TA_BIN_DIAG=1
endif
