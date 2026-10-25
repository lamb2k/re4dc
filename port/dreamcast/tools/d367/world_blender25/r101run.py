# world-blender25: r101 world arm = SMX hook (ps2_world_r4im, 256) [+ wb_filter Blender ops] -> append -> strip groups.
# usage (Windows python): r101run.py <arm>   env WB_* as wb_filter.py
import hashlib, json, os, shutil, struct, subprocess, sys
from pathlib import Path

ARM = sys.argv[1]
L = '//wsl.localhost/Ubuntu-24.04/root/work/lanes/world-blender25-scratch'
SRC = Path(L + '/r101src'); RUN = Path(L + '/r101-' + ARM)
TO = Path('//wsl.localhost/Ubuntu-24.04/root/work/lanes/world-blender25/port/dreamcast/tools')
B = Path('C:/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13')
HERE = Path(__file__).resolve().parent
assert RUN.as_posix().startswith(L + '/r101-') and ARM, RUN.as_posix()
shutil.rmtree(RUN, ignore_errors=True)
shutil.copytree(SRC, RUN)
os.environ['WB_WORK'] = '/root/work/lanes/world-blender25-scratch/r101-' + ARM
cc = RUN / 'r101/control-command.json'; j = json.loads(cc.read_text(encoding='utf-8-sig'))
old = 'asset-only-smx-r103-r101-v1'
j['argv'] = [s.replace('\\\\wsl.localhost\\Ubuntu-24.04\\root\\work\\lanes\\w2ms-scratch\\sweep13\\r101hook\\256\\' + old,
                       str(RUN).replace('/', '\\')) for s in j['argv']]
cc.write_text(json.dumps(j, indent=2) + '\n', encoding='utf-8')
hook = (RUN / 'smx_asset_candidate_scratch.py').read_text(encoding='utf-8')
o1 = "O=Path('//wsl.localhost/Ubuntu-24.04/root/work/lanes/w2ms-scratch/sweep13/r101hook/256/asset-only-smx-r103-r101-v1')"
assert hook.count(o1) == 1; hook = hook.replace(o1, "O=Path(%r)" % RUN.as_posix())
o2 = " mod.build=build\n"
assert hook.count(o2) == 1
hook = hook.replace(o2, o2 + " sys.path.insert(0,%r);import wb_filter;mod.build=wb_filter.wrap(mod.build)\n" % str(HERE))
hp = RUN / 'smx_hook_wb.py'; hp.write_text(hook, encoding='utf-8')
r = subprocess.run([sys.executable, str(hp), 'r101'], capture_output=True, text=True, cwd=str(RUN))
(RUN / 'hook.log').write_text(r.stdout + r.stderr, encoding='utf-8')
print('\n'.join(l for l in (r.stdout + r.stderr).splitlines() if l.startswith('WB_')))
assert r.returncode == 0, (r.stdout + r.stderr)[-1500:]
C = RUN / 'r101/candidate-smx-only'; A = RUN / 'append'; F = RUN / 'final'
for d in (A, F): d.mkdir()
def run(argv, log):
    r = subprocess.run([sys.executable, *map(str, argv)], capture_output=True, text=True)
    log.write_text(r.stdout + r.stderr); assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
run([TO/'ps2_world_append.py', C/'ps2-world.re4mesh', '--obj', B/'r101-bake.obj', '--materials', B/'r101-bake-materials.json',
     '--out', A, '--placement-base', 209], A/'append.log')
run([TO/'ps2_strip_groups.py', A/'ps2-world.re4mesh', A/'ps2-world.r4pw', F/'ps2-world.re4mesh', F/'ps2-world.r4sg', '--groups', 4], F/'groups.log')
shutil.copy2(A/'ps2-world.r4pw', F)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for f in sorted(F.glob('ps2-world.*')): print(' ', f.name, f.stat().st_size, sha(f)[:16])
h = struct.unpack_from('<4s19I', (F/'ps2-world.re4mesh').read_bytes())
print('ARM', ARM, 'meshes', h[4], 'parts', h[5], 'meshlets', h[6], 'vertices', h[7], 'crc %08x' % h[3], 'bytes', h[2])
