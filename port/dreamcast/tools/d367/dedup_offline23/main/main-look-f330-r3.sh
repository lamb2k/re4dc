#!/bin/bash
set -euo pipefail
ARM=${1:?on or off}; SCENE=${2:?cross farm forest}
TR=/root/work/lanes/dedup-offline23-integration
T=$TR/port/dreamcast/tools/d367
EV='C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023'
case "$ARM" in on) LABEL=dd23af09on2rW;;off) LABEL=dd23af09offrW;;*)exit 2;;esac
case "$SCENE" in cross|farm|forest);;*)exit 2;;esac
FIX="C:\Game Dev\Emulators\codex-lanes\dedup-offline23\\${SCENE}-f330.txt"
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 21474836480 ]
SYMS=$(cat /root/probe/lanes/route/out-$LABEL/syms.txt)
HARNESS=$(wslpath -w "$T/fullplay/fp_run.py")
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 TRACE_LOCK_OWNER=codex-dedup-offline23 TRACE_SLOTS=16
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS"
/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe -c 'import os; assert os.environ.get("RE4DC_EMU")=="console"'
bash "$T/trace_lock.sh" /mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe "$HARNESS" \
 --base "$EV\base-$ARM" --cap "${EV}\\${SCENE}-${ARM}-console-f330-r3" --syms "$SYMS" --warp "$FIX" \
 --seconds 54 --period 4 --stop 'warp: frozen at tick 330' --grace 8 --name "dd3-$SCENE-$ARM-f330"
