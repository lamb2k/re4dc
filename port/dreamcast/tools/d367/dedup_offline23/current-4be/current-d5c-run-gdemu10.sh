#!/bin/bash
set -euo pipefail
SEED=${1:?seed2..10}
case "$SEED" in 2|3|4|5|6|7|8|9|10);;*)exit 2;;esac
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
. "$OWN/current-d5c-pins.sh"
python3 "$OWN/current-d5c-gdemu10.py" admit "$SEED"
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
exec 7>"$WORK/guest.lock";flock -n 7 || { echo OWN_GUEST_BUSY;exit 2; }
T=$TREE/port/dreamcast/tools/d367
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
O=/root/probe/lanes/route/out-fpdd23cur4be08e01ongW
export RE4DC_GD_PROFILE=gdemu RE4DC_GD_JITTER=20000 RE4DC_GD_SEED="$SEED"
export RE4DC_EMU=console RE4DC_CONSOLE_EXE='C:\\Flycast-Evidence\\re4-dreamcast\\flycast-console-bin\\flycast-console.exe'
export RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16 TRACE_LOCK_OWNER="dedup-current4be-gdemu$SEED"
export PYTHONDONTWRITEBYTECODE=1
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_CONSOLE_EXE:RE4DC_MAX_FLYCASTS:FP_NOLIMIT:PYTHONDONTWRITEBYTECODE:RE4DC_GD_PROFILE:RE4DC_GD_JITTER:RE4DC_GD_SEED"
"$P" -c 'import os,sys;assert os.environ.get("RE4DC_EMU")=="console";assert os.environ.get("FP_NOLIMIT")=="1";assert {k:os.environ.get(k) for k in ("RE4DC_GD_PROFILE","RE4DC_GD_JITTER","RE4DC_GD_SEED")}==dict(RE4DC_GD_PROFILE="gdemu",RE4DC_GD_JITTER="20000",RE4DC_GD_SEED=sys.argv[1]);print("WINDOWS_EXACT_SEED_ENV_VERIFIED",sys.argv[1])' "$SEED"
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --base "$(wslpath -w "$EVIDENCE/base-standard-current4be-on-r1")" --cap "$(wslpath -w "$EVIDENCE/gdemu$SEED-console-r1")" --syms "$(cat "$O/syms.txt")" --seconds 50 --period 10 --name "dedup-current4be-gdemu$SEED" --warp "$(wslpath -w "$T/fullplay/segments/door103-warp.txt")" --stop 'phase=enter room=103' --grace 3
python3 "$OWN/current-d5c-gdemu10.py" check "$SEED"

