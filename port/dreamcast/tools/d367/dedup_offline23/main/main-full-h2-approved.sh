#!/bin/bash
set -euo pipefail
# User explicitly authorized one OFF/ON H2 pair, <=240 seconds each, on 2026-10-23.
ARM=${1:?on or off}
TR=/root/work/lanes/dedup-offline23-integration
T=$TR/port/dreamcast/tools/d367
EW='C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023'
case "$ARM" in on) LABEL=dd23af09on2rW;;off) LABEL=dd23af09offrW;;*)exit 2;;esac
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 21474836480 ]
SYMS=$(cat /root/probe/lanes/route/out-$LABEL/syms.txt)
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_LOCK_OWNER=codex-dedup-offline23-h2 TRACE_SLOTS=16
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
"$P" -c 'import os; assert os.environ.get("RE4DC_EMU")=="console"'
bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$T/fullplay/fp_run.py")" \
 --base "$EW\base-$ARM" --cap "${EW}\\full-h2-${ARM}-console-r1" --syms "$SYMS" \
 --warp "$(wslpath -w "$T/fullplay/segments/h2-warp.txt")" --pad "$(wslpath -w "$T/fullplay/segments/h2-pad.txt")" \
 --seconds 240 --period 12 --stop 'route movie terminal=1 id=10030' --grace 5 --name "dd3-full-h2-$ARM"
