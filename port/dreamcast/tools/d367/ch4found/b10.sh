cd /mnt/c/tmp/ch4; sed -i 's/\r$//' build.sh
OTW=2 bash build.sh cxc4l PS2_CH4_ENEMY=1 PS2_ENEMY_CH4_DIR=/root/probe/lanes-20261016/ch4found/private-include ROUTE_MOVIES_CH4=1 GAME_TICK_LOG=300 PHASE_METER=1 DISC_READ_METER=1 MOTION_STATS_LOG=1 AICA_STR_ENT_MAX=80 > /mnt/c/tmp/ch4/b10.full 2>&1; tail -4 /mnt/c/tmp/ch4/b10.full
grep -n 'error' /root/probe/lanes-20261016/ch4found/k/logs-build.txt | tail -5
