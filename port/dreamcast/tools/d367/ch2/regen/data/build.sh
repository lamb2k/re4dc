set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen
[ -d $L/t-int ] || git -C $L/tree worktree add -q --detach $L/t-int origin/t15/int
cd $L/t-int; git log -1 --format='%h %s'
git merge-base --is-ancestor 7e84fcb5 HEAD && echo "has PS2_ASHLEY_ROOMS=2" || echo "no 7e84fcb5"
git -C $L/t-int submodule update --init --quiet 2>&1 | tail -2; mkdir -p $L/k
T=$L/t-int K=$L/k LP=cr bash port/dreamcast/tools/d367/ch2/ch2-build.sh mW > $L/k/build-mW.log 2>&1; echo rc=$?
tail -15 $L/k/build-mW.log
