cd /mnt/c/tmp/ch4; sed -i 's/\r$//' build.sh
OTW=2 bash build.sh cxc4m PS2_CH4_ENEMY=1 PS2_ENEMY_CH4_DIR=/root/probe/lanes-20261016/ch4found/private-include ROUTE_MOVIES_CH4=1 OT_WALK_CHECK=1 > /mnt/c/tmp/ch4/b11.full 2>&1; tail -4 /mnt/c/tmp/ch4/b11.full
grep -n 'error' /root/probe/lanes-20261016/ch4found/k/logs-build.txt | tail -5
