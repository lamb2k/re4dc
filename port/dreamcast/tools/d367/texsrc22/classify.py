#!/usr/bin/env python3
"""classify.py (lane texsrc22): STATIC source-based class + mip decision for the owner-unclassified keys.

    classify.py --keys keys1035.txt --pack tex.pak --gc gc-disc1.json --data DC_DIR --origins scoped_origins792.inc
                --resident RESIDENT_DIR --texclass unclassified.tsv [--textrefs textrefs.json] --out-tsv T --out-json J

Sources, all static (no runtime warps):
  * GC disc 1: scan.py's key -> (file, context) map (le_mirror TPL observer + raw TPL scan; same identity as dc/tex).
  * tex.pak descriptor name (the converter's label: "PS2 r106 texture 21", "PS2 items ...", "ps2mask_*", "leon4k").
  * Shipped room packages: every dc/native/<room>/* file of the data set, searched for the key's LE {crc, fnv}
    words, directly or through a rect21 scoped key whose original it is (scoped_origins).
  * Room resident lists (tools/d367/vram/resident/<room>.tsv) and optional text references (textrefs.py).
Route = chapters 1-3: stage 1 rooms r100..r120 and the castle r200..r22f (stage_route.py stages 1 and 2).
"""
import argparse, collections, json, os, re, struct

FMT = {0: 'RGB565', 1: 'ARGB1555', 2: 'ARGB4444', 3: 'YUV422', 4: 'PAL4', 5: 'PAL8', 6: 'BUMP'}
LAY = {0: 'linear', 1: 'twiddled', 2: 'vq'}


def route_room(r):
    try:
        n = int(r[1:], 16)
    except ValueError:
        return False
    return 0x100 <= n <= 0x120 or 0x200 <= n <= 0x22f


def read_pak(path):
    blob = open(path, 'rb').read()
    _, _, count, ioff, _ = struct.unpack_from('<8s4I', blob, 0)
    out = {}
    for i in range(count):
        c, f, o, n = struct.unpack_from('<4I', blob, ioff + 16 * i)
        out['%08x-%08x' % (c, f)] = blob[o:o + n]
    return out


def desc(b):
    h = struct.unpack_from('<8s10I', b)
    imgs = []
    for i in range(h[4]):
        t = struct.unpack_from('<64s8I', b, h[5] + 96 * i)
        imgs.append(dict(name=t[0].split(b'\0')[0].decode('latin-1'), w=t[1], h=t[2], fmt=FMT.get(t[3], str(t[3])),
                         mip=bool(t[6] & 4), layout=LAY.get(t[7], str(t[7]))))
    return imgs


def gc_class(file, ctx):
    f = file.lower()
    m = re.match(r'st(\d)/r([0-9a-f]{3})', f)
    if m:
        c = ctx.lower()
        kind = 'effect' if '.eff' in c or 'esp' in c else 'weapon' if 'wep' in c else 'world'
        return kind, ['r' + m.group(2)]
    m = re.match(r'evd/r([0-9a-f]{3})', f)
    if m:
        return 'cutscene', ['r' + m.group(1)]
    if f.startswith('em/'):
        base = os.path.basename(f)
        if base.startswith(('pl', 'emwp', 'wep')) or 'wep' in base:
            return ('weapon' if 'wep' in base or base.startswith('emwp') else 'character'), ['global']
        return 'enemy', ['global:' + base.split('.')[0]]
    if f.startswith('etc/') and ('efm' in ctx.lower() or 'eff' in ctx.lower()):
        return 'effect', ['global']
    if f.startswith(('ss/', 'fnt/', 'font', 'etc/title', 'title', 'mes/', 'file/')):
        return 'hud', ['global']
    if f.startswith('etc/') and f.endswith(('.eff', '.esp')):
        return 'effect', ['global']
    if f.startswith('omk/'):
        return 'unreferenced', ['extra']
    return 'other', ['global']


