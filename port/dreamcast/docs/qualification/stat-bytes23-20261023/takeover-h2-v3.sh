#!/usr/bin/env bash
set -euo pipefail
ARM=${1:?off or on};case "$ARM" in off|on);;*)exit 2;;esac
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
T=/root/work/lanes/stat-bytes23-complete/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
EW='C:\Flycast-Evidence\re4-dreamcast\stat-bytes23\takeover-2a14662d'
B="$E/_discs/$ARM-g"
[ ! -e "$E/h2-$ARM" ]
[ -s "$B/base.json" ] || bash "$D/takeover-stage-v2.sh" "$ARM" g
SYMS=$(cat "$E/identities/$ARM-g-syms.txt")
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_LOCK_OWNER=codex-stat23-h2-$ARM TRACE_SLOTS=16
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
"$P" -c 'import os; assert os.environ.get("RE4DC_EMU")=="console"; assert os.environ.get("FP_NOLIMIT")=="1"; print("CONSOLE_ENV_VERIFIED")'
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" \
 --base "$(wslpath -w "$B")" --cap "$(wslpath -w "$E/h2-$ARM")" --syms "$SYMS" \
 --warp "$(wslpath -w "$T/fullplay/segments/h2-warp.txt")" --pad "$(wslpath -w "$T/fullplay/segments/h2-pad.txt")" \
 --seconds 45 --period 12 --stop 'route movie terminal=1 id=10030' --grace 2 --name "stat23-h2-$ARM"
python3 - "$E/h2-$ARM/run-output.txt" <<'PY'
import pathlib,re,sys,json
p=pathlib.Path(sys.argv[1]);s=p.read_text(errors='replace').replace('\0','')
rows=[x for x in s.splitlines() if '10030' in x and ('movie' in x or 'heap_before' in x)]
print('\n'.join(rows[-10:]))
print('STOP_LINES',len(re.findall(r'HALT|FAULT|Out of memory|MISSING',s)))
PY
