set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
B=$L/extra/base
T=$L/trees/origin/lane/castle-1015/port/dreamcast/tools
NT="/mnt/c/Game Dev/Emulators/re4-assets-private/t11-20261014/blackps2/newtex"
A="/mnt/c/Game Dev/Emulators"
cd /tmp
python3 "$S/c3r_t12d3.py" "$T" "$B/t121-b097d061.pak" "$NT" "$B/tex-t12d-43be4b59.pak" \
  "$A/re4-assets-private/items-20261014/tex-items.pak" "$A/re4-assets-private/p2a5-regblobs-20261011/tex-e531a3dddfd30779.pak" \
  "$A/re4-cx-ch23-20261013/w9-common-vq78-seal-v1/after-tex.pak" "$A/re4-cx-ch23-20261013/r11c-441a-pal4-candidate-v1/tex.pak" \
  "$B/t15-15611245.pak"
