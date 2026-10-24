#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/gc-port23
export GCGATE_SOURCE=${1:?Pass root-approved immutable source SHA}
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || { printf 'Tree build lease busy\n' >&2; exit 1; }
cd "$TREE"
export SOURCE_DATE_EPOCH=1790000000
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
source port/dreamcast/kos-env.sh
export PATH="$KOS_BASE/utils/build_wrappers:$KOS_CC_BASE/bin:$PATH"
exec /root/probe/d367-buildslot.sh python3 port/dreamcast/tools/d367/gc_port23/target_current_objects.py
