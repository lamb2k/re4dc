#!/bin/bash
# terrainL.sh (WSL): terrain-only mode + --lock-borders (no cracks/T-junction seams against neighbour meshes) for the test 17
# rooms r102 r108 r10a. Output /root/probe/worldtest16-20261016/terrainL/<room>/{out/ps2-wv5.re4mesh,class.json,L2.json,job.log}.
set -u
B=/root/probe/worldtest16-20261016/tree/port/dreamcast/tools; R16=/root/probe/world16-20261016/rooms
W=/root/probe/worldtest16-20261016/terrainL; mkdir -p $W
job() { r=$1; O=$W/$r; rm -rf $O; mkdir -p $O/out; cd $O
  python3 $B/ps2_world_vert_ladder.py $R16/$r/src.re4mesh L2.re4mesh --sidecar $R16/$r/src.r4pw --walk $R16/$r/walk.json \
    --mode terrain --keep-walk-mm 1500 --keep-pieces --lock-borders --class-report class.json --px 96 --colour-guard 3 --colour-per-m 8 \
    --uv-guard 0.03 --uv-per-m 0.05 --per-vertex --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 --baked 0 --protect-last 0 \
    --report L2.json > job.log 2>&1 || { echo "$r FAIL"; tail -3 job.log; return; }
  cp L2.re4mesh out/ps2-wv5.re4mesh
  python3 -c "
import json;d=json.load(open('L2.json'))['summary'];o=json.load(open('/root/probe/worldtest16-20261016/terrainL/../tt/$r-L2.json'))['summary'] if 0 else None
print('$r lock-borders kept %.3f bytes %d -> %d'%(d['all_corners_out']/d['all_corners_in'],d['bytes_in'],d['bytes_out']))"
}
for r in ${ROOMS:-r102 r108 r10a}; do job $r & done
wait
for r in r102 r108 r10a; do python3 -c "
import json;d=json.load(open('/mnt/c/Game Dev/Emulators/re4-assets-private/worldtest-20261016/terrain-$r/L2.json'))['summary'];print('$r old kept %.3f bytes_out %d'%(d['all_corners_out']/d['all_corners_in'],d['bytes_out']))"; done
