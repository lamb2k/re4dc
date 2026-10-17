cd /mnt/c/tmp/ch4
K="PS2_CH4_ENEMY=1 PS2_ENEMY_CH4_DIR=/root/probe/lanes-20261016/ch4found/private-include ROUTE_MOVIES_CH4=1 OT_WALK_CHECK=2"
OTW=2 bash build.sh cxc4y $K > /mnt/c/tmp/ch4/b18y.full 2>&1; tail -3 /mnt/c/tmp/ch4/b18y.full | cut -c1-200
grep -a "error" /root/probe/lanes-20261016/ch4found/k/logs-build.txt | tail -3
echo B18DONE
