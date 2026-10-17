cd /mnt/c/tmp/ch4
K="PS2_CH4_ENEMY=1 PS2_ENEMY_CH4_DIR=/root/probe/lanes-20261016/ch4found/private-include ROUTE_MOVIES_CH4=1 OT_WALK_CHECK=1"
OTW=2 bash build.sh cxc4q $K > /mnt/c/tmp/ch4/b12q.full 2>&1; tail -3 /mnt/c/tmp/ch4/b12q.full
OTW=2 bash build.sh cxc4r $K OT_PRIM_BUFFERS=2 > /mnt/c/tmp/ch4/b12r.full 2>&1; tail -3 /mnt/c/tmp/ch4/b12r.full
echo B12DONE
