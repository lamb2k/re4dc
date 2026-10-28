#!/bin/bash
# cast-ps2-25 r20: knob-off identity of the lane tree vs its base (origin/t15/int), same recipe.
set -euo pipefail
L=/root/work/lanes/cast-ps2-25; S=$L/_s/r19; mkdir -p $S; ROUTE=/root/probe/lanes/route
export SOURCE_DATE_EPOCH=1760000000
REC="$(cat $L/_s/r17/cand-22c6a1c9.txt) PS2_LEON_DIR=/root/re4data/private/ps2leon-rig-20261026 LEON_PS2_RIG=1 LEON_PS2_PORTRAIT_HAIR=1"
B=/root/work/lanes/cast-ps2-25-base
if [ ! -d "$B/.git" ] && [ ! -f "$B/.git" ]; then (cd $L && git worktree add -q --detach "$B" origin/t15/int); fi
(cd "$B" && git checkout -q --detach origin/t15/int && git log --oneline -1)
(cd "$B" && TREE="$B" bash /root/probe/d367-buildslot.sh bash port/dreamcast/tools/d367/route/route-build.sh cp25base $REC) | tail -1
(cd $L && TREE=$L bash /root/probe/d367-buildslot.sh bash port/dreamcast/tools/d367/route/route-build.sh cp25id $REC) | tail -1
T=/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy
for x in cp25base cp25id; do $T -R .stack -O binary $ROUTE/out-$x/re4dc-game.elf $S/$x.bin; done
sha256sum $S/cp25base.bin $S/cp25id.bin | sed 's#  .*/#  #'
for o in $ROUTE/out-cp25base/*.ovl; do n=$(basename $o); cmp -s $o $ROUTE/out-cp25id/$n && echo "same" || echo "DIFF $n"; done | sort | uniq -c
rm -f "${S:?}"/*.bin
