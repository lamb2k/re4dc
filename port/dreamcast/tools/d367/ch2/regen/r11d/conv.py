"""conv.py TREE INPUTS ARCHIVE PRESET OUTDIR [convert args...] | conv.py finish TREE OUTDIR | conv.py regcast TREE CAST MODEL...
| conv.py mask TREE MODEL DRS A B SEC OUT  (Windows Python; ps2_cast.py replays, lane ch2regen)."""
import os, subprocess, sys
from pathlib import Path
U = '//wsl.localhost/Ubuntu-24.04'
L = Path(U + '/root/probe/lanes-20261017r/ch2regen')
os.environ['RE4_CAST_BUNDLE'] = str(L / 'tools/cast_bundle.py')
py = [sys.executable, '-B']
a = sys.argv[1:]
if a[0] == 'finish':
    T = L / a[1] / 'port/dreamcast/tools'
    subprocess.check_call(py + [str(T / 'ps2_cast.py'), 'finish', a[2]], stdout=subprocess.DEVNULL); print('finished', a[2])
elif a[0] == 'regcast':
    T = L / a[1] / 'port/dreamcast/tools'
    subprocess.check_call(py + [str(T / 'ps2_cast.py'), 'regcast', a[2], 'ps2-overlay'] + a[3:])
elif a[0] == 'mask':
    T = L / a[1] / 'port/dreamcast/tools'
    subprocess.check_call(py + [str(T / 'ps2_mask_runs.py')] + a[2:], stdout=subprocess.DEVNULL); print('mask', a[-1])
else:
    tree, inputs, arch, preset, out = a[:5]
    T = L / tree / 'port/dreamcast/tools'
    os.environ['PS2CAST_INPUTS'] = inputs
    Path(inputs).mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(T)); import ps2_cast as pc
    pc.INPUTS = Path(inputs)
    if not (Path(inputs) / (arch + '.drs')).exists():
        print(pc.inputs(arch, L, pc.PS2_ISO, pc.GC_ISO)[2]['gc']['sha256'][:16])
    r = subprocess.run(py + [str(T / 'ps2_cast.py'), 'convert', preset, out] + a[5:], capture_output=True, text=True)
    if r.returncode: print(r.stdout[-1500:], r.stderr[-2500:]); sys.exit(1)
    print('converted', preset)
