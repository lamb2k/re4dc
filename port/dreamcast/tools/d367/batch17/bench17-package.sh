#!/bin/bash
# bench17-package.sh <variant> [label]  (WSL) lane batch17 console A/B disc: benchpub/bench-package.sh on the test 16 data
# (pkg-t16rcrP.json = T16_DATA, r101 = bake13 level 0, byte for byte) plus the batched r101 world as level 5
# (dc/native/r101/ps2-wv5.re4mesh + .r4sg, LOSTPART PASS). Program b17t16B = test 16 + bench knobs + WORLD_VERT=1.
# Scene 1 (warp.txt)  = the cross, `wvlevel 0`: the test 16 world.  Scene 2 (bench2.txt) = the same cross, `wvlevel 5`:
# the batched world. Each scene starts from a soft reset, so r101's world package is opened again with the scene's level.
set -euo pipefail
V=${1:?variant}; L=${2:-b17t16B}
B=/root/probe/lanes-20261016/batch17
T=$B/t16tree/port/dreamcast/tools/d367
VD="/mnt/c/Game Dev/Emulators/re4-assets-private/batch17-r101-20261016/$V"
K=$B/bench
O=/root/probe/lanes/route/out-$L
W1=${SMOKE:+5 15}; W1=${W1:-300 1200}
D=$K/disc-$L-$V${SMOKE:+-smoke}
[ -s $O/re4dc-game.elf ] || { echo "no build $O" >&2; exit 1; }
[ ! -s $O/missing.txt ] || { echo "$L has missing symbols" >&2; exit 1; }
grep -q ": PASS (" "$VD/LOSTPART.txt" || { echo "no LOSTPART PASS for $V" >&2; exit 1; }
rm -rf $D; mkdir -p $D/fix
python3 - /root/probe/lanes-20261016/t16rc/fix/pkg-t16rcrP.json "$O" "$D/pkg.json" "$VD" <<'PY'
import json, sys, hashlib
src, out, dst, vd = sys.argv[1:5]
d = json.load(open(src))
n = 0
for rel in list(d['replace']):
    base = rel.rsplit('/', 1)[-1]
    if rel.startswith('dc/') and rel.endswith('.ovl') and '/programs/candidate-route' in d['replace'][rel]:
        d['replace'][rel] = out + '/' + base; n += 1
for f in ('ps2-wv5.re4mesh', 'ps2-wv5.r4sg'):
    d['replace']['dc/native/r101/' + f] = vd + '/' + f
assert d['replace']['dc/native/r101/ps2-world.re4mesh'].endswith('crowd12-bake-20261015/r101-t13/ps2-world.re4mesh')
p = d.setdefault('provenance', {})
p['bench'] = 'lane batch17 console A/B disc: program overlays from %s (%d replaced); r101 level 5 = %s' % (out, n, vd)
json.dump(d, open(dst, 'w'), indent=1)
print('program overlays from the bench build:', n, '| r101 L0 =', d['replace']['dc/native/r101/ps2-world.re4mesh'])
PY
PKG_K=$D python3 /root/probe/lanes-20261011/test8/t8-pkgtree.py $L $D/pkg.json > $D/pkgtree.txt
tail -1 $D/pkgtree.txt | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 $D/pkgtree.txt; exit 1; }
# the two scenes: the benchmark cross (benchpub scene1) with the world level of each arm
S1=$T/benchpub/scene1-warp.txt
{ echo "name bench-r101-cross-t16"; echo "wvlevel 0"; tr -d '\r' < $S1 | grep -v -E '^(name|bench) '; echo "bench 1 $W1 CROSS TEST16"; } > $D/fix/warp.txt
{ echo "name bench-r101-cross-batched"; echo "wvlevel 5"; tr -d '\r' < $S1 | grep -v -E '^(name|bench) '; echo "bench 2 $W1 CROSS BATCHED"; } > $D/fix/bench2.txt
[ $(stat -c %s $D/fix/warp.txt) -lt 2048 ] && [ $(stat -c %s $D/fix/bench2.txt) -lt 2048 ]
TITLE="RE4DC BATCH A/B (NOT THE GAME)" PRODUCT=T0002 bash $T/mkgdi.sh $O/re4dc-game.elf $D/pkgtree $D/gdemu $D/fix | tail -2
head -c 256 $D/gdemu/IP.BIN | grep -aq "RE4DC BATCH A/B (NOT THE GAME)" || { echo "IP.BIN title missing" >&2; exit 1; }
rm -f $D/gdemu/IP.BIN
(cd $D/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin) > $D/gdemu-sha256.txt
rm -rf $D/pkgtree
cat $D/gdemu-sha256.txt
echo "DISC $D/gdemu"
