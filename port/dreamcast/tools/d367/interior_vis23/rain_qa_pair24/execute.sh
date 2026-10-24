#!/bin/bash
set -euo pipefail
HERE='/mnt/c/Game Dev/Emulators/codex-lanes/rain-diag24/qa-pair-prep-v1'
: "${RAIN8CE_QA_ROOT_GRANT:?ROOT_QA_GRANT_REQUIRED}"
: "${RAIN8CE_QA_GRANT_SHA256:?ROOT_QA_GRANT_PIN_REQUIRED}"
: "${RAIN8CE_QA_ALLOCATED:?ROOT_QA_ALLOCATION_REQUIRED}"
export PYTHONDONTWRITEBYTECODE=1
# -B and a private unused cache root prevent any shared bytecache writes.
export PYTHONPYCACHEPREFIX='/dev/shm/rain8ce-qa-pair-v1-2ykw93ke/unused-controller-bytecache'
[ ! -e "$PYTHONPYCACHEPREFIX" ]
exec /usr/bin/python3 -B "$HERE/controller.py" --execute
