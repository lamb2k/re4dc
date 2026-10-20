set -euo pipefail
# bp.sh <arm label> [squeeze bytes frag]  (WSL) actorplan19 bench disc: Test 18 line data (T17R_PAYLOAD + res18f, then
# boss18g50 on top) over the payload base tree, program overlays from the bench build, four scenes:
#   warp.txt  scene 1 r101 cross (benchpub scene1), bench2 r100 house (benchpub scene2),
#   bench3    r10b Del Lago (bench/definitive-2026-10 scene3), bench4 r103 farm (definitive scene4).
# Standard GD-ROM layout (mkgdi.sh LAYOUT=standard). Output: $K/disc-<label>[-sq..]/gdemu on ext4.
L=${1:?label}; SQB=${2:-}; SQF=${3:-0}
T=/root/work/lanes/actorplan19/tree/port/dreamcast/tools/d367
K=/root/work/lanes/actorplan19/bench
S=/root/work/lanes/actorplan19/k/scenes
O=/root/probe/lanes/route/out-$L
D=$K/disc-$L${SQB:+-sq$SQB-$SQF}
export RE4DC_PAYLOAD_ROOT=/root/re4payload/t164-20261018
export PKG_SRC=$RE4DC_PAYLOAD_ROOT/tree
[ -s $O/re4dc-game.elf ] || { echo "no build $O" >&2; exit 1; }
[ ! -s $O/missing.txt ] || { echo "$L has missing symbols" >&2; exit 1; }
rm -rf "${D:?}"; mkdir -p $D/fix
DATA=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('f','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T17R_PAYLOAD+',res18f')")
python3 $T/test11/t11-fix.py a9krP $D/pkg0.json --base payload --data $DATA > $D/fix.log
bash $T/ch2/ch2-gigante-g50.sh a9krP $D/pkg1.json --base $D/pkg0.json --base-label a9krP >> $D/fix.log
python3 - "$D/pkg1.json" "$O" "$D/pkg.json" <<'PY'
import json, sys
src, out, dst = sys.argv[1:4]
d = json.load(open(src))
n = 0
for rel in list(d['replace']):
    base = rel.rsplit('/', 1)[-1]
    if rel.startswith('dc/') and rel.endswith('.ovl') and '/candidate-route' in d['replace'][rel]:
        d['replace'][rel] = out + '/' + base; n += 1
left = [v for v in d['replace'].values() if isinstance(v, str) and 'candidate-route' in v]
assert not left, left[:3]
d.setdefault('provenance', {})['bench'] = 'actorplan19 bench disc: program overlays from %s (%d replaced); data T17R_PAYLOAD+res18f+boss18g50' % (out, n)
json.dump(d, open(dst, 'w'), indent=1)
print('program overlays from the bench build:', n)
PY
PKG_K=$D python3 $T/test8/t8-pkgtree.py $L $D/pkg.json > $D/pkgtree.txt
tail -1 $D/pkgtree.txt | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 $D/pkgtree.txt; exit 1; }
{ [ -z "$SQB" ] || echo "squeeze $SQB $SQF"; tr -d '\r' < $S/scene1.txt; } > $D/fix/warp.txt
tr -d '\r' < $S/scene2.txt > $D/fix/bench2.txt
tr -d '\r' < $S/scene3.txt > $D/fix/bench3.txt
tr -d '\r' < $S/scene4.txt > $D/fix/bench4.txt
for f in $D/fix/*.txt; do [ $(stat -c %s $f) -lt 2048 ] || { echo "$f too long" >&2; exit 1; }; done
(cd $T && LAYOUT=standard TITLE="RE4DC ACTOR PLAN BENCH (NOT THE GAME)" PRODUCT=T0003 bash mkgdi.sh $O/re4dc-game.elf $D/pkgtree $D/gdemu $D/fix | tail -2)
rm -f $D/gdemu/IP.BIN
(cd $D/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin) > $D/gdemu-sha256.txt
rm -rf "${D:?}/pkgtree"
cat $D/gdemu-sha256.txt
echo "DISC $D/gdemu"
