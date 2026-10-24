#!/usr/bin/env bash
set -euo pipefail
MODE=${1:?r101/r10c/r117/r200/h2/kos}
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
T=/root/work/lanes/audits23-target-diag/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
CAP=$E/diag-$MODE-r1
[ ! -e "$CAP" ]
case "$MODE" in
 r101|r10c|r117|r200)WF=$E/census-on/_fixtures/$MODE.txt;ARGS=(--warp "$(wslpath -w "$WF")");SECONDS_GUEST=40;;
 h2)ARGS=(--warp "$(wslpath -w "$T/fullplay/segments/h2-warp.txt")" --pad "$(wslpath -w "$T/fullplay/segments/h2-pad.txt")" --stop 'route movie terminal=1 id=10030' --grace 2);SECONDS_GUEST=45;;
 kos)WF=$E/_fixtures/diag-kos-49152-0.txt;mkdir -p "$E/_fixtures";{ echo 'squeeze 49152 0';tr -d '\r' < "$T/fullplay/segments/kos-fight-warp.txt"; } > "$WF";ARGS=(--warp "$(wslpath -w "$WF")");SECONDS_GUEST=45;;
 *)exit 2;;
esac
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
SYMS=$(cat "$E/identities/on-d-syms.txt")
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16 TRACE_LOCK_OWNER=audits23-diag-$MODE
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --base "$(wslpath -w "$E/_discs/on-d")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --seconds "$SECONDS_GUEST" --period 15 --name audits23-diag-$MODE "${ARGS[@]}"
python3 - "$CAP" <<'PY'
import pathlib,json,re,sys
p=pathlib.Path(sys.argv[1]);s=(p/'run-output.txt').read_text(errors='replace');r=json.loads((p/'run-result.json').read_text());b=json.loads((p/'bounded-launch.json').read_text())
assert not r['errors'] and not b['deadline_fired']
assert not re.search('HALT|FAULT|MISSING|Out of memory',s)
print('DIAG_CAPTURE_COMPLETE',p.name,'lines',sum(x.startswith('cachep2diag ') for x in s.splitlines()))
PY