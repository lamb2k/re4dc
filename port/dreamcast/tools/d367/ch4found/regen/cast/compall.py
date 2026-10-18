#!/usr/bin/env python3
"""ch4regen copy of /c/tmp/ch4/cast/compall.py (ch4found16 10-17): effect-compact castle enemy archives.
Inputs remapped to the replayed copies (ch3regen castle / ch3found prepem + aica). Logic unchanged.
usage: c4r-compall.py <name>=<shipped drs>:<report dir> ...   (texture dirs searched under TEXROOTS)"""
import glob, json, os, struct, subprocess, sys, shutil
L = '/root/probe/lanes-20261018/ch4regen/ch4found'
TOOLS = '/root/probe/lanes-20261018/ch4regen/tree/port/dreamcast/tools'
OUT = L + '/snd/aica-c4c/em'
S = L + '/hot11/ce'
TEXROOTS = ['/root/probe/lanes-20261018/ch3regen', '/root/probe/lanes-20261018/ch4regen']
os.makedirs(OUT, exist_ok=True); os.makedirs(S, exist_ok=True)


def rec0(b):
    for i in range(4):
        t, size, _, off = struct.unpack_from('<4I', b, 0x20 + 32 * i)
        if t == 0:
            return size, off, i
    raise ValueError('no body record')


texdirs = sorted(set(os.path.dirname(p) for r in TEXROOTS for p in glob.glob(r + '/**/*.re4tex', recursive=True)))
for arg in sys.argv[1:]:
    n, rest = arg.split('=', 1); shipped, report = rest.split(':', 1)
    r = json.load(open(report + '/motion-residency-report.json'))
    keys = [s['key'] for s in r['textures']['selected']]
    tex = next((d for d in texdirs if all(os.path.exists(d + '/' + k + '.re4tex') for k in keys)), None)
    if tex is None:
        print(n, 'no texture dir', keys[:3]); continue
    src = '/root/probe/lanes/ps2cast/inputs/%s.drs' % n
    args = ['python3', 'prepare_enemy_motions.py', '--source', src, '--textures', tex]
    if r.get('motions_resident'):
        args += ['--keep-motion-resident']
    else:
        audit = S + '/%s-audit.json' % n
        json.dump(r['prefetch_audit'], open(audit, 'w'))
        args += ['--hot-audit', audit, '--diagnostic-incomplete-prefetch']
    ship = open(shipped, 'rb').read()
    bs, bo, bi = rec0(ship)
    assert bo + bs == len(ship), n
    res = {}
    for tag, extra in (('base', []), ('ce', ['--compact-effects'])):
        o = S + '/%s-%s' % (n, tag)
        shutil.rmtree(o, ignore_errors=True)
        p = subprocess.run(args + ['--output', o] + extra, cwd=TOOLS, capture_output=True, text=True)
        if p.returncode:
            print(n, tag, 'FAIL', (p.stderr.strip().splitlines() or [''])[-1][:200]); break
        out = open(o + '/%s.drs' % n, 'rb').read()
        s2, o2, _ = rec0(out)
        res[tag] = out[o2:o2 + s2]
    else:
        same = res['base'] == ship[bo:bo + bs]
        body = res['ce']
        new = bytearray(ship[:bo]) + body
        struct.pack_into('<I', new, 0x20 + 32 * bi + 4, len(body))
        open(OUT + '/%s.drs' % n, 'wb').write(new)
        import hashlib
        print(n, 'base==shipped:', same, 'sha', hashlib.sha256(new).hexdigest()[:8], 'tex', tex)
