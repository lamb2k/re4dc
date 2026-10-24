#!/bin/bash
set -euo pipefail
T=/root/work/lanes/dedup-offline23-integration/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023'
LOGS=("$E/gate-cg100-r1/run-output.txt" "$E/gate-cg101-r1/run-output.txt" "$E/gate-cg103-r1/run-output.txt")
python3 "$T/cast_gc.py" "${LOGS[@]}" --not-drawn --label dd3 --json "$E/castgc-r1.json" > "$E/castgc-r1.txt" 2>&1 || RC=$?
printf 'castgc exit=%s\n' "${RC:-0}"
tail -7 "$E/castgc-r1.txt"
python3 "$T/texchk/texchk.py" "${LOGS[@]}" "$E/gate-kos0-r1/run-output.txt" "$E/gate-kos1-r1/run-output.txt" > "$E/texchk-r1.txt" 2>&1 || TX=$?
printf 'texchk exit=%s\n' "${TX:-0}"
tail -4 "$E/texchk-r1.txt"
for R in 100 101 103;do python3 "$T/mcheck/leongc_check.py" "$E/gate-cg$R-r1/run-output.txt" > "$E/leongc-$R-r1.txt" 2>&1 || true; tail -1 "$E/leongc-$R-r1.txt";done
