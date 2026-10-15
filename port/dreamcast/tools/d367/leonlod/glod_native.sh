#!/bin/bash
# leonlod GANADO_LOD stage 2 (WSL): glod_rung.py's appearance dirs -> runtime/castmodel_runtime.h, exactly as
# tools/ps2_cast_native.sh steps 1-2 (host check with this tree's native_actor_fast.cpp, fastpath build_blob.py
# --look 8, verify_blob.py, patch_header.py). No texture step: a rung keeps today's atlas.
#   glod_native.sh <rung dir (WSL path)> [app ...]     (default: every <rung>/ganado-* dir)
set -euo pipefail
R=$(realpath "$1"); shift
T=$(cd "$(dirname "$0")/../../../../.." && pwd)
PRIV=${RE4_PRIVATE:-/mnt/c/Game Dev/Emulators/re4-assets-private}
F="$PRIV/character-prototype-20260925/tools/fastpath"
CT="$PRIV/cast-20260925/tools"
H=${PS2CAST_HOSTCHECK:-/root/probe/lanes/ps2cast/host-check}
mkdir -p "$H/host/dc"
[ -f "$H/host/dc/pvr.h" ] || cp /root/probe/d367-agents/actors30/test/host/dc/pvr.h "$H/host/dc/pvr.h"
TEST="$CT/test_cast_dynamic.cpp"
STAMP=$(cat "$T/port/dreamcast/game/platform/native_actor_fast.cpp" "$T/port/dreamcast/room/pvr_geometry.cpp" \
        "$T/port/dreamcast/room/source_lighting.cpp" "$TEST" | sha256sum | cut -c1-16)
if [ ! -x "$H/check-$STAMP" ]; then
  FLAGS=(-O1 -g -std=gnu++20 -DRE4DC_ACTOR_TEST -DRE4DC_D349_RENDERER_STACK=1 -DRE4DC_NATIVE_ACTOR_SKIN=1
         -DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1 -DRE4DC_ACTOR_LOD_BUDGET=0 -I"$H/host" -I"$T/port/dreamcast/game/platform/include"
         -I"$T/port/dreamcast/room")
  objs=()
  for s in game/platform/native_actor_fast.cpp room/pvr_geometry.cpp room/source_lighting.cpp; do
    g++ "${FLAGS[@]}" -c "$T/port/dreamcast/$s" -o "$H/$(basename "$s")-$STAMP.o"; objs+=("$H/$(basename "$s")-$STAMP.o")
  done
  g++ "${FLAGS[@]}" -I"$CT" "$TEST" "${objs[@]}" -o "$H/check-$STAMP"
fi
apps=("$@")
[ ${#apps[@]} -gt 0 ] || apps=($(cd "$R" && ls -d ganado-* ))
for a in "${apps[@]}"; do
  O="$R/$a"; N="$O/native"
  "$H/check-$STAMP" "$N" > "$N/host-check.txt" || { cat "$N/host-check.txt"; echo "$a host check FAILED"; exit 1; }
  rm -rf "$O/fitted" "$O/runtime"; mkdir -p "$O/fitted" "$O/runtime"
  python3 "$F/build_blob.py" "$N" "$O/fitted" --report "$O/fit-report.json" --look 8 > "$O/fit.log"
  python3 "$F/verify_blob.py" "$N" "$O/fitted" > "$O/verify.log"
  python3 "$F/patch_header.py" "$N/castmodel_native.h" "$O/fitted" "$O/runtime/castmodel_runtime.h" > "$O/header.log"
  echo "$a $(tail -1 "$N/host-check.txt" | cut -c1-120) | $(grep -c SAME "$O/verify.log") SAME / $(grep -c '^info' "$O/verify.log") infos | $(sha256sum "$O/runtime/castmodel_runtime.h" | cut -c1-16)"
done
