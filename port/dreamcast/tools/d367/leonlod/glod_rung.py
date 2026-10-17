#!/usr/bin/env python3
"""leonlod GANADO_LOD stage 1 (Windows Python: numpy): one mesh rung of the PS2 cast Ganados (PS2_GANADO's five
appearances), reduced by lod_mesh.py and re-packed with the cast's own packer.

  glod_rung.py <store dir> <out dir> --pct P [--apps a,b,...] [--spec base.json] [--repack-only]

<store dir>  the ps2_cast.py store the play bundle came from (ps2cast-all-20261010: <app>/mesh.json, source.json,
             validation.json, source-bindings.json, runtime/castmodel_runtime.h).
--pct P      the rung: P % of the appearance's positions (all four roles). The hands (roles 2 / 3) stay whole (they
             are the hand-pose slots); body (0) and head (1) are reduced by the same triangle ratio, searched so the
             whole appearance lands at P % of its positions (lod_mesh.py's own target is triangles per role).
--head-pow H  the head's triangle ratio is the body's ** H (H < 1 keeps the face richer; default 1)
--repack-only  no reduction: the store mesh.json re-packed (a check that this pipeline reproduces the store header).

Per appearance <out>/<app>/: mesh.json (reduced), lod-report.json, source.json + source-bindings.json + validation.json
(copied), native/ (pack_coarse_actor.pack + host-fixture.bin). Stage 2 is glod_native.sh (WSL): host check, fastpath
build_blob / verify_blob / patch_header -> <out>/<app>/runtime/castmodel_runtime.h; then glod_pack.py.
Every surviving vertex is an original PS2 vertex (lod_mesh.py half-edge collapse): no new bone combination, so the
palette count of each chunk is at most today's; the skeleton, bind and atlas are today's.
"""
import argparse, importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
PRIV = Path(os.environ.get('RE4_PRIVATE', 'C:/Game Dev/Emulators/re4-assets-private'))
PROTO = Path(os.environ.get('RE4_CAST_PROTO', PRIV / 'character-prototype-20260925'))
APPS = ['ganado-em12-01', 'ganado-em15-00', 'ganado-em15-03', 'ganado-em15-04', 'ganado-em15-0b']
BASE_SPEC = {"keep_roles": [2, 3], "allow_border": False, "hard_cap_mm": 20, "w_bone": 1.0,
             "lock_components_below": {"0": 13, "1": 13}}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def positions(mesh):
    return len({c['vertex'] for t in mesh['triangles'] for c in t['corners']})


def role_tris(mesh):
    out = {}
    for t in mesh['triangles']:
        out[t['source_info']] = out.get(t['source_info'], 0) + 1
    return out


def reduce(src, dst, spec, work, ratio, head_pow=1.0):
    tris = role_tris(json.loads(Path(src).read_text()))
    s = dict(spec)
    # the head (role 1: face, ears, hair) keeps more of its triangles than the body: ratio ** head_pow
    # a one-role appearance (lane cast16: Mendez's separated legs) has no head role
    s['targets'] = {'0': {'*': max(4, int(round(tris[0] * ratio)))}}
    if 1 in tris:
        s['targets']['1'] = {'*': max(4, int(round(tris[1] * ratio ** head_pow)))}
    sp = work / 'spec.json'
    sp.write_text(json.dumps(s, indent=1))
    r = subprocess.run([sys.executable, str(HERE / 'lod_mesh.py'), str(src), str(dst), '--spec', str(sp), '--report',
                        str(work / 'lod-report.json')], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    return positions(json.loads(Path(dst).read_text()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('store', type=Path); ap.add_argument('out', type=Path)
    ap.add_argument('--pct', type=float, default=100.0); ap.add_argument('--apps', default=','.join(APPS))
    ap.add_argument('--spec'); ap.add_argument('--repack-only', action='store_true')
    ap.add_argument('--head-pow', type=float, default=1.0)
    # --shift N (lane cast16 2026-10-16, boss levels): the preset's position shift (El Gigante / Mendez 2): positions are
    # packed / 2^(4 - N) as ps2_cast.py convert does (mesh.json keeps millimetres; the descriptor carries the shift)
    ap.add_argument('--shift', type=int, default=4)
    a = ap.parse_args()
    spec = dict(BASE_SPEC)
    if a.spec:
        spec.update(json.loads(Path(a.spec).read_text()))
    pk = load_module('pack_coarse_actor', PROTO / 'tools/pack_coarse_actor.py')
    pc = load_module('ps2_cast', TOOLS / 'ps2_cast.py')
    summary = {}
    for app in a.apps.split(','):
        s, o = a.store / app, a.out / app
        if o.exists():
            shutil.rmtree(o)
        o.mkdir(parents=True)
        for f in ('source.json', 'source-bindings.json', 'validation.json'):
            shutil.copy2(s / f, o / f)
        mesh0 = json.loads((s / 'mesh.json').read_text())
        p0 = positions(mesh0)
        if a.repack_only:
            shutil.copy2(s / 'mesh.json', o / 'mesh.json')
            got, ratio = p0, 1.0
        else:
            want = p0 * a.pct / 100.0
            hands = sum(1 for _ in {c['vertex'] for t in mesh0['triangles'] if t['source_info'] in (2, 3) for c in t['corners']})
            # positions of body + head scale ~ with their triangles: start there, then bisect the triangle ratio
            lo_r, hi_r = 0.02, 1.0
            ratio = max(0.05, (want - hands) / max(1, p0 - hands))
            best = None
            for _ in range(7):
                got = reduce(s / 'mesh.json', o / 'mesh.json', spec, o, ratio, a.head_pow)
                if best is None or abs(got - want) < abs(best[1] - want):
                    best = (ratio, got)
                if abs(got - want) <= max(2, 0.01 * p0):
                    break
                if got > want:
                    hi_r = ratio
                else:
                    lo_r = ratio
                ratio = (lo_r + hi_r) / 2
            if best[1] != got:
                got = reduce(s / 'mesh.json', o / 'mesh.json', spec, o, best[0], a.head_pow); ratio = best[0]
        native = o / 'native'
        mp = o / 'mesh.json'
        if a.shift != 4:
            pm = json.loads(mp.read_text())
            pm['positions_mm'] = [[x / (1 << (4 - a.shift)) for x in q] for q in pm['positions_mm']]
            mp = o / 'mesh-pack.json'
            mp.write_text(json.dumps(pm))
        pk.pack(mp, o / 'source.json', native, 'castmodel')
        pc.host_fixture(native, json.loads((o / 'source.json').read_text()))
        rep = json.loads((native / 'native-report.json').read_text())
        summary[app] = dict(positions=[p0, got], pct=round(100.0 * got / p0, 1), ratio=round(ratio, 4),
                            chunks=[(c['info'], c['positions'], c['triangles'], c['palettes']) for c in rep['chunks']])
        print(app, json.dumps(summary[app]))
    (a.out / 'rung.json').write_text(json.dumps(dict(pct=a.pct, head_pow=a.head_pow, spec=spec, apps=summary), indent=1))


if __name__ == '__main__':
    main()
