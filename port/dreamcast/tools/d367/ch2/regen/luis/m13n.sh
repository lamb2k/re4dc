set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen; R=$L/luis
[ -d $L/t-m13 ] || git -C $L/tree worktree add -q --detach $L/t-m13 f9d5b8c5
[ "${1:-}" = native ] || exit 0
mkdir -p $R/host-m13/host/dc; cp -n $L/tools/pvr.h $R/host-m13/host/dc/pvr.h
cd $L/t-m13
for m in merchant13-c0 merchant13-o0; do PS2CAST_HOSTCHECK=$R/host-m13 bash port/dreamcast/tools/ps2_cast_native.sh $R/models/$m > $R/models/$m/native-stage.log 2>&1 || { tail -4 $R/models/$m/native-stage.log; exit 1; }; echo "$m native ok"; done
