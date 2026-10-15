#!/bin/bash
# release31.sh <lane-root> <room> [<aica dar>]  (WSL; castle lane 2026-10-15)
# The route lane's r104..r107 method for a PS2-world castle room: under PS2_WORLD_ROOMS=2 the PS2 world draws the
# room and the GC scenery package is never opened, so the room archive's SMD BIN geometry only costs heap 4.
#   1. convert_room_bins.py --color prelit: the GC scenery package (release identity + open-failure fallback only);
#   2. room_smd.py release: every BIN keeps header, joints, box corners and part headers (module docstring);
#   3. room_smd.py check: everything else unchanged (NTR / ESQ rebased).
# Inputs: <lane>/compact31-v1c/<room>/<room>.arc (compact-room output), the GC source .das, and the room's AICA
# container when it has one (else the compact .dar). Outputs <lane>/rel31/pkg-<room>, <lane>/rel31/rel-<room>/st2.
set -euo pipefail
L=$1; R=$2; DAR=${3:-$L/compact31-v1c/$R/$R.dar}
SRC=${SRC:-/root/probe/codex-cx-fixtures-20261013/output/$R/ancillary/source/st2/$R.das}
here=$(cd "$(dirname "$0")/../../.." && pwd)   # port/dreamcast
O=$L/rel31; mkdir -p $O/pkg-$R $O/rel-$R/st2
python3 $here/tools/convert_room_bins.py $O/pkg-$R/MAINSCENARIO.re4mesh --owner 0xff --smd $SRC --lod --lod-min-gain 0.4 \
  --lod-max-levels 4 --lod-eps 24,48,96,192,384 --lod-share --class-auto --color prelit > $O/pkg-$R.log
for pair in "$L/compact31-v1c/$R/$R.arc:$O/rel-$R/st2/$R.arc" "$DAR:$O/rel-$R/st2/$R.dar"; do
  in=${pair%%:*}; out=${pair#*:}
  python3 $here/tools/room_smd.py release $in $O/pkg-$R/MAINSCENARIO.re4mesh.json $out
  python3 $here/tools/room_smd.py check $in $out > /dev/null
  echo "$R $(basename $out): $(stat -c %s $in) -> $(stat -c %s $out) $(sha256sum $out | cut -c1-16)"
done
