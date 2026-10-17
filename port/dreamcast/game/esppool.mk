# esppool.mk (lane cast16 2026-10-16; default off): the room effect-sprite pool (cEsp, 0x150 B a slot) sized by the
#   room cons value (ConsGetRoomValue(2): 1024 slots = 344,064 B of heap 4 in r11f). The GameCube sized it for its
#   own memory; the Dreamcast's heap 4 is the tight resource in the boss rooms (r11f: full PS2 Ashley + Mendez).
# ESP_POOL_DIAG=1 (test only): logs each room's pool size, its peak live sprites (ActiveEspNum high-water) and the
#   sprites refused because the pool was full ("esp pool:" lines, at the next room's pool allocation and at every
#   new 32-slot peak). Use it to price ESP_POOL_CAP: the cap must sit above the largest peak of every room it covers.
# ESP_POOL_CAP=<n> (0 = off): a room asks for at most n slots (min(cons, n)). A cap below a room's peak refuses
#   sprites (PullEsp hands back the dummy esp, as the source does on a full pool), so a cap ships only with the
#   peak survey and refusal count 0 (ESP_POOL_DIAG) on the gate runs.
ESP_POOL_DIAG ?= 0
ESP_POOL_CAP ?= 0
ifeq ($(filter $(ESP_POOL_DIAG),0 1),)
$(error ESP_POOL_DIAG must be 0 or 1)
endif
ifneq ($(shell echo '$(ESP_POOL_CAP)' | grep -Ex '[0-9]+'),$(ESP_POOL_CAP))
$(error ESP_POOL_CAP must be a slot count)
endif
ifeq ($(ESP_POOL_DIAG),1)
GAME_CPPFLAGS += -DRE4DC_ESP_POOL_DIAG=1
endif
ifneq ($(ESP_POOL_CAP),0)
GAME_CPPFLAGS += -DRE4DC_ESP_POOL_CAP=$(ESP_POOL_CAP)
endif
