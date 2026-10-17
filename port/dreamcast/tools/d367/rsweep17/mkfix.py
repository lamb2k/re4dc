#!/usr/bin/env python3
"""rsweep17: per-room render-sweep fixtures. Warps = tools/d367/castgc/warps/<room>.txt (castgc17) with a walk
(act 300 fwd 20) added when the warp has no act line; fixture via t11-fix.py + texchk/fixture_arm.py (stage overlays)."""
import os, subprocess, sys
from pathlib import Path
TREE = Path('/root/probe/d367-agents/rsweep17/tree/port/dreamcast/tools/d367')
W = Path('/root/probe/d367-agents/rsweep17/warps'); FIX = Path('/root/probe/d367-agents/rsweep17/fix')
W.mkdir(parents=True, exist_ok=True); FIX.mkdir(parents=True, exist_ok=True)
lab = sys.argv[1]; rooms = sys.argv[2:]
data = subprocess.run([sys.executable, '-c', "import importlib.util as u;s=u.spec_from_file_location('t','%s/test11/t11-fix.py');"
                       "m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T17V_DATA)" % TREE],
                      check=True, capture_output=True, text=True).stdout.strip()
print('data', data)
env = dict(os.environ, PKG_SRC='/root/probe/lanes-20261015/t15k/pkgsrc-t14cand')
for room in rooms:
    body = (TREE / 'castgc' / 'warps' / (room + '.txt')).read_text().splitlines()
    if not any(l.strip().startswith('act ') for l in body):
        body.append('act 300 fwd 20')
    w = W / (room + '.txt'); w.write_text('\n'.join(body) + '\n')
    fx = str(FIX / ('%s-%s.json' % (room, lab)))
    r = subprocess.run([sys.executable, str(TREE / 'test11' / 't11-fix.py'), lab, fx, '--data', data, '--warp', str(w)],
                       env=env, capture_output=True, text=True)
    if r.returncode == 0:
        r = subprocess.run([sys.executable, str(TREE / 'texchk' / 'fixture_arm.py'), fx, fx + '.tmp', lab], capture_output=True, text=True)
        if r.returncode == 0:
            os.replace(fx + '.tmp', fx)
    o = (r.stdout + r.stderr).strip().splitlines()
    print(lab, room, 'rc=%d' % r.returncode, o[-1][:160] if o else '')
