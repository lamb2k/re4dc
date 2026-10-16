#!/bin/bash
# cN.sh (WSL): r101 control set N = the world32 pipeline with the vertex reduction off (ladder --px 1 --max-error-mm 50 --per-vertex: errors under 5 cm; --px 0 overflows the level-0 size
# 0), then batch (4 m cells), strip groups and the 32 m spatial batch as usual. Fence-rail hunt: if the rails are missing
# in N, a step after the ladder loses them.
W=/root/probe/worldtest16-20261016
B13="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"
bash $W/room_c.sh r101 N "$B13" /root/probe/lanes-20261015/worldlod-work/walk/r101.json "$B13/ps2-world.r4sg" \
  209,210,211,212,213,214,215,216,217,218,219,220,221,222 -- --px 1 --max-error-mm 50 --per-vertex --protect-last 14
grep -h "SPATIAL\|KEPT\|FAIL\|over" $W/rooms/r101-N/job.log
