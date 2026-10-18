set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen; R=$L/r11d; rm -rf "${R:?}/regcast-r11dp"
python3 "/mnt/c/Game Dev/Emulators/ps2cast-20261014/sh/conv/merge_cast.py" $R/regcast-r11dp $R/regcast-cart $R/regcast-em16p | tail -1
bash /mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch2regen/reg.sh t-2f4a731e $L/t-2f4a731e/port/dreamcast/tools/d367/model-registry/ps2-ch2-r11dp.json reg-11dp 11d $R/regcast-r11dp "/root/probe/lanes-20261016/cast16/conv/e16p-mask-sack=$R/e16p-mask-sack" --pack-bones 64 --wide-identity --pool
