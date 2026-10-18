"""luis_a.py: replay of Codex 2026-10-13 Luis chain, step A (Windows Python).
1. luis-inputs = ps2_cast.inputs('pl14') with INPUTS override (extract_luis_sources.py, 18:23).
2. ps2_luis --kind gun -> models/luis-gun-v1 (tree 4837f203), validation.json texture key (18:40).
3. ps2_luis --kind actor -> models/luis-actor-v2 (orientation tree e0fc9745, 22:30)."""
import hashlib, json, subprocess, sys
from pathlib import Path
U = '//wsl.localhost/Ubuntu-24.04'
L = Path(U + '/root/probe/lanes-20261017r/ch2regen')
R = L / 'luis'
G = L / 't-luisg/port/dreamcast/tools'
O = L / 't-luiso/port/dreamcast/tools'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
step = sys.argv[1]
if step == 'inputs':
    sys.path.insert(0, str(G)); import ps2_cast as pc
    pc.INPUTS = R / 'luis-inputs'
    (R / 'luis-inputs').mkdir(parents=True, exist_ok=True)
    p, g, rec = pc.inputs('pl14', R, pc.PS2_ISO, pc.GC_ISO)
    print(json.dumps(rec))
    for f in sorted((R / 'luis-inputs').iterdir()):
        print(f.name, f.stat().st_size, sha(f)[:16])
elif step == 'gun':
    out = R / 'models/luis-gun-v1'
    subprocess.check_call([sys.executable, str(G / 'ps2_luis.py'), '--kind', 'gun', '--inputs', str(R / 'luis-inputs'), '--output', str(out), '--pack'])
    sys.path.insert(0, str(G)); import ps2_cast as pc
    a = json.loads((out / 'coverage-manifest.json').read_text())
    a['texture'] = {'key': pc.texture_key(out / 'atlas.png'), 'atlas': a['atlas']['size'], 'alpha_contract': 'Original opacity images retained separately; native mask runs pending'}
    (out / 'validation.json').write_text(json.dumps(a, indent=2)); print('gun key', a['texture']['key'])
elif step == 'actor2':
    out = R / 'models/luis-actor-v2'
    subprocess.check_call([sys.executable, str(O / 'ps2_luis.py'), '--kind', 'actor', '--inputs', str(R / 'luis-inputs'), '--output', str(out), '--pack'])
    print('coverage', sha(out / 'coverage-manifest.json'))
