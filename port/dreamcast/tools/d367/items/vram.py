#!/usr/bin/env python3
"""vram.py: per room, the texture-RAM bytes of the GC pictures lane items replaces (their tex.pak packages) vs the
PS2 packages that replace them (unique keys per room). Offline accounting from package descriptors (payload bytes)."""
import json
import struct
import sys
from pathlib import Path

sys.path[:0] = ['/root/probe/lanes-20261014/items/tree/port/dreamcast/tools', '/root/probe/lanes-20261014/items/tree/tools',
                '/root/probe/lanes-20261014/items/work']
import ps2_items as pi  # noqa
import pakmerge as pm  # noqa
import prepare_native_ui as pnu  # noqa

W = Path('/root/probe/lanes-20261014/items/work')
PAK = pm.read_pak(Path('/root/probe/lanes-20261014/t11/data/tex-t11.pak').read_bytes())


def pkg_vram(blob):
    # RE4DCTX header <8s10I: texture table at word 5 (offset), descriptor <64s8I: payload size at +64+16
    h = struct.unpack_from('<8s10I', blob, 0)
    t = struct.unpack_from('<64s8I', blob, h[5])
    return t[5]


def gc_key(pay, recs, tpl, j):
    n, desc = struct.unpack_from('<2I', pay, tpl + 4)
    h, clut = struct.unpack_from('<2I', pay, tpl + desc + 8 * j)
    hh, ww, fmt, data = struct.unpack_from('<2H2I', pay, tpl + h)
    at = tpl + data
    if at in recs:
        c, f = struct.unpack_from('<2I', pay, at + 8)
        return (c, f)
    k = pi.identity_key(ww, hh, fmt, bytes(pay[at:at + pi.image_size(ww, hh, fmt)]))
    return tuple(int(x, 16) for x in k.split('-'))


def main():
    lib = W / 'lib'
    ps2tex = {}
    for c in ('items', 'breakables'):
        for r in json.loads((lib / c / 'tex' / 'tex.json').read_text()):
            ps2tex[r['key']] = r['vram_bytes']
    tot = [0, 0]
    for room in pi.ROUTE:
        dar = (W / 'base' / (room + '.dar')).read_bytes()
        pay, off = pi.payload_of(dar)
        recs = pi.ntr_records(pay)
        gc, ps2 = {}, {}
        rep = []
        # walk the slots exactly like pack, collecting TPL offsets
        P = pi.Packer(bytearray(pay), lib, rep)
        tpls = []
        orig = P.pictures

        def grab(a, tpl):
            tpls.append((a, tpl))
            return []
        P.pictures = grab
        P.model = lambda a, at, end: 'already'
        # replicate pack_payload's walk with this Packer
        want = [a for c in ('items', 'breakables') for a in pi.assets_for(lib, c, room)]
        ents = pi.rs.tagged_entries(bytes(pay), '<')
        effk = 0
        for t, s, e in ents:
            tag = t.rstrip(b'\0').decode()
            if tag == 'ITM':
                ids, bo, to, tabs = pi.itm_tables(bytes(pay[s:e]), '<')
                pos = {i: k for k, i in enumerate(ids)}
                for a in want:
                    if a['locator']['kind'] == 'ITM' and a['status'] == 'PS2':
                        tpls.append((a, s + to[pos[a['locator']['id']]]))
            elif tag == 'EFF':
                efm = {i: (mo, to) for i, mo, to in pi.eff_efm(bytes(pay[s:e]), '<')}
                for a in want:
                    if a['locator']['kind'] == 'EFF' and a['locator']['eff'] == effk and a['status'] == 'PS2':
                        tpls.append((a, s + efm[a['locator']['id']][1]))
                effk += 1
            elif tag == 'ETM':
                for nm, s2, e2 in pi.po.etm_entries(bytes(pay[s:e]), '<'):
                    base = s + s2 + 0x40
                    efm = None
                    for a in want:
                        if a['locator']['kind'] == 'ETM' and a['locator']['member'] == nm and a['status'] == 'PS2':
                            efm = efm or {i: (mo, to) for i, mo, to in pi.eff_efm(bytes(pay[base:s + e2]), '<')}
                            tpls.append((a, base + efm[a['locator']['id']][1]))
        for a, tpl in tpls:
            for s in a.get('swaps', []):
                if s.get('role') == 'mask':
                    continue
                k = gc_key(pay, recs, tpl, s['j'])
                gc[k] = pkg_vram(PAK[k]) if k in PAK else 0
                ps2[s['key']] = ps2tex[s['key']]
            for pr in a.get('pairs', []):
                kc, km = gc_key(pay, recs, tpl, pr['color']), gc_key(pay, recs, tpl, pr['mask'])
                pk = pnu.material_pair_identity('%08x-%08x' % kc, '%08x-%08x' % km)
                k = tuple(int(x, 16) for x in pk.split('-'))
                gc[k] = pkg_vram(PAK[k]) if k in PAK else 0
                ps2[pr['key']] = ps2tex[pr['key']]
        g, p = sum(gc.values()), sum(ps2.values())
        tot[0] += g; tot[1] += p
        miss = sum(1 for v in gc.values() if v == 0)
        print('%s pictures %d: GC %7d B -> PS2 %7d B (%+d)%s' % (room, len(gc), g, p, p - g, ' (%d GC keys not in pak)' % miss if miss else ''))
    print('sum over rooms (not concurrent): GC %d -> PS2 %d' % tuple(tot))


if __name__ == '__main__':
    main()
