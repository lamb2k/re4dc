#!/usr/bin/env python3
"""mkroute.py: one route fixture = the test 10 package fixture + every chapter 2-2 / 2-3 room's data.

  mkroute.py --base pkg-t10stP.json --winners <codex-cx-textures output/rooms> --out route.json \
      [--keep-base-shared] room=fixture ...   (rooms in route order; later rooms do not override a room's own files)

Rules (written into provenance.mkroute):
  * program files (1ST_READ.BIN, dc/*.ovl, dc/warp.txt, dc/padscript.txt) are never taken from room fixtures;
  * a room's own files (st*/<room>.*, dc/native/<room>/*, evd/<room>*) come from that room's fixture only;
  * dc/tex/<key>.re4tex: the central texture-fit winner (Codex fit_ps2_world_textures, collisions []) when any
    route room selects that key; else the base fixture's file when the base has the key; else the first room
    fixture (route order) that carries it; differing room copies are listed as conflicts;
  * every other new path: the first room fixture that carries it; differing copies are conflicts;
  * paths the base already replaces keep the base file (test 10 data unchanged), except the listed winners;
    each such room difference is reported (shared audio, em drs, tex.pak);
  * remove = base remove minus every replaced path.
"""
import argparse, collections, hashlib, json, os, re, sys

PROG = re.compile(r'^(1ST_READ\.BIN|dc/[^/]*\.ovl|dc/warp\.txt|dc/padscript\.txt)$')
_sha = {}


def sha(p):
    if p not in _sha:
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''):
                h.update(b)
        _sha[p] = h.hexdigest()
    return _sha[p]


def own(room, path):
    return (re.match(r'^st\d/%s[._]' % room, path) or path.startswith('dc/native/%s/' % room)
            or path.startswith('evd/%s' % room))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--winners', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('rooms', nargs='+')
    a = ap.parse_args()
    base = json.load(open(a.base))
    rep = dict(base['replace'])
    brep = base['replace']
    rooms = [r.split('=', 1) for r in a.rooms]
    win = {}
    for room, _ in rooms:
        wf = os.path.join(a.winners, room + '.json')
        if not os.path.exists(wf):
            continue
        for t in json.load(open(wf))['textures']:
            p = t['chosen']['path']
            k = 'dc/tex/%s/%s.re4tex' % (t['key'][0], t['key'])
            if k in win and sha(win[k][1]) != sha(p):
                sys.exit('central winner disagreement %s %s %s' % (k, win[k], p))
            win.setdefault(k, (room, p))
    fx = {}
    for room, f in rooms:   # room=fixture[,fixture...]: earlier fixtures win (the room's runtime fixture first)
        merged = {}
        for one in reversed(f.split(',')):
            merged.update(json.load(open(one))['replace'])
        fx[room] = {'replace': merged}
    taken = {}        # path -> (room, src)
    conflicts = collections.defaultdict(dict)
    base_kept = collections.defaultdict(dict)
    for room, _ in rooms:
        for k, v in fx[room]['replace'].items():
            if PROG.match(k) or not isinstance(v, str):
                continue
            s = sha(v)
            if k in win:
                continue
            if own(room, k):
                if k in taken and taken[k][0] != room and sha(taken[k][1]) != s:
                    conflicts[k]['owner ' + room] = s[:16]
                taken[k] = (room, v)
                continue
            if any(own(r2, k) for r2, _ in rooms if r2 != room):
                continue   # another route room's own file: that room's fixture decides
            if k in brep:
                if sha(brep[k]) != s:
                    base_kept[k][room] = s[:16]
                continue
            if k in taken:
                if sha(taken[k][1]) != s:
                    conflicts[k][room] = s[:16]
                    conflicts[k][taken[k][0]] = sha(taken[k][1])[:16]
                continue
            taken[k] = (room, v)
    for k, (room, p) in win.items():
        if k in brep and sha(brep[k]) != sha(p):
            base_kept[k]['WINNER-REPLACES-BASE ' + room] = sha(p)[:16]
        rep[k] = p
    for k, (room, v) in taken.items():
        rep[k] = v
    missing = [k for k, v in rep.items() if isinstance(v, str) and not os.path.exists(v)]
    if missing:
        sys.exit('missing sources: %s' % missing[:20])
    rem = sorted(set(base['remove']) - set(rep))
    prov = dict(base.get('provenance', {}))
    prov['mkroute'] = dict(base=a.base, base_sha256=sha(a.base), winners=a.winners,
                           rooms={r: [dict(fixture=x, sha256=sha(x)) for x in f.split(',')] for r, f in rooms},
                           added=len(set(rep) - set(brep)), winners_used=len(win),
                           base_kept_differences={k: v for k, v in sorted(base_kept.items())},
                           conflicts={k: v for k, v in sorted(conflicts.items())})
    out = dict(replace=dict(sorted(rep.items())), remove=rem, provenance=prov)
    json.dump(out, open(a.out, 'w'), indent=1, sort_keys=True)
    print('ROUTE_FIXTURE %s replace=%d (+%d) remove=%d winners=%d conflicts=%d base_kept=%d' % (
        a.out, len(rep), len(set(rep) - set(brep)), len(rem), len(win), len(conflicts), len(base_kept)))
    for k, v in sorted(base_kept.items()):
        print('  base kept / winner over base:', k, v)
    for k, v in sorted(conflicts.items()):
        print('  conflict:', k, v)


main()
