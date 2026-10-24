#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import pathlib,subprocess,json
T=pathlib.Path('/root/work/lanes/stat-bytes23-complete/port/dreamcast/tools/game30');E=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d')
control=E/'mendez-camera-control-r1/run-output.txt';out={}
for n,left,right in [('off-control',E/'mendez-bounded-off-r3/run-output.txt',control),('on-control',E/'mendez-bounded-on-r3/run-output.txt',control)]:
 p=subprocess.run(['python3',str(T/'decision_cmp.py'),str(left),str(right),'--align','frame','--json',str(E/('camera-'+n+'.json'))],capture_output=True,text=True)
 (E/('camera-'+n+'.txt')).write_text(p.stdout+p.stderr);print(p.stdout);out[n]={'rc':p.returncode,'report':str(E/('camera-'+n+'.json'))}
(E/'camera-control-verdicts.json').write_text(json.dumps(out,indent=2)+'\n')
PY
