#!/usr/bin/env bash
set -euo pipefail
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23/takeover-decisions-v1.sh'
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
T=/root/work/lanes/stat-bytes23-complete/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
if [ "${1:-}" != --in-slot ];then
 ARM=${1:?off or on};case "$ARM" in off|on);;*)exit 2;;esac
 bash "$D/takeover-stage-v2.sh" "$ARM" t
 exec bash "$D/stat-guest-slot.sh" bash "$SELF" --in-slot "$ARM"
fi
ARM=${2:?off or on}
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
SYMS=$(cat "$E/identities/$ARM-t-syms.txt")
for SC in bell mendez;do
 CAP=$E/decisions-$SC-$ARM
 [ ! -e "$CAP" ]
 if [ "$SC" = bell ];then
  WF=$T/fullplay/segments/bell-trg-warp.txt;EXTRA=(--stop 'route movie terminal=1 id=10130' --grace 2)
 else
  WF=$T/fullplay/segments/mendez-warp.txt;EXTRA=(--pad "$(wslpath -w "$T/fullplay/segments/mendez-pad.txt")" --stop 'phase=enter room=10f' --grace 2)
 fi
 TRACE_LOCK_OWNER=stat23-$SC-$ARM bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --base "$(wslpath -w "$E/_discs/$ARM-t")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --warp "$(wslpath -w "$WF")" --seconds 45 --period 15 --name "stat23-$SC-$ARM" "${EXTRA[@]}"
done
