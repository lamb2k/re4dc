# mendezfx.mk (lane fix-mendez-fx23, 2026-10-23; every knob default 0 = no effect, image unchanged).
# Issue #55 item 5 (Mendez fight, r11f barn: see-through layers, lighting switching on and off, freeze) and #41 (r200
# effect sprites skipped at the castle gate).
#
# LIGHT_CUT_LOG=1 (test only): logs each light-cut change of cLightMgr::update (cut, its environment: ambients, TEV
#   scale, filter, light count, every light of the cut) with Leon's position, the room's camera-area table once, and
#   every camera switch (area, attr, cut).
# LIGHT_CUT_HOLD=1 (render only, approximation; #55): when Leon leaves every camera area of the room (the shoulder camera
#   takes over, cam_ctrl.cpp areaHitCheck), keep the light cut of the last area instead of switching to cut 0. In r11f
#   cut 0 is the outdoor cut (TEV scale x4, the sun lights); its phase 2 ground area 7 is only 3,900 high and the loft
#   area 8 covers only the back half, so standing on the front loft or a crate lit the barn as outdoors until Leon
#   stepped back into an area (the "lighting switches on and off" of #55). The light set never feeds game logic.
#   Rooms: LIGHT_CUT_HOLD_ROOMS (hex room ids, default 11f).
# FX_QUEUE_LOG=1 (log only): every 120 frames the peak UI quads, effect sprites and frame-queue bytes of a frame.
LIGHT_CUT_LOG ?= 0
LIGHT_CUT_HOLD ?= 0
LIGHT_CUT_HOLD_ROOMS ?= 11f
FX_QUEUE_LOG ?= 0
ifeq ($(filter $(LIGHT_CUT_LOG),0 1),)
$(error LIGHT_CUT_LOG must be 0 or 1)
endif
ifeq ($(filter $(LIGHT_CUT_HOLD),0 1),)
$(error LIGHT_CUT_HOLD must be 0 or 1)
endif
ifeq ($(filter $(FX_QUEUE_LOG),0 1),)
$(error FX_QUEUE_LOG must be 0 or 1)
endif
ifeq ($(LIGHT_CUT_LOG),1)
GAME_CPPFLAGS += -DRE4DC_LIGHT_CUT_LOG=1
endif
ifeq ($(LIGHT_CUT_HOLD),1)
LIGHT_CUT_HOLD_LIST := $(shell echo '$(LIGHT_CUT_HOLD_ROOMS)' | tr ', ' '\n\n' | grep -E '^[0-9a-fA-F]{3}$$' | sed 's/^/0x/' | paste -sd, -)
ifeq ($(LIGHT_CUT_HOLD_LIST),)
$(error LIGHT_CUT_HOLD_ROOMS must list hex room ids, e.g. 11f)
endif
$(OBJDIR)/src/game/cam_ctrl.o: GAME_CPPFLAGS += -DRE4DC_LIGHT_CUT_HOLD=1 '-DRE4DC_LIGHT_CUT_HOLD_ROOMS=$(LIGHT_CUT_HOLD_LIST)'
endif
ifeq ($(FX_QUEUE_LOG),1)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FX_QUEUE_LOG=1
endif
# FX_QUEUE_MARGIN=<bytes> (render only; 0 = the 8,192 B of today): what an effect sprite leaves free in the frame queue
#   for the world's later see-through parts, on top of the UI reserve (max(8 KiB, UI quads)). Effect sprites are capped
#   at EFFECT_SPRITE_MAX (64) a frame; in the heavy frames (r113 kill rig, r200 truck) the queue refused sprites below
#   that cap (#41). A smaller margin admits them from the same memory; the cost is world parts refused instead
#   (WORLD_HOLE_FIX "dropped"), which the gate runs count.
# ESP_POOL_ROOM_MIN=<slots> (0 = off): the effect pool (cEsp, 336 B a slot, game heap) of the rooms in
#   ESP_POOL_ROOM_LIST (hex ids, default 11f) has at least this many slots (the GC cons value is 1,024). Sized from the
#   ESP_POOL_DIAG peak of the Mendez fight.
ESP_POOL_ROOM_MIN ?= 0
ESP_POOL_ROOM_LIST ?= 11f
ifneq ($(shell echo '$(ESP_POOL_ROOM_MIN)' | grep -Ex '[0-9]+'),$(ESP_POOL_ROOM_MIN))
$(error ESP_POOL_ROOM_MIN must be a slot count)
endif
ifneq ($(ESP_POOL_ROOM_MIN),0)
ESP_POOL_ROOM_IDS := $(shell echo '$(ESP_POOL_ROOM_LIST)' | tr ', ' '\n\n' | grep -E '^[0-9a-fA-F]{3}$$' | sed 's/^/0x/' | paste -sd, -)
ifeq ($(ESP_POOL_ROOM_IDS),)
$(error ESP_POOL_ROOM_LIST must list hex room ids, e.g. 11f)
endif
$(OBJDIR)/src/game/esp.o: GAME_CPPFLAGS += -DRE4DC_ESP_POOL_ROOM_MIN=$(ESP_POOL_ROOM_MIN) '-DRE4DC_ESP_POOL_ROOM_LIST=$(ESP_POOL_ROOM_IDS)'
endif
# FX_ROOM_SPILL_KB=<n> (render only; 0 = off): the frame queue's spill, asked for only when the 26 KiB frame_storage is
#   full, becomes an <n> KiB heap-4 room cell (native-static reserve rule, allocated on the room's first overflow, freed at
#   room leave) instead of the 8 KiB model-slab tail. Measured need (FRAME_QUEUE_DIAG): r200 truck 8 + 14.8 KiB (#41),
#   r113 kill rig 8 + 47 KiB of which the effect-sprite cap admits ~2 KiB more. 0 KOS bytes; heap 4 only in rooms that overflow.
FX_ROOM_SPILL_KB ?= 0
ifneq ($(shell echo '$(FX_ROOM_SPILL_KB)' | grep -Ex '[0-9]+'),$(FX_ROOM_SPILL_KB))
$(error FX_ROOM_SPILL_KB must be a KiB count)
endif
ifneq ($(FX_ROOM_SPILL_KB),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FX_ROOM_SPILL_KB=$(FX_ROOM_SPILL_KB)
endif
FX_QUEUE_MARGIN ?= 0
ifneq ($(shell echo '$(FX_QUEUE_MARGIN)' | grep -Ex '[0-9]+'),$(FX_QUEUE_MARGIN))
$(error FX_QUEUE_MARGIN must be a byte count)
endif
ifneq ($(FX_QUEUE_MARGIN),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FX_QUEUE_MARGIN=$(FX_QUEUE_MARGIN)U
endif
# FX_ROOM_SPILL_FORCE=1 (test only, needs FX_ROOM_SPILL_KB): allocate the spill cell at each room's first frame, the
#   earliest an overflow could ask for it (the heap-4 worst case for the room's movies and loads).
FX_ROOM_SPILL_FORCE ?= 0
ifeq ($(FX_ROOM_SPILL_FORCE),1)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_FX_ROOM_SPILL_FORCE=1
endif
