set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
T=$L/trees/origin/lane/castle-1015/port/dreamcast/tools
O=$L/extra/castlepak; mkdir -p "$O"
cd /tmp
nice python3 "$S/c3r_castlepak.py" "$T" "$L/extra/base/tex-t12d-43be4b59.pak" "$O" "$S/castleloose.json"
