#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/gc-catalog24
SOURCE=a132648e8199b50a5ac51cec4d339fe7dbc60135
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/gc-catalog24/catalog-target-a132.sh'
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/gc-catalog24'
if [ "${1:-}" = --slot ];then
 shift
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
 exec "$@"
fi
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null;then echo RELEASE_PRIORITY_HOLD;exit 3;fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || exit 2
cd "$TREE"
export GC_CATALOG24_ALLOCATED="$SOURCE" SOURCE_DATE_EPOCH=1760000000 PYTHONDONTWRITEBYTECODE=1 JOBS=1
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
source port/dreamcast/kos-env.sh
export PATH="$KOS_BASE/utils/build_wrappers:$KOS_CC_BASE/bin:$PATH"
exec /root/probe/d367-buildslot.sh bash "$SELF" --slot python3 -B "$OWN/catalog-target-a132.py"
