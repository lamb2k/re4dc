#!/usr/bin/env python3
"""Look gallery fixtures (look study 2026-10-10): one staging fixture per shot of shots.json for a route-build arm.

usage: [LOOK=<preset>] mkfix.py <arm label> <out dir> [shot ...]
Writes <out dir>/warp-<shot>.txt and <out dir>/fix-<shot>.json: the shot's base play-content fixture (shots.json
"bases") with dc/warp.txt = the shot's warp lines + `freeze <tick>`, no padscript, and every dc/*.ovl taken from the
arm's own harness program dir (candidate-route<label>), so the overlays match the ELF. Prints one line per shot:
"<shot> <fixture> <seconds>". Shots with "from" (crops of another shot) are skipped.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS = Path('/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1')


def main():
    arm, out = sys.argv[1], Path(sys.argv[2])
    want = set(sys.argv[3:])
    spec = json.loads((HERE / 'shots.json').read_text())
    prog = HARNESS / 'programs' / ('candidate-route' + arm)
    if not prog.is_dir():
        raise SystemExit('no harness program dir %s (build the arm with route-build.sh first)' % prog)
    out.mkdir(parents=True, exist_ok=True)
    for s in spec['shots']:
        if 'dc' not in s or (want and s['name'] not in want):
            continue
        d = json.loads(Path(spec['bases'][s['base']]).read_text())
        w = out / ('warp-%s.txt' % s['name'])
        extra = ''
        if os.environ.get('LOOK'):   # LOOK_TOGGLE builds: the look preset (native_static.cpp re4dc_looks) at load
            extra = 'look %d\n' % int(os.environ['LOOK'])
        w.write_text('name look-%s\n' % s['name'] + '\n'.join(s['dc']['warp']) + '\n' + extra +
                     'freeze %d\n' % s['dc']['freeze'])
        r = d['replace']
        r['dc/warp.txt'] = str(w)
        r.pop('dc/padscript.txt', None)
        for k in [k for k in r if k.startswith('dc/') and k.endswith('.ovl')]:
            own = prog / os.path.basename(k)
            if not own.exists():
                raise SystemExit('%s: the arm has no %s' % (s['name'], own.name))
            r[k] = str(own)
        d['remove'] = sorted((set(d.get('remove', [])) | {'dc/padscript.txt'}) - set(r))
        d.setdefault('provenance', {})['look_gallery'] = dict(shot=s['name'], arm=arm, base=spec['bases'][s['base']])
        for k, v in r.items():
            if not os.path.exists(v):
                raise SystemExit('%s: missing %s -> %s' % (s['name'], k, v))
        f = out / ('fix-%s.json' % s['name'])
        f.write_text(json.dumps(d, indent=1))
        print(s['name'], f, s.get('seconds', 45))


if __name__ == '__main__':
    main()
