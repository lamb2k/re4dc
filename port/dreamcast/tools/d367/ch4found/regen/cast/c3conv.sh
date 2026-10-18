#!/bin/bash
# ch4regen: cast16 conv3 castle Zealots (10-16 21:58-22:25Z): convert / native / finish / masks / regcast per archive.
# tools: 9b4cb31f (t9b4) for em19/em1a/em1b/em14-07..09; dd9e7fe1 (tdd9) for em14-06p and regcast-em14.
set -euo pipefail
R=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261016/cast16
RL=/root/probe/lanes-20261016/cast16
W=$R/conv3
NAT=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen/c4r-native.sh
cd /c/tmp
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash -c "for a in em14 em19 em1a; do cp -n /root/probe/lanes/ps2cast/inputs/\$a.drs $RL/conv3/\$a.drs; done; ls $RL/conv3/*.drs"
T9=$R/t9b4/port/dreamcast/tools; TD=$R/tdd9/port/dreamcast/tools
N9="zealot-em1a-07p zealot-em1a-08p zealot-em1a-09p zealot-em14-07p zealot-em14-08p zealot-em14-09p zealot-em19-07p zealot-em19-08p zealot-em19-09p zealot-em1b-0ap"
for p in $N9; do rm -rf "$W/${p:?}"; python $T9/ps2_cast.py convert $p "$W/$p" --bone-tol 0.05 > /dev/null 2>&1 || echo "conv FAIL $p"; done
rm -rf "$W/zealot-em14-06p"; python $TD/ps2_cast.py convert zealot-em14-06p "$W/zealot-em14-06p" --bone-tol 0.05 > /dev/null 2>&1 || echo "conv FAIL 06p"
L=""; for p in $N9; do [ -d //wsl.localhost/Ubuntu-24.04$RL/conv3/$p ] && L="$L $RL/conv3/$p"; done
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash $NAT $RL/t9b4 $L | cut -c1-70
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash $NAT $RL/tdd9 $RL/conv3/zealot-em14-06p | cut -c1-70
for p in $N9; do [ -d $W/$p ] && { python $T9/ps2_cast.py finish $W/$p >/dev/null 2>&1 || echo "finish FAIL $p"; }; done
python $TD/ps2_cast.py finish $W/zealot-em14-06p >/dev/null 2>&1 || echo "finish FAIL 06p"
mk(){ a=$1; t=$2; tp=$3; d=$W/zealot-$a-${t}p; for x in "13 0x202 $tp hood" "16 0x20f 0x210 acc1" "20 0x217 0x218 acc5"; do set -- $x; rm -rf "$W/mask-$a-$t-$4"; python $T9/ps2_mask_runs.py $d $W/$a.drs $2 $3 $1 $W/mask-$a-$t-$4 >/dev/null 2>&1 || echo "mask FAIL $a $t $4"; done; }
for a in em14 em19 em1a; do mk $a 07 0x1fd; mk $a 08 0x21a; mk $a 09 0x21e; done
rm -rf $W/mask-em14-06-extra $W/mask-em14-06-s5 $W/mask-em14-06-s6
python $TD/ps2_mask_runs.py $W/zealot-em14-06p $W/em14.drs 0x1f0 0x1f1 2 $W/mask-em14-06-extra >/dev/null 2>&1 || echo "mask FAIL extra"
python $TD/ps2_mask_runs.py $W/zealot-em14-06p $W/em14.drs 0x1ed 0x1f1 5 $W/mask-em14-06-s5 >/dev/null 2>&1 || echo "mask FAIL s5"
python $TD/ps2_mask_runs.py $W/zealot-em14-06p $W/em14.drs 0x1ee 0x1f1 6 $W/mask-em14-06-s6 >/dev/null 2>&1 || echo "mask FAIL s6"
for a in em19 em1a em1b; do rm -rf "$W/regcast-$a"; python $T9/ps2_cast.py regcast "$W/regcast-$a" ps2-overlay $(ls -d $W/zealot-$a-0?p) 2>&1 | tail -1 | cut -c1-60; done
rm -rf "$W/regcast-em14"; python $TD/ps2_cast.py regcast "$W/regcast-em14" ps2-overlay $W/zealot-em14-0[6789]p 2>&1 | tail -1 | cut -c1-60
echo C3CONV-DONE
