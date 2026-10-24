#!/bin/bash -p
set -euo pipefail
# The canonical caller MUST use bash -p; normal bash processes BASH_ENV first.
case $- in *p*) ;; *) echo 'Use canonical /bin/bash -p invocation' >&2; exit 3 ;; esac
HERE='/mnt/c/Game Dev/Emulators/codex-lanes/rain-diag24/qa-pair-prep-v2'
for key in BASH_ENV ENV LD_PRELOAD LD_LIBRARY_PATH; do
  if [ -n "${!key-}" ]; then echo "Startup injection refused: $key" >&2; exit 3; fi
done
for key in ${!PYTHON@}; do
  case "$key" in
    PYTHONDONTWRITEBYTECODE) [ "${!key}" = '1' ] || { echo "Startup injection refused: $key" >&2; exit 3; } ;;
    *) [ -z "${!key}" ] || { echo "Startup injection refused: $key" >&2; exit 3; } ;;
  esac
done
: "${RAIN8CE_QA_ROOT_GRANT:?ROOT_QA_GRANT_REQUIRED}"
: "${RAIN8CE_QA_GRANT_SHA256:?ROOT_QA_GRANT_PIN_REQUIRED}"
: "${RAIN8CE_QA_ALLOCATED:?ROOT_QA_ALLOCATION_REQUIRED}"
export PYTHONDONTWRITEBYTECODE=1
# -I ignores Python environment/user paths; -S disables site; -B forbids writes.
exec /usr/bin/python3 -I -S -B "$HERE/controller.py" --execute
