#!/bin/bash
set -euo pipefail
HERE='/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/full-normal-rain8ce-exec-v1'
TREE=/root/work/lanes/codex-composition-int24
SOURCE=8ce5ee2d00027268c3e69c9c300b819c1b14c63f
: "${RAIN8CE_ROOT_GRANT:?ROOT_GRANT_REQUIRED}"
: "${RAIN8CE_GRANT_SHA256:?ROOT_GRANT_PIN_REQUIRED}"
: "${RAIN8CE_FULL_ALLOCATED:?ROOT_ALLOCATION_REQUIRED}"
[ "$(sha256sum "$HERE/CONTRACT.json" | cut -d' ' -f1)" = "$RAIN8CE_FULL_ALLOCATED" ]
[ "$(sha256sum "$RAIN8CE_ROOT_GRANT" | cut -d' ' -f1)" = "$RAIN8CE_GRANT_SHA256" ]
[ "$(git --no-optional-locks -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git --no-optional-locks -C "$TREE" status --porcelain)" ]
[ -z "${MAKEFLAGS:-}${MFLAGS:-}" ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null; then echo RELEASE_PRIORITY_HOLD; exit 3; fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || exit 2
unset D367_SLOT_HELD
export PYTHONPYCACHEPREFIX='/dev/shm/rain8ce-full-normal-179r4a5c/unused-pycache-root-v1'
export PYTHONDONTWRITEBYTECODE=1
[ ! -e "$PYTHONPYCACHEPREFIX" ]
exec /root/probe/d367-buildslot.sh /usr/bin/python3 -B "$HERE/controller.py" --execute
