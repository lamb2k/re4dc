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
#   BENCH_ID=<id>  build id shown on the start and results screens and in the results code (default dev).
#   TAIL_METER=1   (lane frame-tail 2026-10-19; benchmark discs only, needs BENCHMARK=1 and PACE_VMU_GPU=1; default 0 = no
#                  object changes) where each drawn picture's time goes: CPU work, CPU blocked in the PVR scene open /
#                  finish, spin to the next vblank, spin over further vblanks (pacing), TA done, PVR render, render still
#                  running after the CPU work. One log line per drawn picture ("tail:") and a second results page (Y).
BENCHMARK ?= 0
BENCH_ID ?= dev
TAIL_METER ?= 0
ifneq ($(filter $(TAIL_METER),0 1),$(TAIL_METER))
$(error TAIL_METER must be 0 or 1)
endif
ifeq ($(TAIL_METER),1)
ifneq ($(BENCHMARK),1)
$(error TAIL_METER=1 needs BENCHMARK=1 (benchmark discs only))
endif
ifneq ($(PACE_VMU_GPU),1)
$(error TAIL_METER=1 needs PACE_VMU_GPU=1 (the PVR event stamps))
endif
ifeq ($(DOOR_PROBE),1)
$(error TAIL_METER=1 and DOOR_PROBE=1 both own the main loop spin marks)
endif
$(OBJDIR)/src/game/main.o $(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_TAIL_METER=1
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/bench.o: PLATFORM_CPPFLAGS += -DRE4DC_TAIL_METER=1
endif
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
PLATFORM_OBJS += $(OBJDIR)/bench.o
# included after the link rule: name the object as its prerequisite too
$(TARGET): $(OBJDIR)/bench.o
GAME_LDFLAGS += -Wl,--wrap=OSInit -Wl,--wrap=maple_dev_status -Wl,--wrap=maple_enum_dev -Wl,--wrap=re4dc_ui_frame
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_BENCHMARK=1
$(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_BENCHMARK=1
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
