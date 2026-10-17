cd /mnt/c/tmp/ch4
K="PS2_CH4_ENEMY=1 PS2_ENEMY_CH4_DIR=/root/probe/lanes-20261016/ch4found/private-include ROUTE_MOVIES_CH4=1 GAME_TICK_LOG=300 PHASE_METER=1 DISC_READ_METER=1 MOTION_STATS_LOG=1 MOTION_MISS_LOG=1 AICA_STR_ENT_MAX=80 MOTION_COLD_POOL_CASTLE=131072"
OTW=2 bash build.sh cxc4z $K > /mnt/c/tmp/ch4/b19z.full 2>&1; tail -3 /mnt/c/tmp/ch4/b19z.full | cut -c1-120
echo B19DONE
