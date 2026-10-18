"""m13.py STEP: Codex 2026-10-13 17:54-17:58 merchant13 chain (tree f9d5b8c5 = 4837f203^), Windows Python.
inputs | convert | finish | masks | regcast ; native runs in WSL between convert and finish (m13n.sh)."""
import os, subprocess, sys
from pathlib import Path
U = '//wsl.localhost/Ubuntu-24.04'
L = Path(U + '/root/probe/lanes-20261017r/ch2regen')
r = L / 'luis'; T = L / 't-m13/port/dreamcast/tools'; IN = r / 'm13-inputs'
os.environ['PS2CAST_INPUTS'] = str(IN); os.environ['RE4_CAST_BUNDLE'] = str(L / 'tools/cast_bundle.py')
py = [sys.executable, '-B']
step = sys.argv[1]
if step == 'inputs':
    IN.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(T)); import ps2_cast as pc
    pc.INPUTS = IN; print(pc.inputs('em13', r, pc.PS2_ISO, pc.GC_ISO)[2])
elif step == 'convert':
    for m in ('merchant13-c0', 'merchant13-o0'):
        subprocess.check_call(py + [str(T / 'ps2_cast.py'), 'convert', m, str(r / 'models' / m)], stdout=subprocess.DEVNULL)
        print(m, 'converted')
elif step == 'finish':
    for m in ('merchant13-c0', 'merchant13-o0'):
        subprocess.check_call(py + [str(T / 'ps2_cast.py'), 'finish', str(r / 'models' / m)], stdout=subprocess.DEVNULL)
elif step == 'masks':
    for m, a, b, n, k in (('c0', '0x1f0', '0x1f1', '1', 'robe'), ('c0', '0x1ee', '0x1f1', '2', 'cloth'), ('o0', '0x1f0', '0x1f1', '1', 'robe'), ('o0', '0x1ed', '0x1f1', '2', 'cloth')):
        subprocess.check_call(py + [str(T / 'ps2_mask_runs.py'), str(r / f'models/merchant13-{m}'), str(IN / 'em13.drs'), a, b, n, str(r / f'models/merchant13-{m}-mask-{k}')], stdout=subprocess.DEVNULL)
    print('masks ok')
elif step == 'regcast':
    subprocess.check_call(py + [str(T / 'ps2_cast.py'), 'regcast', str(r / 'regcast-merchant'), 'ps2-overlay', str(r / 'models/merchant13-c0'), str(r / 'models/merchant13-o0')])
