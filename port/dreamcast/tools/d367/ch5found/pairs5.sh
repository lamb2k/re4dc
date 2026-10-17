#!/bin/bash
# island material pairs the round 2 runs logged as "pair missing" (r311 / r327: 5ec91893-07ced5eb), from GC disc 2
set -e
L=/root/probe/lanes-20261016/ch5found
T=$L/tree/port/dreamcast/tools/d367
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016
ISO="/mnt/c/Game Dev/Emulators/Resident Evil 4 (USA) (Disc 2).iso"
LOGS=$(ls $E/h-cx5cmW/scenarios/*/capture/run-output.txt $E/h-cx5vmW/scenarios/*/capture/run-output.txt)
grep -h 'pair missing' $LOGS | sed 's/ [0-9]*x[0-9]*$//' | sort -u
PY=python3
for v in /root/probe/codex-ps2-assets-blind/.venv/bin/python /root/probe/lanes-20261014/st3/tools/.venv/bin/python; do [ -x $v ] && PY=$v && break; done
echo "python: $PY"
mkdir -p $L/pairs-c5
$PY $T/pairs_from_log.py --iso "$ISO" --output $L/pairs-c5 $(for f in $LOGS; do echo --log $f; done) \
  --file st3/r311.das --file st3/r327.das --file em/em1d.drs --file em/em1e.drs --file em/em1f.drs --file etc/core.das 2>&1 | tail -8
ls -la $L/pairs-c5
