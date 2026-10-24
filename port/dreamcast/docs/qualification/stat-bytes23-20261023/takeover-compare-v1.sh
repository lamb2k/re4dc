#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-complete/port/dreamcast/tools/game30
E='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
for SC in bell mendez;do
 python3 "$T/decision_cmp.py" "$E/decisions-$SC-off/run-output.txt" "$E/decisions-$SC-on/run-output.txt" --align frame --json "$E/decisions-$SC-comparison.json" > "$E/decisions-$SC-comparison.txt" 2>&1 || true
 cat "$E/decisions-$SC-comparison.txt" | head -35
done
