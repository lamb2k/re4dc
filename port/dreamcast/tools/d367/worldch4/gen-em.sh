#!/bin/bash
# gen-em.sh <work> <Disc 1 release tree>   (WSL; lane world-ch4 2026-11-02; castlegca26/gen-em.sh for chapter 4)
#   models  ps2cast/ps2_ganado_bins.py on W4_CEM (castle content em/emNN.drs): every GameCube BIN member with a PS2 BIN
#           at the same ARC rebuilt with the PS2 geometry; --cast-tree = Disc 1 dc/native + castle dc/native
#   motion  motion/ps2_motion_prepared.py rewrite + verify on the enemy archives and the chapter 4 room archives
# An enemy without PS2 inputs (no emNN.dat in $EMIN) is reported and skipped (stays as the castle content copy).
set -euo pipefail
WK=${1:?work}; D1=${2:?Disc 1 tree}
H=$(cd "$(dirname "$0")" && pwd); D=$(cd "$H/.." && pwd)
source "$H/env.sh"
I=${EMIN:-$WK/emin}   # GC disc emNN.drs + PS2 AFS emNN.dat for every W4_CEM enemy (emin.py)
python3 "$H/emin.py" "$I" $W4_CEM > /dev/null
ISO=${PS2_ISO:-/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso}
rm -rf "${WK:?}/em" "${WK:?}/m" "${WK:?}/cast"; mkdir -p "$WK/cast/dc" "$WK/em" "$WK/m" "$WK/reports"
# --remove-destination: the castle copies replace the hard links instead of writing through them into the Disc 1 tree
cp -al "$D1/dc/native" "$WK/cast/dc/native" 2>/dev/null || { rm -rf "${WK:?}/cast/dc/native"; cp -a "$D1/dc/native" "$WK/cast/dc/native"; }; cp -a --remove-destination "$CT/dc/native/." "$WK/cast/dc/native/"
OK=""
for e in $W4_CEM; do
  if [ ! -f "$I/$e.dat" ] || [ ! -f "$I/$e.drs" ]; then echo "$e SKIP (no PS2 input in $I)"; continue; fi
  if python3 "$D/ps2cast/ps2_ganado_bins.py" build --release "$CT/em/$e.drs" --gc "$I/$e.drs" --ps2 "$I/$e.dat" --cast-tree "$WK/cast" \
    --out "$WK/em/$e.drs" --json "$WK/reports/$e-bins.json" > "$WK/reports/$e-bins.log" 2>&1; then
    echo "$e $(grep TOTAL "$WK/reports/$e-bins.log")"; OK="$OK $e"
  else echo "$e BINS FAILED: $(tail -2 "$WK/reports/$e-bins.log" | tr '\n' ' ')"; fi
done
echo "$OK" > "$WK/em-ok.txt"
M=$D/motion/ps2_motion_prepared.py
mot() {  # mot <name> <input> <dat> [mot dir]
  if ! python3 "$M" rewrite "$2" "$ISO" "$3" "$WK/m/$1" ${4:+--mot-dir "$4"} > "$WK/reports/mot-$1.log" 2>&1; then
    # the PS2 motion rewrite failed (r229: a PS2 FCV shorter than its header): the archive keeps its motion (reported)
    rm -rf "${WK:?}/m/$1"; mkdir -p "$WK/m/$1/em"; cp "$2" "$WK/m/$1/em/"; echo "MOTION KEPT (rewrite failed: $(tail -1 "$WK/reports/mot-$1.log"))"; return 0
  fi
  tail -1 "$WK/reports/mot-$1.log"
  local o; o=$(ls "$WK/m/$1/em/"*)
  python3 "$M" verify "$o" "$2" "$ISO" "$3" "$WK/m/$1/dc/mot" ${4:+"$4"} | tail -1
}
for e in $OK; do echo "mot $e: $(mot $e "$WK/em/$e.drs" $e.dat "$CT/dc/mot" 2>&1 | tr '\n' ' ')"; done
for r in $W4_ROOMS; do echo "mot $r: $(mot $r "$WK/obj/$r/x/$r.dar" $r.dat 2>&1 | tr '\n' ' ')"; done
