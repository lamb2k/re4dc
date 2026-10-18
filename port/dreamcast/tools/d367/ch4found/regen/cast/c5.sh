#!/bin/bash
# ch4regen: replay of ch4found 14:14-14:18Z conv5 (em1a / em19 Zealots) + gen209.sh (16:5xZ) -> ch4found/cast/reg-209, reg-20d.
set -euo pipefail
S=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
T=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261018/ch4regen/tree/port/dreamcast/tools
C5=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261018/ch4regen/ch4found/cast/conv5
C5L=/root/probe/lanes-20261018/ch4regen/ch4found/cast/conv5
N="zealot-em1a-07p zealot-em1a-08p zealot-em1a-09p zealot-em19-07p zealot-em19-08p zealot-em19-09p"
cd /c/tmp
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- mkdir -p $C5L
python $S/c4r-drv.py $T/ps2_cast.py $C5 --plain --tol=0.001 $N 2>&1 | grep -E " OK | FAIL" | cut -c1-80
L=""; for n in $N; do L="$L $C5L/$n"; done
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash /mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen/c4r-native.sh /root/probe/lanes-20261018/ch4regen/tree $L | cut -c1-80
for n in $N; do python $T/ps2_cast.py finish $C5/$n >/dev/null 2>&1 || echo "finish FAIL $n"; done
args=""; for n in $N; do args="$args $n:13,16,20,21"; done
python $S/c4r-mask.py $T $C5 $args 2>&1 | grep -v "rc 0" || true
for a in em1a em19; do python $T/ps2_cast.py regcast "$C5/regcast-$a" ps2-overlay $C5/zealot-$a-07p $C5/zealot-$a-08p $C5/zealot-$a-09p 2>&1 | tail -1 | cut -c1-80; done
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash /mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen/c4r-gen209.sh
