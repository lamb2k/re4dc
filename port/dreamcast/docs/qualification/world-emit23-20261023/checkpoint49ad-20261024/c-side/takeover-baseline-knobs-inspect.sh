#!/usr/bin/env bash
set -euo pipefail
O=/root/probe/lanes/route/out-rra5e972erP/resolved-knobs.txt
rg '^(SCENERY_DEDUP|ACTOR_SETUP_LEAN|SCENERY_UV_SNAPSHOT|PS2_PVS|SCENERY_SELECT|SCENERY_REPLAY|SCENERY_SUBMIT|WORLD_METER)' "$O"