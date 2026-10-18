set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
B=$L/extra/base
[ -e "$B/p-51f1f7a4.pak" ] || python3 "$S/c3r_isox.py" /mnt/c/Flycast-Evidence/_disccache/23b02efeb438cd7cc097de7a1ce3924175e7d1aef10efafd9cd7a25715961bc1/track03.iso "$B/p-51f1f7a4.pak" dc/tex.pak
sha256sum "$B/p-51f1f7a4.pak" | cut -c1-8
