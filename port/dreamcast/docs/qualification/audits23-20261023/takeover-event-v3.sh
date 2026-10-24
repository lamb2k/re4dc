#!/usr/bin/env bash
set -euo pipefail
MODE=${1:?r117/dam};case "$MODE" in r117|dam);;*)exit 2;;esac
A='/mnt/c/Game Dev/Emulators/codex-lanes/audits23'
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
T=/root/work/lanes/audits23-target-on/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
F=$A/event-fixtures
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
CAP=$E/event-$MODE-on-r3
[ ! -e "$CAP" ];[ -s "$E/_discs/on-g/base.json" ]
if [ "$MODE" = r117 ];then WF=$F/r117-light-solve-warp.txt;EXTRA=(--pad "$(wslpath -w "$F/r117-light-solve-idle180-pad.txt")");else WF=$F/r10c-first-villager-warp.txt;EXTRA=();fi
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16 TRACE_LOCK_OWNER=audits23-event-$MODE
export AUD23_CAPTURE_STILLS=1
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT:AUD23_CAPTURE_STILLS"
SYMS=$(cat "$E/identities/on-g-syms.txt")
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$A/aud23-event-observer-v3.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" "$(wslpath -w "$F/on-5e4d-symbols-v3.json")" "$MODE" --base "$(wslpath -w "$E/_discs/on-g")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --warp "$(wslpath -w "$WF")" "${EXTRA[@]}" --seconds 53 --period 0 --name audits23-event-$MODE
python3 - "$CAP" <<'PY'
import pathlib,sys,json,re
p=pathlib.Path(sys.argv[1]);r=json.loads((p/'run-result.json').read_text());b=json.loads((p/'bounded-launch.json').read_text());w=json.loads((p/'aud23-event-observation.json').read_text());s=(p/'run-output.txt').read_text(errors='replace')
print(json.dumps({'mode':w['mode'],'elapsed_s':r['elapsed_s'],'summary':w['summary'],'unknown_samples':w['unknown_samples'],'samples':w['samples'],'deadline_fired':b['deadline_fired'],'errors':r['errors']},indent=2))
assert not b['deadline_fired'] and not r['errors']
assert not re.search('HALT|FAULT|MISSING|Out of memory',s)
# Source-state observations alone are not an automatic acceptance gate.
PY