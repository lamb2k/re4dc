#!/bin/bash
# Git Bash orchestrator: full.sh <arm> (env WB_* for r101run.py). Converter -> twin -> disc -> cross perf + still -> diff
set -euo pipefail
A=${1:?}
H=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/3eafc4fe-ad61-4030-8af6-7352db985ae8/scratchpad/world-blender25
W=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/3eafc4fe-ad61-4030-8af6-7352db985ae8/scratchpad/world-blender25
cd $H
L=$(python r101run.py $A 2>&1 | tee $H/conv-$A.log | grep '^ARM')
echo "$L"
crc=0x$(echo "$L" | sed 's/.* crc \([0-9a-f]*\) bytes.*/\1/'); by=$(echo "$L" | sed 's/.* bytes \([0-9]*\)$/\1/')
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash $W/tw.sh $A $crc $by | tail -1 | cut -c1-80
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash $W/stg.sh $A /root/work/lanes/world-blender25-scratch/r101-$A/final 2>&1 | grep -v Warn | tail -1
