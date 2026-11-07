# D367 VMU saves (design-vmu/DESIGN.md). Included at the end of the Makefile. Every knob defaults
# to 0 and then contributes nothing: the default image is byte-identical (card.cpp keeps the
# no-card stub, lz_small.cpp / vmu_store.cpp compile empty).
#   VMU_SAVE=1          virtual memory card over the VMU (platform/card.cpp, vmu_store.cpp,
#                       lz_small.cpp): bh4_dataNN <-> RE4DCSnnA/B (LZ4-style, 16-36 blocks),
#                       bh4_system <-> RE4DCSYS. The game's card.cpp is unchanged; the game never
#                       formats (unformatted -> its "cannot be used" message); a VMU too full for a
#                       safe new-then-delete overwrite overwrites in place.
#   VMU_SLOT_EST=24     VMU blocks per save assumed by the free-space figure the game sees.
#   VMU_GCRAW=1         test backend (gate G1): the card is served read-only from GameCube-format
#                       images /cd/dc/gcsave/bh4_dataNN (tools/vmusave.py unpack).
#   CARD_FIXED_LATENCY=N  test: every async CARD op takes at least N polls (equal frames per arm).
#   VMU_DEBUG_SLOT=1    test builds: the RE4DCDBG debug slot (hold L+START 1 s in play; FILE 20 in
#                       the Load list; RAM diagnostic ring flushed with the next debug save).
VMU_SAVE ?= 0
VMU_SLOT_EST ?= 24
VMU_GCRAW ?= 0
CARD_FIXED_LATENCY ?= 0
VMU_DEBUG_SLOT ?= 0
# VMU_SAFE_IO=1 (#66): bounded VMU block IO (vmu_store.cpp), no VMU LCD packets during a card op, a damaged newest save
# falls back to the older copy. VMU_IO_FAULT=N test discs only: hold maple sends 700 ms before the Nth block write.
VMU_SAFE_IO ?= 0
VMU_IO_FAULT ?= 0
# SAVE_ROW_FIX=1 (#66 bug 4): the save screen's write animation reads its key count in Dreamcast byte order, so the
# saved row shows the new save count and time at once (was: the old ones until the screen was reopened).
SAVE_ROW_FIX ?= 0
ifneq ($(filter-out 0 1,$(SAVE_ROW_FIX)),)
$(error SAVE_ROW_FIX is 0 or 1)
endif
ifeq ($(SAVE_ROW_FIX),1)
$(OBJDIR)/src/game/card.o: GAME_CPPFLAGS += -DRE4DC_SAVE_ROW_FIX=1
endif
ifneq ($(VMU_GCRAW)$(VMU_DEBUG_SLOT),00)
ifneq ($(VMU_SAVE),1)
$(error VMU_GCRAW / VMU_DEBUG_SLOT need VMU_SAVE=1)
endif
endif
.PHONY: vmusave-force
$(OBJDIR)/vmusave.h: vmusave-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_VMU_SAVE %s\n#define RE4DC_VMU_SLOT_EST %s\n#define RE4DC_VMU_GCRAW %s\n#define RE4DC_CARD_FIXED_LATENCY %s\n#define RE4DC_VMU_DEBUG_SLOT %s\n#define RE4DC_VMU_SAFE_IO %s\n#define RE4DC_VMU_IO_FAULT %s\n' \
	  '$(VMU_SAVE)' '$(VMU_SLOT_EST)' '$(VMU_GCRAW)' '$(CARD_FIXED_LATENCY)' '$(VMU_DEBUG_SLOT)' '$(VMU_SAFE_IO)' '$(VMU_IO_FAULT)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
VMUSAVE_PLATFORM = $(OBJDIR)/platform/card.o $(OBJDIR)/platform/lz_small.o $(OBJDIR)/platform/vmu_store.o \
  $(OBJDIR)/platform/pad.o $(OBJDIR)/platform/fault.o $(OBJDIR)/platform/mem.o $(OBJDIR)/platform/os.o \
  $(OBJDIR)/platform/native_ui.o
ifeq ($(VMU_SAFE_IO),1)
GAME_LDFLAGS += -Wl,--wrap=vmu_block_write -Wl,--wrap=vmu_block_read
VMUSAVE_PLATFORM += $(OBJDIR)/platform/vmu_lcd.o
else ifneq ($(VMU_IO_FAULT),0)
GAME_LDFLAGS += -Wl,--wrap=vmu_block_write
endif
$(VMUSAVE_PLATFORM): $(OBJDIR)/vmusave.h
$(VMUSAVE_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/vmusave.h
$(OBJDIR)/ui_bridge.o: $(OBJDIR)/vmusave.h
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -include $(OBJDIR)/vmusave.h
ifeq ($(VMU_DEBUG_SLOT),1)
# rnd.cpp's read-only RNG accessor (re4dc_rnd_state, as LOGIC_TRACE builds have it) for the extras.
$(OBJDIR)/src/game/rnd.o: GAME_CPPFLAGS += -DRE4DC_LOGIC_TRACE=1
PLATFORM_OBJS += $(OBJDIR)/dbgslot_bridge.o
# Included after the link rule: name the object as its prerequisite here.
$(TARGET): $(OBJDIR)/dbgslot_bridge.o
$(OBJDIR)/dbgslot_bridge.o: dbgslot_bridge.cpp $(OBJDIR)/vmusave.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -Iplatform/include -include $(OBJDIR)/vmusave.h -MMD -MP -c $< -o $@
-include $(OBJDIR)/dbgslot_bridge.d
endif
