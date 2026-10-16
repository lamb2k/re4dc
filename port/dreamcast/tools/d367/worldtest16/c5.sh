#!/bin/bash
# c5.sh (WSL): r101 version C5 = C4 (the test 16 candidate set) + a second vertex box over the house fence rails right of the
# pyre (bins 0x7e / 0x94: x 17500..24500, y -500..3600, z -7000..-1000; diffverts from the cross camera).
W=/root/probe/worldtest16-20261016
B13="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"
export LADDER=$W/ladder_region.py
export WT_PROTECT_VBOX="-7000,-500,-1500,1500,6500,7000;17500,-500,-7000,24500,3600,-1000"
bash $W/room_c.sh r101 C5 "$B13" /root/probe/lanes-20261015/worldlod-work/walk/r101.json "$B13/ps2-world.r4sg" \
  209,210,211,212,213,214,215,216,217,218,219,220,221,222 -- --px 96 --colour-guard 3 --colour-per-m 8 --uv-guard 0.03 \
  --uv-per-m 0.05 --per-vertex --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 \
  --protect-bins 0x2d,0x10,0x65,0xa4,0x7f,0x80,0x95,0xd --protect-last 14
tail -12 $W/rooms/r101-C5/job.log
cd $W/rooms/r101-C5 && TOP=2000 python3 $W/diffverts.py src.re4mesh L2.re4mesh src.r4pw -7914,2000,1.5708 40000 | grep -E "0x7e|0x94" || echo "no fence-bin vertices removed"
