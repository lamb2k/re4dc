#!/bin/bash
# prepc.sh <out-prefix> <hot.json> <E>: prepare an island enemy with streamed motions (the lane tool's MOTION_SMALL contract)
L=/root/probe/lanes-20261016/ch5found; P=$L/prepem; TT=$L/tree/port/dreamcast/tools
O=$1; H=$2; E=$3
cd $P; rm -rf $O-$E
python3 $TT/prepare_enemy_motions.py --source src/em/$E.drs --output $O-$E --hot-audit $H --diagnostic-incomplete-prefetch --textures tex-$E > $O-$E.log 2>&1 || { tail -4 $O-$E.log; exit 1; }
tail -1 $O-$E.log
python3 - $O-$E/motion-residency-report.json <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
print('resident_body',r['resident_body_bytes'],'hot_payload',r['hot_payload_bytes'],'cold_reserve',r['cold_reserve_bytes'],'entries',len(r['entries']),'hot',sum(1 for e in r['entries'] if e['hot']))
PY
sha256sum $O-$E/$E.drs | cut -c1-16
