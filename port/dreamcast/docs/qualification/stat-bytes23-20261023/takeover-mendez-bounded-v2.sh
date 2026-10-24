#!/usr/bin/env bash
set -euo pipefail
ARM=${1:?off or on};case "$ARM" in off|on);;*)exit 2;;esac
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
T=/root/work/lanes/stat-bytes23-complete/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
F='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23-20261023/mendez-bounded-proposal'
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
CAP=$E/mendez-bounded-$ARM-r2
[ ! -e "$CAP" ]
(cd "$F" && sha256sum -c SHA256SUMS)
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16 TRACE_LOCK_OWNER=stat23-mendez-bounded-$ARM
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
SYMS=$(cat "$E/identities/$ARM-t-syms.txt")
case "$ARM" in off) PPL=0x8c363a20;PG=0x8c2b325c;;on) PPL=0x8c3639c0;PG=0x8c2b31fc;;esac
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$D/mendez-window-observer.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" "$PPL" "$PG" --base "$(wslpath -w "$E/_discs/$ARM-t")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --warp "$(wslpath -w "$F/mendez-bounded-warp.txt")" --pad "$(wslpath -w "$F/mendez-bounded-pad.txt")" --seconds 53 --period 0 --stop 'phase=enter room=10f' --grace 2 --name "stat23-mendez-bounded-$ARM"
python3 - "$CAP" <<'PY'
import pathlib,sys,re,json
p=pathlib.Path(sys.argv[1]);s=(p/'run-output.txt').read_text(errors='replace').replace('\0','')
for x in s.splitlines():
 if re.search(r'route movie terminal|warp: goto|phase=enter room=10f|warp: act|PAD.*(?:goto|state)|HALT|FAULT|MISSING',x):print(x)
b=json.loads((p/'bounded-launch.json').read_text());print('DEADLINE',b['deadline_fired'])
PY
