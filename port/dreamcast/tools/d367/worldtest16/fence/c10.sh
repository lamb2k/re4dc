#!/bin/bash
# c10.sh (WSL): r101 version C10 = C9 (C4 + every fence mesh and house 0x19 kept at level 0) + the fence meshes' placements
# gated out of ps2_world_spatial_batch.py (left source-identical): in game C9 still lost the rails although every
# rail-texture triangle in view survived the ladder, and C9's own level 0 (loaded=0) lost them too, while the bake13
# level 0 on the same build draws them: the spatial batch is the step that loses them.
W=/root/probe/worldtest16-20261016; S="/mnt/c/Game Dev/Emulators/worldtest-20261016/scripts"
B13="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"
FB=$(MAXV=120 python3 "$S/texbins.py" "$B13/ps2-world.re4mesh" "$B13/ps2-world.r4pw" 1a6203f9 2>/dev/null)
ROWS=$(python3 "$S/rows.py" "$B13/ps2-world.re4mesh" "$B13/ps2-world.r4pw" "0x1a,0x73,0x75,$FB")
echo "gated fence rows: $ROWS"
export LADDER=$W/ladder_region.py
export WT_PROTECT_VBOX="-7000,-500,-1500,1500,6500,7000"
bash $W/room_c.sh r101 ${TAG:-C10} "$B13" /root/probe/lanes-20261015/worldlod-work/walk/r101.json "$B13/ps2-world.r4sg" \
  209,210,211,212,213,214,215,216,217,218,219,220,221,222,$ROWS -- --px 96 --colour-guard 3 --colour-per-m 8 --uv-guard 0.03 \
  --uv-per-m 0.05 --per-vertex --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 \
  --protect-bins 0x2d,0x10,0x65,0xa4,0xd,0x19,0x1a,0x73,0x75,$FB --protect-last 14
grep -h "SPATIAL\|KEPT" $W/rooms/r101-${TAG:-C10}/job.log; python3 -c "import json;d=json.load(open('$W/rooms/r101-${TAG:-C10}/sp/report.json'));print('cells',d['cells'],'batch_parts',d['batch_parts'],'retained',d['retained_parts'])"
