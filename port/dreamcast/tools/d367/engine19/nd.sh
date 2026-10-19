set -euo pipefail
cd /root/work/lanes/engine19/port/dreamcast/tools/d367
for x in "$@"; do
  g=/root/probe/lanes-20261019/engine19/k/ev-$x.txt
  echo "== $x"
  python3 cast_gc.py $g --allow castgc/allow.tsv --not-drawn > /root/probe/lanes-20261019/engine19/k/nd-$x.txt 2>&1 || true
  grep -a "NOT-DRAWN\|never drawn\|not judged" /root/probe/lanes-20261019/engine19/k/nd-$x.txt || true
done
