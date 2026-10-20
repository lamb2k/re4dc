set -euo pipefail
# bp.sh <arm label> (WSL; lane scenery19, after engine19 bp19.sh): console bench disc. Test 18 line data (T17R_PAYLOAD +
# res18f + rc19 [RC19D = rc19s: OCCL + SCDD room files], then boss18g50) over the payload base tree, program overlays
# from the bench build. Scenes: 1 r101 cross, 2 r100 house, 3 r101 bell spot, 4 r103 farm (explore), 5 r103 farm fight.
L=${1:?label}
T=/root/work/lanes/scenery19/port/dreamcast/tools/d367
K=/root/work/lanes/scenery19-scratch/bench
S=$T/scenery19/bench/scenes
O=/root/probe/lanes/route/out-$L
D=$K/disc-$L
export RC19D=/root/re4data/private/rc19s-20261019
export RE4DC_PROGRAMS_DIR="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/programs"
PL=${PL:-h5krP}   # a registered program label for the data fixture (its overlays are replaced by the bench build's)
export RE4DC_PAYLOAD_ROOT=/root/re4payload/t164-20261018
export PKG_SRC=$RE4DC_PAYLOAD_ROOT/tree
[ -s $O/re4dc-game.elf ] || { echo "no build $O" >&2; exit 1; }
# Allowed: _re4dc_disc_meter_totals only. With DISC_READ_METER=1 and DOOR_PROBE=0, platform/door_probe.o is linked
# although the Makefile's filter-out means to drop it, and its unguarded reference stays unresolved. Its callers are
# the DOOR_PROBE hooks, which are compiled out, so the stub is never reached (reported to the coordinator 10-19).
if [ -s $O/missing.txt ] && [ "$(tr -d '\n' < $O/missing.txt)" != "_re4dc_disc_meter_totals" ]; then
  echo "$L has missing symbols: $(cat $O/missing.txt)" >&2; exit 1; fi
rm -rf "${D:?}"; mkdir -p $D/fix
DATA=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('f','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T17R_PAYLOAD+',res18f,rc19')")
python3 $T/test11/t11-fix.py $PL $D/pkg0.json --base payload --data $DATA > $D/fix.log
bash $T/ch2/ch2-gigante-g50.sh $PL $D/pkg1.json --base $D/pkg0.json --base-label $PL >> $D/fix.log
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
d.setdefault('provenance', {})['bench'] = 'scenery19 bench disc: program overlays from %s (%d replaced); data T17R_PAYLOAD+res18f+rc19(rc19s: OCCL+SCDD)+boss18g50; %d room files' % (out, n, len(rc))
json.dump(d, open(dst, 'w'), indent=1)
print('program overlays from the bench build:', n, 'room files:', len(rc))
PY
PKG_K=$D python3 $T/test8/t8-pkgtree.py $L $D/pkg.json > $D/pkgtree.txt
tail -1 $D/pkgtree.txt | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 $D/pkgtree.txt; exit 1; }
tr -d '\r' < $S/scene1.txt > $D/fix/warp.txt
for i in 2 3 4 5; do tr -d '\r' < $S/scene$i.txt > $D/fix/bench$i.txt; done
for f in $D/fix/*.txt; do [ $(stat -c %s $f) -lt 2048 ] || { echo "$f too long" >&2; exit 1; }; done
(cd $T && LAYOUT=standard TITLE="RE4DC SCENERY BENCH (NOT THE GAME)" PRODUCT=T0003 bash mkgdi.sh $O/re4dc-game.elf $D/pkgtree $D/gdemu $D/fix | tail -2)
rm -f $D/gdemu/IP.BIN
(cd $D/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin) > $D/gdemu-sha256.txt
rm -rf "${D:?}/pkgtree"
cat $D/gdemu-sha256.txt
echo "DISC $D/gdemu"
