#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23-target-on/port/dreamcast/tools/d367
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
B=$E/_discs/on-c
FRAG=${1:?0 or 1};case "$FRAG" in 0|1);;*)exit 2;;esac
CAP=$E/kos-on-49152-$FRAG
[ ! -e "$CAP" ]
[ -s "$B/base.json" ]
mkdir -p "$E/_fixtures"
WF=$E/_fixtures/kos-49152-$FRAG.txt
{ echo "squeeze 49152 $FRAG";tr -d '\r' < "$T/fullplay/segments/kos-fight-warp.txt"; } > "$WF"
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_LOCK_OWNER=codex-audits23-kos-$FRAG TRACE_SLOTS=16
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
SYMS=$(cat "$E/identities/on-c-syms.txt")
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --base "$(wslpath -w "$B")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --warp "$(wslpath -w "$WF")" --seconds 45 --period 15 --name "audits23-kos-$FRAG"
python3 - "$CAP" <<'PY'
import pathlib,re,json,sys
p=pathlib.Path(sys.argv[1]);s=(p/'run-output.txt').read_text(errors='replace').replace('\0','')
head=[int(x) for x in re.findall(r'kos watch:[^\n]*headroom=(\d+)',s)]
held=re.findall(r'kos squeeze:[^\n]*held=(\d+)',s)
bad=re.findall(r'HALT|FAULT|MISSING|Out of memory',s)
bound=json.loads((p/'bounded-launch.json').read_text());run=json.loads((p/'run-result.json').read_text())
r={'min_headroom':min(head) if head else None,'held':held,'stop_lines':bad,'end_marker':bool(re.search(r'warp: alert at room frame',s)),'deadline_fired':bound['deadline_fired'],'run_errors':run['errors']}
r['pass']=bool(head) and min(head)>=4096 and held and int(held[0])==49152 and not bad and r['end_marker'] and not r['deadline_fired'] and not r['run_errors']
(p/'gate.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));assert r['pass'],r
PY
