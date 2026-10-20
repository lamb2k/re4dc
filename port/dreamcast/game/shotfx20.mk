# Lane shotfx20 (2026-10-20): the cost of shooting Ganados (user console report on the Test 21 preview: "each shot tanks
# the frame rate"). MODELLED: a hit adds ~+4 hw ms for 2-3 s (blood burst sprites) and, the first time a part is drawn,
# one ~20 hw ms frame of run-time detail-level building. Each knob defaults to 0 = off (nothing is compiled).
#
# ACTOR_LOD_ENTRY=K (render only, exact triangles): for the first K frames of each room, parts drawn have their detail
#   levels built at once, with no per-frame budget (platform/native_actor_fast.cpp re4dc_actor_frame), so the builds
#   land in the room-entry window instead of a later gameplay frame. Built in place: no memory cost.
ACTOR_LOD_ENTRY ?= 0
ifneq ($(ACTOR_LOD_ENTRY),0)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_LOD_ENTRY=$(ACTOR_LOD_ENTRY)
endif
#
# ACTOR_LOD_PART_MAX=N (render only): a part over N triangles is never simplified at run time; it keeps full detail.
#   The fallback if building at room entry is not enough (native_actor_fast.cpp relod).
ACTOR_LOD_PART_MAX ?= 0
ifneq ($(ACTOR_LOD_PART_MAX),0)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_LOD_PART_MAX=$(ACTOR_LOD_PART_MAX)
endif
#
# ESP_HIT_THIN=N (2..8; render only, visible, logic STRICT): of the hit-burst particles an enemy, animal or object
#   spawns (ids 0x1A blood jitter, 0x00 spray, 0x10 drops), only those in every Nth pool slot are drawn (src/game/esp.cpp
#   re4dc_esp_hit_ghost). The others still live and make their Rnd() draws (the shared generator feeds the AI), but skip
#   drawing and the 0x1A camera jitter. Gore stays: every burst still shows.
ESP_HIT_THIN ?= 0
ifneq ($(ESP_HIT_THIN),0)
ifneq ($(filter $(ESP_HIT_THIN),2 3 4 5 6 7 8),$(ESP_HIT_THIN))
$(error ESP_HIT_THIN must be 0 or 2..8 (got $(ESP_HIT_THIN)))
endif
$(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/esp1a.o: GAME_CPPFLAGS += -DRE4DC_ESP_HIT_THIN=$(ESP_HIT_THIN)
endif
