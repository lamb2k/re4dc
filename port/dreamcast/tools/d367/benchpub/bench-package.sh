#!/bin/bash
# bench-package.sh <arm label> [squeeze bytes frag]   (WSL; tools/d367/benchpub) masters the public benchmark disc.
# Release build rule 3: the disc tree and the GDI are built on WSL ext4 ($K) and cross to C: once.
#   data   the test release's data set (pkg json of $BASE's label, t11-fix.py --data ...), with the five program
#          overlays the json takes from the release program replaced by this arm's (overlays are linked to their ELF)
#   dc/    warp.txt = scene1-warp.txt, bench<n>.txt = scene<n>-warp.txt, n = 2, 3, ... (3 = r10b Del Lago) (a squeeze level, if given, is prepended to
#          warp.txt for the KOS_SQUEEZE twin's gate disc)
#   IP.BIN title "RE4DC BENCHMARK (NOT THE GAME)", product T0002 (not the game's T0000)
# Output: $K/disc-<label>[-sq<bytes>-<frag>]/gdemu (disc.gdi, track01.bin, track02.raw, track03.bin) + gdemu-sha256.txt.
# Env: K (work dir, default /root/probe/bench-public), PKG_JSON (default the 12.1 package json).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
L=${1:?arm label}; SQB=${2:-}; SQF=${3:-0}
K=${K:-/root/probe/bench-public}
O=/root/probe/lanes/route/out-$L
PKG_JSON=${PKG_JSON:-/root/probe/t12dark/rel/fix/pkg-t121tP.json}
D=$K/disc-$L${SQB:+-sq$SQB-$SQF}
[ -s $O/re4dc-game.elf ] || { echo "no build $O" >&2; exit 1; }
[ ! -s $O/missing.txt ] || { echo "$L has missing symbols" >&2; cat $O/missing.txt >&2; exit 1; }
rm -rf $D; mkdir -p $D/fix
python3 - "$PKG_JSON" "$O" "$D/pkg.json" <<'PY'
import json, sys
src, out, dst = sys.argv[1:4]
d = json.load(open(src))
n = 0
for rel in list(d['replace']):
    base = rel.rsplit('/', 1)[-1]
    if rel.startswith('dc/') and rel.endswith('.ovl') and '/programs/candidate-route' in d['replace'][rel]:
        d['replace'][rel] = out + '/' + base; n += 1
d.setdefault('provenance', {})['bench'] = 'public benchmark disc: program overlays from %s (%d replaced)' % (out, n)
json.dump(d, open(dst, 'w'), indent=1)
print('program overlays from the bench build:', n)
PY
PKG_K=$D python3 /root/probe/lanes-20261011/test8/t8-pkgtree.py $L $D/pkg.json > $D/pkgtree.txt
tail -1 $D/pkgtree.txt | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 $D/pkgtree.txt; exit 1; }
{ [ -z "$SQB" ] || echo "squeeze $SQB $SQF"; tr -d '\r' < $here/scene1-warp.txt; } > $D/fix/warp.txt
n=2
while [ -s $here/scene$n-warp.txt ]; do
  tr -d '\r' < $here/scene$n-warp.txt > $D/fix/bench$n.txt
  [ $(stat -c %s $D/fix/bench$n.txt) -lt 2048 ] || { echo "scene$n-warp.txt is 2048 B or more" >&2; exit 1; }
  n=$((n+1))
done
[ $(stat -c %s $D/fix/warp.txt) -lt 2048 ]
# QA_LINK=1 programs (lane link28): dial the DreamPi at the first tick (no QA menu on this disc); harmless without a line
echo 'auto 1' > $D/fix/link.txt
TITLE="RE4DC BENCHMARK (NOT THE GAME)" PRODUCT=T0002 bash $here/../mkgdi.sh $O/re4dc-game.elf $D/pkgtree $D/gdemu $D/fix | tail -2
head -c 256 $D/gdemu/IP.BIN | grep -aq "RE4DC BENCHMARK (NOT THE GAME)" || { echo "IP.BIN title missing" >&2; exit 1; }
rm -f $D/gdemu/IP.BIN
(cd $D/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin) > $D/gdemu-sha256.txt
rm -rf $D/pkgtree
cat $D/gdemu-sha256.txt
echo "DISC $D/gdemu"
