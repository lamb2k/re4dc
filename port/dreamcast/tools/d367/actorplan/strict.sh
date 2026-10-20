#!/bin/bash
# strict.sh <ref run> <cand run> (WSL): logic_trace_diff --align frame over two actorplan trace runs
E=/mnt/c/Flycast-Evidence/re4-dreamcast/actorplan17-20261016
D=/root/probe/lanes-20261016/actorplan17/tree/port/dreamcast/tools/game30/logic_trace_diff.py
python3 $D --align frame $E/$1/capture/run-output.txt $E/$2/capture/run-output.txt > $E/strict-$2.json 2>&1
python3 -c "
import json;d=json.load(open('$E/strict-$2.json'))
print('$1 vs $2:', d.get('verdict'), 'compared', d.get('compared'), 'window', d.get('window'), 'gaps', d.get('ref_gaps'), d.get('cand_gaps'), 'first', d.get('first_divergence'))" || tail -3 $E/strict-$2.json
