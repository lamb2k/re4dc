#!/bin/bash
# ch4regen: aica-c4c em1a / em16 / em1c by sha-only AICA search (ch3regen method): compact the unconverted prep archive
# (compall logic), then aica_search4k.py (castle 4000 Hz cap) against the target sha with the castle layout.
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
L=/root/probe/lanes-20261018/ch4regen; C=/root/probe/lanes-20261018/ch3regen
P=$L/ch4found/prepem
python3 $S/c4r-compall.py em1a=$C/prepem/origin_lane_castle-1015/prep-em1a/em1a.drs:$C/prepem/origin_lane_castle-1015/prep-em1a \
  em16=$P/prep-em16/em16.drs:$P/prep-em16 em1c=$P/prep-em1c/em1c.drs:$P/prep-em1c
mkdir -p $L/aica-cand $L/aica-cache
LAY=127936,253856,72544,264576,0,0,0,32736,1004192
for x in em1a:df0e4f984039090aad4bdcb11bb889b65ffaaec85100b29e85f2de174eafe165 em16:14b0a45036db25da30a1bddaebdc4c75907d078e3dc713451c077404ca33929e em1c:1c5ce248c877327f33c4a26ba60af52b8554be0a956d5adc20e4424cf462e52b; do
  n=${x%%:*}; sha=${x#*:}
  cp $L/ch4found/snd/aica-c4c/em/$n.drs $L/aica-cand/$n.drs
  ( cd /tmp && nice python3 $C/aica_search4k.py $L/tree/port/dreamcast/tools $L/aica-cand/$n.drs $sha $L/aica-cache $L/ch4found/snd/aica-c4c/em/$n.drs --layout $LAY 2>&1 | tail -2 )
  echo "$n $(sha256sum $L/ch4found/snd/aica-c4c/em/$n.drs | cut -c1-8) want ${sha:0:8}"
done
