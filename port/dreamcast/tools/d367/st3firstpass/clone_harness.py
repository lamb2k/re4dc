"""clone_harness.py <src-harness> <dst-harness> <arm label>  (WSL python3)

Lane adapter (the coordinator's round-1 OK to adapt private worker scripts): cx_harness_install.py refuses since the
source harness's stage-scenario.py became the ext4 front door. This clones an already-installed lane harness (its
stage-scenario*.py / run-emulator-novsync.py / snapshots, unchanged and hash-checked against its provenance) and
installs another arm's programs from the build's programs-route.json, exactly as the installer lays them out.
"""
import hashlib, json, shutil, sys
from pathlib import Path

src, dst, label = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
arm = 'candidate-route' + label
B = Path('/root/probe/lanes-20261014/st3/build')
assert not dst.exists(), dst
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
prov = json.loads((src / 'cx-harness-provenance.json').read_text())
for name, h in prov['installed_files'].items():
    if not name.startswith('programs/'):
        assert sha(src / name) == h, name
dst.mkdir(parents=True)
for name in ('stage-scenario.py', 'stage-scenario-v2.py', 'stage-scenario-v2.provenance.json', 'run-emulator-novsync.py'):
    shutil.copy2(src / name, dst / name)
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
(dst / 'programs-route.json').write_text(json.dumps({arm: entry}, indent=2) + '\n')
shutil.copy2(entry['resolved_knobs'], dst / 'cx-resolved-knobs.txt')
prov.update(output_root=str(dst), arm=arm, installed_files=installed,
            cloned_from=str(src), clone_reason='cx_harness_install refuses the ext4 front-door source; lane adapter')
prov['resolved_diagnostics'] = {k: v for k, v in (l.split('=', 1) for l in (dst / 'cx-resolved-knobs.txt').read_text().split('\n') if '=' in l)
                                if k in prov.get('resolved_diagnostics', {})}
(dst / 'cx-harness-provenance.json').write_text(json.dumps(prov, indent=2) + '\n')
print(json.dumps(dict(status='PRIVATE_HARNESS_READY', arm=arm, diagnostics=prov['resolved_diagnostics'])))
