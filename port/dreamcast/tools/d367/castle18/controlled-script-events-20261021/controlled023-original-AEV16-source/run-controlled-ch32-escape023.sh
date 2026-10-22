set -euo pipefail
test "${1:-}" = --execute-allocated023
export TRACE_SLOTS=16 TRACE_LOCK_OWNER=castle21-controlled-ch32-escape023
bash /root/probe/codex-castle18/port/dreamcast/tools/d367/trace_lock.sh /mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe 'C:\Game Dev\Emulators\codex-lanes\castle18\run-controlled-ch32-escape023.py' "$@"
