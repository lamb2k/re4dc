set -euo pipefail
# cg.sh <evidence names...>: CAST-GC (+ NOT-DRAWN), TEXCHK, cull counts per run
cd /root/work/lanes/engine19/port/dreamcast/tools/d367
E=/mnt/c/Flycast-Evidence/re4-dreamcast/engine19-20261019
K=/root/probe/lanes-20261019/engine19/k
for x in "$@"; do
  g=$K/ev-$x.txt
  tr -d '\0' < $E/$x/capture/run-output.txt > $g
  echo "== $x hides=$(grep -ac 'ENEMYVIS hide' $g || true) $(grep -a INVISPCO $g | tail -1 | grep -o 'skipped=[0-9]*' || true)"
  timeout 300 python3 cast_gc.py $g --allow castgc/allow.tsv 2>&1 | tail -4 || true
  timeout 300 bash texchk/texchk.sh $g 2>&1 | grep -o 'TEXCHK [A-Z]*' | tail -1 || true
done
