#!/bin/bash
set -euo pipefail
SCENE=${1:?cross-off/cross-on/farm-off/farm-on/forest-off/forest-on}
case "$SCENE" in cross-off|cross-on|farm-off|farm-on|forest-off|forest-on);;*)echo STILL_ONLY_CONTROL;exit 2;;esac
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
. "$OWN/current-d5c-pins.sh"
T=$TREE/port/dreamcast/tools/d367
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TREE" status --porcelain --untracked-files=no)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
mkdir -p "$EVIDENCE/fixtures"
exec 7>"$WORK/guest.lock";flock -n 7 || { echo OWN_GUEST_BUSY;exit 2; }
ARM=on;KIND=standard;LABEL=fpdd23cur${S8}ongW;ARGS=();SECONDS_GUEST=45;PERIOD=10
export RE4DC_GD_PROFILE='' RE4DC_GD_JITTER='' RE4DC_GD_SEED=''
case "$SCENE" in
 h2-off|h2-on)
  ARM=${SCENE#h2-};LABEL=fpdd23cur${S8}${ARM}gW
  ARGS=(--warp "$(wslpath -w "$T/fullplay/segments/h2-warp.txt")" --pad "$(wslpath -w "$T/fullplay/segments/h2-pad.txt")" --stop 'route movie terminal=1 id=10030' --grace 2);SECONDS_GUEST=50;;
 cross-off|cross-on|farm-off|farm-on|forest-off|forest-on)
  ARM=${SCENE##*-};VIEW=${SCENE%-*};LABEL=fpdd23cur${S8}${ARM}gW
  ARGS=(--warp "$(wslpath -w "$T/dedup_offline23/main/$VIEW-f330.txt")" --stop 'warp: frozen at tick 330' --grace 7);SECONDS_GUEST=45;PERIOD=3;;
 kos-*)
  KIND=diag;LABEL=fpdd23cur${S8}diagW;TAIL=${SCENE#kos-};FRAG=${TAIL##*-};PART=${TAIL%-*}
  case "$FRAG" in 0|1);;*)exit 2;;esac
  case "$PART" in fight|call|leave100|leave103);;*)exit 2;;esac
  WF=$EVIDENCE/fixtures/$SCENE.txt
  [ ! -e "$WF" ];{ echo "squeeze 49152 $FRAG";tr -d '\r' < "$T/fullplay/segments/kos-$PART-warp.txt"; } > "$WF"
  ARGS=(--warp "$(wslpath -w "$WF")");SECONDS_GUEST=45;;
 cg-r100|cg-r101|cg-r103)
  KIND=diag;LABEL=fpdd23cur${S8}diagW;ROOM=${SCENE#cg-}
  ARGS=(--warp "$(wslpath -w "$T/castgc/warps/$ROOM.txt")");SECONDS_GUEST=40;;
 gdemu1)
  export RE4DC_GD_PROFILE=gdemu RE4DC_GD_JITTER=20000 RE4DC_GD_SEED=1
  ARGS=(--warp "$(wslpath -w "$T/fullplay/segments/door103-warp.txt")" --stop 'phase=enter room=103' --grace 3);SECONDS_GUEST=50;;
 *)echo 'Unknown bounded scene';exit 2;;
esac
if [ "$KIND" = standard ];then BASE_DISC=$EVIDENCE/base-standard-current4be-$ARM-r1;else BASE_DISC=$EVIDENCE/base-diag-current4be-r1;fi
O=/root/probe/lanes/route/out-$LABEL
[ "$(cat "$O/stack.txt")" = "$SOURCE" ];[ ! -s "$O/missing.txt" ];[ -s "$BASE_DISC/base.json" ]
CAP=$EVIDENCE/$SCENE-limited-console-r3;[ ! -e "$CAP" ]
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
export RE4DC_EMU=console RE4DC_CONSOLE_EXE='C:\\Flycast-Evidence\\re4-dreamcast\\flycast-console-bin\\flycast-console.exe'
export RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=0 TRACE_SLOTS=16 TRACE_LOCK_OWNER=dedup-current4be-$SCENE
export PYTHONDONTWRITEBYTECODE=1
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_CONSOLE_EXE:RE4DC_MAX_FLYCASTS:FP_NOLIMIT:PYTHONDONTWRITEBYTECODE:RE4DC_GD_PROFILE:RE4DC_GD_JITTER:RE4DC_GD_SEED"
"$P" -c 'import os;assert os.environ.get("RE4DC_EMU")=="console";assert os.environ.get("FP_NOLIMIT")=="0";print("CONSOLE_STILL_FPS_LIMITED_VERIFIED")'
SYMS=$(cat "$O/syms.txt")
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --base "$(wslpath -w "$BASE_DISC")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --seconds "$SECONDS_GUEST" --period "$PERIOD" --name "dedup-current4be-$SCENE" "${ARGS[@]}"
python3 - "$CAP" <<'PY'
from pathlib import Path
import json,re,sys
p=Path(sys.argv[1]);r=json.loads((p/'run-result.json').read_text());b=json.loads((p/'bounded-launch.json').read_text())
s=(p/'run-output.txt').read_text(errors='replace')
assert r['emu']=='console' and not r['errors'] and not b['deadline_fired'],(r.get('errors'),b['deadline_fired'])
faults=re.findall(r'(?m)^(?:.*(?:HALT|FAULT|MISSING|Out of memory).*)$',s)
assert not faults,faults[:5]
print('BOUNDED_CAPTURE_FINISHED',p.name,'seconds',b.get('guest_observed_elapsed_s'),'gate judgement pending')
PY
