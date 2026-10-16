#!/bin/bash
# c11.sh (WSL): r101 version C14 = C12 + 0x63 (C13 without the houses 0x17 / 0x19); C12 = C4 + the house-fence meshes 0x93, 0xbd and 0x7c kept at level 0 (rail texture 1a6203f9 in view 79->18, 57->21, 78->57 in C4; screen right is the NEGATIVE inview angle, so C5..C11 protected the wrong side). Hunt history (C5..C10,
# inview.py / stagedump.py / lods.py) found every rail-texture (1a6203f9) triangle in view kept except in 0x63, a
# 703-vertex wooden-structure mesh in front of the house right of the pyre (15 -> 5 triangles in view).
W=/root/probe/worldtest16-20261016
B13="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"
export LADDER=$W/ladder_region.py
export WT_PROTECT_VBOX="-7000,-500,-1500,1500,6500,7000"
bash $W/room_c.sh r101 C14 "$B13" /root/probe/lanes-20261015/worldlod-work/walk/r101.json "$B13/ps2-world.r4sg" \
  209,210,211,212,213,214,215,216,217,218,219,220,221,222 -- --px 96 --colour-guard 3 --colour-per-m 8 --uv-guard 0.03 \
  --uv-per-m 0.05 --per-vertex --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 \
  --protect-bins 0x2d,0x10,0x65,0xa4,0x7f,0x80,0x95,0xd,0x93,0xbd,0x7c,0x63 --protect-last 14
grep -h "SPATIAL\|KEPT" $W/rooms/r101-C14/job.log
