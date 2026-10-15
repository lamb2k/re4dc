#!/bin/bash
# rel33.sh <room>: castle release31 method for a st3 room (compact-room output -> GC scenery release). WSL.
set -euo pipefail
R=$1; L=/root/probe/lanes-20261014/st3/rel33; C=$L/compact-$R
A=$(ls -d /root/probe/lanes-20261014/st3/fixtures/$R/ancillary-* | head -1)
SRC=$A/source/st3/$R.das
T=/root/probe/lanes-20261014/st3/tree/port/dreamcast/tools
O=$L; mkdir -p $O/pkg-$R $O/rel-$R/st3
python3 $T/convert_room_bins.py $O/pkg-$R/MAINSCENARIO.re4mesh --owner 0xff --smd $SRC --lod --lod-min-gain 0.4 \
  --lod-max-levels 4 --lod-eps 24,48,96,192,384 --lod-share --class-auto --color prelit > $O/pkg-$R.log
for pair in "$C/$R.arc:$O/rel-$R/st3/$R.arc" "$C/$R.dar:$O/rel-$R/st3/$R.dar"; do
  in=${pair%%:*}; out=${pair#*:}
  python3 $T/room_smd.py release $in $O/pkg-$R/MAINSCENARIO.re4mesh.json $out > $out.log
  python3 $T/room_smd.py check $in $out > /dev/null
  echo "$R $(basename $out): $(stat -c %s $in) -> $(stat -c %s $out) $(sha256sum $out | cut -c1-16)"
done
