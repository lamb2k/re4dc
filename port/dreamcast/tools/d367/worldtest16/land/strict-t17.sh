#!/bin/bash
# strict-t17.sh (WSL): r101 C16 landing STRICT + decisions: o = C4 data, n = C16, same ELF w16crT. Output <ev>/strict-t17.
# same ELF w16mrT. Output <ev>/strict/st{A,B,C}-{raw.json,raw.txt,dcmp.txt}.
G=/root/probe/worldtest16-20261016/tree/port/dreamcast/tools/game30
E=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016; mkdir -p $E/strict-t17
for p in "st2 t17-st2-o t17-st2-n" "st8 t17-st8-o t17-st8-n" "sta t17-sta-o t17-sta-n"; do
  set -- $p
  python3 $G/logic_trace_diff.py $E/$2/capture/run-output.txt $E/$3/capture/run-output.txt --align frame --json $E/strict-t17/$1-raw.json > $E/strict-t17/$1-raw.txt 2>&1
  python3 $G/decision_cmp.py $E/$2/capture/run-output.txt $E/$3/capture/run-output.txt --align frame > $E/strict-t17/$1-dcmp.txt 2>&1
  echo "$1 raw $(python3 -c "import json;d=json.load(open('$E/strict-t17/$1-raw.json'));print(d['verdict'],d['compared'],d['rooms'])") | $(head -2 $E/strict-t17/$1-dcmp.txt | tr '\n' ' ' | grep -o 'verdict [A-Z-]*\|[0-9]* ticks')"
  sed -n 4,5p $E/strict-t17/$1-dcmp.txt
done
