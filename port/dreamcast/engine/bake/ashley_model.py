"""Ashley's body for the engine's actor catalogue, from her PS2 cast package (lane eng-e1d, E1).

Source: dc/native/r11d/partner.re4nmr (RE4NMR1, the old port's PS2_ASHLEY package; descriptor ashley11: 7 sections,
one 512 x 512 atlas). The package draws through 64 skin slots; its parents run holds, after the 141 source joints'
parents, the source joint of every slot (ps2cast.md, "the slot palettes' bind"), and its bind run has one inverse bind
per SOURCE joint. The source joints are the parts of her original model (cParts order, 141), which is the order of her
native skeleton table. So the catalogue entry keeps all 141 joints with their binds and rewrites every skin row's slot
to its source joint: the engine renderer then reads bone k of her skeleton table (its palette or its world record)
for model bone k, as it does for Leon. Positions are 1/16 units (shift 4), the renderer's quantum.

Not baked: the package's mask runs (hair and eyelash alpha; their pictures are not in tex.pak), so every part is drawn
opaque with the atlas.
usage: ashley_model.py <package> [--texpak tex.pak] [descriptor]
"""
import struct
from boss_model import Package
from geometry import actor_strips

SOURCE_JOINTS = 141


def ashley_model(package_bytes, texpack_lookup, material, name='ashley11', stats=None):
    pk = Package(package_bytes)
    desc = next((d for d in pk.descriptors() if d['name'] == name), None)
    if desc is None:
        raise ValueError(f'descriptor {name} not in the package')
    slots = desc['bones']
    pat = pk.sec['parents'][0] + desc['parents_at']
    slot_joint = list(pk.d[pat + SOURCE_JOINTS:pat + SOURCE_JOINTS + slots])
    if len(slot_joint) != slots or max(slot_joint) >= SOURCE_JOINTS:
        raise ValueError('slot to joint map')
    if desc['shift'] != 4:
        raise ValueError('position shift other than 4')
    bind_at = pk.sec['bind'][0] + 48 * desc['bind_first']
    binds = pk.d[bind_at:bind_at + 48 * SOURCE_JOINTS]
    refs = [struct.unpack('<4I', r) for r in pk.rows('ref', 16)]
    geoms = [struct.unpack('<16I', r) for r in pk.rows('geom', 64)]
    texes = [struct.unpack('<4I', r) for r in pk.rows('tex', 16)]
    blob_at = pk.sec['blob'][0]
    weights, vertices, normals = {}, {}, {}
    strips = bytearray(); bindings = []; tris = 0
    for k in range(desc['sections']):
        g_index, t_index, owner, word12 = refs[desc['first_ref'] + k]
        g = geoms[g_index]
        pc, nc, palc, triangles, stream_len, uv_len, skin_bytes, gbones = g[:8]
        at_pos, at_nrm, at_uv, at_stream, at_w = (blob_at + x for x in g[8:13])
        if gbones != slots:
            raise ValueError('section slot count differs from its descriptor')
        rows = []
        for i in range(palc):
            r = pk.d[at_w + 16 * i:at_w + 16 * (i + 1)]
            n = r[3]
            if not 1 <= n <= 3 or max(r[:n]) >= slots:
                raise ValueError('invalid skin row')
            b = [slot_joint[r[j]] if j < n else 0 for j in range(3)]
            rows.append(struct.pack('<3BB', *b, n) + r[4:16])
        mats = [weights.setdefault(r, len(weights)) for r in rows]
        pos = pk.d[at_pos:at_pos + 8 * pc]; nrm = pk.d[at_nrm:at_nrm + 8 * nc]
        uv = pk.d[at_uv:at_uv + uv_len]; stream = pk.d[at_stream:at_stream + stream_len]

        def vector(records, buf, index):
            x, y, z, pal = struct.unpack_from('<3hH', buf, index * 8)
            if pal >= palc:
                raise ValueError('vector names a missing skin row')
            return records.setdefault((x, y, z, mats[pal]), len(records))
        key = tuple(texes[t_index][:2])
        if key not in texpack_lookup:
            raise ValueError(f'texture {key[0]:08x}-{key[1]:08x} not in tex.pak')
        start = len(strips)
        for strip in actor_strips(stream, 0, False):
            strips += struct.pack('<I', len(strip))
            for v, n, t in strip:
                u, vv = struct.unpack_from('<2H', uv, t * 4)
                strips += struct.pack('<4H', vector(vertices, pos, v & 16383), vector(normals, nrm, n & 16383), u, vv)
            tris += len(strip) - 2
        bindings.append((1, material(key, 1), start, len(strips) - start))
    raw = struct.pack('<6I', SOURCE_JOINTS, len(weights), len(vertices), len(normals), len(bindings), len(strips))
    raw += binds + b''.join(weights)
    raw += b''.join(struct.pack('<3hH', *r) for r in vertices) + b''.join(struct.pack('<3hH', *r) for r in normals)
    raw += b''.join(struct.pack('<4I', *r) for r in bindings) + strips
    if stats is not None:
        stats.update(name=name, joints=SOURCE_JOINTS, slots=slots, slot_joint=slot_joint, weights=len(weights),
                     positions=len(vertices), normals=len(normals), parts=len(bindings), strip_bytes=len(strips),
                     triangles=tris, texture='%08x-%08x' % tuple(texes[0][:2]), bytes=len(raw))
    return raw


if __name__ == '__main__':
    import argparse, json
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument('package', type=Path); ap.add_argument('name', nargs='?', default='ashley11')
    a = ap.parse_args()

    class Any:
        def __contains__(self, k): return True
    st = {}
    ashley_model(a.package.read_bytes(), Any(), lambda k, p: 0, a.name, st)
    print(json.dumps(st))
