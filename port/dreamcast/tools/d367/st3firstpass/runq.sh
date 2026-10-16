#!/bin/bash
# runq.sh <harness-dir-name> <room> <suffix> <fixture variant>  (Git Bash): wait for a free Flycast slot (<8 total) and C: >= 20 GB, then run one scenario.
[ -f /c/Users/lambd/.claude/jobs/1e668c67/tmp/st3/HOLD ] && { echo "{\"room\":\"$2\",\"status\":\"HELD_BY_COORDINATOR\"}"; exit 4; }
H=$1; R=$2; SUF=$3; V=$4
n=0
while :; do
  c=$(tasklist 2>/dev/null | grep -ci flycast)
  f=$(python -c "import shutil;print(int(shutil.disk_usage('C:/').free/1e9))")
  [ "$c" -lt 7 ] && [ "$f" -ge 16 ] && break
  sleep 30; n=$((n+1)); [ $n -ge 240 ] && { echo "{\"room\":\"$R\",\"status\":\"WAIT_TIMEOUT\",\"flycasts\":$c,\"free_gb\":$f}"; exit 3; }
done
cd /tmp && RE4DC_MAX_FLYCASTS=8 MSYS_NO_PATHCONV=1 timeout 900 python "C:/Users/lambd/.claude/skills/re4-room-firstpass/scripts/rfp-run-one.py" --harness "C:/Game Dev/Emulators/$H" --room $R --view ${VIEW:-walk} ${SECS:+--seconds $SECS} --fixture /root/probe/lanes-20261014/st3/fixtures/$R/cx-$R-${VIEW:-walk}-$V.armed.json --tree /root/probe/lanes-20261014/st3/tree --suffix $SUF --stager stage-scenario-v2.py --min-free-gb 15.0 > /tmp/runq-$R-$SUF.json 2>&1
P="C:/Game Dev/Emulators/$H/scenarios/cx-$R-${VIEW:-walk}-$SUF"
python - "$P" <<'PY'
import json,sys,os,glob
p=sys.argv[1]
try: d=json.load(open(p+'/rfp-result.json')); print(json.dumps({k:d.get(k) for k in ('scenario','checks','overall','discs_removed','disc_sha256')}))
except Exception as e: print('NO_RESULT', p, e)
for b in glob.glob(p+'/**/disc.bin', recursive=True): os.remove(b); print('removed', b)
PY
# st3 lane (10-15): discs are staged on WSL ext4; delete this scenario's ext4 disc after the run (sha256 kept in stage.json).
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- rm -rf "/root/probe/lanes-20261014/st3/discs/cx-$R-${VIEW:-walk}-$SUF"
