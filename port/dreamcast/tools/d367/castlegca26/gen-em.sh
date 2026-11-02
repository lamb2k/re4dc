#!/bin/bash
# gen-em.sh <work> <Disc 1 release tree>   (WSL; lane castle-gca-26, 2026-11-01; gen-all.sh step 3)
#   models  ps2cast/ps2_ganado_bins.py on the castle Zealot / Garrador archives em19 em1a em1b em1c (castle content) and
#           em14 (Disc 1's copy; Disc 2 keeps it): every GameCube BIN member with a PS2 BIN at the same ARC (BIO4DAT
#           emNN.dat) rebuilt with the PS2 geometry; --cast-tree = the Disc 1 dc/native packages + the castle ones (BINs
#           the native cast acquires by exact bytes are kept) -> <work>/em/
#   motion  motion/ps2_motion_prepared.py rewrite + verify (every FCV / SEQ member = the PS2 entry of the same slot) of
#           em19 em1a em1b em1c (on the models output), em3b (Disc 1 copy) and the room archives <work>/obj/rNNN/x/rNNN.dar
#           -> <work>/m/<name>/{em,dc/mot}
# Inputs: GC + PS2 enemy files in $EMIN (default /root/probe/lanes/ps2cast/inputs: emNN.drs, emNN.dat), PS2 ISO.
set -euo pipefail
WK=${1:?work}; D1=${2:?Disc 1 tree}
H=$(cd "$(dirname "$0")" && pwd); D=$(cd "$H/.." && pwd)
CT=${D2_CASTLE_TREE:-/root/re4data/private/castle-d2-j-20261021}
I=${EMIN:-/root/probe/lanes/ps2cast/inputs}
ISO=${PS2_ISO:-/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso}
CEM="em19 em1a em1b em1c"
rm -rf "${WK:?}/em" "${WK:?}/m" "${WK:?}/cast"; mkdir -p "$WK/cast/dc" "$WK/em" "$WK/m" "$WK/reports"
cp -al "$D1/dc/native" "$WK/cast/dc/native"; cp -a "$CT/dc/native/." "$WK/cast/dc/native/"
src() { case "$1" in em14) echo "$D1/em/$1.drs";; *) echo "$CT/em/$1.drs";; esac; }
for e in $CEM em14; do
  python3 "$D/ps2cast/ps2_ganado_bins.py" build --release "$(src $e)" --gc "$I/$e.drs" --ps2 "$I/$e.dat" --cast-tree "$WK/cast" \
    --out "$WK/em/$e.drs" --json "$WK/reports/$e-bins.json" > "$WK/reports/$e-bins.log"
  echo "$e $(grep TOTAL "$WK/reports/$e-bins.log")"
done
M=$D/motion/ps2_motion_prepared.py
mot() {  # mot <name> <input> <dat> [mot dir]
  python3 "$M" rewrite "$2" "$ISO" "$3" "$WK/m/$1" ${4:+--mot-dir "$4"} | tail -1
  local o; o=$(ls "$WK/m/$1/em/"*)
  python3 "$M" verify "$o" "$2" "$ISO" "$3" "$WK/m/$1/dc/mot" ${4:+"$4"} | tail -1
}
for e in $CEM; do mot $e "$WK/em/$e.drs" $e.dat "$CT/dc/mot"; done
mot em3b "$D1/em/em3b.drs" em3b.dat "$D1/dc/mot"
for r in r201 r202 r204 r208; do mot $r "$WK/obj/$r/x/$r.dar" $r.dat; done
