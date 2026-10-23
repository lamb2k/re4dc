#!/bin/bash
set -euo pipefail
export TRACE_SLOTS=16 TRACE_LOCK_OWNER=actor23-root-material-census23-r1
lock=/root/probe/codex-pvs23-build-3dd7dfe4/port/dreamcast/tools/d367/trace_lock.sh
test "$(sha256sum "$lock" | cut -d' ' -f1)" = e5d301a1e5888b5256feee01ab7e90b7c21633d36450691a9e9df1836e913688
execute=0
for arg in "$@"; do [ "$arg" != --execute ] || execute=1; done
if [ "$execute" -eq 0 ]; then
  exec "/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe" -B 'C:\Game Dev\Emulators\codex-lanes\actor-visibility23\material-census23-run\root-native-census-bea2.py' "$@"
fi
exec bash "$lock" "/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe" -B 'C:\Game Dev\Emulators\codex-lanes\actor-visibility23\material-census23-run\root-native-census-bea2.py' "$@"
