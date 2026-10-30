# D367 frame pacing (design-pacing DESIGN.md: option B, render skip with catch-up). Included at
# the end of the Makefile. Every knob defaults to 0 / off and then contributes nothing: the
# default image is byte-identical with or without this file.
#   PACE_CATCHUP=1   logic ticks at 29.97 Hz on the vblank clock (anchor + 2 vblanks per tick,
#                    so a slow frame is repaid by shorter waits). When the game is at least one
#                    tick behind, the next iteration runs its whole logic tick (TaskScheduler,
#                    Trans(), every OT callback, pad, sound, fades, messages) with the draw
#                    skipped: ModelRender returns at entry, the native frame is not begun (no UI
#                    quads, effect sprites or ID quads), nothing is presented (the previous
#                    picture stays). Never while a movie, the sub screen (inventory/map/radio/
#                    typewriter card) or a held picture (System_flg 0x400) owns the frame, nor
#                    outside in-room play (Rno0 3: title, picker, card, loads and doors run as
#                    today), nor when GetSystemVcnt() != 2.
#   PACE_CATCHUP=2   v2: also no ModelTrans (emTrans/objTrans) for a dropped image: the drop is
#                    decided before Trans() of tick k and iteration k+1 then skips as above.
#   PACE_CAP=N       consecutive skipped iterations at most (default 1 = 2 ticks per drawn
#                    frame). PACE_CAP=0 keeps the anchor clock without any skip (reference arm).
#                    PACE_CAP=2 (crowd lane 2026-10-04): up to 3 ticks per drawn frame. Only Fast takes the
#                    second skip (Smooth's 15 fps floor blocks it), and only while the game is still >= 1 tick
#                    behind after one skip (drawn + skipped tick > 66.7 ms). Logic STRICT (PACE_FORCE=T trace vs
#                    the unpaced control: r101 square 4951 ticks).
#   PACE_CAP2_SPEED=N (default 0 = no gate; with PACE_CAP >= 2): the second consecutive skip only while one
#                    skip per drawn image would leave the game below N% speed (draw_ema + skip_ema > 66.7 ms
#                    x 100 / N), so a scene slightly over budget keeps CAP 1's frame rate (house: 97% at
#                    14.5 fps instead of 100% at 13.5 fps with N=90).
#   Runtime mode (pace.cpp re4dc_pace_mode, read every iteration, safe to change at any moment;
#                    it only changes which ticks draw): Smooth (the floor below; the default) /
#                    Fast (no floor, catch-up up to the cap) / Off (no pacing: today's loop).
#                    QUALITY=1 builds keep it in RE4DCCFG features bits 16-17 (mode + 1,
#                    re4dc_quality_pace / re4dc_quality_set_pace); quality.txt pace=1|2|3 sets it.
#                    (The in-game Options row that changes it is a later item.)
#   PACE_FLOOR_FPS=N Smooth's floor: a skip is taken only while the gap between two presents
#                    stays at or under 1/N s (default 15). Load beyond it degrades to slow motion
#                    instead of dropping more frames. 0 makes Fast the default (Smooth: 15).
#   PACE_MODE=smooth|fast|off  the build's default mode (before RE4DCCFG / quality.txt / menu).
#   PACE_DEBUG=1     (default: QUALITY_DEBUG) in game, a START press that begins with R held (L not held)
#                    cycles Smooth -> Fast -> Off with a 2 s on-screen note; the game never sees
#                    that START (pad.cpp, like the L+START debug chord).
#   PACE_LOG=N      one "PACE" telemetry line every N ticks (default 300 = 10 s).
#   PACE_VMU=1      (default 0) a speed page on the first VMU LCD, rewritten once a second: drawn fps,
#                    game speed (% of 30 ticks/s) and CPU load (work per tick before the vblank wait, % of a
#                    33.4 ms tick; >100 = saturated). One
#                    queued maple LCD write a second (vmu_draw_lcd does not wait); reads pace state only.
#   SPEED_VMU_OFF=1 (default 0; RENDER_OPTION builds, issue #29, user 2026-10-14) the speed display never writes the
#                    VMU: R + START cycles Off -> Screen -> Off (two boxes in the note), a stored VMU or Both setting
#                    shows on screen, and the VMU keeps showing what it shows when the display is off (VMU_CONTEXT:
#                    the context pages). The one-second window, its log lines and the on-screen counter are unchanged.
#                    SPEED_VMU_OFF=2 (user 2026-10-14, "off unless toggled on"): as 1, but a stored VMU setting reads
#                    as Off (only a stored Screen or Both shows on screen); the stored record is not rewritten. A fresh
#                    boot (no RE4DCCFG) is Off with 0, 1 and 2.
#   PACE_VMU_GPU=1  (default 0; test builds, needs PACE_VMU=1) a fourth line "GPU <mean>/<max>" on the speed page
#                    (FPS / SPD / CPU / GPU / MODE: the 4x6 font fits five lines): the graphics chip's render time
#                    per scene in ms (rounded), mean and max over the renders that completed in the same window
#                    ("GPU -" if none). The interval is KOS's rnd_last_time: from the render start (KOS writes
#                    ISP_START, then stamps PVR_SYNC_RNDSTART) to the TSP render-done interrupt (PVR_SYNC_RNDDONE).
#                    KOS starts a render only after its lists are in, the previous render is done and the previous
#                    picture was flipped or discarded, so a render's wait for the previous one is NOT included; the
#                    render-done interrupt latency is. Every render counts once: pvr_sync_stats is wrapped at link
#                    time (-Wl,--wrap=pvr_sync_stats, this knob only; KOS's own statistics run unchanged first) and
#                    pace.cpp stamps the same events (integers, interrupt context). Also logs "PACE vmu ..." per
#                    window: renders, mean/max us, PVR busy %, the queue wait of a finished scene (last list in ->
#                    its render start: ~0 while the CPU is the bottleneck) and KOS's reg interval (pvr_scene_begin ->
#                    last list in: mostly CPU submission time in this pipeline, so it stays off the LCD). Render-side
#                    observation only: logic untouched.
# Test instrumentation (never in a product image):
#   PACE_FORCE=3|N|R|A|T  forced skip pattern, a pure function of the eligible-tick index (timing,
#                    cap and floor ignored): every Nth image (3 = every 3rd), R = p 0.5 from a
#                    platform xorshift seeded by PACE_SEED (never the game RNG), A = every image,
#                    T = two of every three (one drawn, two skipped: PACE_CAP=2's saturated pattern).
#                    iTaskScheduler runs on every iteration. For the forced-skip STRICT gate.
#   PACE_SEED=N      xorshift seed for PACE_FORCE=R (default 1).
#   PACE_TEST_DRAW_US=N  busy-wait N us on drawn iterations only (the skippable half).
#   PACE_TEST_TICK_US=N  busy-wait N us on every iteration (the per-tick half).
#   PACE_TEST_TOGGLE_S=N  cycle the mode every N s (the STRICT mode-toggle gate).
#   PACE_CHECK=2     (PACE_CATCHUP=2 + LOGIC_TRACE=1) a dropped image still runs ModelTrans,
#                    between two hashes of every logic-trace field; "pacechk=<n>/<fail>".
# Build every arm in its own OBJDIR; pace.h is regenerated when a value changes.
PACE_CATCHUP ?= 0
PACE_CAP ?= 1
PACE_CAP2_SPEED ?= 0
PACE_FLOOR_FPS ?= 15
PACE_LOG ?= 300
PACE_FORCE ?= 0
PACE_SEED ?= 1
PACE_TEST_DRAW_US ?= 0
PACE_TEST_TICK_US ?= 0
PACE_CHECK ?= 0
PACE_TEST_TOGGLE_S ?= 0
PACE_VMU ?= 0
PACE_VMU_GPU ?= 0
SPEED_VMU_OFF ?= 0
PACE_DEBUG ?= $(or $(QUALITY_DEBUG),0)
PACE_MODE ?= $(if $(filter 0,$(PACE_FLOOR_FPS)),fast,smooth)
ifneq ($(PACE_CATCHUP),0)
PACE_MODE_NUM = $(if $(filter steady,$(PACE_MODE)),$(if $(filter 0,$(PACE_STEADY)),$(error PACE_MODE=steady needs PACE_STEADY=1),3),$(if $(filter off,$(PACE_MODE)),2,$(if $(filter fast,$(PACE_MODE)),1,$(if $(filter smooth,$(PACE_MODE)),0,$(error PACE_MODE=smooth|fast|off|steady)))))
PACE_FORCE_NUM = $(if $(filter R,$(PACE_FORCE)),-1,$(if $(filter T,$(PACE_FORCE)),-2,$(if $(filter A,$(PACE_FORCE)),1,$(PACE_FORCE))))
ifneq ($(PACE_CAP2_SPEED),0)
ifneq ($(filter 0 1,$(PACE_CAP)),)
$(error PACE_CAP2_SPEED gates the second consecutive skip (PACE_CAP >= 2))
endif
endif
ifneq ($(PACE_VMU_GPU),0)
ifneq ($(PACE_VMU),1)
$(error PACE_VMU_GPU=1 adds the GPU line to the PACE_VMU speed page and needs PACE_VMU=1)
endif
# pace.cpp __wrap_pvr_sync_stats: KOS's PVR statistics hook, its render start / render done stamped for every render.
GAME_LDFLAGS += -Wl,--wrap=pvr_sync_stats
endif
ifneq ($(SPEED_VMU_OFF),0)
ifneq ($(RENDER_OPTION),1)
$(error SPEED_VMU_OFF=1 changes the RENDER_OPTION speed display and needs RENDER_OPTION=1)
endif
endif
ifneq ($(PACE_CHECK),0)
ifneq ($(LOGIC_TRACE),1)
$(error PACE_CHECK=2 hashes the logic-trace fields and needs LOGIC_TRACE=1)
endif
ifneq ($(LOGIC_TRACE_MASK_RENDER),1)
$(error PACE_CHECK=2 needs LOGIC_TRACE_MASK_RENDER=1 (be_flag 0x08000000 is the draw marker))
endif
endif
.PHONY: pace-force
$(OBJDIR)/pace.h: pace-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_PACE_CATCHUP %s\n#define RE4DC_PACE_CAP %s\n#define RE4DC_PACE_FLOOR_FPS %s\n#define RE4DC_PACE_LOG %s\n#define RE4DC_PACE_FORCE %s\n#define RE4DC_PACE_SEED %s\n#define RE4DC_PACE_TEST_DRAW_US %s\n#define RE4DC_PACE_TEST_TICK_US %s\n#define RE4DC_PACE_CHECK %s\n#define RE4DC_PACE_TEST_TOGGLE_S %s\n#define RE4DC_PACE_DEBUG %s\n#define RE4DC_PACE_MODE %s\n#define RE4DC_PACE_VMU %s\n#define RE4DC_PACE_CAP2_SPEED %s\n#define RE4DC_PACE_VMU_GPU %s\n#define RE4DC_SPEED_VMU_OFF %s\n' '$(PACE_CATCHUP)' '$(PACE_CAP)' '$(PACE_FLOOR_FPS)' '$(PACE_LOG)' '$(PACE_FORCE_NUM)' '$(PACE_SEED)' '$(PACE_TEST_DRAW_US)' '$(PACE_TEST_TICK_US)' '$(PACE_CHECK)' '$(PACE_TEST_TOGGLE_S)' '$(PACE_DEBUG)' '$(PACE_MODE_NUM)' '$(PACE_VMU)' '$(PACE_CAP2_SPEED)' '$(PACE_VMU_GPU)' '$(SPEED_VMU_OFF)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
PLATFORM_OBJS += $(OBJDIR)/pace.o
$(TARGET): $(OBJDIR)/pace.o
PACE_GAME = $(OBJDIR)/src/game/main.o $(OBJDIR)/src/game/main_sub.o $(OBJDIR)/src/game/trans.o
# RE4DCCFG bits, quality.txt pace= (QUALITY=1) and the test-build chord.
PACE_GAME += $(OBJDIR)/quality_picker.o
PACE_PLATFORM = $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/pad.o $(OBJDIR)/platform/quality.o
$(PACE_GAME) $(PACE_PLATFORM) $(OBJDIR)/pace.o: $(OBJDIR)/pace.h
$(PACE_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/pace.h
$(PACE_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/pace.h
ifneq ($(PACE_CHECK),0)
$(OBJDIR)/logic_trace.o: $(OBJDIR)/pace.h
$(OBJDIR)/logic_trace.o: GAME_CPPFLAGS += -include $(OBJDIR)/pace.h
endif
$(OBJDIR)/pace.o: pace.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -include $(OBJDIR)/pace.h -MMD -MP -c $< -o $@
-include $(OBJDIR)/pace.d
endif

# METER_ROWS=1 (T12 Meter disc, 2026-10-15; display / log only, default 0 = image unchanged; needs PACE_VMU_GPU=1): the VMU
# speed page's last row shows the pacing mode and the render mode (STD / FSAA), and a "PACE meter:" log line follows each
# "PACE vmu" line with the render mode and the PVR stats (TA vertex buffer last / peak, frame / registration / render ms).
METER_ROWS ?= 0
ifneq ($(filter $(METER_ROWS),0 1),$(METER_ROWS))
$(error METER_ROWS must be 0 or 1)
endif
ifeq ($(METER_ROWS),1)
ifneq ($(PACE_VMU_GPU),1)
$(error METER_ROWS=1 needs PACE_VMU_GPU=1)
endif
$(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_METER_ROWS=1
endif

# PHASE_METER=1 (T12 Phases disc, 2026-10-15; display / log only, default 0 = image unchanged; needs GAME_TICK_LOG=N,
# PACE_VMU_GPU=1, RENDER_OPTION=1, RENDER_FSAA=1): next to the on-screen speed counter a column of 0.1 ms values (GPU render, render
# mode, logic, effects move, effects trans, objects trans, other trans, post, draw remain, vblank wait, total) from the
# game's ProcessTickGet stamps (tick_log.cpp window), and a "PHASES:" log line per window. Legend: native_ui.cpp.
PHASE_METER ?= 0
ifneq ($(filter $(PHASE_METER),0 1),$(PHASE_METER))
$(error PHASE_METER must be 0 or 1)
endif
ifeq ($(PHASE_METER),1)
ifeq ($(GAME_TICK_LOG),0)
$(error PHASE_METER=1 needs GAME_TICK_LOG=N)
endif
ifneq ($(PACE_VMU_GPU),1)
$(error PHASE_METER=1 needs PACE_VMU_GPU=1)
endif
$(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_PHASE_METER=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PHASE_METER=1
endif

# PMC_ROW=1 (T12 Phases disc, 2026-10-15; display / log only, default 0; needs PHASE_METER=1): one more row under the phase
# column from the SH-4 performance counter 2 (KOS keeps counter 1 for its ns timer). One event per one-second window,
# in turn: 0x25 pipeline freeze by D-cache miss, 0x24 freeze by I-cache miss (cycles, shown in 0.1 ms per drawn
# frame), 0x04 operand-cache read misses, 0x05 operand-cache write misses, 0x08 instruction-cache misses (shown in
# 0.1 k per drawn frame). The event code is drawn left of the value (25, 24, 4, 5, 8). A whole window per event
# (not a per-tick rotation), so draw / skip ticks cannot alias with the event (10-04 hwcal trap). "PMC:" log line.
PMC_ROW ?= 0
ifneq ($(filter $(PMC_ROW),0 1),$(PMC_ROW))
$(error PMC_ROW must be 0 or 1)
endif
ifeq ($(PMC_ROW),1)
ifneq ($(PHASE_METER),1)
$(error PMC_ROW=1 needs PHASE_METER=1)
endif
$(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_PMC_ROW=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PMC_ROW=1
endif
# DISC_READ_METER (Makefile, next to DVD_READ_SAFE) draws in the PHASE_METER column.
ifeq ($(DISC_READ_METER),1)
ifneq ($(PHASE_METER),1)
$(error DISC_READ_METER=1 needs PHASE_METER=1)
endif
endif

# Lane pace20 (2026-10-20, user-approved "Steady" pacing choice; default 0 = image unchanged):
#   PACE_STEADY=1   a fourth Frame pacing value, "Steady" (Options row, RE4DCCFG, quality.txt pace=4, the test chord): each
#                   picture is held a constant number of TV fields (2, 3 or 4) chosen from recent work with hysteresis;
#                   the drawn/dropped pattern follows the hold (3: every third image dropped, 4: every other), the flip
#                   is deferred to its target field (pace_present.cpp). The 29.97 Hz logic clock, PACE_CAP and the
#                   pending-drop rule are unchanged; a hold is only taken while its work fits, so it is never slower
#                   than Fast. Stored as RQ_PACE_STEADY_BIT + Fast (a build without Steady reads Fast).
#   PACE_PRECISE=1  the v2 drop prediction on the microsecond timer (vblank time stamps) instead of whole retrace counts,
#                   every mode.
#   PACE_HOLD_LOG=1 (bench builds) a "PACE hold" histogram per PACE_LOG window: fields each picture was shown
#                   (flip to flip), scene finish -> flip latency, Steady releases; =2 adds a "PACE pic" line per picture
#                   (scene finish field, target, flip, paced tick count, latency).
PACE_STEADY ?= 0
PACE_PRECISE ?= 0
PACE_HOLD_LOG ?= 0
ifneq ($(PACE_STEADY)$(PACE_HOLD_LOG),00)
ifneq ($(PACE_CATCHUP),2)
$(error PACE_STEADY / PACE_HOLD_LOG need PACE_CATCHUP=2)
endif
ifneq ($(PVR_PIPELINE),2)
$(error PACE_STEADY / PACE_HOLD_LOG need PVR_PIPELINE=2)
endif
PLATFORM_OBJS += $(OBJDIR)/pace_present.o
$(TARGET): $(OBJDIR)/pace_present.o
$(OBJDIR)/pace_present.o: pace_present.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -DRE4DC_PACE_STEADY=$(PACE_STEADY) -DRE4DC_PACE_HOLD_LOG=$(PACE_HOLD_LOG) -MMD -MP -c $< -o $@
-include $(OBJDIR)/pace_present.d
$(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_PACE_STEADY=$(PACE_STEADY) -DRE4DC_PACE_HOLD_LOG=$(PACE_HOLD_LOG)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PACE_STEADY=$(PACE_STEADY) -DRE4DC_PACE_HOLD_LOG=$(PACE_HOLD_LOG)
endif
ifneq ($(PACE_STEADY),0)
$(OBJDIR)/platform/quality.o: PLATFORM_CPPFLAGS += -DRE4DC_PACE_STEADY=1
$(OBJDIR)/option_rows.o: GAME_CPPFLAGS += -DRE4DC_PACE_STEADY=1
endif
ifneq ($(PACE_PRECISE),0)
ifeq ($(PACE_CATCHUP),0)
$(error PACE_PRECISE needs PACE_CATCHUP)
endif
$(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_PACE_PRECISE=1
endif

# PACE_COST_LOG: bounded diagnostic drawn/skipped work sums per VMU window.
# No decision/pacing change. Default0 has no macro, counters, strings or code.
PACE_COST_LOG ?= 0
ifneq ($(words $(PACE_COST_LOG)),1)
$(error PACE_COST_LOG must be exactly 0 or 1)
endif
ifneq ($(filter $(PACE_COST_LOG),0 1),$(PACE_COST_LOG))
$(error PACE_COST_LOG must be exactly 0 or 1)
endif
ifeq ($(PACE_COST_LOG),1)
ifneq ($(PACE_VMU),1)
$(error PACE_COST_LOG=1 needs PACE_VMU=1)
endif
$(OBJDIR)/pace.o: GAME_CPPFLAGS += -DRE4DC_PACE_COST_LOG=1
endif
