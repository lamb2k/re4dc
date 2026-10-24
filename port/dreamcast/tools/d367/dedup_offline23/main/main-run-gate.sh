#!/bin/bash
set -euo pipefail
GATE=${1:?kos0 kos1 cg100 cg101 cg103 gdemu s30}
TR=/root/work/lanes/dedup-offline23-integration
T=$TR/port/dreamcast/tools/d367
EV='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023'
EW='C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023'
mkdir -p "$EV/fixtures"
FIX="$EV/fixtures/$GATE.txt"
[ ! -e "$FIX" ]
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1
case "$GATE" in
 kos0|kos1) printf 'squeeze 49152 %s\n' "${GATE#kos}" > "$FIX"; tr -d '\r' < "$T/fullplay/segments/kos-fight-warp.txt" >> "$FIX";;
 cg100|cg101|cg103) tr -d '\r' < "$T/castgc/warps/r${GATE#cg}.txt" > "$FIX";;
 gdemu) tr -d '\r' < "$T/fullplay/segments/door103-warp.txt" > "$FIX"; export RE4DC_GD_PROFILE=gdemu RE4DC_GD_SEED=1 RE4DC_GD_JITTER=20000;;
 s30) tr -d '\r' < '/mnt/c/Game Dev/Emulators/codex-lanes/world-scratch23/native-memory813/fixtures/s30-only.txt' > "$FIX";;
 *)exit 2;;
esac
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 21474836480 ]
SYMS=$(cat /root/probe/lanes/route/out-fpdd23diagW/syms.txt)
export TRACE_LOCK_OWNER=codex-dedup-offline23 TRACE_SLOTS=16
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT:RE4DC_GD_PROFILE:RE4DC_GD_SEED:RE4DC_GD_JITTER"
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
"$P" -c 'import os; assert os.environ.get("RE4DC_EMU")=="console"; print("WINDOWS_ENV_CONSOLE_VERIFIED")'
bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$T/fullplay/fp_run.py")" \
 --base "${EW}\base-diag" --cap "${EW}\\gate-${GATE}-r1" --syms "$SYMS" --warp "$(wslpath -w "$FIX")" \
 --seconds 60 --period 6 --name "dd3-gate-$GATE"
