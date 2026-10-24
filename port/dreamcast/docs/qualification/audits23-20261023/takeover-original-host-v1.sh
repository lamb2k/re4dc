#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23
D=$T/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/host-original-fixes-r1'
[ ! -e "$E" ]
O=$(mktemp -d /dev/shm/audits23-original-host-XXXXXX)
mkdir -p "$E"
git -C "$T" rev-parse HEAD > "$E/source.txt"
python3 "$D/effect_pool_audit/inventory.py" --output "$O/fx-inventory" > "$E/inventory.log" 2>&1
python3 "$D/effect_pool_audit/test_failures.py" --output "$O/fx-failures" > "$E/failures.log" 2>&1
python3 "$D/dam_audit/check_missing_actor.py" --output "$O/dam-host" > "$E/dam-host.log" 2>&1
find "$O" -type f -name '*.json' -exec cp --parents '{}' "$E" \;
find "$O" -type f -printf '%P %s bytes\n'
tail -5 "$E/inventory.log"
tail -5 "$E/failures.log"
tail -5 "$E/dam-host.log"
printf 'HOST_CONTROL_OUTPUT=%s\n' "$O"