def name_class(name):
    m = re.match(r'PS2 (r[0-9a-f]{3}) (texture|object)', name)
    if m:
        return 'world', [m.group(1)]
    if name.startswith('PS2 items'):
        return 'item', []
    if name.startswith('PS2 breakables'):
        return 'world-object', []
    if name.startswith('hud-'):
        return 'hud', ['global']
    if name.startswith(('leon', 'cast_human', 'ps2_luis', 'ps2cast_luis')) or 'ashley' in name:
        return 'character', ['global']
    if name.startswith('cast_animal') or re.search(r'_(fish|bat|crow|dog|cow|chicken)', name):
        return 'enemy', []          # animals: drawn as em actors
    if name.startswith(('ps2mask_', 'ps2cast_', 'ganado')):
        return 'enemy', []
    return None, []


def main():
    ap = argparse.ArgumentParser()
    for k in ('keys', 'pack', 'gc', 'data', 'origins', 'resident', 'texclass', 'out_tsv', 'out_json'):
        ap.add_argument('--' + k.replace('_', '-'), required=True)
    ap.add_argument('--textrefs')
    a = ap.parse_args()
    keys = [l.strip() for l in open(a.keys) if l.strip()]
    pak = read_pak(a.pack)
    gc = json.load(open(a.gc))
    # scoped -> original, and original -> scoped
    scoped_of = collections.defaultdict(set)
    for l in open(a.origins):
        v = re.findall(r'0x([0-9a-fA-F]{8})U', l)
        if len(v) >= 4:
            scoped_of['%s-%s' % (v[2].lower(), v[3].lower())].add('%s-%s' % (v[0].lower(), v[1].lower()))
    want = {}
    for k in keys:
        for x in {k} | scoped_of.get(k, set()):
            c, f = x.split('-')
            want[struct.pack('<II', int(c, 16), int(f, 16))] = k
    pk_refs = collections.defaultdict(set)   # key -> {room/file}
    nat = os.path.join(a.data, 'native')
    for room in sorted(os.listdir(nat)):
        for fn in sorted(os.listdir(os.path.join(nat, room))):
            blob = open(os.path.join(nat, room, fn), 'rb').read()
            for pos in range(0, len(blob) - 7, 4):
                k = want.get(blob[pos:pos + 8])
                if k:
                    pk_refs[k].add('%s/%s' % (room, fn))
    res_refs = collections.defaultdict(set)
    for fn in sorted(os.listdir(a.resident)):
        if fn.endswith('.tsv'):
            for l in open(os.path.join(a.resident, fn)):
                k = l.split('\t')[0]
                if k in pak:
                    res_refs[k].add(fn[:-4])
    texrefs = json.load(open(a.textrefs)) if a.textrefs and os.path.exists(a.textrefs) else {}
    old = {}
    for l in open(a.texclass):
        f = l.rstrip('\n').split('\t')
        if f[0] != 'key':
            old[f[0]] = f
    rows = []
    for k in keys:
        imgs = desc(pak[k])
        im = imgs[0]
        srcs, rooms, cls = [], set(), None
        for s in gc.get(k, []):
            c, r = gc_class(s['file'], s['context'])
            srcs.append('gc:%s:%s' % (s['file'], s['context'][:40]))
            rooms.update(r)
            cls = cls or c
        nc, nr = name_class(im['name'])
        if nc and (cls is None or cls in ('other',)):
            cls = nc
        rooms.update(nr)
        srcs.append('pak:' + im['name'])
        for p in sorted(pk_refs.get(k, ())):
            srcs.append('pkg:' + p)
            rooms.add(p.split('/')[0])
        for r in sorted(res_refs.get(k, ())):
            srcs.append('resident:' + r)
            rooms.add(r)
        for p in texrefs.get(k, [])[:4]:
            srcs.append('text:' + p.replace('/mnt/c/Game Dev/Emulators/', 'C:/').replace('/root/', '~/'))
        cls = cls or 'unreferenced'
        bound = bool(gc.get(k) or pk_refs.get(k) or res_refs.get(k))
        # Packaged (non-room) PS2 assets: items/breakables/cast/masks are bound by their own tables, not R4PW.
        if cls in ('item', 'world-object', 'enemy', 'character', 'hud') and not bound:
            bound = bool(texrefs.get(k))
        sq = im['w'] == im['h'] and im['w'] & (im['w'] - 1) == 0
        gen = (im['fmt'] in ('RGB565', 'ARGB1555', 'ARGB4444') and im['layout'] in ('twiddled', 'vq')) or \
              (im['fmt'] == 'PAL4' and im['layout'] == 'twiddled')
        if any(r.startswith('global:') for r in rooms):
            rooms.add('global')
        on_route = [r for r in rooms if route_room(r)]
        offroute = [r for r in rooms if r.startswith('r') and not route_room(r)]
        if len(imgs) > 1:
            dec, why = 'convert-blocked', 'multi-image package (%d): split per image first' % len(imgs)
        elif im['mip']:
            dec, why = 'already-mipped', 'pack carries a chain'
        elif cls == 'hud':
            dec, why = 'exclude', 'screen-space HUD/UI (1:1)'
        elif cls == 'unreferenced' or (not bound and not on_route and 'global' not in rooms):
            dec, why = 'not-reachable', 'no shipped package, room archive or resident list binds it'
        elif offroute and not on_route and 'global' not in rooms:
            dec, why = 'not-reachable', 'only in rooms outside ch1-3: ' + ','.join(sorted(offroute))
        elif not bound and cls == 'world':
            dec, why = 'not-reachable', 'PS2 world texture not bound by its room R4PW (orphan in pack)'
        elif max(im['w'], im['h']) <= 16:
            dec, why = 'exclude', 'tiny (<=16): a chain buys nothing'
        elif not sq:
            dec, why = 'convert-blocked', 'rectangular %dx%d: needs a rect21 square scoped representation' % (im['w'], im['h'])
        elif not gen:
            dec, why = 'convert-blocked', '%s %s: needs a %s chain generator (or re-encode to VQ/twiddled 16-bit)' % (
                im['fmt'], im['layout'], im['fmt'])
        else:
            dec, why = 'mip-chain', 'minified 3D surface (%s)' % cls
        o = old.get(k)
        oldd = o[1] if o else '-'
        contra = ''
        if o and oldd == 'not-on-route' and dec in ('mip-chain', 'convert-blocked', 'already-mipped'):
            contra = 'texclass22 not-on-route but statically bound on route'
        elif o and oldd in ('convert', 'not-worth', 'needs-work') and dec == 'not-reachable':
            contra = 'texclass22 saw it drawn but no static binding found'
        rows.append(dict(key=k, cls=cls, decision=dec, reason=why, w=im['w'], h=im['h'], fmt=im['fmt'],
                         layout=im['layout'], bytes=len(pak[k]),
                         rooms=','.join(sorted(rooms, key=lambda r: (not r.startswith('r'), r))) or '-',
                         route_rooms=len(on_route), sources=' | '.join(srcs[:8]), texclass22=oldd, contradiction=contra))
    cols = ['key', 'sources', 'rooms', 'cls', 'decision', 'reason', 'w', 'h', 'fmt', 'layout', 'bytes', 'route_rooms',
            'texclass22', 'contradiction']
    with open(a.out_tsv, 'w') as f:
        f.write('\t'.join(cols) + '\n')
        for r in rows:
            f.write('\t'.join(str(r[c]) for c in cols) + '\n')
    summ = dict(keys=len(rows), by_class=collections.Counter(r['cls'] for r in rows),
                by_decision=collections.Counter(r['decision'] for r in rows),
                class_decision=collections.Counter('%s/%s' % (r['cls'], r['decision']) for r in rows),
                contradictions=collections.Counter(r['contradiction'] for r in rows if r['contradiction']))
    json.dump(summ, open(a.out_json, 'w'), indent=1, sort_keys=True)
    print(json.dumps(summ, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
