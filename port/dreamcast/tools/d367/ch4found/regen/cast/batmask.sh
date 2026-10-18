#!/bin/bash
set -euo pipefail
D=/root/probe/lanes-20261014/ps2cast/work/conv
mkdir -p "$D"
[ -e "$D/mask-bat-em29-00" ] || cp -a '/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/cast/common/mask-bat-em29-00' "$D/"
ls "$D/mask-bat-em29-00"
ROOMS=229 bash /mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen/c4r-reg.sh
