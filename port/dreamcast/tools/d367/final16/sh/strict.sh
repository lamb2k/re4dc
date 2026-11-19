# strict.sh <ref run> <cand run> [extra args]: STRICT (logic_trace_diff) + decisions (decision_cmp) of two f3rT runs, frame aligned
G=/root/probe/lanes-20261016/final16/tree/port/dreamcast/tools/game30
H=/mnt/c/Flycast-Evidence/re4-dreamcast/final16-20261016/h-f3rT/scenarios; [ -n "$HREF" ] && HR=/mnt/c/Flycast-Evidence/re4-dreamcast/final16-20261016/$HREF/scenarios
HR=${HR:-$H}; R=$HR/cx-r332-fight-$1/capture/run-output.txt; C=$H/cx-r332-fight-$2/capture/run-output.txt; O=$H/cx-r332-fight-$2
python3 $G/logic_trace_diff.py $R $C --align frame --json $O/strict-$1-vs-$2-raw.json > $O/strict-$1-vs-$2-raw.txt 2>&1
python3 $G/decision_cmp.py $R $C --align frame --json $O/strict-$1-vs-$2-dcmp.json > $O/strict-$1-vs-$2-dcmp.txt 2>&1
python3 - $O/strict-$1-vs-$2-raw.json <<'PY'
import json,sys
j=json.load(open(sys.argv[1])); print('raw', j.get('verdict'), 'compared', j.get('compared'), 'window', j.get('window'), 'rooms', j.get('rooms'), 'first', j.get('first_divergence'))
PY
head -6 $O/strict-$1-vs-$2-dcmp.txt | cut -c1-300
