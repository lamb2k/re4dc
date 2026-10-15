#!/bin/bash
# poc-devbase.sh <arm label> <windows outdir>   (WSL; tools/d367/poc101)
# A full-play-style BASE (fp_master.sh) of a POC101 build for development Flycast checks: one row per run, each run
# <= 60 s (user rule), its fixture written into track 1 by fp_run.py --base --warp. The game data is the POC disc's own
# (bench-package.sh: the test 14 package + this build's overlays); the bench fixtures are taken off the tree, so a run
# measures only the scene of its --warp fixture and then shows the results pages.
# Env: K (work dir, default /root/probe/lanes-20261015/poc101-work), PKG_JSON (default the test 14 package json).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
L=${1:?arm label}; OUTW=${2:?windows outdir (/mnt/c/...)}
K=${K:-/root/probe/lanes-20261015/poc101-work}
export K PKG_JSON=${PKG_JSON:-/root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json}
F=$K/devfix-$L; rm -rf $F; mkdir -p $F
printf 'name poc-devbase\nroom 0x101\n' > $F/warp.txt
FIXDIR=$F FIXTAG=dev bash $here/../benchpub/bench-package.sh $L > $K/devbase-$L.log 2>&1 || { tail -20 $K/devbase-$L.log; exit 1; }
D=$K/disc-$L-dev
B=$K/devbase-$L; rm -rf $B; mkdir -p $B
python3 $here/../fullplay/fp_iso.py extract $D/gdemu/track03.bin $B/tree --manifest $B/manifest-disc.json --ipbin $B/IP.BIN > /dev/null
rm -f $B/tree/dc/warp.txt $B/tree/dc/bench*.txt
python3 - $B/manifest-disc.json $B/manifest.json <<'PY'
import json, sys, re
d = json.load(open(sys.argv[1]))
files = d['files'] if isinstance(d, dict) and 'files' in d else d
drop = [k for k in files if re.fullmatch(r'dc/(warp|bench\d+)\.txt', k.lstrip('/'))]
for k in drop: del files[k]
json.dump(d, open(sys.argv[2], 'w'), indent=1)
print('fixtures dropped from the manifest:', drop)
PY
rm -rf $D
bash $here/../fullplay/fp_master.sh $B/tree $B/manifest.json $B/IP.BIN "$OUTW"
cp /root/probe/lanes/route/out-$L/syms.txt "$OUTW/syms.txt"
echo "DEVBASE $OUTW"
