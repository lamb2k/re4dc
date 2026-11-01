#!/bin/bash
set -euo pipefail
X=/root/work/lanes/world-blender25-scratch
for a in "$@"; do python3 /mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/3eafc4fe-ad61-4030-8af6-7352db985ae8/scratchpad/world-blender25/finish.py $X/r101-$a/final $X/r101-$a/ship; done
