"""ch4regen copy of /c/tmp/c4mask2.py + c4mask.py (cast16 10-17): ps2_mask_runs.py per section.
usage: c4r-mask.py <tools> <convdir> <preset>:<idx,idx|all> ...      -> <convdir>/mask-<preset>-s<i>
       c4r-mask.py <tools> <convdir> --tag <preset>                   -> mask-<preset>-{hood,acc1,acc5} (c4mask.py)
       c4r-mask.py <tools> <convdir> --raw <preset> <bin> <tpl> <idx> <outname>"""
import sys, importlib.util, json, subprocess
T, W = sys.argv[1:3]
s = importlib.util.spec_from_file_location('pc', T + '/ps2_cast.py'); pc = importlib.util.module_from_spec(s); s.loader.exec_module(pc)


def run(n, b, tpl, i, out):
    drs = json.load(open(f'{W}/{n}/validation.json'))['inputs']['gc']['cache']
    r = subprocess.run([sys.executable, T + '/ps2_mask_runs.py', f'{W}/{n}', drs, b, tpl, str(i), f'{W}/{out}'], capture_output=True, text=True)
    print(n, out, 'rc', r.returncode, (r.stderr.strip().splitlines() or [''])[-1][:110], flush=True)


a = sys.argv[3:]
if a and a[0] == '--raw':
    run(a[1], a[2], a[3], a[4], a[5])
elif a and a[0] == '--tag':
    for n in a[1:]:
        secs = pc.section_specs(pc.PRESETS[n])
        for b, tag in ((0x202, 'hood'), (0x20f, 'acc1'), (0x217, 'acc5')):
            idx = [i for i, (bb, role, t) in enumerate(secs) if bb == b]
            if idx:
                i = idx[0]; run(n, hex(b), hex(secs[i][2]), i, f'mask-{n}-{tag}')
else:
    for arg in a:
        n, ix = arg.split(':'); secs = pc.section_specs(pc.PRESETS[n])
        idxs = range(len(secs)) if ix == 'all' else [int(x) for x in ix.split(',')]
        for i in idxs:
            b, role, tpl = secs[i]; run(n, hex(b), hex(tpl), i, f'mask-{n}-s{i}')
