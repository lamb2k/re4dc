#!/bin/bash
# terrain_all.sh (WSL): worldtest16 B, the terrain/rock-only mode on the chapter 1 rooms projected below 30 fps.
# Per room: ladder --mode terrain --keep-walk-mm 1500 --keep-pieces (B's L2 error settings on the terrain parts only);
# the variant-5 file is the ladder output itself (no batching / strip groups: the A arm of these rooms has none either).
# Output /root/probe/worldtest16-20261016/terrain/<room>/{out,class.json,L2.json,job.log}.
set -u
B=/root/probe/worldtest16-20261016/tree/port/dreamcast/tools; R16=/root/probe/world16-20261016/rooms
W=/root/probe/worldtest16-20261016/terrain; mkdir -p $W
job() { r=$1; O=$W/$r; rm -rf $O; mkdir -p $O/out; cd $O
  python3 $B/ps2_world_vert_ladder.py $R16/$r/src.re4mesh L2.re4mesh --sidecar $R16/$r/src.r4pw --walk $R16/$r/walk.json \
    --mode terrain --keep-walk-mm 1500 --keep-pieces --class-report class.json --px 96 --colour-guard 3 --colour-per-m 8 \
    --uv-guard 0.03 --uv-per-m 0.05 --per-vertex --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 --baked 0 --protect-last 0 \
    --report L2.json > job.log 2>&1 || { echo "$r FAIL"; return; }
  cp $R16/$r/src.re4mesh out/ps2-world.re4mesh; cp $R16/$r/src.r4pw out/ps2-world.r4pw; cp $R16/$r/src.ids out/ps2-world.ids
  cp L2.re4mesh out/ps2-wv5.re4mesh
  python3 -c "
import json;d=json.load(open('L2.json'))['summary'];c=json.load(open('class.json'))['parts']
print('$r kept %.3f bytes %d -> %d terrain parts %d of %d'%(d['all_corners_out']/d['all_corners_in'],d['bytes_in'],d['bytes_out'],sum(1 for v in c.values() if v['cls']=='terrain'),len(c)))"
}
for r in ${ROOMS:-r100 r102 r103 r104 r105 r106 r107 r108 r109 r10a}; do job $r & done
wait
