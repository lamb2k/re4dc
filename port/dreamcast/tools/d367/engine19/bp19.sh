set -euo pipefail
# bp19.sh <arm label> [squeeze bytes frag] (WSL): engine19 console bench disc, after actorplan19 bp.sh: Test 18 line data
# (T17R_PAYLOAD + res18f + rc19 [RC19D = OCCL room files], then boss18g50) over the payload base tree, program overlays
# from the bench build. Scenes: 1 r101 cross, 2 r100 house, 3 r101 bell spot, 4 r103 farm. Output on ext4.
L=${1:?label}; SQB=${2:-}; SQF=${3:-0}
T=/root/work/lanes/engine19/port/dreamcast/tools/d367
K=/root/work/lanes/engine19-scratch/bench
S=/root/work/lanes/engine19-scratch/bench/scenes
O=/root/probe/lanes/route/out-$L
D=$K/disc-$L${SQB:+-sq$SQB-$SQF}
export RC19D=/root/re4data/private/rc19o2-20261019
export RE4DC_PAYLOAD_ROOT=/root/re4payload/t164-20261018
export PKG_SRC=$RE4DC_PAYLOAD_ROOT/tree
[ -s $O/re4dc-game.elf ] || { echo "no build $O" >&2; exit 1; }
[ ! -s $O/missing.txt ] || { echo "$L has missing symbols" >&2; exit 1; }
rm -rf "${D:?}"; mkdir -p $D/fix
DATA=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('f','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T17R_PAYLOAD+',res18f,rc19')")
python3 $T/test11/t11-fix.py e19xrP $D/pkg0.json --base payload --data $DATA > $D/fix.log
bash $T/ch2/ch2-gigante-g50.sh e19xrP $D/pkg1.json --base $D/pkg0.json --base-label e19xrP >> $D/fix.log
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
rc = [k for k in d['replace'] if k.endswith('room.r4rc')]
assert rc, 'no room files'
d.setdefault('provenance', {})['bench'] = 'engine19 bench disc: program overlays from %s (%d replaced); data T17R_PAYLOAD+res18f+rc19(OCCL)+boss18g50; %d room files' % (out, n, len(rc))
json.dump(d, open(dst, 'w'), indent=1)
print('program overlays from the bench build:', n, 'room files:', len(rc))
PY
PKG_K=$D python3 $T/test8/t8-pkgtree.py $L $D/pkg.json > $D/pkgtree.txt
tail -1 $D/pkgtree.txt | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 $D/pkgtree.txt; exit 1; }
{ [ -z "$SQB" ] || echo "squeeze $SQB $SQF"; tr -d '\r' < $S/scene1.txt; } > $D/fix/warp.txt
tr -d '\r' < $S/scene2.txt > $D/fix/bench2.txt
tr -d '\r' < $S/scene3.txt > $D/fix/bench3.txt
tr -d '\r' < $S/scene4.txt > $D/fix/bench4.txt
for f in $D/fix/*.txt; do [ $(stat -c %s $f) -lt 2048 ] || { echo "$f too long" >&2; exit 1; }; done
(cd $T && LAYOUT=standard TITLE="RE4DC WALL CHECK BENCH (NOT THE GAME)" PRODUCT=T0003 bash mkgdi.sh $O/re4dc-game.elf $D/pkgtree $D/gdemu $D/fix | tail -2)
rm -f $D/gdemu/IP.BIN
(cd $D/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin) > $D/gdemu-sha256.txt
rm -rf "${D:?}/pkgtree"
cat $D/gdemu-sha256.txt
echo "DISC $D/gdemu"
