# D367 public benchmark disc (bench.cpp + hooks in dbgwarp_bridge.cpp, pace.cpp, platform/native_ui.cpp,
# platform/dvd_read_safe.cpp). Included at the end of the Makefile. Default 0: nothing is compiled or linked and the image
# is byte-identical with or without this file.
#   BENCHMARK=1    benchmark disc only, never a play image (user 2026-10-15: "make the benchmark disk public for testers ...
#                  with a clear indicator that it isn't the game"). The disc boots into a start screen (KOS framebuffer,
#                  before pvr_init) that says it is not the game, then runs the scripted scenes of /cd/dc/warp.txt (scene 1)
#                  and /cd/dc/bench2.txt (scene 2) through the warp rig, each scene from a soft reset of the source
#                  (systemSoftReset, as Game Reset), then a results screen (drawn into the displayed framebuffer while the
#                  frame loop stops; hwcal r21v 10-04 method) with a code testers can type. A pressed A runs both scenes
#                  again. Every presented frame carries the banner "BENCHMARK DISC - NOT THE GAME". VMU: memory cards are
#                  hidden from the game (no save, no VMU file), the controller is masked after START (scripted input only).
#                  Measurement = the existing one-second pace windows (pace.cpp: drawn frames, ticks, GPU render time),
#                  the tick log snapshot (CPU), the disc read meter (reads, game blocked time) and KOS headroom per tick.
#                  Warp lines: `bench <scene no> <begin room frame> <end room frame> <name>` (the measured window).
#                  v2 (2026-10-15): a second results page (B or Y switches pages) with SH-4 performance counters by
#                  part of the frame (logic, actor prep, actor draw, world draw, other, wait), per drawn frame:
#                  time (counter 1 cycles, KOS's ns timer), D-cache miss pipeline freeze cycles, operand-cache read and
#                  write misses and I-cache miss freeze cycles on counter 2, one event per drawn-frame period in turn
#                  (not per vblank tick: the 10-04 hwcal aliasing trap), every ratio taken over the same periods.
#                  Marks: src/game/main.cpp, src/game/trans.cpp, coarse.cpp. A second CODE line with its own check.
#                  Scene 3 (/cd/dc/bench3.txt, results page 3, CODE 3): the geometry sweep, the r101 cross view with the
#                  game logic frozen (TaskScheduler skipped, state hash logged and checked) and six render-only settings
#                  (as shipped, half / no Ganados, PS2 world far 18.75 m, no Leon, world far 12.5 m): TA
#                  vertices, CPU / GPU ms and misses per frame, and ms per 1k vertices from the differences.
#   BENCH_ID=<id>  build id shown on the start and results screens and in the results code (default dev).
BENCHMARK ?= 0
BENCH_ID ?= dev
ifneq ($(filter $(BENCHMARK),0 1),$(BENCHMARK))
$(error BENCHMARK must be 0 or 1)
endif
ifeq ($(BENCHMARK),1)
ifneq ($(DBG_WARP),1)
$(error BENCHMARK=1 needs DBG_WARP=1 (the scenes are warp rig fixtures))
endif
ifneq ($(WARP_AFTER_RESET),1)
$(error BENCHMARK=1 needs WARP_AFTER_RESET=1 (the next scene is armed from systemSoftReset))
endif
ifneq ($(DISC_READ_METER),1)
$(error BENCHMARK=1 needs DISC_READ_METER=1 (disc reads / blocked time per window))
endif
ifneq ($(PHASE_METER),1)
$(error BENCHMARK=1 needs PHASE_METER=1 (CPU per tick from the tick log window))
endif
ifneq ($(RENDER_OPTION),1)
$(error BENCHMARK=1 needs RENDER_OPTION=1 (the banner is drawn next to the speed display))
endif
ifneq ($(CRASH_SCREEN),1)
$(error BENCHMARK=1 needs CRASH_SCREEN=1 (re4dc_ui_frame is wrapped for its hang watchdog))
endif
ifneq ($(PACE_VMU),1)
$(error BENCHMARK=1 needs PACE_VMU=1 (the one-second pace windows))
endif
ifeq ($(PMC_ROW),1)
$(error BENCHMARK=1 owns performance counter 2 (results page 2); PMC_ROW=1 uses it too)
endif
# BENCH_POC=1 (lane poc101 2026-10-15, POC101 disc; needs BENCHMARK=1): the speed-up layers as run-time toggles in one
# image. Scenes 1..9 = live runs of the r101 cross, one per row, the fixture's `poc <mask>` line (after its `bench`
# line) turns layers on (bench.cpp kPocLayer bits; 0x8000 = ALL ON); scene 10 = frozen render sweep (all off, each
# render layer, all on); scene 11 = look sweep (all off / all on: development still sheets). A layer is in the image
# when its knob is on in the make line; its code asks re4dc_poc_on(bit) at its decision point (BENCH_POC builds only).
# 0 (default): nothing changes (knob-off identity with the definitive benchmark program).
BENCH_POC ?= 0
# BENCH_AUTO_S=N: seconds the start screen waits for START before it starts by itself (default 20). hw-model trace builds
# (interpreter, no pad input) use 1: same image layout, one constant.
BENCH_AUTO_S ?= 20
ifneq ($(BENCH_AUTO_S),20)
$(OBJDIR)/bench.o: PLATFORM_CPPFLAGS += -DRE4DC_BENCH_AUTO_S=$(BENCH_AUTO_S)
endif
ifeq ($(BENCH_POC),1)
POC_CPPFLAGS := -DRE4DC_BENCH_POC=1
POC_CPPFLAGS += $(if $(filter-out 0,$(PS2_PVS)),-DRE4DC_POC_HAS_PVS=1)
POC_CPPFLAGS += $(if $(filter-out 0,$(WORLD_LOD)),-DRE4DC_POC_HAS_WLOD=1,$(if $(filter-out 0,$(WORLD_LOD_PROBE)),-DRE4DC_POC_HAS_WLOD=2))
POC_CPPFLAGS += $(if $(filter-out 0,$(LEON_LOD)),-DRE4DC_POC_HAS_LEON=$(if $(filter 70,$(LEON_LOD)),2,1))
POC_CPPFLAGS += $(if $(filter-out 0,$(UI_OT_CACHE)),-DRE4DC_POC_HAS_UIOT=1)
POC_CPPFLAGS += $(if $(filter-out 0,$(COLL_BROADPHASE_CACHE)),-DRE4DC_POC_HAS_COLL=1)
POC_CPPFLAGS += $(if $(filter-out 0,$(CROWD_FAR)),-DRE4DC_POC_HAS_FARMESH=1)
POC_CPPFLAGS += $(if $(filter-out 0,$(CROWD_FLAT_LIGHT)),-DRE4DC_POC_HAS_FLATLIGHT=1)
POC_CPPFLAGS += $(if $(filter-out 0,$(FAR_HALF)),-DRE4DC_POC_HAS_FARHALF=1)
$(OBJDIR)/bench.o: PLATFORM_CPPFLAGS += $(POC_CPPFLAGS)
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_BENCH_POC=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_BENCH_POC=1
ifneq ($(filter-out 0,$(FAR_HALF)),)
ifneq ($(FAR_HALF_RT),1)
$(error BENCH_POC with FAR_HALF needs FAR_HALF_RT=1 (bench.cpp poc_apply sets its run-time switch))
endif
endif
# the layers' hooks (each acts only while its bit is on)
ifneq ($(filter-out 0,$(WORLD_LOD))$(filter-out 0,$(WORLD_LOD_PROBE)),)
ifneq ($(filter-out 0,$(WORLD_LOD)),)
ifneq ($(filter-out 0,$(WORLD_LOD_PROBE)),)
$(error BENCH_POC: WORLD_LOD and WORLD_LOD_PROBE share layer 0x02; build one)
endif
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_POC_WLOD=1
endif
else ifneq ($(BENCH_POC),0)
$(error BENCH_POC must be 0 or 1)
endif
PLATFORM_OBJS += $(OBJDIR)/bench.o
# included after the link rule: name the object as its prerequisite too
$(TARGET): $(OBJDIR)/bench.o
GAME_LDFLAGS += -Wl,--wrap=OSInit -Wl,--wrap=maple_dev_status -Wl,--wrap=maple_enum_dev -Wl,--wrap=re4dc_ui_frame
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_BENCHMARK=1
$(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_BENCHMARK=1
$(OBJDIR)/src/game/main.o $(OBJDIR)/src/game/trans.o $(OBJDIR)/coarse.o: GAME_CPPFLAGS += -DRE4DC_BENCHMARK=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_BENCHMARK=1
$(OBJDIR)/platform/dvd_read_safe.o: PLATFORM_CPPFLAGS += -DRE4DC_BENCHMARK=1
.PHONY: bench-force
$(OBJDIR)/bench.h: bench-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_BENCH_ID "%s"\n' '$(BENCH_ID)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/bench.o: bench.cpp $(OBJDIR)/bench.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -include $(OBJDIR)/bench.h -MMD -MP -c $< -o $@
-include $(OBJDIR)/bench.d
endif
