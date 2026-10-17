#!/bin/bash
# strict2.sh <ref run-output> <test run-output> <out name> (WSL): STRICT (frame alignment) + decisions
E=/mnt/c/Flycast-Evidence/re4-dreamcast/farmprop17-20261017
G=/root/probe/lanes-20261016/farmprop17/port/dreamcast/tools/game30
R=$1; C=$2; O=$E/strict/$3
mkdir -p $E/strict
for f in $R $C; do grep -q 'LOG OVERRUN' $f && echo "INVALID: LOG OVERRUN in $f"; done
python3 $G/logic_trace_diff.py $R $C --align frame --json $O-raw.json > $O-raw.txt 2>&1
python3 -c "import json,sys;j=json.load(open(sys.argv[1]));fd=j.get('first_divergence') or {};print(sys.argv[2],'STRICT verdict',j.get('verdict'),'compared',j.get('compared'),'masked',j.get('masked'),'first',fd.get('ref_frame'),list((fd.get('fields') or {}).keys())[:6])" $O-raw.json $3
python3 $G/decision_cmp.py $R $C --align frame > $O-dcmp.txt 2>&1; head -2 $O-dcmp.txt; grep -m1 "must" $O-dcmp.txt | cut -c1-200
for f in $R $C; do echo "  last tick $(grep -a -o '^LT [0-9]*' $f | tail -1) s30 $(grep -a -o 'route movie terminal=[0-9] id=10030 frames=[0-9/]*' $f | tail -1)"; done
