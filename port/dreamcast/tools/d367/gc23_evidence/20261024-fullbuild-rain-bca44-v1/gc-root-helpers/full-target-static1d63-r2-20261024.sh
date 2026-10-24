#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/gc-port23
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23/full-target-static1d63-r2-20261024.sh'
if [ "${1:-}" = --slot ];then
 shift
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 32212254720 ]
 exec "$@"
fi
[ "$(git -C "$TREE" rev-parse HEAD)" = 1d63cffe3a232c402418f2f2d919e7abae476957 ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null;then echo RELEASE_PRIORITY_HOLD;exit 3;fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || exit 2
exec /root/probe/d367-buildslot.sh bash "$SELF" --slot python3 -B '/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23/full-target-static1d63-r2-20261024.py'