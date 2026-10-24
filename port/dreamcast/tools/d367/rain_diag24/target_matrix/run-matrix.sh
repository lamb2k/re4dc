#!/usr/bin/env bash
# FUTURE SDK entry only. Preparation never executes this file.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
self=$(readlink -f "${BASH_SOURCE[0]}")
here=$(dirname "$self")
if [[ "${1:-}" != --slot ]]; then
  [[ $# == 3 && -z "${D367_SLOT_HELD:-}" && -z "${RAIN_DIAG_MATRIX_SLOT:-}" ]] || { echo 'fresh public root allocation entry required' >&2; exit 2; }
  pins=$(readlink -f "$1"); grant=$(readlink -f "$2"); output=$3
  python3 "$here/matrix.py" check --pins "$pins" --grant "$grant" --out "$output"
  export RAIN_DIAG_MATRIX_SLOT=$(sha256sum "$pins" | cut -d' ' -f1)
  lease=/tmp/d367-build-$(printf %s '/root/work/lanes/rain-diag24' | md5sum | cut -c1-12).lock
  exec 7>"$lease"
  flock 7
  exec /root/probe/d367-buildslot.sh /usr/bin/timeout --signal=TERM --kill-after=2 380 bash "$self" --slot "$pins" "$grant" "$output"
fi
shift
[[ $# == 3 && "${D367_SLOT_HELD:-}" == 1 && -n "${RAIN_DIAG_MATRIX_SLOT:-}" && -e /proc/$$/fd/7 ]] || { echo 'missing canonical lease/slot' >&2; exit 2; }
pins=$1; grant=$2; output=$3
ulimit -v 262144
python3 "$here/matrix.py" reserve --pins "$pins" --grant "$grant" --out "$output"
# Pinned KOS environment includes an m4-single C compile probe and kos-cc
# -dumpversion. Both are SDK work,
# deliberately after root grant, lease, slot and resource admission.
# Avoid an inherited wrapper earlier on PATH during KOS's version probe.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
export RE4DC_KOS_PORTS=/root/work/kos-ports
export RE4DC_KOS_CC_BASE=/opt/toolchains/dc/sh-elf
unset GCC_EXEC_PREFIX COMPILER_PATH CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH LIBRARY_PATH LD_PRELOAD
set -o noclobber
mkdir "$output/bootstrap-tmp"
export TMPDIR="$output/bootstrap-tmp"
/usr/bin/timeout --signal=TERM --kill-after=2 60 bash -c '
  set -ex
  source /root/work/lanes/rain-diag24/port/dreamcast/kos-env.sh
  env -0 >"$1/environment.nul"
' _ "$output" >"$output/environment-bootstrap.log" 2>&1
exec python3 "$here/matrix.py" run --pins "$pins" --grant "$grant" --out "$output"
