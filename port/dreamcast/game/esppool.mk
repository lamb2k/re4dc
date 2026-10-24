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

# Source failure-path fixes (2026-10-23), independently selectable and default off.
# ESP_POOL_RECYCLE retires a low-priority effect in the wrapped full-pool search,
# matching the forward search's destructor and active/owner accounting.
# R117_EFFECT_FAILURE_SAFE tolerates a missing puzzle beam: no beam wait or
# beam-field access; the light objects still rotate with the original timing.
# Neither option changes pool capacity, rendering caps, or successful free-slot
# allocation. See docs/D367_EFFECT_POOL_FAILURE_AUDIT_20261023.md.
ESP_POOL_RECYCLE ?= 0
R117_EFFECT_FAILURE_SAFE ?= 0
ifeq ($(filter $(ESP_POOL_RECYCLE),0 1),)
$(error ESP_POOL_RECYCLE must be 0 or 1)
endif
ifeq ($(filter $(R117_EFFECT_FAILURE_SAFE),0 1),)
$(error R117_EFFECT_FAILURE_SAFE must be 0 or 1)
endif
ifeq ($(ESP_POOL_RECYCLE),1)
GAME_CPPFLAGS += -DRE4DC_ESP_POOL_RECYCLE=1
endif
ifeq ($(R117_EFFECT_FAILURE_SAFE),1)
GAME_CPPFLAGS += -DRE4DC_R117_EFFECT_FAILURE_SAFE=1
endif
