#!/bin/bash
# c7.sh (WSL): r101 version C9 = C8 + house mesh 0x19 (its rail-texture parts lost 295->90 in C8); C8 = C7 + the long fence runs 0x73 / 0x75 and 0x1a (rail texture lost there in C7: 156->73, 105->81, 25->16); C7 = C4 + every small fence mesh kept at level 0: the meshes of at most
# 120 source vertices with a part on the rail-plank texture 1a6203f9 (texbins.py: 39 bins, 0x72..0x9a fence segments
# plus 0x2b/0x34/0x38/0xbb/0xbd). C5/C6 protected the wrong segments (0x7e/0x94); the house fence right of the pyre is
# in 0x81-0x84 / 0x98-0x9a (inview.py: rail-texture triangles in view 876 at level 0, 513 in C6).
W=/root/probe/worldtest16-20261016
B13="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"
FB=$(MAXV=120 python3 "/mnt/c/Game Dev/Emulators/worldtest-20261016/scripts/texbins.py" "$B13/ps2-world.re4mesh" "$B13/ps2-world.r4pw" 1a6203f9 2>/dev/null)
export LADDER=$W/ladder_region.py
export WT_PROTECT_VBOX="-7000,-500,-1500,1500,6500,7000"
bash $W/room_c.sh r101 C9 "$B13" /root/probe/lanes-20261015/worldlod-work/walk/r101.json "$B13/ps2-world.r4sg" \
  209,210,211,212,213,214,215,216,217,218,219,220,221,222 -- --px 96 --colour-guard 3 --colour-per-m 8 --uv-guard 0.03 \
  --uv-per-m 0.05 --per-vertex --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 \
  --protect-bins 0x2d,0x10,0x65,0xa4,0xd,0x19,0x1a,0x73,0x75,$FB --protect-last 14
grep -h "SPATIAL\|KEPT" $W/rooms/r101-C9/job.log
for st in "src.re4mesh src.r4pw" "out/ps2-wv5.re4mesh out/ps2-world.r4pw"; do
  python3 "/mnt/c/Game Dev/Emulators/worldtest-20261016/scripts/inview.py" $W/rooms/r101-C9 -7914,2000,1.5708 12,30 12,40 $st | tail -1 | tr ' ' '\n' | grep -i "1a6203f9\|782aed8c"
done
