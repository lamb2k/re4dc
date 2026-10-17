#!/bin/bash
# round 3 VRAM: resident lists for r329 / r31d / r327 from the round 2 logs (first-sight loads incl. the effect
# textures the thrash guard skipped), the r311 / r327 material pair added to the island pak, resident-ch5b.bin.
set -e
L=/root/probe/lanes-20261016/ch5found
T=$L/tree/port/dreamcast/tools/d367
R=$T/vram/resident
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016
for r in 329 31d 327; do
  logs=$(ls $E/h-cx5cmW/scenarios/cx-r$r-*/capture/run-output.txt $E/h-cx5vmW/scenarios/cx-r$r-*/capture/run-output.txt 2>/dev/null || true)
  before=$(($(wc -l < $R/r$r.tsv) - 1))
  python3 $T/vram/resident_keys.py list $r $R/r$r.tsv $logs | tail -1
  echo "r$r: $before -> $(($(wc -l < $R/r$r.tsv) - 1)) keys"
done
python3 /mnt/c/tmp/ch5/pakadd.py $L/vram/tex-ch5b.pak $L/vram/tex-ch5.pak $L/pairs-c5/*.re4tex
python3 $T/texpack.py --verify $L/vram/tex-ch5b.pak
python3 $T/vram/resident_keys.py pack $L/vram/resident-ch5b.bin $R/r000.tsv $R/r3*.tsv | tail -1
sha256sum $L/vram/tex-ch5b.pak $L/vram/resident-ch5b.bin | cut -c1-16,65-
