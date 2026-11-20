"""Boss models for the engine's actor catalogue, from the PS2 cast packages (RE4NMR1 registry.re4nmr).

eng-boss (E2): the El Gigante body is the PS2 cast the old port already ships for the room
(dc/native/r119/registry.re4nmr, descriptor gigante-em2b-00: 64 bones, two sections, one atlas). The catalogue
entry keeps the source skeleton (the capture records the source cParts matrices in source order), the source
weights and the indexed strips. The renderer's position quantum is fixed at 1/16; a package whose positions use
another shift has its inverse binds' 3x3 scaled by 16 / 2^shift so pose x bind x (p / 16) = pose x bind x (p / 2^shift).
"""
import struct
from geometry import actor_strips

SECTIONS = ('desc', 'ref', 'geom', 'blob', 'tex', 'parents', 'bind', 'fmodel', 'fpart', 'ftex', 'role', 'sblob')


class Package:
    def __init__(self, data):
        if data[:8] != b'RE4NMR1\0':
            raise ValueError('not a RE4NMR1 package')
        self.d = data
        self.header = struct.unpack_from('<14I', data, 8)
        self.sec = {}
        for i in range(self.header[3]):
            kind, at, size, count = struct.unpack_from('<4I', data, 64 + 16 * i)
            self.sec[SECTIONS[kind - 1]] = (at, size, count)

    def rows(self, name, size):
        at, _, count = self.sec[name]
        return [self.d[at + size * i:at + size * (i + 1)] for i in range(count)]

    def descriptors(self):
        out = []
        for raw in self.rows('desc', 48):
            name = raw[:16].rstrip(b'\0').decode()
            appearance, model_id, bones, sections, first_ref, parents_at, bind_first, word44 = struct.unpack_from('<8I', raw, 16)
            out.append(dict(name=name, appearance=appearance, model_id=model_id, bones=bones, sections=sections,
                            first_ref=first_ref, parents_at=parents_at, bind_first=bind_first,
                            shift=(word44 & 255) or 4, lod_of=(word44 >> 16) & 255 if word44 & (1 << 25) else 0))
        return out


def boss_model(package_bytes, name, texpack_lookup, material, stats=None):
    """One catalogue entry (native_models layout) for descriptor `name`. material(key, phase) -> header row."""
    pk = Package(package_bytes)
    desc = next((d for d in pk.descriptors() if d['name'] == name), None)
    if desc is None:
        raise ValueError(f'descriptor {name} not in the package')
    refs = [struct.unpack('<4I', r) for r in pk.rows('ref', 16)]
    geoms = [struct.unpack('<16I', r) for r in pk.rows('geom', 64)]
    texes = [struct.unpack('<4I', r) for r in pk.rows('tex', 16)]
    blob_at = pk.sec['blob'][0]
    bind_at = pk.sec['bind'][0]
    bones = desc['bones']
    scale = 16.0 / (1 << desc['shift'])
    binds = bytearray()
    for b in range(bones):
        m = list(struct.unpack_from('<12f', pk.d, bind_at + 48 * (desc['bind_first'] + b)))
        for r in range(3):
            for c in range(3):
                m[4 * r + c] *= scale
        binds += struct.pack('<12f', *m)
    weights, vertices, normals = {}, {}, {}
    strips = bytearray()
    bindings = []
    uv_lo, uv_hi, tris = [1 << 30] * 2, [-(1 << 30)] * 2, 0
    for k in range(desc['sections']):
        g_index, t_index, owner, word12 = refs[desc['first_ref'] + k]
        g = geoms[g_index]
        pc, nc, palc, triangles, stream_len, uv_len, skin_bytes, gbones = g[:8]
        at_pos, at_nrm, at_uv, at_stream, at_w = (blob_at + x for x in g[8:13])
        if gbones != bones:
            raise ValueError('section bone count differs from its descriptor')
        rows = [pk.d[at_w + 16 * i:at_w + 16 * (i + 1)] for i in range(palc)]
        for row in rows:
            b0, b1, b2, n = row[:4]
            if not 1 <= n <= 3 or max((b0, b1, b2)[:n]) >= bones:
                raise ValueError('invalid skin row')
        mats = [weights.setdefault(r, len(weights)) for r in rows]
        pos = pk.d[at_pos:at_pos + 8 * pc]
        nrm = pk.d[at_nrm:at_nrm + 8 * nc]
        uv = pk.d[at_uv:at_uv + uv_len]
        stream = pk.d[at_stream:at_stream + stream_len]

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
                uv_lo = [min(uv_lo[0], u), min(uv_lo[1], vv)]; uv_hi = [max(uv_hi[0], u), max(uv_hi[1], vv)]
                strips += struct.pack('<4H', vector(vertices, pos, v & 16383), vector(normals, nrm, n & 16383), u, vv)
            tris += len(strip) - 2
        bindings.append((1, material(key, 1), start, len(strips) - start))
    raw = struct.pack('<6I', bones, len(weights), len(vertices), len(normals), len(bindings), len(strips))
    raw += bytes(binds) + b''.join(weights)
    raw += b''.join(struct.pack('<3hH', *r) for r in vertices) + b''.join(struct.pack('<3hH', *r) for r in normals)
    raw += b''.join(struct.pack('<4I', *r) for r in bindings) + strips
    if stats is not None:
        stats.update(name=name, bones=bones, shift=desc['shift'], weights=len(weights), positions=len(vertices),
                     normals=len(normals), parts=len(bindings), strip_bytes=len(strips), triangles=tris,
                     uv_min=uv_lo, uv_max=uv_hi, textures=[f'{t[0]:08x}-{t[1]:08x}' for t in texes])
    return raw


if __name__ == '__main__':
    import argparse, json, sys
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument('package', type=Path); ap.add_argument('name'); ap.add_argument('--texpak', type=Path)
    a = ap.parse_args()
    lookup = None
    if a.texpak:
        tp = a.texpak.read_bytes()
        count, idx = struct.unpack_from('<2I', tp, 12)
        lookup = {(x, y) for x, y, _, _ in struct.iter_unpack('<4I', tp[idx:idx + 16 * count])}
    st = {}
    class Any:
        def __contains__(self, k): return True
    raw = boss_model(a.package.read_bytes(), a.name, lookup if lookup is not None else Any(), lambda k, p: 0, st)
    print(json.dumps(st))
    print('catalogue bytes', len(raw))
