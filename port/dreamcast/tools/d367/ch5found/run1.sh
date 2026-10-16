#!/bin/bash
# run1.sh <room> <view> <variant> <suffix> [seconds] (Git Bash): one Flycast run on the ch5found16 harness; ext4 disc deleted after.
R=$1; V=$2; VAR=$3; SUF=$4; S=${5:-60}
H="C:/Flycast-Evidence/re4-dreamcast/ch5found-20261016/${HARN:-h-cx5amW}"
cd /tmp && RE4DC_MAX_FLYCASTS=16 MSYS_NO_PATHCONV=1 timeout 900 python "C:/Users/lambd/.claude/skills/re4-room-firstpass/scripts/rfp-run-one.py" --harness "$H" --room $R --view $V --seconds $S --fixture /root/probe/lanes-20261016/ch5found/fixtures/$R/cx-$R-$V-$VAR.armed.json --tree /root/probe/lanes-20261016/ch5found/tree --suffix $SUF --stager stage-scenario-v2.py --min-free-gb 15.0 > /tmp/ch5run-$R-$SUF.json 2>&1
echo "rc=$?"
P="$H/scenarios/cx-$R-$V-$SUF"
python - "$P" <<'PY'
import json,sys,os,glob
p=sys.argv[1]
try: d=json.load(open(p+'/rfp-result.json')); print(json.dumps({k:d.get(k) for k in ('scenario','checks','overall','disc_sha256')}))
except Exception as e: print('NO_RESULT', p, e)
for b in glob.glob(p+'/**/disc.bin', recursive=True): os.remove(b); print('removed', b)
PY
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- rm -rf "/root/probe/lanes-20261016/ch5found/discs/cx-$R-$V-$SUF"
tail -5 /tmp/ch5run-$R-$SUF.json
