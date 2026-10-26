#!/bin/bash
# gen26.sh (lane windows26, 2026-10-26): window panes back in the seven window rooms, member by member, on top of the
# current room archives. PS2 draws no intact pane (PS2 et0000 / et2500 are one degenerate triangle and the PS2
# Et00_init loads them exactly as GC); the user requires glass and bars, so the GC panes return (GC-ASSET allowlist):
#   ETM et0000.bin / et2500.bin  <- le_mirror(GC)            (ps2_objects.py --etm-restore-gc; was emptied by gen24 EMP)
#   ETM et0000.tpl (5 rooms)     <- the GC package record     (--etm-member-from, r100's record; T24 put the PS2 64x16
#                                                              frame-wood picture there, which the pane cannot use)
# Everything else in each archive is unchanged except the NTR / ESQ rebases ps2_objects.py does.
#   BASE=<tree with st1/*.dar> OUT=<dir> bash gen26.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
B=${BASE:?BASE tree}; O=${OUT:?OUT dir}
mkdir -p "$O/st1"
for r in r100 r101 r105 r107 r111 r11c r11f; do
  case $r in r101|r105|r111) M=et0000.bin,et2500.bin;; *) M=et0000.bin;; esac
  X=()
  case $r in r105|r107|r111|r11c|r11f) X=(--etm-member-from "et0000.tpl=$B/st1/r100.dar");; esac
  python3 ps2_objects.py room --dar "$B/st1/$r.dar" --room "$r" --etm "$M" --etm-restore-gc "$M" "${X[@]}" \
    --out "$O/st1/$r.dar" --json "$O/$r.json"
done
