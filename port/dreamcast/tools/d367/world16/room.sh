#!/bin/bash
# world16 per-room offline job. usage: room.sh <room> <ganado:1|0>
set -u
R=$1; G=$2
T=/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools
W=/root/probe/world16-20261016
O=$W/rooms/$R; rm -rf $O; mkdir -p $O; cd $O
exec > $O/job.log 2>&1
S=$(python3 -c "import json;d=json.load(open('$W/${SRCJ:-sources.json}'))['rooms']['$R'];print(d['ps2-world.re4mesh']['path'])")
SP=$(python3 -c "import json;d=json.load(open('$W/${SRCJ:-sources.json}'))['rooms']['$R'];print(d['ps2-world.r4pw']['path'])")
SI=$(python3 -c "import json;d=json.load(open('$W/${SRCJ:-sources.json}'))['rooms']['$R'];print(d['ps2-world.ids']['path'])")
SZ=$(stat -c %s "$S")
cp "$S" src.re4mesh; cp "$SP" src.r4pw; cp "$SI" src.ids
SAT=/root/probe/lanes/ps2rooms/extract/work/$R/$R/${R}_001.SAT
echo "room $R ganado=$G src=$S bytes=$SZ"
python3 $T/d367/worldlod/walk.py $SAT walk.json || { echo "FAIL walk"; exit 2; }
if [ "$G" = 1 ]; then
  python3 $T/ps2_world_vert_ladder.py src.re4mesh L2.re4mesh --sidecar src.r4pw --walk walk.json \
    --px 96 --colour-guard 3 --colour-per-m 8 --uv-guard 0.03 --uv-per-m 0.05 --per-vertex \
    --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 --baked 0 --protect-last 0 --report L2.json >/dev/null \
    || { echo "FAIL ladder"; exit 3; }
else
  cp src.re4mesh L2.re4mesh
fi
python3 $T/ps2_world_batch.py L2.re4mesh flat.re4mesh --sidecar src.r4pw --cell-mm 4000 --max-vertices 256 \
  --contiguous --max-bytes $SZ --report flat.json || { echo "contiguous over ceiling: indexed batch only";   python3 $T/ps2_world_batch.py L2.re4mesh flat.re4mesh --sidecar src.r4pw --cell-mm 4000 --max-vertices 256   --max-bytes $SZ --report flat.json || { echo "FAIL batch"; exit 4; }; echo "STORAGE=indexed"; }
python3 $T/ps2_strip_groups.py flat.re4mesh src.r4pw flatg.re4mesh flat.r4sg --report flatsg.json || { echo "FAIL groups"; exit 5; }
SPATIAL=none
if [ "$G" = 1 ]; then
  python3 - <<PY
import json,struct
b=open('src.r4pw','rb').read(); crc=struct.unpack_from('<4s7I',b)[5]
json.dump({'r4pw_crc':'%08x'%crc,'objects':[]},open('gate.json','w'))
PY
  head -c 262144 /dev/zero > cap.r4sg
  if python3 $T/ps2_world_spatial_batch.py flat.re4mesh src.r4pw src.ids sp --cell-mm 32000 --max-bytes $SZ \
       --source-groups cap.r4sg --gated-manifest gate.json > spatial.out 2>&1; then SPATIAL=ok; else SPATIAL=fail; tail -3 spatial.out; fi
fi
mkdir -p out
if [ "$SPATIAL" = ok ] && [ "$(python3 -c "import json;print(json.load(open('sp/report.json'))['cells'])")" = 0 ]; then SPATIAL=nocells; fi
if [ "$SPATIAL" = ok ]; then
  head -c $(stat -c %s sp/ps2-wv5.r4sg) sp/ps2-world.r4sg > sp/l0cap.r4sg; mv sp/l0cap.r4sg sp/ps2-world.r4sg
  cp sp/ps2-world.re4mesh sp/ps2-world.r4pw sp/ps2-world.ids sp/ps2-world.r4sg sp/ps2-wv5.re4mesh sp/ps2-wv5.r4sg out/
else
  cp src.re4mesh out/ps2-world.re4mesh; cp src.r4pw out/ps2-world.r4pw; cp src.ids out/ps2-world.ids
  cp flatg.re4mesh out/ps2-wv5.re4mesh; cp flat.r4sg out/ps2-wv5.r4sg
  head -c $(stat -c %s flat.r4sg) /dev/zero > out/ps2-world.r4sg
fi
if [ "$R" = r100 ]; then
  # movie layout/reload contract: padded L0 at the source size, valid L0 groups, no wv5
  python3 $T/ps2_strip_groups.py out/ps2-world.re4mesh out/ps2-world.r4pw l0g.re4mesh l0.r4sg --report l0sg.json || { echo "FAIL r100 L0 groups"; exit 6; }
  mv l0g.re4mesh out/ps2-world.re4mesh; mv l0.r4sg out/ps2-world.r4sg; rm -f out/ps2-wv5.re4mesh out/ps2-wv5.r4sg
fi
echo "SPATIAL=$SPATIAL"
ls -l out; sha256sum out/*
echo DONE
