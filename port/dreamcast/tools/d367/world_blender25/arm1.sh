#!/bin/bash
# one regroup arm end to end with ONE disc on C: (Git Bash). usage: arm1.sh <arm>   (uses the ctl twin, no cert row)
set -euo pipefail
A=${1:?}
H=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/3eafc4fe-ad61-4030-8af6-7352db985ae8/scratchpad/world-blender25
W=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/3eafc4fe-ad61-4030-8af6-7352db985ae8/scratchpad/world-blender25
E=/c/Flycast-Evidence/re4-dreamcast/world-blender25
cd $H
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- env TWIN=ctl bash $W/stg.sh $A /root/work/lanes/world-blender25-scratch/r101-$A/ship 2>&1 | grep -v Warn | tail -1
MSYS_NO_PATHCONV=1 bash runs.sh "wave \"run cross-$A $A hwcross.txt\" \"run bell-$A $A bell.txt\" \"run still-cross-$A $A still-hwcross.txt --period 5\"" | tail -1
python pair.py C:/Flycast-Evidence/re4-dreamcast/world-blender25 still-cross-ctl still-cross-$A
for v in cross bell; do echo "$v-$A $(grep -a '^WC24 q=3' $E/$v-$A/run-output.txt | cut -c1-200)"; done
echo "$(grep -a -o 'total_fails=[0-9]*' $E/cross-$A/run-output.txt | sort -u | tr '\n' ' ') halts=$(grep -a -c 'HALT\|FAULT' $E/cross-$A/run-output.txt) $(grep -a 'PS2DYN room=101 ids' $E/cross-$A/run-output.txt | cut -c1-90) $(grep -a 'PS2DYN frame=' $E/cross-$A/run-output.txt | tail -1 | cut -c1-90) $(grep -a 'trans: room=101' $E/cross-$A/run-output.txt | cut -c1-80)"
rm -rf "$E/_discs/${A:?}"
