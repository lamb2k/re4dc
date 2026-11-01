#!/bin/bash
# gen26.sh (lane props-ps2-26 2026-10-26): the ch1/ch2 room objects that shipped as PS2 meshes LARGER than the GC model
# (--keep-larger, objs13 / props24) reconverted with the converter's reduction step (ps2_objects.py LOD: mesh_lod with
# the UV guard, strips, self-check), as GRAFT member sets on the composed archives (never whole .dar).
#   gen26.sh <fixture pkg.json (t11-fix output: the composed archives)> <out store dir>
# Plan: props_inventory.py rows source=PS2 with out_tris > gc_tris (plan26.txt: room, ETM names, room BIN pairs).
set -euo pipefail
FIX=${1:?fixture json}; OUT=${2:?out dir}
H=$(cd "$(dirname "$0")" && pwd); T=$(cd "$H/../.." && pwd)
mkdir -p "$OUT/st1" "$OUT/reports"
while read -r room etm pairs; do
  [ -z "$room" ] && continue
  case "$room" in \#*) continue;; esac
  src=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['replace']['st1/%s.dar' % sys.argv[2]])" "$FIX" "$room")
  a=(room --dar "$src" --room "$room" --uv-fold --out "$OUT/st1/$room.dar" --json "$OUT/reports/$room.json" --graft-json "$OUT/reports/$room.graft.json")
  [ "$etm" != "-" ] && a+=(--etm "$etm" --reconvert-etm "$etm")
  if [ "$pairs" != "-" ]; then a+=(--pairs "$pairs" --reconvert "$(echo "$pairs" | sed 's/:[0-9a-f]*//g')"); fi
  echo "== $room"
  ( cd "$T" && python3 ps2_objects.py "${a[@]}" )
done < "$H/plan26.txt"
