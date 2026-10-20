#!/bin/bash
# dcw_room.sh <in native root> <in r4tc root> <out root> <cell mm> <rooms...> (WSL, lane scenery19): DC world data set.
# Per room: dcworld_build.py (merged world-space cell meshes + R4TC carried over), ps2_strip_groups.py (r4sg for the new
# package), room_compile.py --world (GRID + OCCL bound to the new R4PW crc). Output <out>/<room>/{ps2-world.*,room.r4rc}.
set -euo pipefail
IN=${1:?}; TC=${2:?}; OUT=${3:?}; CELL=${4:?}; shift 4
HERE=$(cd "$(dirname "$0")" && pwd)
TOOLS=$(cd "$HERE/../.." && pwd)
ISO=${ISO:-/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso}
mkdir -p "$OUT/_w" "$OUT/_rc"
# placements kept on their source mesh besides the dynamic ids: sky rows (native_static.cpp ps2_sky_row) and
# STATIC_OBJ_BAKE's gated objects (model_bridge.cpp kTable)
keep_of() {
  case $1 in
    r100) echo 2,3,33,34,35,36,37,75 ;;
    r101) echo 0,1,2,209,210,211,212,213,214,215,216,217,218,219,220,221,222 ;;
    *) echo "" ;;
  esac
}
for R in "$@"; do
  W="$OUT/_w/$R"; mkdir -p "$W" "$OUT/$R"
  python3 "$HERE/dcworld_build.py" "$IN/$R" "$W" --cell "$CELL" --r4tc "$TC/$R/ps2-world.r4tc" --keep "$(keep_of $R)" > "$OUT/$R/dcworld.txt"
  python3 "$TOOLS/ps2_strip_groups.py" "$W/ps2-world.re4mesh" "$W/ps2-world.r4pw" "$OUT/$R/ps2-world.re4mesh" \
    "$OUT/$R/ps2-world.r4sg" --groups 4 > "$OUT/$R/sg.txt"
  cp "$W/ps2-world.r4pw" "$W/ps2-world.ids" "$OUT/$R/"
  [ ! -f "$W/ps2-world.r4tc" ] || cp "$W/ps2-world.r4tc" "$OUT/$R/"
done
# the room file reads the final package (the strip-group pass permutes vertex records)
for R in "$@"; do mkdir -p "$OUT/_rcw/$R"; cp "$OUT/$R"/ps2-world.{re4mesh,r4pw,ids} "$OUT/_rcw/$R/"; done
( cd "$TOOLS/enginebake" && python3 room_compile.py --iso "$ISO" --world "$OUT/_rcw" --out "$OUT/_rc" "$@" > "$OUT/_rc/compile.log" 2>&1 )
for R in "$@"; do cp "$OUT/_rc/$R/room.r4rc" "$OUT/$R/room.r4rc"; done
rm -rf "${OUT:?}/_w" "${OUT:?}/_rcw"
for R in "$@"; do echo "$R $(cat "$OUT/$R/dcworld.txt" | cut -c1-160)"; ls -l "$OUT/$R" | awk '{print "  ",$5,$9}'; done
