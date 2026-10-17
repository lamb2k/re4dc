#!/bin/bash
# ab-package.sh [label]  (WSL) lane actorplan17 console A/B disc: benchpub/bench-package.sh's steps on the test 16 data
# (pkg-t16rcrP.json = T16_DATA, byte for byte) with program ap17t16B (test 16 + bench knobs + ACTOR_PLAN=1
# ACTOR_PLAN_AB=1). One image, four scenes, each from a soft reset:
#   scene 1 (warp.txt)   = the benchmark r101 cross (benchpub scene 1), `actorplan 0`: every proof as in test 16
#   scene 2 (bench2.txt) = the same cross, `actorplan 1`: the character draw plan's reuses on
#   scene 3 (bench3.txt) = the r103 farm wide view (benchmark Part 2 "A230": Leon by the r106 door looking back over the
#                          farm, 5 Ganados, god, no pad input), `actorplan 0`
#   scene 4 (bench4.txt) = the same farm view, `actorplan 1`
# Windows: room frames 300..1200 (30 s of game time) in every scene. SMOKE=1: 5..15 (a Flycast smoke of the disc).
set -euo pipefail
L=${1:-ap17t16B}
A=/root/probe/lanes-20261016/actorplan17
T=$A/t16tree/port/dreamcast/tools/d367
K=$A/bench
O=/root/probe/lanes/route/out-$L
W1=${SMOKE:+5 15}; W1=${W1:-300 1200}
D=$K/disc-$L${SMOKE:+-smoke}
[ -s $O/re4dc-game.elf ] || { echo "no build $O" >&2; exit 1; }
[ ! -s $O/missing.txt ] || { echo "$L has missing symbols" >&2; exit 1; }
rm -rf $D; mkdir -p $D/fix
python3 - /root/probe/lanes-20261016/t16rc/fix/pkg-t16rcrP.json "$O" "$D/pkg.json" <<'PY'
import json, sys
src, out, dst = sys.argv[1:4]
d = json.load(open(src))
n = 0
for rel in list(d['replace']):
    base = rel.rsplit('/', 1)[-1]
    if rel.startswith('dc/') and rel.endswith('.ovl') and '/programs/candidate-route' in d['replace'][rel]:
        d['replace'][rel] = out + '/' + base; n += 1
p = d.setdefault('provenance', {})
p['bench'] = 'lane actorplan17 console A/B disc: program overlays from %s (%d replaced); data = test 16 (pkg-t16rcrP)' % (out, n)
json.dump(d, open(dst, 'w'), indent=1)
print('program overlays from the bench build:', n)
PY
PKG_K=$D python3 /root/probe/lanes-20261011/test8/t8-pkgtree.py $L $D/pkg.json > $D/pkgtree.txt
tail -1 $D/pkgtree.txt | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 $D/pkgtree.txt; exit 1; }
S1=$T/benchpub/scene1-warp.txt
FARM=$T/actorplan/farm-warp.txt
cross() { echo "name bench-r101-cross-plan$1"; echo "actorplan $1"; tr -d '\r' < $S1 | grep -v -E '^(name|bench) '; echo "bench $2 $W1 $3"; }
farm()  { echo "name bench-r103-farm-plan$1"; echo "actorplan $1"; tr -d '\r' < $FARM | grep -v -E '^(name|bench) '; echo "bench $2 $W1 $3"; }
cross 0 1 "CROSS OFF" > $D/fix/warp.txt
cross 1 2 "CROSS ON"  > $D/fix/bench2.txt
farm 0 3 "FARM OFF"   > $D/fix/bench3.txt
farm 1 4 "FARM ON"    > $D/fix/bench4.txt
for f in $D/fix/*.txt; do [ $(stat -c %s $f) -lt 2048 ] || { echo "$f too long" >&2; exit 1; }; done
TITLE="RE4DC ACTOR PLAN A/B (NOT THE GAME)" PRODUCT=T0003 bash $T/mkgdi.sh $O/re4dc-game.elf $D/pkgtree $D/gdemu $D/fix | tail -2
head -c 256 $D/gdemu/IP.BIN | grep -aq "RE4DC ACTOR PLAN A/B (NOT THE GAME)" || { echo "IP.BIN title missing" >&2; exit 1; }
rm -f $D/gdemu/IP.BIN
(cd $D/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin) > $D/gdemu-sha256.txt
rm -rf $D/pkgtree
cat $D/gdemu-sha256.txt
echo "DISC $D/gdemu"
