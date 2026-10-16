#!/bin/bash
# class_r101.sh (WSL): B check: does terrain mode leave r101's fence-holding meshes (0x17, 0x19, 0x63, 0x73, 0x75, 0x93,
# 0xbd, 0x7c) at level 0? Runs the terrain-mode ladder on bake13 r101 and prints those parts' classes.
W=/root/probe/worldtest16-20261016/terrain/r101; mkdir -p $W; cd $W
B13="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"
python3 /root/probe/worldtest16-20261016/tree/port/dreamcast/tools/ps2_world_vert_ladder.py "$B13/ps2-world.re4mesh" L2.re4mesh \
  --sidecar "$B13/ps2-world.r4pw" --walk /root/probe/lanes-20261015/worldlod-work/walk/r101.json --mode terrain --keep-walk-mm 1500 \
  --keep-pieces --class-report class.json --px 96 --colour-guard 3 --colour-per-m 8 --uv-guard 0.03 --uv-per-m 0.05 --per-vertex \
  --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 --baked 0 --protect-last 14 --report L2.json > job.log 2>&1 || tail -3 job.log
python3 - <<'P'
import json
c = json.load(open('class.json'))['parts']; L = json.load(open('L2.json'))['summary']
print('r101 terrain mode kept %.3f' % (L['all_corners_out'] / L['all_corners_in']))
want = {0x17, 0x19, 0x63, 0x73, 0x75, 0x93, 0xbd, 0x7c}
for pi, v in sorted(c.items(), key=lambda kv: int(kv[0])):
    if v['bin'] in want:
        print('part %s bin 0x%x %s planarity %.2f big %.2f' % (pi, v['bin'], v['cls'], v['planarity'], v['big_share']))
print('terrain parts', sum(1 for v in c.values() if v['cls'] == 'terrain'), 'of', len(c))
P
