"""ch5regen copy of the recorded c4mask2.py logic (cast16 10-16/17): ps2_mask_runs.py per section, Windows python.
usage: c5r_mask.py <tools> <convdir> <preset>:<idx,idx|all> ...   -> <convdir>/mask-<preset>-s<i> (rc 0 kept)
       c5r_mask.py <tools> <convdir> --raw <preset> <bin> <tpl> <idx> <outname> [extra args...]"""
import sys, importlib.util, json, subprocess
T, W = sys.argv[1:3]
s = importlib.util.spec_from_file_location('pc', T + '/ps2_cast.py'); pc = importlib.util.module_from_spec(s); s.loader.exec_module(pc)


def run(n, b, tpl, i, out, extra=()):
    drs = json.load(open(f'{W}/{n}/validation.json'))['inputs']['gc']['cache']
    r = subprocess.run([sys.executable, T + '/ps2_mask_runs.py', f'{W}/{n}', drs, b, tpl, str(i), f'{W}/{out}', *extra],
                       capture_output=True, text=True)
    print(n, i, out, 'rc', r.returncode, (r.stderr.strip().splitlines() or [''])[-1][:110], flush=True)


a = sys.argv[3:]
if a and a[0] == '--raw':
    run(a[1], a[2], a[3], a[4], a[5], a[6:])
else:
    for arg in a:
        n, ix = arg.split(':'); secs = pc.section_specs(pc.PRESETS[n])
        idxs = range(len(secs)) if ix == 'all' else [int(x) for x in ix.split(',')]
        for i in idxs:
            b, role, tpl = secs[i]; run(n, hex(b), hex(tpl), i, f'mask-{n}-s{i}')
