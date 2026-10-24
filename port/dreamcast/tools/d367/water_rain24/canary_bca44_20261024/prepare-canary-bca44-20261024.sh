#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/water-rain24
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/water-rain24/prepare-canary-bca44-20261024.sh'
if [ "${1:-}" = --slot ]; then
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 32212254720 ]
 exec python3 -B '/mnt/c/Game Dev/Emulators/codex-lanes/water-rain24/prepare-canary-bca44-20261024.py'
fi
[ "$(git -C "$TREE" rev-parse HEAD)" = bca44d58a1fa0a51fd87ba94deba8cba925c8998 ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null; then echo RELEASE_PRIORITY_HOLD;exit 3;fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || { echo TREE_LEASE_BUSY;exit 2; }
exec /root/probe/d367-buildslot.sh bash "$SELF" --slot