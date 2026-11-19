#!/bin/bash
# run.sh <variant> <suffix> [seconds] (Git Bash): one <=60 s Flycast run of fixture fx-r332-<variant> on harness h-$ARM;
# the staged ext4 disc and the captured disc.bin are deleted after the run (lane final16).
V=$1; SUF=$2; S=${3:-60}
ARM=${ARM:-f1mW}
H="C:/Flycast-Evidence/re4-dreamcast/final16-20261016/h-$ARM"
cd /tmp && RE4DC_MAX_FLYCASTS=16 MSYS_NO_PATHCONV=1 timeout 900 python "${RUNPY:-C:/Users/lambd/.claude/skills/re4-room-firstpass/scripts/rfp-run-one.py}" --harness "$H" --room r332 --view fight --seconds $S --fixture /root/probe/lanes-20261016/final16/fixtures/r332/fx-r332-$V.armed.json --tree /root/probe/lanes-20261016/final16/tree --suffix $SUF --stager stage-scenario-v2.py --min-free-gb ${MINGB:-12.0} > /tmp/f16run-$SUF.json 2>&1
echo "rc=$?"
P="$H/scenarios/cx-r332-fight-$SUF"
python - "$P" <<'PY'
import json,sys,os,glob
p=sys.argv[1]
try: d=json.load(open(p+'/rfp-result.json')); print(json.dumps({k:d.get(k) for k in ('scenario','checks','overall','disc_sha256')})[:1500])
except Exception as e: print('NO_RESULT', p, e)
for b in glob.glob(p+'/**/disc.bin', recursive=True): os.remove(b); print('removed', b)
PY
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- rm -rf "/root/probe/lanes-20261016/final16/discs/cx-r332-fight-$SUF"
tail -3 /tmp/f16run-$SUF.json
