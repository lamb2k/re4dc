#!/bin/bash
# c17.sh (WSL): r101 version C17 = C4 (no bin 0x17 hand protection) + ps2_world_vert_ladder.py --thin-edge-frac F (the B
# lesson: a per-vertex thinness guard instead of per-bin protection). Ladder from lane/worldtest16 (WT_TOOLS).
W=/root/probe/worldtest16-20261016; TAG=${TAG:-C17}; TEF=${TEF:-0.5}
B13="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"
export LADDER=$W/ladder_region.py WT_TOOLS=$W/tree/port/dreamcast/tools
export WT_PROTECT_VBOX="-7000,-500,-1500,1500,6500,7000"
bash $W/room_c.sh r101 $TAG "$B13" /root/probe/lanes-20261015/worldlod-work/walk/r101.json "$B13/ps2-world.r4sg" \
  209,210,211,212,213,214,215,216,217,218,219,220,221,222 -- --px 96 --colour-guard 3 --colour-per-m 8 --uv-guard 0.03 \
  --uv-per-m 0.05 --per-vertex --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 --thin-edge-frac $TEF \
  --protect-bins 0x2d,0x10,0x65,0xa4,0x7f,0x80,0x95,0xd --protect-last 14
grep -h "SPATIAL\|KEPT\|FAIL" $W/rooms/r101-$TAG/job.log
KEY=1a6203f9 python3 "/mnt/c/Game Dev/Emulators/worldtest-20261016/scripts/inview.py" $W/rooms/r101-$TAG -7914,2000,1.5708 -32,-10 10,40 L2.re4mesh src.r4pw | grep "bins on"
