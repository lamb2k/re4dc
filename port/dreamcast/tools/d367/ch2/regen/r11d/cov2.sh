set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch2regen; L=/root/probe/lanes-20261017r/ch2regen
python3 $S/cover.py $S/need-rem2.json $S/cover-rem2.json $L/worlds $L/rooms $L/luis $L/r11d $L/regs $L/em16 $L/em $L/ps2cast $L/snd 2>&1 | tail -20
