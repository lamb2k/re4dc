# prep-room.sh <room>: compact + package + release the GC room archive (Codex cx_room_fixtures.py prepare_room recipe)
set -e
R=$1; ST=st${R:1:1}
TOOLS=/root/probe/lanes-20261016/ch2/tree/port/dreamcast/tools
A=/root/probe/codex-cx-fixtures-20261013/output/$R/ancillary-c3d2f4cd6f00
W=/root/probe/lanes-20261016/ch2/rooms/$R
rm -rf $W; mkdir -p $W/package $W/released/$ST
SRC=$A/source/$ST/$R.das; TEX=$A/tex
ls -la $SRC; ls $TEX | wc -l
t0=$(date +%s)
python3 $TOOLS/prepare_native_ui.py --compact-room $SRC --compact-room-mips --textures $TEX --output $W/compact > $W/compact.log 2>&1 || { tail -20 $W/compact.log; exit 1; }
tail -2 $W/compact.log
python3 $TOOLS/convert_room_bins.py $W/package/MAINSCENARIO.re4mesh --owner 0xff --smd $SRC --lod --lod-min-gain 0.4 --lod-max-levels 4 --lod-eps 24,48,96,192,384 --lod-share --class-auto --color prelit > $W/package.log 2>&1 || { tail -20 $W/package.log; exit 1; }
head -c 300 $W/package.log; echo
for x in arc dar; do
python3 $TOOLS/room_smd.py release $W/compact/$R.$x $W/package/MAINSCENARIO.re4mesh.json $W/released/$ST/$R.$x > $W/release-$x.log 2>&1 || { tail -20 $W/release-$x.log; exit 1; }
python3 -c "import json;d=json.load(open('$W/release-$x.log'));print('$x',{k:d.get(k) for k in ('archive_source','archive_resident','saved','container_source','container')})"
done
ls -la $W/released/$ST
echo "PREP_DONE $R $(( $(date +%s)-t0 ))s"
