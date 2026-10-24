#!/bin/bash
set -euo pipefail
ARM=${1:?off/on};KIND=${2:?boot/warp/h2}
case "$ARM" in off|on);;*)exit 2;;esac
case "$KIND" in boot|warp|h2);;*)exit 2;;esac
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
. "$OWN/current-d5c-pins.sh"
T=$TREE/port/dreamcast/tools/d367
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ];[ -z "$(git -C "$TREE" status --porcelain --untracked-files=no)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
exec 7>"$WORK/guest.lock";flock -n 7 || { echo OWN_GUEST_BUSY;exit 2; }
O=/root/probe/lanes/route/out-dd234be08e01${ARM}qrW
[ "$(cat "$O/stack.txt")" = "$SOURCE" ];[ ! -s "$O/missing.txt" ]
FIX=$EVIDENCE/qa-media-r1/fixtures;mkdir -p "$FIX"
KF=$FIX/qa-boot-keys.txt
if [ ! -e "$KF" ];then
 printf '%s\n' 'qa: screen 0 | 2 | down 0.03' '- | 0.5 | a 0.03' 'qa: screen 1 | 0.5 | a 0.03' 'qa: screen 2 | 0.5 | a 0.03' > "$KF"
 printf '%s\n' 'name r101' 'room 0x101' 'pos -7914 0 -254' 'ang 2.9600' 'find 0x00002000' 'inv default' 'qa_menu 300 r103.txt 800' > "$FIX/qa-menu-warp.txt"
fi
CAP=$EVIDENCE/qa-$ARM-$KIND-console-r1;[ ! -e "$CAP" ]
case "$ARM" in off) PRIVATE='/mnt/c/Game Dev/Emulators/RE4DC-QA23-Dedup-Off-4be08e01';;on) PRIVATE='/mnt/c/Game Dev/Emulators/RE4DC-QA23-Dedup-On-4be08e01';;esac
if [ "$KIND" = boot ];then
 ARGS=(--disc "$(wslpath -w "$PRIVATE/gdemu")" --keys "$(wslpath -w "$KF")" --stop 'qa: boot choice /cd/dc/qa/' --grace 15)
elif [ "$KIND" = warp ];then
 ARGS=(--base "$(wslpath -w "$EVIDENCE/qa-proxy-$ARM-r1")" --warp "$(wslpath -w "$FIX/qa-menu-warp.txt")" --stop 'phase=enter room=103' --grace 3)
else
 ARGS=(--base "$(wslpath -w "$EVIDENCE/qa-proxy-$ARM-r1")" --warp "$(wslpath -w "$T/fullplay/segments/h2-warp.txt")" --pad "$(wslpath -w "$T/fullplay/segments/h2-pad.txt")" --stop 'route movie terminal=1 id=10030' --grace 2)
fi
export RE4DC_EMU=console RE4DC_CONSOLE_EXE='C:\\Flycast-Evidence\\re4-dreamcast\\flycast-console-bin\\flycast-console.exe'
export RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16 TRACE_LOCK_OWNER=dedup-current4be-qa-$ARM-$KIND
export RE4DC_GD_PROFILE='' RE4DC_GD_JITTER='' RE4DC_GD_SEED='' PYTHONDONTWRITEBYTECODE=1
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_CONSOLE_EXE:RE4DC_MAX_FLYCASTS:FP_NOLIMIT:PYTHONDONTWRITEBYTECODE:RE4DC_GD_PROFILE:RE4DC_GD_JITTER:RE4DC_GD_SEED"
"$P" -c 'import os;assert os.environ.get("RE4DC_EMU")=="console";assert os.environ.get("FP_NOLIMIT")=="1";assert not os.environ.get("RE4DC_GD_PROFILE");print("QA_CONSOLE_NOLIMIT_ENV_VERIFIED")'
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --cap "$(wslpath -w "$CAP")" --syms "$(cat "$O/syms.txt")" --seconds 50 --period 10 --name "dedup-current4be-qa-$ARM-$KIND" "${ARGS[@]}"
python3 "$OWN/current-d5c-qa-judge.py" "$ARM" "$KIND"

