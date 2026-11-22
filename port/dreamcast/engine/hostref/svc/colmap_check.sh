#!/bin/bash
# colmap_check.sh (lane eng-skel2): the map entry (services/collision col_map_floor: the floor or slope polygon under a
# point, from the baked floor group) against src/Sscrn/ss_map.cpp mapPositionCheck's search run with the original
# At_poly_line_ck on the unbaked SAT file 0 (svc/colb_host.cpp RE4_COLMAP). Run it in WSL.
#
#   RE4_TREE=<converted data tree> colmap_check.sh <out dir> [fixture ...]
#
# For each fixture (default: e1-route, door103-walk, hill-ashley, bell-ganado, square-follow) the native build plays it
# once (the points: Leon's position every tick, and every model the collision checks, col.txt), then the check runs at
# the room load: those points and a 48 x 48 grid over the floor group, SEck 0 and 1 (the attribute filter both ways):
# the same polygon, hit point and three vertices to the bit, or the same miss. Rows:
#   <fixture>          every point as the original's search (mismatches 0)
#   <fixture>-control  RE4_COLMAP_CONTROL=1 (the entry reports v[1] and v[2] swapped): must FAIL (mismatches > 0)
#   loop               the copied search loop is ss_map.cpp's, line for line (whitespace aside)
# Exit 0 when every row ends as it must; the table also goes to <out dir>/colmap_check.md.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
ROOT=$(git -C "$here" rev-parse --show-toplevel)
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
PR=$ROOT/port/dreamcast/tools/plays_right
TREE=${RE4_TREE:?RE4_TREE=<converted data tree>}
OUT=$1; shift
FXS=("$@"); [ ${#FXS[@]} -eq 0 ] && FXS=(e1-route door103-walk hill-ashley bell-ganado square-follow)
mkdir -p "$OUT"
rows=(); bad=0
row() { rows+=("| $1 | $2 | $3 | $4 |"); [ "$3" = "$2" ] || bad=1; }
for fx in "${FXS[@]}"; do
  d=$OUT/$fx; mkdir -p "$d"
  RE4_SVC_OUT="$d" RE4_SVC_CLOTH_WIND=0 "$B/native/re4ref" --tree "$TREE" --fixture "$PR/fixtures/$fx.txt" \
    --out "$d/trace.txt" --log "$d/run.log" > "$d/play.txt" 2>&1
  python3 - "$d/trace.txt" "$d/col.txt" > "$d/points.txt" <<'PY'
import re, sys
pts = set()
for line in open(sys.argv[1]):
    m = re.match(r'T t=\d+ .*? p=([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8})', line)
    if m: pts.add(m.groups())
try:
    for line in open(sys.argv[2]):
        m = re.search(r' [CA]\S* \d+ ([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8})', line)
        if m: pts.add(m.groups())
except OSError:
    pass
for p in sorted(pts): print(*p)
PY
  for arm in plain control; do
    rm -f "$d/colmap-$arm.txt"
    ctl=0; [ $arm = control ] && ctl=1
    RE4_COLMAP="$d/colmap-$arm.txt" RE4_COLMAP_POINTS="$d/points.txt" RE4_COLMAP_CONTROL=$ctl RE4_SVC_CLOTH_WIND=0 \
      "$B/native/re4ref" --tree "$TREE" --fixture "$PR/fixtures/$fx.txt" --out /dev/null --log /dev/null > /dev/null 2>&1
    line=$(grep -h "^COLMAP room" "$d/colmap-$arm.txt" 2>/dev/null | tail -1)
    mm=$(echo "$line" | sed -n 's/.*mismatches \([0-9]*\).*/\1/p')
    got=FAIL; [ -n "$mm" ] && [ "$mm" = 0 ] && got=PASS
    if [ $arm = plain ]; then row "$fx" PASS $got "${line#COLMAP }"; else row "$fx-control" FAIL $got "${line#COLMAP }"; fi
  done
done
# the copied loop against the original's lines
python3 - "$ROOT/src/Sscrn/ss_map.cpp" "$here/colb_host.cpp" > "$OUT/loop.txt" <<'PY'
import sys
def block(path):
    L = [l.strip() for l in open(path)]
    i = L.index('poly = satB.poly_p;')
    return L[i:i + 10]
a, b = block(sys.argv[1]), block(sys.argv[2])
print('\n'.join(a)); print('---'); print('\n'.join(b))
print('SAME' if a == b else 'DIFFERENT')
PY
lr=$(tail -1 "$OUT/loop.txt"); got=FAIL; [ "$lr" = SAME ] && got=PASS
row loop PASS $got "ss_map.cpp's search loop and colb_host.cpp map_ref's: $lr"
{
  echo "| row | must | got | detail |"; echo "|---|---|---|---|"
  printf '%s\n' "${rows[@]}"
} | tee "$OUT/colmap_check.md"
[ $bad = 0 ] && echo "colmap_check: every row as it must" || echo "colmap_check: a row is not as it must"
exit $bad
