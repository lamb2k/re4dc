#!/bin/bash
# gen-all.sh <Disc 2 tex.pak (WSL)> <Disc 1 release tree (WSL)> [tag]   (Git Bash on the Windows host; lane world-ch32 copy
# of castlegca26/gen-all.sh for chapter 3-2: sets cw32 + pmcw32; ROOMS / CEM / SNDEM / SPECS from env)
# Regenerates the Disc 2 data sets cgca26 + pmcgca26 (recipe.conf D2_DATA; user 11-01 "Convert in Test 26") from the
# castle content (D2_CASTLE_TREE) and the PS2 USA ISO, in one command:
#   1. step.sh itemlib   ps2_items.py convert (castle rooms' ITM items + EFF debris, PS2) into <work>/itemlib
#   2. per room          step.sh objects (ps2_objects.py ETM all + room BIN pairs [+ --etm-from], ps2_items.py pack), then
#                        Windows python ps2_objects_tex.py (PS2 pictures; <pak> = the Disc 2 tex.pak for material pairs)
#   3. ps2_items_tex.py  the item / debris picture packages (Windows python)
#   4. gen-em.sh         em19 em1a em1b em1c em14 PS2 BINs; PS2 motion for the em archives, em3b and the rooms
#   5. step.sh snd       ps2_audio.py banks (PS2 PCM in place) on the room archives + em19 / em1a; snd28_store.py rows
#   6. step.sh final     mkfinal.py -> /root/re4data/private/{cgca26,pmcgca26}-<tag>; seal (SHA256SUMS.txt)
# Room specs room|ETM|PAIRS|ETM-FROM or empty:NAMES (castle content GC BIN index : PS2 .dat index). et1400 (+ et14.eff):
# the torch etc model the PS2 deleted from every ETM (r201 r202, also r10c): emptied (ps2_objects.py --etm-empty), the
# PS2 draws the torch with its world and the room EFF fire (pfire26 / PS2_FIRE_SST).
set -euo pipefail
PAK=${1:?Disc 2 tex.pak}; D1=${2:?Disc 1 tree}; TAG=${3:-20261101}
SPECS=${SPECS:-"r205|all|-|- r209|all|20:20,22:22,24:24|- r20a|all|21:21|- r20b|all|1f:1f|-"}
export ROOMS=${ROOMS:-"r205 r209 r20a r20b"} CEM=${CEM:-"em2d em23 em18 em22"} SNDEM=${SNDEM:-"em2d em23 em22"}
export WSLENV=ROOMS/u:CEM/u:SNDEM/u:EMIN/u
CT=${D2_CASTLE_TREE:-/root/re4data/private/castle-d2-j-20261021}
WK=${WK:-/root/work/lanes/world-ch32-scratch/work}
TW=/root/work/lanes/world-ch32/port/dreamcast/tools
H=$TW/d367/worldch32
WS=//wsl.localhost/Ubuntu-24.04
GI="C:/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso"
PI="C:/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso"
W() { MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -u root -- bash "$@"; }
S1=/root/re4data/private/cw32-$TAG; S2=/root/re4data/private/pmcw32-$TAG
W "$H/step.sh" itemlib "$WK/itemlib" "$(echo $ROOMS | tr ' ' ,)"
for spec in $SPECS; do
  IFS='|' read -r r etm pairs from <<< "$spec"
  O=$WK/obj/$r
  W "$H/step.sh" objects "$r" "$etm" "$pairs" "$from" "$O" "$CT" "$WK/itemlib"
  (cd "$WS$TW" && MSYS_NO_PATHCONV=1 py ps2_objects_tex.py --room "$r" --dar "$WS$O/i/$r.dar" --report "$WS$O/$r.json" \
    --out "$WS$O/x/$r.dar" --texdir "$WS$O/x/tex" --json "$WS$O/x/tex.json" --pak "$WS$PAK" --gc-room "$WS$WK/obj/gcroom/$r.arc" \
    --gc-iso "$GI" --ps2-iso "$PI" > "$WS$O/x/tex.log" 2>&1) || { echo "$r: tex step failed"; tail -5 "$WS$O/x/tex.log"; exit 1; }
  echo "$r $(tail -1 "$WS$O/x/tex.log")"
done
(cd "$WS$TW" && MSYS_NO_PATHCONV=1 py ps2_items_tex.py "$WS$WK/itemlib" > "$WS$WK/itemlib/tex.log" 2>&1) || { tail -5 "$WS$WK/itemlib/tex.log"; exit 1; }
echo "items tex: $(tail -1 "$WS$WK/itemlib/tex.log")"
W "$H/gen-em.sh" "$WK" "$D1"
W "$H/step.sh" snd "$WK/snd" "$WK" "${BASECAT:-/root/work/lanes/castle-disc2-26/rrhome/work/1101-1407-1409ac5e/gca2/catalog/catalog.json}"
echo "$D1" > "$WS$WK/d1tree.txt"
W "$H/step.sh" clean "$S1" "$S2"
W "$H/step.sh" final "$S1" "$S2" "$WK"
W "$H/step.sh" seal "$S1" "$S2"
