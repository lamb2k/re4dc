#!/bin/bash
# round 2 arms: cx5tmW = dba49b85 (before the round-10 hooks) + LOGIC_TRACE=1; cx5umW = the tree with the hooks + LOGIC_TRACE=1;
# cx5vmW = the tree with the hooks, play knobs + AICA_STR_ENT_MAX=56 (island stream file). -j4 via build.sh.
L=/root/probe/lanes-20261016/ch5found
XON="ROUTE_CH3=1 DISC2=1 STAGE_OVL=1 PS2_ENEMY_ST3=23 ALIVE_CAP=6 ALIVE_CAP_PARK=1 ALIVE_CAP_LOG=1 PRIM_MIN_ST3=393216 FOG_OFF_CLEAR=1 ROUTE_MOVIES=1 NATIVE_MODEL_REGISTRY_CENSUS=1 HEAP4_WATER=1 WARP_JUMP=1 GAME_DECISION_TRACE=0"
cd $L/tree
[ -d $L/base ] || git worktree add --detach $L/base dba49b85 >/dev/null 2>&1
git -C $L/base log --oneline -1
for a in "$@"; do
  case $a in
    t) T=$L/base bash /mnt/c/tmp/ch5/build.sh cx5t mW $XON LOGIC_TRACE=1 ;;
    u) bash /mnt/c/tmp/ch5/build.sh cx5u mW $XON LOGIC_TRACE=1 ;;
    v) bash /mnt/c/tmp/ch5/build.sh cx5v mW $XON LOGIC_TRACE=0 AICA_STR_ENT_MAX=56 ;;
  esac
done
