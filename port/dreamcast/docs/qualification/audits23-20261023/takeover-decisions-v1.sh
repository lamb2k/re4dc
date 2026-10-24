#!/usr/bin/env bash
set -euo pipefail
SC=${1:?bell/mendez};case "$SC" in bell|mendez);;*)exit 2;;esac
T=/root/work/lanes/audits23-target-on/port/dreamcast/tools/d367
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
S='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
F='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23-20261023/mendez-bounded-itemack-r3'
CAP=$E/decisions-$SC-on-r1
[ ! -e "$CAP" ]
if [ "$SC" = bell ];then WF=$T/fullplay/segments/bell-trg-warp.txt;PAD=();STOP='route movie terminal=1 id=10130';REF=$S/decisions-bell-on/run-output.txt;else
 WF=$F/mendez-bounded-warp.txt;PAD=(--pad "$(wslpath -w "$F/mendez-bounded-pad.txt")");STOP='phase=enter room=10f';REF=$S/mendez-bounded-on-r3/run-output.txt
fi
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16 TRACE_LOCK_OWNER=audits23-$SC
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
SYMS=$(cat "$E/identities/on-t-syms.txt")
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --base "$(wslpath -w "$E/_discs/on-t")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --warp "$(wslpath -w "$WF")" "${PAD[@]}" --seconds 53 --period 0 --stop "$STOP" --grace 2 --name audits23-$SC
python3 "$T/../game30/decision_cmp.py" "$REF" "$CAP/run-output.txt" --align frame --json "$E/decisions-$SC-comparison.json" > "$E/decisions-$SC-comparison.txt" 2>&1
cat "$E/decisions-$SC-comparison.txt"
python3 - "$CAP" "$SC" <<'PY'
import pathlib,sys,json,re
p=pathlib.Path(sys.argv[1]);scene=sys.argv[2];s=(p/'run-output.txt').read_text(errors='replace').replace('\0','');r=json.loads((p/'run-result.json').read_text());b=json.loads((p/'bounded-launch.json').read_text())
assert r['stopped']=='goal' and not r['errors'] and not b['deadline_fired']
assert not re.search(r'HALT|FAULT|MISSING|Out of memory',s)
if scene=='mendez':
 assert 'phase=enter room=10f' in s
 for id,n in [('11f02',1067),('11f10',265),('11f11',321)]:assert re.search(f'route movie terminal=1 id={id} frames={n}/{n}',s),id
 assert len(re.findall('warp: kill 0x35 hp<=0',s))==2
print('AUDIT_DECISIONS_ROUTE_PASS',scene)
PY