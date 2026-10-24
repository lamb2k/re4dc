#!/usr/bin/bash -p
case $- in *p*) ;; *) echo PRIVILEGED_BASH_REQUIRED; exit 2;; esac
set -euo pipefail
export PATH=/usr/bin:/bin
TREE=/root/work/lanes/gc-motion24-budget
SOURCE=427784b1f48aa30742850bb5025925ab619b740e
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-budget-qa-on-continuation-v1/run.sh'
[ "${GC_BUDGET_QA_SOURCE:-}" = "$SOURCE" ] || { echo ROOT_BUDGET_QA_SOURCE_GRANT_REQUIRED; exit 2; }
[ -n "${GC_BUDGET_QA_PLAN:-}" ] && [ -n "${GC_BUDGET_QA_TOOLS:-}" ] || { echo ROOT_EXACT_PLAN_AND_TOOLS_GRANT_REQUIRED; exit 2; }
for key in CC CXX CPP AS AR LD NM OBJCOPY OBJDUMP RANLIB STRIP CFLAGS CXXFLAGS CPPFLAGS LDFLAGS MAKEFLAGS MFLAGS GNUMAKEFLAGS GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH BASH_ENV ENV LD_PRELOAD LD_LIBRARY_PATH PYTHONPATH PYTHONHOME PYTHONPYCACHEPREFIX RE4DC_KOS_CC_BASE KOS_CFLAGS KOS_CPPFLAGS KOS_LDFLAGS KOS_CC_BASE KOS_CC KOS_CXX; do
  [ -z "${!key:-}" ] || { echo "INHERITED_INJECTION_REFUSED:$key"; exit 2; }
done
[ "$GC_BUDGET_QA_PLAN" = "$(sha256sum '/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-budget-qa-on-continuation-v1/CONTRACT.json' | cut -d' ' -f1)" ] || exit 2
[ "$GC_BUDGET_QA_TOOLS" = "$(sha256sum '/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-budget-qa-on-continuation-v1/TOOLCHAIN-SEAL.json' | cut -d' ' -f1)" ] || exit 2
export PATH=/usr/bin:/bin
export PYTHONDONTWRITEBYTECODE=1
if [ "${1:-}" = --slot ]; then
  export GC_BUDGET_QA_SLOT=1
  exec /usr/bin/python3 -I -S -B '/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-budget-qa-on-continuation-v1/launch.py'
fi
[ "$#" = 0 ]
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null; then echo RELEASE_PRIORITY_HOLD; exit 3; fi
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || { echo CANONICAL_GC_MOTION_LEASE_BUSY; exit 2; }
exec /usr/bin/bash -p /root/probe/d367-buildslot.sh /usr/bin/bash -p "$SELF" --slot
