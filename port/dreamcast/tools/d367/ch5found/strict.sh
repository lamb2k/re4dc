#!/bin/bash
# STRICT pairs (Flycast): cx5tmW (dba49b85, no hooks) vs cx5umW (round-10 hooks), same fixture data and warp, LOGIC_TRACE=1
D=/root/probe/d367-agents/game30/tools/logic_trace_diff.py
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016
for r in r317 r31b r31c r320 r321 r325 r330; do
  A=$E/h-cx5tmW/scenarios/cx-$r-walk-t2/capture/run-output.txt
  B=$E/h-cx5umW/scenarios/cx-$r-walk-u2/capture/run-output.txt
  J=$E/h-cx5umW/scenarios/cx-$r-walk-u2/trace-t2-vs-u2-frame.json
  [ -f $A ] && [ -f $B ] || { echo "$r: missing run"; continue; }
  python3 $D $A $B --align frame --json $J >/dev/null 2>$J.err || true
  python3 -c "
import json;j=json.load(open('$J'));fd=j.get('first_divergence') or {}
print('$r', j.get('verdict'), 'compared', j.get('compared'), 'first', fd.get('ref_frame'), list((fd.get('fields') or {}).keys())[:6])" 2>/dev/null || { echo "$r: no result"; tail -2 $J.err; }
  echo "   events/movies: $(grep -a -h -o -E 'route movie[^,]{0,40}|EvtRead[A-Za-z]*: [^ ]+' $B | sort | uniq -c | head -4 | tr '\n' ';')"
done
