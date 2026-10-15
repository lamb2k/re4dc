#!/bin/bash
# strict-all.sh (WSL): i-strict.sh for every finished <name>-c / <name>-i trace pair not yet compared; appends to strict/summary.txt
E=/mnt/c/Flycast-Evidence/re4-dreamcast/items-20261014
cd $E/_tools
for n in sq101 h2 wi119 wi105 wi106 wi103 wi108 wi118 wi10a wi10b wi11a wi11b wi117 wi102 wi104 wi107 wi109; do
  [ -f $E/$n-c/capture/run-output.txt ] && [ -f $E/$n-i/capture/run-output.txt ] || continue
  grep -q "^== $n " $E/strict/summary.txt 2>/dev/null && continue
  mkdir -p $E/strict
  { echo "== $n $(date +%T)"; bash i-strict.sh $n-c $n-i $n 2>&1; } >> $E/strict/summary.txt
done
