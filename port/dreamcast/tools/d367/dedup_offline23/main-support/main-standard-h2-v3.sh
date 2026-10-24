#!/bin/bash
set -euo pipefail
ARM=${1:?off or on}
case "$ARM" in off|on);;*)exit 2;;esac
TR=/root/work/lanes/dedup-offline23-next
T=$TR/port/dreamcast/tools/d367
EV='C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023'
O=/root/probe/lanes/route/out-fpdd23std${ARM}5be3gW
[ -s "$O/re4dc-game.elf" ] && [ -s "$O/syms.txt" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
SYMS=$(cat "$O/syms.txt")
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_LOCK_OWNER=codex-dedup-offline23-standard-h2 TRACE_SLOTS=16
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
"$P" -c 'import os; assert os.environ.get("RE4DC_EMU")=="console"; print("WINDOWS_ENV_CONSOLE_VERIFIED")'
bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$T/fullplay/fp_run.py")" \
 --base "${EV}\base-standard-repair5be-${ARM}" --cap "${EV}\\full-h2-standard-repair5be-${ARM}-console-r1" --syms "$SYMS" \
 --warp "$(wslpath -w "$T/fullplay/segments/h2-warp.txt")" --pad "$(wslpath -w "$T/fullplay/segments/h2-pad.txt")" \
 --seconds 60 --period 12 --stop 'route movie terminal=1 id=10030' --grace 2 --name "dd3-standard-repair5be-h2-$ARM"