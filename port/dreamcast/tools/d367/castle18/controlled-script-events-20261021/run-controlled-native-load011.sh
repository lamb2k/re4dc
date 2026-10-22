set -euo pipefail
test "${1:-}" = --execute-allocated011
export TRACE_SLOTS=16 TRACE_LOCK_OWNER=castle21-controlled-native-load011
bash /root/probe/codex-castle18/port/dreamcast/tools/d367/trace_lock.sh /mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe 'C:\Game Dev\Emulators\codex-lanes\castle18\run-controlled-native-load011.py' "$@"
