set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
cd /tmp
nice python3 "$S/c3r_vq34.py" "$L/trees/origin/lane/ch3found16" "$L/extra/base/t15-15611245.pak" "$S/loosemap34.json" "$L/extra/vq-c34" 2>&1 | tail -3
