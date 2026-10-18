#!/bin/bash
# ch4regen: cast16 conv4 member conversions (Windows python, recorded final methods), git-bash side.
set -euo pipefail
S=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
R=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261016/cast16
T=$R/tree/port/dreamcast/tools; TM=$R/c4m/port/dreamcast/tools; W=$R/conv4
cd /c/tmp
python $S/c4r-drv.py $T/ps2_cast.py $W zealot-em11-08g zealot-em11-09g zealot-em1c-0ag zealot-em1c-0dg ganado-em15-00g ganado-em15-03g ganado-em15-04g ganado-em16-03g ganado-em16-04g 2>&1 | grep -E " OK | FAIL" || true
python $S/c4r-drv.py $T/ps2_cast.py $W --plain --tol=2.1 ganado-em15-0bg 2>&1 | grep -E " OK | FAIL" || true
python $S/c4r-drv.py $T/ps2_cast.py $W --plain zealot-em14-06p zealot-em14-07p zealot-em14-08p zealot-em14-09p zealot-em1a-09p armor-em25-00 armor-em3c-00 novis-em2d-04 2>&1 | grep -E " OK | FAIL" || true
python $S/c4r-drv.py $T/ps2_cast.py $W --plain --tol=0.001 armor-em3c-02 2>&1 | grep -E " OK | FAIL" || true
python $S/c4r-drv.py $T/ps2_cast.py $W --em1b0ag zealot-em1b-0ag 2>&1 | grep -E " OK | FAIL" || true
python $S/c4r-drv.py $TM/ps2_cast.py $W --plain --tol=0.001 zealot-em14-09q zealot-em1c-09h 2>&1 | grep -E " OK | FAIL" || true
echo CONVDONE
