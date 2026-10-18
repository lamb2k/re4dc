#!/bin/bash
# ch5regen: native pass over every conv5 soldr-* member (t5 tree), as c5n3.sh / c5n5.sh did.
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
W=/root/probe/lanes-20261018/ch5regen/c16/conv5
bash "$S/c5r-c16nat.sh" t5 "$W"/soldr-*[!g]
