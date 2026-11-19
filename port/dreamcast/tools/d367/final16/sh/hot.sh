set -e
L=/root/probe/lanes-20261016/final16; M=$L/tree/port/dreamcast/tools/d367/motion
E=/mnt/c/Flycast-Evidence/re4-dreamcast/final16-20261016
R=""
for f in $E/h-f*/scenarios/cx-r332-fight-*/capture/run-output.txt; do grep -q "motion miss #.*archive=1452032" $f && R="$R $f" && echo "run $f"; done
python3 $M/motion_hot.py $L/prepem/prepc-em31/motion-residency-report.json $M/hot/em31-r332.json $R --profile "r332 Saddler fight opening (Flycast f1mW/f2mW runs a2a m2a m3a m4a m5a: s00 skip, up-cut, walk, tentacle swipes, close attacks, hit reactions)"
python3 - $M/hot/em31-r332.json $L/prepem/prepc-em31/motion-residency-report.json <<'PY'
import json,sys
h=json.load(open(sys.argv[1])); r=json.load(open(sys.argv[2]))
print({k:v for k,v in h.items() if k!='union'}); print('arcs',h['union']['source_arc_indices'])
PY
