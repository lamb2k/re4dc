#!/usr/bin/env bash
set -euo pipefail
A='/mnt/c/Game Dev/Emulators/codex-lanes/audits23'
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
for room in r101 r10c r117 r200;do
 python3 "$A/judge-cache-diag.py" "$E/diag-$room-r1/run-output.txt" --room "$room" --output "$E/diag-$room-r1/cache-diag.json"
done
python3 "$A/judge-cache-diag.py" "$E/diag-h2-r1/run-output.txt" --room r100 --output "$E/diag-h2-r1/cache-diag.json"
python3 "$A/judge-cache-diag.py" "$E/diag-kos-r1/run-output.txt" --room r101 --output "$E/diag-kos-r1/cache-diag.json"