set -euo pipefail
# bx.sh <room> <st dir>: breakables (box ETM geometry + debris/pickups pack) on the props24p tree. lane purge-props24
r=${1:?}; sd=${2:-st1}
T=/root/work/lanes/purge-props24/port/dreamcast/tools; S=/root/work/lanes/purge-props24-scratch
O=$S/b; mkdir -p $O
BRK=et0100.bin,et0200.bin,et1100.bin,et1200.bin,et1e00.bin,et1f00.bin,et2d00.bin,et2e00.bin,et2e01.bin,et2f00.bin,et2f01.bin,et3c00.bin
cd $T
python3 ps2_objects.py room --dar ${IN:-$S/candp/tree/$sd/$r.dar} --room $r --etm $BRK --keep-larger --out $O/$r-g.dar --json $O/$r-g.json | grep -v "^etc  *et[0-9a-f]*\.bin *tris None" || true
if [ "${PACK:-1}" = 1 ]; then
python3 ps2_items.py pack --dar $O/$r-g.dar --room $r --lib $S/lib --out $O/$r-t.dar --json $O/$r-t.json --classes items,breakables 2>&1 | tail -2
else cp $O/$r-g.dar $O/$r-t.dar; fi
