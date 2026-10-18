set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen; T=$L/t-int/port/dreamcast/tools/d367
python3 $T/test11/t11-fix.py crmW $L/fix/s-siegek-crmW.json --data ch2,cast16 --warp $T/ch2/warps/s-siegek.txt | tail -1 | cut -c1-120
python3 /mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch2regen/fxov.py | grep siege
