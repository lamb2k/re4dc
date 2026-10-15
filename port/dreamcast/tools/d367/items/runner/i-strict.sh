#!/bin/bash
# i-strict.sh <ref run> <test run> [out name] (WSL): STRICT + decision_cmp of two lane items trace runs (copy of test11/strict.sh).
E=/mnt/c/Flycast-Evidence/re4-dreamcast/items-20261014
G=/root/probe/lanes-20261014/items/tree/port/dreamcast/tools/game30
R=$E/$1/capture/run-output.txt; C=$E/$2/capture/run-output.txt; O=$E/strict/${3:-$1-vs-$2}
mkdir -p $E/strict
for f in $R $C; do grep -q 'LOG OVERRUN' $f && echo "INVALID: LOG OVERRUN in $f"; done
python3 $G/logic_trace_diff.py $R $C --align frame --json $O-raw.json > $O-raw.txt 2>&1
python3 -c "import json,sys;j=json.load(open(sys.argv[1]));fd=j.get('first_divergence') or {};print('STRICT verdict',j.get('verdict'),'compared',j.get('compared'),'masked',j.get('masked'),'first',fd.get('ref_frame'),list((fd.get('fields') or {}).keys())[:6])" $O-raw.json
python3 $G/decision_cmp.py $R $C --align frame > $O-dcmp.txt 2>&1; head -2 $O-dcmp.txt
for f in $R $C; do echo "s30 $(grep -a -o 'route movie terminal=[0-9] id=10030 frames=[0-9/]*' $f | tail -1)  $(grep -ac 'LOG OVERRUN' $f) overruns"; done
