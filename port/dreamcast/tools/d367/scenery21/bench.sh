set -euo pipefail
# bench.sh [label] (WSL; lane cache20, after logiclod20/bench.sh): the cache20 console bench disc of the release recipe
# (rr/recipe.conf over t15-build.sh), ONE program with both arms: the start screen's D-pad picks the arm (LEFT A = as
# shipped, RIGHT B = GAME_SHZ_MEMSET + SQ_OUT + PREF_WALK on: re4dc_cache20_mask). Census rows (BENCH_CENSUS=1):
# scenes/fileN.txt are the fixture files (file1 = warp.txt, fileN = benchN.txt), each with one or more `bench` rows.
# Output: /root/work/lanes/scenery21-scratch/bench/disc-<label>/gdemu + gdemu-sha256.txt.
L=${1:-c20bW}
TR=/root/work/lanes/scenery21
T=$TR/port/dreamcast/tools/d367
S=$T/cache20/scenes
K=/root/work/lanes/scenery21-scratch/bench; mkdir -p "$K"
export SOURCE_DATE_EPOCH=1760000000
ID=$(git -C $TR rev-parse --short=8 HEAD)
NF=$(ls $S/file*.txt | wc -l)
NR=$(cat $S/file*.txt | grep -c '^bench ')
BW="DBG_WARP=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 BENCHMARK=1 BENCH_ID=$ID ARENA_FIT_KOS_BYTES=262144 BENCH_SCENES=$NR BENCH_FILES=$NF PC_SAMPLER=0 PACE_VMU_GPU=1 TAIL_METER=1 BENCH_CENSUS=1 RIGID_CENSUS=2 MIST_CUT=239"
LEVERS="SCENERY_PIECE_STATE=1 SCENERY21_AB=1"
L0=${L%W}
eval "$(grep '^CH2=' $T/rr/recipe.conf)"
(cd $TR && git submodule update --init -q port/dreamcast/game/third_party/sh4zam)
K=/root/work/lanes/scenery21-scratch/k T=$TR LP=$L0 CH2="$CH2 $LEVERS" XON="$BW" bash $T/ch2/ch2-build.sh rW | grep '^rc=' | cut -c1-90
K=/root/work/lanes/scenery21-scratch/bench
O=/root/probe/lanes/route/out-${L0}rW
D=$K/disc-$L
export RC19D=/root/re4data/private/rc19s-20261019
export RE4DC_PROGRAMS_DIR="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/programs"
export RE4DC_PAYLOAD_ROOT=/root/re4payload/t164-20261018
export PKG_SRC=$RE4DC_PAYLOAD_ROOT/tree
[ -s $O/re4dc-game.elf ] || { echo "no build $O" >&2; exit 1; }
[ ! -s $O/missing.txt ] || { echo "$L has missing symbols: $(cat $O/missing.txt)" >&2; exit 1; }
rm -rf "${D:?}"; mkdir -p $D/fix
eval "$(grep '^DATA=' $T/rr/recipe.conf)"
python3 $T/test11/t11-fix.py ${L0}rW $D/pkg0.json --base payload --data "$DATA" > $D/fix.log
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
d.setdefault('provenance', {})['bench'] = 'scenery21 A/B bench disc: overlays from %s (%d)' % (out, n)
json.dump(d, open(dst, 'w'), indent=1)
print('overlays from the bench build:', n)
import os
SC='/root/re4data/private/sc21-20261020'
m = 0
for r in ('r100', 'r101', 'r103', 'r10b', 'r11b'):   # the bench rooms: arm B reads dc/native/<room>/sc21/
    for f in ('ps2-world.re4mesh', 'ps2-world.r4sg', 'room.r4rc'):
        d['replace']['dc/native/%s/sc21/%s' % (r, f)] = '%s/%s/%s' % (SC, r, f); m += 1
d['provenance']['bench'] += '; scenery21 arm B files: %d' % m
json.dump(d, open(dst, 'w'), indent=1)
print('sc21 arm B files:', m)
PY
PKG_K=$D python3 $T/test8/t8-pkgtree.py ${L0}rW $D/pkg.json > $D/pkgtree.txt
tail -1 $D/pkgtree.txt | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 $D/pkgtree.txt; exit 1; }
tr -d '\r' < $S/file1.txt > $D/fix/warp.txt
for i in $(seq 2 $NF); do tr -d '\r' < $S/file$i.txt > $D/fix/bench$i.txt; done
for f in $D/fix/*.txt; do [ $(stat -c %s $f) -lt 4000 ] || { echo "fixture too long $f"; exit 1; }; done
(cd $T && LAYOUT=standard TITLE="RE4DC SCENERY21 AB BENCH (NOT THE GAME)" PRODUCT=T0004 bash mkgdi.sh $O/re4dc-game.elf $D/pkgtree $D/gdemu $D/fix | tail -2)
rm -f $D/gdemu/IP.BIN
(cd $D/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin) > $D/gdemu-sha256.txt
rm -rf "${D:?}/pkgtree"
cat $D/gdemu-sha256.txt
echo "DISC $D/gdemu rows=$NR files=$NF id=$ID"
