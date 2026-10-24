#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/world-emit23-census
cat "$T/port/dreamcast/tools/d367/world_emit23/README.md"
rg -n -C3 'SCENERY_EMIT_CENSUS' "$T/port/dreamcast/game/scenery19.mk"