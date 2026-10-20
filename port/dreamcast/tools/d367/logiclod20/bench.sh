set -euo pipefail
# bench.sh <A|B> (WSL; lane logiclod20, after scenery19 bench/bb.sh + bp.sh): console bench disc of the Test 19.1 recipe,
# five scenes (BENCH_SCENES=5): 1 r101 cross, 2 r100 house, 3 r101 bell spot, 4 r103 farm, 5 r103 farm fight.
# A = recipe; B = recipe + LOGIC_LOD_EM=2 LOGIC_APPROX_MASK=0x01 (GAME_TRIG_FSCA dropped: +3 ms actor drawing).
ARM=${1:?A or B}
TR=/root/work/lanes/logiclod20
T=$TR/port/dreamcast/tools/d367
S=$T/logiclod20/scenes
K=/root/work/lanes/logiclod20-scratch/bench; mkdir -p "$K"
export SOURCE_DATE_EPOCH=1760000000
ID=$(git -C $TR rev-parse --short=8 HEAD)
BW="DBG_WARP=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 BENCHMARK=1 BENCH_ID=$ID ARENA_FIT_KOS_BYTES=262144 BENCH_SCENES=5"
case $ARM in
  A) X="" ;;
  B) X="LOGIC_LOD_EM=2 LOGIC_APPROX_MASK=0x01" ;;
  *) echo "arm?"; exit 2 ;;
esac
L=ll20b$ARM
XON="$BW" bash $T/logiclod20/b.sh $L rP $X | tail -1 | cut -c1-80
O=/root/probe/lanes/route/out-${L}rP
D=$K/disc-$L
export RC19D=/root/re4data/private/rc19s-20261019
export RE4DC_PROGRAMS_DIR="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/programs"
export RE4DC_PAYLOAD_ROOT=/root/re4payload/t164-20261018
export PKG_SRC=$RE4DC_PAYLOAD_ROOT/tree
[ -s $O/re4dc-game.elf ] || { echo "no build $O" >&2; exit 1; }
if [ -s $O/missing.txt ] && [ "$(tr -d '\n' < $O/missing.txt)" != "_re4dc_disc_meter_totals" ]; then
  echo "$L has missing symbols: $(cat $O/missing.txt)" >&2; exit 1; fi
rm -rf "${D:?}"; mkdir -p $D/fix
eval "$(grep '^DATA=' $T/rr/recipe.conf)"
python3 $T/test11/t11-fix.py ${L}rP $D/pkg0.json --base payload --data "$DATA" > $D/fix.log
python3 - "$D/pkg0.json" "$O" "$D/pkg.json" <<'PY'
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
d.setdefault('provenance', {})['bench'] = 'logiclod20 bench disc: overlays from %s (%d)' % (out, n)
json.dump(d, open(dst, 'w'), indent=1)
print('overlays from the bench build:', n)
PY
PKG_K=$D python3 $T/test8/t8-pkgtree.py ${L}rP $D/pkg.json > $D/pkgtree.txt
tail -1 $D/pkgtree.txt | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 $D/pkgtree.txt; exit 1; }
tr -d '\r' < $S/scene1.txt > $D/fix/warp.txt
for i in 2 3 4 5; do tr -d '\r' < $S/scene$i.txt > $D/fix/bench$i.txt; done
(cd $T && LAYOUT=standard TITLE="RE4DC LOGIC LOD BENCH $ARM (NOT THE GAME)" PRODUCT=T0003 bash mkgdi.sh $O/re4dc-game.elf $D/pkgtree $D/gdemu $D/fix | tail -2)
rm -f $D/gdemu/IP.BIN
(cd $D/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin) > $D/gdemu-sha256.txt
rm -rf "${D:?}/pkgtree"
cat $D/gdemu-sha256.txt
echo "DISC $D/gdemu"
