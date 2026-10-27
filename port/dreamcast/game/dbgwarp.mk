# D367 test warp rig (tools/d367/README.md "Warp rig"). Included at the end of the Makefile.
#   DBG_WARP=1   test builds only: /cd/dc/warp.txt (tools/d367/warp.py) skips the title and starts in
#                a room with Leon placed and synthesized scenario flags (dbgwarp_bridge.cpp). Not
#                STRICT against continued play; never on a user disc. Default 0: the hooks compile
#                out and the default image is byte-identical.
DBG_WARP ?= 0
#   STALL_DIAG=1 test builds only (platform/vi.cpp): a 1 s vblank heartbeat with the frame loop's vsync
#                count, and a log-only stall report (interrupted PC/PR, the main thread's PC/PR and
#                stack return addresses, re4dc_threads_dump) once the frame loop has not finished an
#                iteration for 3 s. Default 0: compiled out, the default image is byte-identical.
STALL_DIAG ?= 0
.PHONY: dbgwarp-force
$(OBJDIR)/dbgwarp.h: dbgwarp-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_DBG_WARP %s\n#define RE4DC_STALL_DIAG %s\n' '$(DBG_WARP)' '$(STALL_DIAG)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/platform/vi.o: $(OBJDIR)/dbgwarp.h
$(OBJDIR)/platform/vi.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/dbgwarp.h
DBGWARP_GAME = $(OBJDIR)/src/game/title.o $(OBJDIR)/src/game/sce_com.o $(OBJDIR)/ui_bridge.o
$(DBGWARP_GAME): $(OBJDIR)/dbgwarp.h
$(DBGWARP_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/dbgwarp.h
# r108's bell task serves the rig's `bell108` requests (DBG_WARP=1 only; 0: the block compiles out)
$(OBJDIR)/mod/st1_1/src/st1/r108.o: $(OBJDIR)/dbgwarp.h
$(OBJDIR)/mod/st1_1/src/st1/r108.o: GAME_CPPFLAGS += -include $(OBJDIR)/dbgwarp.h
$(OBJDIR)/platform/pad.o: $(OBJDIR)/dbgwarp.h
$(OBJDIR)/platform/pad.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/dbgwarp.h
# Late activation (platform/include/warp_late.h, `late <mask> [tick] [room]`): same-binary A/B switches.
# With DBG_WARP=0 every hook is an #if block that compiles out (knob-off identity).
DBGWARP_LATE_GAME = $(OBJDIR)/pace.o $(OBJDIR)/act_cap.o $(OBJDIR)/coarse_actor.o
DBGWARP_LATE_PLATFORM = $(OBJDIR)/platform/quality.o $(OBJDIR)/platform/native_actor_fast.o
$(DBGWARP_LATE_GAME) $(DBGWARP_LATE_PLATFORM): $(OBJDIR)/dbgwarp.h
$(DBGWARP_LATE_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/dbgwarp.h
$(DBGWARP_LATE_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/dbgwarp.h
#   WARP_JUMP=1  test builds only, needs DBG_WARP=1 (diagnostic): `jump <room frame> <from> <to> x y z ang` lines change
#                room through the source's SceAtExecRoomJump (room lifetime proofs between rooms with no wired door).
#                Default 0: the directive compiles out and the DBG_WARP image is unchanged.
WARP_JUMP ?= 0
# Test only: after `kill` completes and its source event ends, `killnext id frame room kind repeat gap`
# changes only the damage rig's target. Default 0 leaves the existing DBG_WARP image unchanged.
WARP_KILL_PHASE ?= 0
ifneq ($(filter-out 0 1,$(WARP_KILL_PHASE)),)
$(error WARP_KILL_PHASE must be 0 or 1)
endif
ifeq ($(WARP_KILL_PHASE),1)
ifneq ($(DBG_WARP),1)
$(error WARP_KILL_PHASE needs DBG_WARP=1)
endif
endif
#   WARP_AFTER_RESET=1  test builds only, needs DBG_WARP=1 (lane resetmem): an `after_reset` warp.txt keeps the rig
#                passive until the first soft reset (main.cpp systemSoftReset), then warps from the title after it
#                (the s30 heap gate after load -> Game Reset -> New Game). Default 0: compiled out.
WARP_AFTER_RESET ?= 0
ifeq ($(WARP_AFTER_RESET),1)
ifneq ($(DBG_WARP),1)
$(error WARP_AFTER_RESET=1 needs DBG_WARP=1)
endif
$(OBJDIR)/src/game/main.o $(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_WARP_AFTER_RESET=1
endif
ifneq ($(filter-out 0 1,$(WARP_JUMP)),)
$(error WARP_JUMP must be 0 or 1)
endif
ifeq ($(WARP_JUMP),1)
ifneq ($(DBG_WARP),1)
$(error WARP_JUMP needs DBG_WARP=1)
endif
endif
ifeq ($(DBG_WARP),1)
PLATFORM_OBJS += $(OBJDIR)/dbgwarp_bridge.o
# castle31 no-warp chain: warp line `god` = Leon takes no damage (LifeDownSet2 player branch; a one-frame hit larger
# than his life would otherwise start the death routine before the per-frame refill). Warp builds only.
$(OBJDIR)/src/game/em_sub.o: GAME_CPPFLAGS += -DRE4DC_WARP_GOD_HOOK=1
$(OBJDIR)/src/game/pl_npc.o: GAME_CPPFLAGS += -DRE4DC_WARP_GOD_HOOK=1
# Included after the link rule: name the object as its prerequisite here.
$(TARGET): $(OBJDIR)/dbgwarp_bridge.o
$(OBJDIR)/dbgwarp_bridge.o: dbgwarp_bridge.cpp $(OBJDIR)/dbgwarp.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -Iplatform/include -include $(OBJDIR)/dbgwarp.h $(if $(filter 1,$(WARP_JUMP)),-DRE4DC_WARP_JUMP=1) $(if $(filter 1,$(WARP_KILL_PHASE)),-DRE4DC_WARP_KILL_PHASE=1) -MMD -MP -c $< -o $@
-include $(OBJDIR)/dbgwarp_bridge.d
endif
#   CODEC_READY_FIXTURE=1  test builds only, needs DBG_WARP=1 (deterministic external-ready contract): the codec
#                call's voice-stream ready poll (src/Sscrn/ss_term.cpp OpeMesMove) is released at the source tick
#                request + K of /cd/dc/codec_ready.txt ("K <n>"), only if the stream is actually ready there;
#                otherwise the run halts with a "codec ready: FAIL" ledger line (codec_ready_fixture.cpp). The
#                host test is tools/d367/codec_ready_gate_test.cpp. Default 0: compiled out, the image is unchanged.
CODEC_READY_FIXTURE ?= 0
ifneq ($(filter-out 0 1,$(CODEC_READY_FIXTURE)),)
$(error CODEC_READY_FIXTURE must be 0 or 1)
endif
ifeq ($(CODEC_READY_FIXTURE),1)
ifneq ($(DBG_WARP),1)
$(error CODEC_READY_FIXTURE needs DBG_WARP=1)
endif
PLATFORM_OBJS += $(OBJDIR)/codec_ready_fixture.o
$(TARGET): $(OBJDIR)/codec_ready_fixture.o
$(OBJDIR)/codec_ready_fixture.o: codec_ready_fixture.cpp codec_ready_gate.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -Iplatform/include -MMD -MP -c $< -o $@
-include $(OBJDIR)/codec_ready_fixture.d
$(OBJDIR)/mod/Sscrn/src/Sscrn/ss_term.o: GAME_CPPFLAGS += -DRE4DC_CODEC_READY_FIXTURE=1
endif
