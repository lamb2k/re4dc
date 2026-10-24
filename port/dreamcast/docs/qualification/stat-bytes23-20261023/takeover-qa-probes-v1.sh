#!/usr/bin/env bash
set -euo pipefail
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
T=/root/work/lanes/stat-bytes23-complete/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
B=$E/qa/_discs/qa
[ -s "$B/base.json" ]
O=/root/probe/lanes/route/out-rr2a14662qrW
SYMS=$(cat "$O/syms.txt")
mkdir -p "$E/_fixtures"
KF=$E/_fixtures/qa-boot-keys.txt
printf '%s\n' 'presets in | 2 | down' '- | 1 | a' '- | 1 | a' '- | 1 | a' > "$KF"
WF=$E/_fixtures/qa-menu-warp.txt
printf '%s\n' 'name r101' 'room 0x101' 'pos -7914 0 -254' 'ang 2.9600' 'find 0x00002000' 'inv default' 'qa_menu 300 r103.txt 800' > "$WF"
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
for SC in boot warp h2;do
 CAP=$E/qa-$SC-r1
 [ ! -e "$CAP" ]
 case "$SC" in
 boot) ARGS=(--keys "$(wslpath -w "$KF")" --stop 'room enter|phase=enter' --grace 15);;
 warp) ARGS=(--warp "$(wslpath -w "$WF")" --stop 'phase=enter room=103' --grace 10);;
 h2) ARGS=(--warp "$(wslpath -w "$T/fullplay/segments/h2-warp.txt")" --pad "$(wslpath -w "$T/fullplay/segments/h2-pad.txt")" --stop 'route movie terminal=1 id=10030' --grace 2);;
 esac
 TRACE_LOCK_OWNER=stat23-qa-$SC bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --base "$(wslpath -w "$B")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --seconds 45 --period 12 --name stat23-qa-$SC "${ARGS[@]}"
done
