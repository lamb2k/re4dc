# nat.sh TREE HOSTDIR MODELDIR... : ps2_cast_native.sh replay (KB 512)
set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen; TREE=${1:?}; H=${2:?}; shift 2
mkdir -p $H/host/dc; cp -n $L/tools/pvr.h $H/host/dc/pvr.h
[ -d $L/$TREE ] || git -C $L/tree worktree add -q --detach $L/$TREE ${TREE#t-}
cd $L/$TREE
for m in "$@"; do PS2CAST_HOSTCHECK=$H PS2CAST_HOST_WORKSPACE_KB=${KB:-512} bash port/dreamcast/tools/ps2_cast_native.sh $m > $m/native-stage.log 2>&1 || { tail -4 $m/native-stage.log; exit 1; }; echo "native ok $(basename $m)"; done
