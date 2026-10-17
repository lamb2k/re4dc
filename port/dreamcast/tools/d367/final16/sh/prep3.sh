# prep3.sh <name> <hot.json>: em31 prepared with a hot audit (lane final16)
set -e
L=/root/probe/lanes-20261016/final16; TT=$L/tree/port/dreamcast/tools
cd $L/prepem; N=$1; H=$2
rm -rf $N
python3 $TT/prepare_enemy_motions.py --source src/em/em31.drs --output $N --hot-audit $H --textures tex-em31 > $N.log 2>&1 || python3 $TT/prepare_enemy_motions.py --source src/em/em31.drs --output $N --hot-audit $H --diagnostic-incomplete-prefetch --textures tex-em31 > $N.log 2>&1 || { tail -5 $N.log; exit 1; }
tail -c 300 $N.log; echo
python3 - $N/motion-residency-report.json <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
print('resident_body',r['resident_body_bytes'],'hot_payload',r['hot_payload_bytes'],'cold_reserve',r['cold_reserve_bytes'],'entries',len(r['entries']),'hot',sum(1 for e in r['entries'] if e['hot']))
PY
