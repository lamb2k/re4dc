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
# TEX_USAGE_LOG=1 (lane texusage22, 2026-10-22; telemetry only, default 0 = no code): the TA_MATERIAL_DIAG observer
# aggregated per texture over a window (300 scenes, or until the room changes) instead of per scene, with each
# triangle's / sprite's texels per pixel (UV area x texture size / unclipped screen area) binned by its clipped screen
# area (<1, 1-2, 2-4, 4-8, >=8 texels per pixel), the polygon header count and the texture size / mip bit. One
# "texuse:" line per (list, source, TSP, TCW) row at the window end. Forces TA_HASH=1 TA_BIN_DIAG=1 TA_MATERIAL_DIAG=1.
# tools/d367/texusage22/texusage.py ranks the lines. Diagnostic builds only.
TEX_USAGE_LOG ?= 0
ifeq ($(TEX_USAGE_LOG),1)
override TA_HASH := 1
override TA_BIN_DIAG := 1
override TA_MATERIAL_DIAG := 1
endif
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
ifeq ($(TA_BIN_DIAG),1)
ifneq ($(TA_HASH),1)
$(error TA_BIN_DIAG=1 needs TA_HASH=1)
endif
endif
.PHONY: tahash-force
$(OBJDIR)/tahash.h: tahash-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_TA_HASH %s\n#define RE4DC_TA_BIN_DIAG %s\n#define RE4DC_TA_MATERIAL_DIAG %s\n#define RE4DC_TEX_USAGE %s\n' '$(TA_HASH)' '$(TA_BIN_DIAG)' '$(TA_MATERIAL_DIAG)' '$(TEX_USAGE_LOG)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
TAHASH_PLATFORM = $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_actor_fast.o
$(TAHASH_PLATFORM): $(OBJDIR)/tahash.h
$(TAHASH_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/tahash.h
ifeq ($(TA_BIN_DIAG),1)
# The translucent fill split (native_ui.cpp tabin "fill"): esp_sub.cpp tags haze / mist sheet sprites.
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_TA_BIN_DIAG=1
endif
