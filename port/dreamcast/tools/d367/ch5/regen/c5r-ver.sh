#!/bin/bash
# ch5regen: c5r-ver.sh <dir>... -> sha-match against missing-src.tsv, append found.tsv
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
python3 "$S/c5r_verify.py" "$S/missing-src.tsv" "$L/found.tsv" "$@"
