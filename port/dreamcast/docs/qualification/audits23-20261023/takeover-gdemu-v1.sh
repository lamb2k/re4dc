#!/usr/bin/env bash
set -euo pipefail
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
T=/root/work/lanes/audits23-target-on/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
SEED=${1:?seed1-10}
[[ "$SEED" =~ ^([1-9]|10)$ ]]
CAP=$E/gdemu-on-seed$SEED
[ ! -e "$CAP" ]
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16 TRACE_LOCK_OWNER=audits23-gdemu$SEED RE4DC_GD_PROFILE=gdemu RE4DC_GD_JITTER=20000 RE4DC_GD_SEED=$SEED
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT:RE4DC_GD_PROFILE:RE4DC_GD_JITTER:RE4DC_GD_SEED"
SYMS=$(cat "$E/identities/on-g-syms.txt")
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --base "$(wslpath -w "$E/_discs/on-g")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --warp "$(wslpath -w "$T/fullplay/segments/door103-warp.txt")" --seconds 45 --stop 'phase=enter room=103' --grace 15 --period 15 --name audits23-gdemu$SEED
python3 - "$CAP" <<'PY'
import pathlib,re,json,sys
p=pathlib.Path(sys.argv[1]);s=(p/'run-output.txt').read_text(errors='replace').replace('\0','')
bad=re.findall(r'MISSING|DISC READ FAILED|short read|open failed|read failed|BAD-READ|DISCNOTE: (?:disc: .*?(?:busy|timeout|abort|not accepted|late|did not land|failed|reinit|pio)|snd: stream table (?:bad|still))|HALT|FAULT|Out of memory',s)
r=json.loads((p/'run-result.json').read_text());b=json.loads((p/'bounded-launch.json').read_text());logs=''.join(x.read_text(errors='replace') for x in p.glob('serial*.txt'))+(p/'flycast.log').read_text(errors='replace')
z={'room103':s.count('phase=enter room=103'),'bad_reads_or_stops':bad,'profile':re.findall(r'GDCONSOLE profile=\w+',logs),'emu_env':r['emu_env'],'deadline_fired':b['deadline_fired'],'errors':r['errors']}
z['pass']=z['room103']>0 and not bad and not z['deadline_fired'] and not z['errors'] and 'GDCONSOLE profile=gdemu' in z['profile']
(p/'gate.json').write_text(json.dumps(z,indent=2)+'\n');print(json.dumps(z));assert z['pass'],z
PY
