#!/bin/bash
# STRICT + decisions: s6a (every em36 clip hot = no cold reads; reference) vs s6h (r307 hot list, 63 clips cold), arm cx5srT
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016/h-cx5srT/scenarios
G=/root/probe/lanes-20261016/ch5found/tree/port/dreamcast/tools/game30
R=$E/cx-r307-walk-s6a/capture/run-output.txt; C=$E/cx-r307-walk-s6h/capture/run-output.txt; O=$E/cx-r307-walk-s6h/strict-s6a-vs-s6h
for f in $R $C; do grep -q 'LOG OVERRUN' $f && echo "INVALID: LOG OVERRUN in $f"; echo "$(basename $(dirname $(dirname $f))) ticks $(grep -a -c '^LT' $f) last $(grep -a '^LT' $f | tail -1 | cut -c1-40)"; done
python3 $G/logic_trace_diff.py $R $C --align frame --json $O-raw.json > $O-raw.txt 2>&1
python3 -c "import json,sys;j=json.load(open(sys.argv[1]));fd=j.get('first_divergence') or {};print('STRICT verdict',j.get('verdict'),'compared',j.get('compared'),'masked',j.get('masked'),'first',fd.get('ref_frame'),list((fd.get('fields') or {}).keys())[:6])" $O-raw.json
python3 $G/decision_cmp.py $R $C --align frame > $O-dcmp.txt 2>&1; head -3 $O-dcmp.txt; grep -m1 -i "must" $O-dcmp.txt | cut -c1-200
