#!/bin/bash
set -euo pipefail
# First arg is the selected Windows Python executable; remaining args are capture.py args.
PYTHON_EXE=${1:?Windows Python executable required}
shift
HERE=$(cd "$(dirname "$0")" && pwd)
export TRACE_SLOTS=16 TRACE_LOCK_OWNER=texture21-benchmark
bash "$HERE/../trace_lock.sh" "$PYTHON_EXE" "$(wslpath -w "$HERE/capture.py")" "$@"
