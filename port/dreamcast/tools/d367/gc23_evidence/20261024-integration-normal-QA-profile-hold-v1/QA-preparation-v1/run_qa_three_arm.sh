#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/gc-motion24
SOURCE=aab201ceac0e18107f64a3212398afe916793327
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/memory-qualification-prep/qa-pair-v1/run_qa_three_arm.sh'
[ "${GC_MOTION24_FULL_ALLOCATED:-}" = "$SOURCE" ] || { echo ROOT_ALLOCATION_REQUIRED; exit 2; }
[ -n "${GC_MOTION24_QA_TOOLS_ALLOCATED:-}" ] || { echo ROOT_QA_TOOL_ALLOCATION_REQUIRED; exit 2; }
[ -n "${GC_MOTION24_QA_ALLOCATED:-}" ] || { echo ROOT_QA_PLAN_ALLOCATION_REQUIRED; exit 2; }
if [ "${1:-}" = --slot ]; then
  shift
  export GC_MOTION24_FULL_SLOT=1
  exec "$@"
fi
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null; then echo RELEASE_PRIORITY_HOLD; exit 3; fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || exit 2
exec /root/probe/d367-buildslot.sh bash "$SELF" --slot python3 -B '/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/memory-qualification-prep/qa-pair-v1/run_qa_three_arm.py'
