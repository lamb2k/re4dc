set -euo pipefail
. '/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/current-d5c-pins.sh'
T=$TREE/port/dreamcast/tools/d367
LOGS=("$EVIDENCE/cg-r100-console-r1/run-output.txt" "$EVIDENCE/cg-r101-console-r1/run-output.txt" "$EVIDENCE/cg-r103-console-r1/run-output.txt")
python3 "$T/cast_gc.py" "${LOGS[@]}" --not-drawn --label current4be --json "$EVIDENCE/castgc-r1.json" > "$EVIDENCE/castgc-r1.txt" 2>&1
tail -7 "$EVIDENCE/castgc-r1.txt"
python3 "$T/texchk/texchk.py" "${LOGS[@]}" "$EVIDENCE/kos-fight-0-console-r1/run-output.txt" "$EVIDENCE/kos-fight-1-console-r1/run-output.txt" > "$EVIDENCE/texchk-r1.txt" 2>&1
tail -5 "$EVIDENCE/texchk-r1.txt"
for ROOM in r100 r101 r103;do
 python3 "$T/mcheck/leongc_check.py" "$EVIDENCE/cg-$ROOM-console-r1/run-output.txt" > "$EVIDENCE/leongc-$ROOM-r1.txt" 2>&1
 tail -1 "$EVIDENCE/leongc-$ROOM-r1.txt"
done
