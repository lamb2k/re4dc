#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/gc-motion24
SOURCE=aab201ceac0e18107f64a3212398afe916793327
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-census-root-graph-fix-v2/run.sh'
[ "${GC_KOS_CENSUS_SOURCE:-}" = "$SOURCE" ] || { echo ROOT_CENSUS_SOURCE_GRANT_REQUIRED; exit 2; }
[ -n "${GC_KOS_CENSUS_PLAN:-}" ] && [ -n "${GC_KOS_CENSUS_TOOLS:-}" ] || { echo ROOT_EXACT_PLAN_AND_TOOLS_GRANT_REQUIRED; exit 2; }
for key in CC CXX CPP AS AR LD NM OBJCOPY OBJDUMP RANLIB STRIP CFLAGS CXXFLAGS CPPFLAGS LDFLAGS MAKEFLAGS MFLAGS GNUMAKEFLAGS GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH BASH_ENV ENV LD_PRELOAD LD_LIBRARY_PATH PYTHONPATH PYTHONHOME PYTHONPYCACHEPREFIX RE4DC_KOS_CC_BASE KOS_CFLAGS KOS_CPPFLAGS KOS_LDFLAGS KOS_CC_BASE KOS_CC KOS_CXX; do
  [ -z "${!key:-}" ] || { echo "INHERITED_INJECTION_REFUSED:$key"; exit 2; }
done
export PATH=/usr/bin:/bin
export PYTHONDONTWRITEBYTECODE=1
if [ "${1:-}" = --slot ]; then
  export GC_KOS_CENSUS_SLOT=1
  CACHE=/dev/shm/gc-motion24-kos-census-v1-2g7teq3g/python-cache-continuation-v2
  [ ! -e "$CACHE" ] || { echo PYTHON_CACHE_ALREADY_EXISTS_PRESERVE_REFUSE; exit 2; }
  mkdir -m 700 "$CACHE"
  exec /usr/bin/python3 -B -E -X "pycache_prefix=$CACHE" '/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-census-root-graph-fix-v2/continue.py'
fi
[ "$#" = 0 ]
[ "$(git --no-optional-locks -c index.threads=1 -c core.preloadIndex=false -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git --no-optional-locks -c index.threads=1 -c core.preloadIndex=false -C "$TREE" status --porcelain)" ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null; then echo RELEASE_PRIORITY_HOLD; exit 3; fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || { echo CANONICAL_GC_MOTION_LEASE_BUSY; exit 2; }
exec /root/probe/d367-buildslot.sh bash "$SELF" --slot
