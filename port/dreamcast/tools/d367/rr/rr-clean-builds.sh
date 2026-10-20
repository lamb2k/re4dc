#!/bin/bash
# rr-clean-builds.sh <sha7>   (WSL; lane rr): delete one cycle's route build outputs (rebuildable from the commit +
# recipe.conf). Only rr's own labels: out-rr<sha7>*, out-fprr<sha7>*.
set -euo pipefail
S7=${1:?sha7}
[[ "$S7" =~ ^[0-9a-f]{7}$ ]] || { echo "rr-clean-builds: bad sha7 '$S7'" >&2; exit 2; }
ROUTE=/root/probe/lanes/route
M=/root/rr/logs/deleted-manifest.txt
for d in "$ROUTE"/out-rr"$S7"* "$ROUTE"/out-fprr"$S7"*; do
  [ -d "$d" ] || continue
  echo "$(date -Is) $d $(du -sh "$d" | cut -f1)" >> "$M"
  rm -rf "${d:?}"
done
# The playability programs registry (candidate-route<label>) is shared infrastructure: left alone.
