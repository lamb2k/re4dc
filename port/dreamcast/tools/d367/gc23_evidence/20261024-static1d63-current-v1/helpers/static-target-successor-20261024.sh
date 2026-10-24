#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/gc-port23
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23'
SOURCE=1d63cffe3a232c402418f2f2d919e7abae476957
if [ "${1:-}" = --slot ];then
 shift
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
 exec "$@"
fi
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 26843545600 ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null;then echo RELEASE_PRIORITY_HOLD;exit 3;fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || exit 2
cd "$TREE"
export GCGATE_PRIOR_REPORT='/dev/shm/gc-port23-current-77d8a20b2-jx_x05a2/report.json'
export GCGATE_SOURCE="$SOURCE" SOURCE_DATE_EPOCH=1760000000 PYTHONDONTWRITEBYTECODE=1
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
source port/dreamcast/kos-env.sh
export PATH="$KOS_BASE/utils/build_wrappers:$KOS_CC_BASE/bin:$PATH"
exec /root/probe/d367-buildslot.sh bash "$OWN/static-target-successor-20261024.sh" --slot python3 -B "$OWN/static-target-successor-20261024.py"
