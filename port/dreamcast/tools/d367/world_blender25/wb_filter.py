# world-blender25: converter-input filter for the r101 chain (ps2_world_r4im build() -> sources). Selected meshes go
# through Blender (wb_reduce.py) per part; everything else is untouched. Env:
#   WB_OP=none|reduce  WB_BOX=cx,cz,half (world mm)  WB_MERGE=<mm>  WB_ANGLE=<deg, 0=off>  WB_RATIO=<decimate, 1=off>
#   WB_WORK=<wsl dir for interchange>  WB_DUMP=1 (also write before/after OBJ of the selected meshes for renders)
import json, os, subprocess, sys

BL = '/root/opt/blender443/blender-4.4.3-linux-x64/blender'
RED = '/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/3eafc4fe-ad61-4030-8af6-7352db985ae8/scratchpad/world-blender25/wb_reduce.py'


def unc(p):
    return '//wsl.localhost/Ubuntu-24.04' + p


def blender(job, work):
    inp, out = work + '/job.json', work + '/res.json'
    open(unc(inp), 'w').write(json.dumps(dict(op=dict(merge=float(os.environ.get('WB_MERGE', '0')),
                                                      angle=float(os.environ.get('WB_ANGLE', '0')),
                                                      ratio=float(os.environ.get('WB_RATIO', '1')),
                                                      dump=os.environ.get('WB_DUMP', '')), meshes=job)))
    r = subprocess.run(['wsl', '-d', 'Ubuntu-24.04', '--', BL, '--background', '--factory-startup',
                        '--python', RED, '--', inp, out], capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if l.startswith('WB_')]
    print('\n'.join(tail), file=sys.stderr)
    if r.returncode or not tail:
        raise SystemExit('blender failed: ' + (r.stdout + r.stderr)[-1500:])
    res = json.load(open(unc(out)))
    return res


def wrap(build):
    def filtered(pkg, tables):
        meshes, placements, sources, parts_meta = build(pkg, tables)
        op = os.environ.get('WB_OP', 'none')
        if op == 'none':
            return meshes, placements, sources, parts_meta
        cx, cz, half = (float(x) for x in os.environ['WB_BOX'].split(','))
        sel = set(); inbox = {}
        for mi, p in placements:
            A = p['affine']
            pos = sources[mi]['positions']
            for v in pos:  # any vertex inside the box selects the mesh
                wx = A[0][0]*v[0] + A[0][1]*v[1] + A[0][2]*v[2] + A[0][3]
                wz = A[2][0]*v[0] + A[2][1]*v[1] + A[2][2]*v[2] + A[2][3]
                if abs(wx - cx) <= half and abs(wz - cz) <= half:
                    sel.add(mi); inbox.setdefault(mi, set()).add(tuple(v))
        work = os.environ['WB_WORK']
        job = []
        for mi in sorted(sel):
            s = sources[mi]
            parts = []
            for part in s['parts']:
                parts.append([[list(s['positions'][c[0]]) + list(s['uv'](c[2])) + list(s['color'](c[1])) + [1 if tuple(s['positions'][c[0]]) in inbox[mi] else 0] for c in tri]
                              for tri in part['loose']])
            job.append(dict(mesh=mi, parts=parts))
        if op == 'meshopt':
            import wb_meshopt
            passes = []
            k = 0
            for mi in range(len(meshes)):
                n = len(sources[mi]['parts']); passes.append([pm[4] for pm in parts_meta[k:k+n]]); k += n
            res = wb_meshopt.run(job, passes, float(os.environ.get('WB_ERR', '8.6')))
        else:
            res = blender(job, work)
        for m in res['meshes']:
            s = sources[m['mesh']]
            import struct as st
            f32 = lambda t: tuple(st.unpack('<f', st.pack('<f', float(x)))[0] for x in t)
            snapP = {f32(v): v for v in s['positions']}
            snapU = {}
            for part in s['parts']:
                for tri in part['loose']:
                    for c in tri:
                        u = s['uv'](c[2]); snapU[f32(u)] = u
            positions, pidx, uvs, uidx, cols, cidx = [], {}, [], {}, [], {}
            def ix(v, lst, d):
                if v not in d:
                    d[v] = len(lst); lst.append(v)
                return d[v]
            for part, tris in zip(s['parts'], m['parts']):
                loose = []
                for tri in tris:
                    cs = []
                    for c in tri:
                        P = snapP.get(f32(c[0:3]), tuple(c[0:3])); U = snapU.get(f32(c[3:5]), tuple(c[3:5]))
                        cs.append((ix(P, positions, pidx), ix(tuple(int(round(x)) for x in c[5:9]), cols, cidx),
                                   ix(U, uvs, uidx), 0))
                    loose.append(tuple(cs))
                part['loose'] = loose
            s['positions'] = positions; s['nvtx'] = min(65535, len(positions))
            s['uv'] = uvs.__getitem__; s['color'] = cols.__getitem__
        print('WB_FILTER selected meshes %d of %d' % (len(sel), len(meshes)), file=sys.stderr)
        return meshes, placements, sources, parts_meta
    return filtered
