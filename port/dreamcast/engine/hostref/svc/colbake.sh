#!/bin/bash
# colbake.sh (lane eng-skel2): the bake step of the room collision (services/collision/col.h, the baked form; the
# integrator's ruling of 2026-11-21, option 2). Run it in WSL.
#
#   colbake.sh <tree> <out dir> [stN/rNNN ...]     (default: every st1 room archive in <tree>)
#   colbake.sh --verify <tree> <out dir>           (the receipt against the inputs and the outputs: exit 0 when it holds)
#
# <tree>: the little-endian game tree the console disc is staged from (build_console_disc.sh's PRISTINE). Each room
# archive is written to <out dir>/stN/rNNN.arc with every file of its SAT and EAT tables in the baked form (the engine's
# own bake, col.cpp bake(), run by the native PC build: svc/colb_host.cpp RE4_COLB_BAKE), the normal table inside each
# file, every other entry's bytes as they were. <out dir>/COLB-RECEIPT.txt: the SHA-256 of every input (the archives,
# this script, colb_host.cpp, colb_verify.py, col.cpp, col.h, col_model.cpp, the native re4ref binary) and of every
# output. svc/colb_verify.py then checks each output against its input: every entry but SAT and EAT the same bytes,
# each baked file's header and normal table the original's, its tables' hash the one the bake printed.
# Private game data: the outputs are never committed.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
ROOT=$(git -C "$here" rev-parse --show-toplevel)
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
BIN=$B/native/re4ref
FX=$ROOT/port/dreamcast/tools/plays_right/fixtures/e1-route.txt
ENG=$ROOT/port/dreamcast/engine
inputs() {   # the script, tools and sources the bake depends on
  echo "$here/colbake.sh" "$here/colb_host.cpp" "$here/colb_verify.py" "$ENG/services/collision/col.cpp" \
       "$ENG/services/collision/col.h" "$ENG/services/collision/col_model.cpp" "$BIN"
}
if [ "${1:-}" = "--verify" ]; then
  exec python3 "$here/colb_verify.py" "$2" "$3" $(inputs)
fi
TREE=$1; OUT=$2; shift 2
ROOMS=("$@")
if [ ${#ROOMS[@]} -eq 0 ]; then
  for f in "$TREE"/st1/r*.arc; do b=$(basename "$f" .arc); ROOMS+=("st1/$b"); done
fi
[ -x "$BIN" ] || { echo "colbake: build the native reference first (make native)"; exit 2; }
mkdir -p "$OUT"
for r in "${ROOMS[@]}"; do mkdir -p "$OUT/$(dirname "$r")"; done
RE4_COLB_BAKE="$OUT" RE4_COLB_ROOMS="${ROOMS[*]}" RE4_TREE="$TREE" \
  "$BIN" --tree "$TREE" --fixture "$FX" --out /dev/null --log /dev/null > "$OUT/COLB-LOG.txt"
{
  echo "# colbake.sh receipt (lane eng-skel2): inputs, then outputs; sha256"
  echo "tree $TREE"
  for r in "${ROOMS[@]}"; do echo "in $(sha256sum "$TREE/$r.arc" | cut -c1-64) $r.arc"; done
  for f in $(inputs); do echo "tool $(sha256sum "$f" | cut -c1-64) ${f#$ROOT/}"; done
  for r in "${ROOMS[@]}"; do echo "out $(sha256sum "$OUT/$r.arc" | cut -c1-64) $r.arc"; done
} > "$OUT/COLB-RECEIPT.txt"
python3 "$here/colb_verify.py" "$TREE" "$OUT" $(inputs)
