#!/bin/bash
# round 4 B arms: cx5mmW = the island play-warp arm (cx5vmW) + MOTION_MISS_LOG=1 (hot-list run, em36 acting);
# cx5srT = the same knobs as a trace arm (rT: LOGIC_TRACE=1 GAME_DECISION_TRACE=1 PACE_MODE=off ...), the STRICT pair arm.
XON="ROUTE_CH3=1 DISC2=1 STAGE_OVL=1 PS2_ENEMY_ST3=23 ALIVE_CAP=6 ALIVE_CAP_PARK=1 ALIVE_CAP_LOG=1 PRIM_MIN_ST3=393216 FOG_OFF_CLEAR=1 ROUTE_MOVIES=1 NATIVE_MODEL_REGISTRY_CENSUS=1 HEAP4_WATER=1 WARP_JUMP=1 AICA_STR_ENT_MAX=56"
for a in "$@"; do
  case $a in
    m) bash /mnt/c/tmp/ch5/build.sh cx5m mW $XON GAME_DECISION_TRACE=0 LOGIC_TRACE=0 MOTION_MISS_LOG=1 ;;
    s) bash /mnt/c/tmp/ch5/build.sh cx5s rT $XON ;;
  esac
done
