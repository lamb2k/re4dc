#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/gc-motion24
SOURCE=aab201ceac0e18107f64a3212398afe916793327
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/check-wrap-providers.sh'
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24'
if [ "${1:-}" = --slot ];then
 shift
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
 exec "$@"
fi
[ "$(git -c index.threads=1 -c core.preloadIndex=false -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -c index.threads=1 -c core.preloadIndex=false -C "$TREE" status --porcelain)" ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null;then echo RELEASE_PRIORITY_HOLD;exit 3;fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || exit 2
cd "$TREE"
export GC_MOTION24_ALLOCATED="$SOURCE" SOURCE_DATE_EPOCH=1760000000 PYTHONDONTWRITEBYTECODE=1 JOBS=1
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
source port/dreamcast/kos-env.sh
export PATH="$KOS_BASE/utils/build_wrappers:$KOS_CC_BASE/bin:$PATH"
exec /root/probe/d367-buildslot.sh bash "$SELF" --slot python3 -B "$OWN/check-wrap-providers.py"