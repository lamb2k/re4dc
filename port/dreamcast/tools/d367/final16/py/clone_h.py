"""clone_h.py <src-harness> <dst-harness> <arm label> <build dir>: lane final16 copy of ch5found16's clone_h.py
(the st3 lane's hash-checked harness copy + this lane's programs), discs staged under the lane's ext4 dir."""
import hashlib, json, shutil, sys
from pathlib import Path
src, dst, label, B = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
arm = 'candidate-route' + label
assert not dst.exists(), dst
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
prov = json.loads((src / 'cx-harness-provenance.json').read_text())
dst.mkdir(parents=True)
for name in ('stage-scenario.py', 'stage-scenario-v2.py', 'stage-scenario-v2.provenance.json', 'run-emulator-novsync.py'):
    shutil.copy2(src / name, dst / name)
v2 = (dst / 'stage-scenario-v2.py').read_text()
old = "DISCROOT=Path('/root/probe/lanes-20261014/st3/discs')"
assert old in v2
(dst / 'stage-scenario-v2.py').write_text(v2.replace(old, "DISCROOT=Path('/root/probe/lanes-20261016/final16/discs')  # lane final16"))
shutil.copytree(src / 'source-snapshots', dst / 'source-snapshots')
(dst / 'scenarios').mkdir()
routes = json.loads((B / 'programs-route.json').read_text())
entry = routes[arm]
pd = dst / 'programs' / arm
pd.mkdir(parents=True)
installed = {k: v for k, v in prov['installed_files'].items() if not k.startswith('programs/')}
for name, meta in entry['files'].items():
    s = B / 'programs' / arm / name
    assert sha(s) == meta['sha256'], name
    shutil.copy2(s, pd / name)
    installed['programs/%s/%s' % (arm, name)] = meta['sha256']
for name in ('stage-scenario-v2.py',):
    installed[name] = sha(dst / name)
(dst / 'programs-route.json').write_text(json.dumps({arm: entry}, indent=2) + '\n')
shutil.copy2(entry['resolved_knobs'], dst / 'cx-resolved-knobs.txt')
prov.update(output_root=str(dst), arm=arm, installed_files=installed, cloned_from=str(src),
            clone_reason='lane final16: st3 lane harness (ext4 stager) with this lane\'s arm and disc root')
prov['resolved_diagnostics'] = {k: v for k, v in (l.split('=', 1) for l in (dst / 'cx-resolved-knobs.txt').read_text().split('\n') if '=' in l)
                                if k in prov.get('resolved_diagnostics', {})}
(dst / 'cx-harness-provenance.json').write_text(json.dumps(prov, indent=2) + '\n')
(dst / 'PURPOSE.txt').write_text('lane final16 2026-10-16: the final boss room r332 (Saddler em31, ROUTE_FINAL) on the island base, arm %s. Flycast only.\n' % label)
print(json.dumps(dict(status='PRIVATE_HARNESS_READY', arm=arm, diagnostics=prov['resolved_diagnostics'])))
