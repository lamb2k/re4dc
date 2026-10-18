# room.sh <room>: room container (r117 lane room.sh recipe) + GC LIT cut 0 json (the PS2 world runs on Windows)
set -e
R=$1
T=/root/probe/lanes-20261013/ch22/port/dreamcast/tools
W=/root/probe/lanes-20261013/ch22w/rooms
mkdir -p $W/iso-src/st1; cd $W
[ -e iso-src/st1/$R.das ] || python3 /root/probe/lanes-20261013/ch22w/tools/gcx.py iso-src st1/$R.das
sha256sum iso-src/st1/$R.das
rm -rf mirror-$R tex-$R w-${R}c pkg-$R rel-$R
python3 $T/le_mirror.py iso-src mirror-$R --native-rooms > mirror-$R.log 2>&1 || { tail mirror-$R.log; exit 1; }
echo st1/$R.arc > $R-tex.manifest
python3 $T/prepare_native_ui.py iso-src $R-tex.manifest tex-$R > tex-$R.log 2>&1 || { tail tex-$R.log; exit 1; }
python3 $T/prepare_native_ui.py --compact-room iso-src/st1/$R.das --compact-room-mips --textures tex-$R --output w-${R}c > w-$R.log 2>&1 || { tail w-$R.log; exit 1; }
mkdir -p pkg-$R
python3 $T/convert_room_bins.py pkg-$R/MAINSCENARIO.re4mesh --owner 0xff --smd iso-src/st1/$R.das --lod --lod-min-gain 0.4 --lod-max-levels 4 --lod-eps 24,48,96,192,384 --lod-share --class-auto --color prelit > pkg-$R.log 2>&1 || { tail pkg-$R.log; exit 1; }
mkdir -p rel-$R/st1
python3 $T/room_smd.py release w-${R}c/$R.arc pkg-$R/MAINSCENARIO.re4mesh.json rel-$R/st1/$R.arc > rel-$R-arc.log 2>&1 || { tail rel-$R-arc.log; exit 1; }
python3 $T/room_smd.py release w-${R}c/$R.dar pkg-$R/MAINSCENARIO.re4mesh.json rel-$R/st1/$R.dar > rel-$R-dar.log 2>&1 || { tail rel-$R-dar.log; exit 1; }
python3 $T/gc_room_lit.py $R $W/$R-gc-lit-cut0.json > gclit-$R.log 2>&1 || { tail gclit-$R.log; exit 1; }
for f in mirror-$R.log tex-$R.log w-$R.log rel-$R-arc.log rel-$R-dar.log; do echo "== $f"; tail -c 400 $f; echo; done
