#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/water-rain24
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/water-rain24/target-rain-bca-20261024.sh'
if [ "${1:-}" = --slot ];then shift;[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ];exec "$@";fi
[ "$(git -C "$TREE" rev-parse HEAD)" = bca44d58a1fa0a51fd87ba94deba8cba925c8998 ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null;then echo RELEASE_PRIORITY_HOLD;exit 3;fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || exit 2
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367 SOURCE_DATE_EPOCH=1760000000 PYTHONDONTWRITEBYTECODE=1
cd "$TREE"
source port/dreamcast/kos-env.sh
export PATH="$KOS_BASE/utils/build_wrappers:$KOS_CC_BASE/bin:$PATH"
exec /root/probe/d367-buildslot.sh bash "$SELF" --slot python3 -B '/mnt/c/Game Dev/Emulators/codex-lanes/water-rain24/target-rain-bca-20261024.py'