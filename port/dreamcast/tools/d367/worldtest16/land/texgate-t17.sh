#!/bin/bash
# texgate.sh (WSL): TEXCHK + LEON-GC on the mW runs (o = t15/int data, n = test 16 data) and the r101 VRAM lines.
D=/root/probe/worldtest16-20261016/land17/port/dreamcast/tools/d367; E=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016
for r in t17-tex2-o t17-tex2-n t17-tex8-o t17-tex8-n t17-texa-o t17-texa-n; do
  echo "== $r"
  bash $D/texchk/texchk.sh $E/$r/capture/run-output.txt | tail -3; echo "texchk rc=${PIPESTATUS[0]}"
  python3 $D/mcheck/leongc_check.py $E/$r/capture/run-output.txt | tail -2; echo "leongc rc=${PIPESTATUS[0]}"
done
for r in t17-tex2-o t17-tex2-n t17-tex8-o t17-tex8-n t17-texa-o t17-texa-n c-still-o c-still-n; do
  echo "== VRAM $r"; grep -a "VRAM" $E/$r/capture/run-output.txt | grep -ai "room" | tail -2 | cut -c1-300
done
