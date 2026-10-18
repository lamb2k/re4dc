# room.sh <room> <tools tree>: replay of the ch22w room.sh (10-13, recovered from the transcript DB) in lane ch2regen.
# Outputs under $L/rooms/<tag>/ ; tag = basename of the tools tree.
set -euo pipefail
R=${1:?room}; TT=${2:?tools tree}
L=/root/probe/lanes-20261017r/ch2regen
T=$TT/port/dreamcast/tools
W=$L/rooms/$(basename "$TT")
mkdir -p "$W/iso-src/st1" "$W/iso-src/st2"
cd "$W"
ST=st${R:1:1}
[ -e iso-src/$ST/$R.das ] || cp "$L/src/$ST/$R.das" iso-src/$ST/$R.das
rm -rf "${W:?}/mirror-$R" "${W:?}/tex-$R" "${W:?}/w-${R}c" "${W:?}/pkg-$R" "${W:?}/rel-$R"
python3 $T/le_mirror.py iso-src mirror-$R --native-rooms > mirror-$R.log 2>&1 || { tail mirror-$R.log; exit 1; }
echo $ST/$R.arc > $R-tex.manifest
python3 $T/prepare_native_ui.py iso-src $R-tex.manifest tex-$R > tex-$R.log 2>&1 || { tail tex-$R.log; exit 1; }
python3 $T/prepare_native_ui.py --compact-room iso-src/$ST/$R.das --compact-room-mips --textures tex-$R --output w-${R}c > w-$R.log 2>&1 || { tail w-$R.log; exit 1; }
mkdir -p pkg-$R
python3 $T/convert_room_bins.py pkg-$R/MAINSCENARIO.re4mesh --owner 0xff --smd iso-src/$ST/$R.das --lod --lod-min-gain 0.4 --lod-max-levels 4 --lod-eps 24,48,96,192,384 --lod-share --class-auto --color prelit > pkg-$R.log 2>&1 || { tail pkg-$R.log; exit 1; }
mkdir -p rel-$R/$ST
python3 $T/room_smd.py release w-${R}c/$R.arc pkg-$R/MAINSCENARIO.re4mesh.json rel-$R/$ST/$R.arc > rel-$R-arc.log 2>&1 || { tail rel-$R-arc.log; exit 1; }
python3 $T/room_smd.py release w-${R}c/$R.dar pkg-$R/MAINSCENARIO.re4mesh.json rel-$R/$ST/$R.dar > rel-$R-dar.log 2>&1 || { tail rel-$R-dar.log; exit 1; }
sha256sum pkg-$R/MAINSCENARIO.re4mesh rel-$R/$ST/$R.arc rel-$R/$ST/$R.dar w-${R}c/$R.arc w-${R}c/$R.dar
