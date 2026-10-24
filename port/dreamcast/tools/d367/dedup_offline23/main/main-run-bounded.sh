#!/bin/bash
set -euo pipefail
ARM=${1:?on or off}; CASE=${2:?s30 or cross}
TR=/root/work/lanes/dedup-offline23-integration
T=$TR/port/dreamcast/tools/d367
EV='C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023'
case "$ARM" in on) LABEL=dd23af09on2rW;;off) LABEL=dd23af09offrW;;*)exit 2;;esac
case "$CASE" in
 s30) FIX='C:\Game Dev\Emulators\codex-lanes\world-scratch23\native-memory813\fixtures\s30-only.txt';;
 cross) FIX='C:\Game Dev\Emulators\codex-lanes\dedup-offline23\cross-still.txt';;
 *)exit 2;;
esac
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 21474836480 ]
SYMS=$(cat /root/probe/lanes/route/out-$LABEL/syms.txt)
HARNESS=$(wslpath -w "$T/fullplay/fp_run.py")
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 TRACE_LOCK_OWNER=codex-dedup-offline23 TRACE_SLOTS=16
bash "$T/trace_lock.sh" /mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe "$HARNESS" \
 --base "$EV\base-$ARM" --cap "${EV}\\${CASE}-${ARM}-r1" --syms "$SYMS" --warp "$FIX" \
 --seconds 54 --period 4 --grace 2 --name "dd3-$CASE-$ARM"
