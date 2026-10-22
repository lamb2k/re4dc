#!/bin/bash
set -euo pipefail
TREE=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=${1:?Pass a new owned output directory}
test ! -e "$OUT"
exec 7>"$TREE/.walk23-tree.lock"
flock -x 7
exec /root/probe/d367-buildslot.sh python3 "$TREE/port/dreamcast/tools/d367/backface_walk23/test_target.py" --output "$OUT"
