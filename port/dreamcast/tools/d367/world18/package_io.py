"""R4IM v3 read/write, adapted from lane worldlod ps2_world_far_lod.py (2026-10-15).
No gameplay data; retains all existing package tables.
"""
import struct,zlib
def align(n,a=32):return (n+a-1)&~(a-1)

HEADER = struct.Struct('<4s19I')
LOD_HEADER = struct.Struct('<8I')
MESH = struct.Struct('<HBBHHIII12f')
PART = struct.Struct('<IIBBBBII4f')
MESHLET = struct.Struct('<IIIHH6H')
VERTEX = struct.Struct('<6H')
PART_LOD = struct.Struct('<II')
CLUSTER = struct.Struct('<6HII')
LEVEL = struct.Struct('<IIf')
INDEXED = 0x8000
FAR_ERROR = 1.0e30
MAX_LET_VERTICES = 256


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def read(blob):
    h = HEADER.unpack_from(blob, 0)
    magic, version, nbytes, crc, nmesh, npart, nlet, nvert, nstrip, npal, o_mesh, o_part, o_let, o_vert, o_strip, \
        o_pal = h[:16]
    reserved = h[16:20]
    assert magic == b'R4IM' and version == 3 and nbytes == len(blob), (magic, version, nbytes, len(blob))
    assert reserved[0] == 2 and reserved[1:] == (0, 0, 0), ('prelit packages only', reserved)
    lod = LOD_HEADER.unpack_from(blob, 80)
    ncl, nlv, o_plod, o_cl, o_lv, o_class, o_rule, o_res = lod
    assert o_class == 0 and o_rule == 0 and o_res == 0, ('class / rule / impostor tables are not carried', lod)
    assert zlib.crc32(blob[80:]) == crc, 'header crc'
    p = dict(
        meshes=[list(MESH.unpack_from(blob, o_mesh + MESH.size * i)) for i in range(nmesh)],
        parts=[list(PART.unpack_from(blob, o_part + PART.size * i)) for i in range(npart)],
        lets=[list(MESHLET.unpack_from(blob, o_let + MESHLET.size * i)) for i in range(nlet)],
        verts=[VERTEX.unpack_from(blob, o_vert + VERTEX.size * i) for i in range(nvert)],
        strip=bytes(blob[o_strip:o_strip + nstrip]),
        pal=[struct.unpack_from('<I', blob, o_pal + 4 * i)[0] for i in range(npal)],
        plods=[list(PART_LOD.unpack_from(blob, o_plod + PART_LOD.size * i)) for i in range(npart)],
        clusters=[list(CLUSTER.unpack_from(blob, o_cl + CLUSTER.size * i)) for i in range(ncl)],
        levels=[list(LEVEL.unpack_from(blob, o_lv + LEVEL.size * i)) for i in range(nlv)])
    return p


def write(p):
    head = HEADER.size + LOD_HEADER.size
    body = bytearray()
    offsets = {}
    for name, blob in (('mesh', b''.join(MESH.pack(*m) for m in p['meshes'])),
                       ('part', b''.join(PART.pack(*x) for x in p['parts'])),
                       ('meshlet', b''.join(MESHLET.pack(*m) for m in p['lets'])),
                       ('vertex', b''.join(VERTEX.pack(*v) for v in p['verts'])),
                       ('index', bytes(p['strip'])),
                       ('palette', b''.join(struct.pack('<I', c) for c in p['pal'])),
                       ('part_lod', b''.join(PART_LOD.pack(*x) for x in p['plods'])),
                       ('cluster', b''.join(CLUSTER.pack(*c) for c in p['clusters'])),
                       ('level', b''.join(LEVEL.pack(*l) for l in p['levels']))):
        start = align(head + len(body)) - head
        body.extend(b'\0' * (start - len(body)))
        offsets[name] = head + len(body)
        body.extend(blob)
    body.extend(b'\0' * (align(head + len(body)) - head - len(body)))
    lod = LOD_HEADER.pack(len(p['clusters']), len(p['levels']), offsets['part_lod'], offsets['cluster'],
                          offsets['level'], 0, 0, 0)
    body = lod + bytes(body)
    total = HEADER.size + len(body)
    header = HEADER.pack(b'R4IM', 3, total, zlib.crc32(body), len(p['meshes']), len(p['parts']), len(p['lets']),
                         len(p['verts']), len(p['strip']), len(p['pal']), offsets['mesh'], offsets['part'],
                         offsets['meshlet'], offsets['vertex'], offsets['index'], offsets['palette'], 2, 0, 0, 0)
    return header + body


def let_corners(p, m):
    """-> (pool vertex index per local corner, [strip corner lists]) of meshlet record m."""
    first_vertex, first_strip, strip_bytes, nv, sc = m[0], m[1], m[2], m[3], m[4]
    s = p['strip']
    if sc & INDEXED:
        table = struct.unpack_from('<%dH' % nv, s, first_strip)
        corners = [first_vertex + o for o in table]
        at = first_strip + 2 * nv
    else:
        corners = [first_vertex + k for k in range(nv)]
        at = first_strip
    end = at + strip_bytes
    strips = []
    while at < end:
        n = s[at]
        strips.append(list(s[at + 1:at + 1 + n]))
        at += 1 + n
    assert len(strips) == (sc & (INDEXED - 1))
    return corners, strips


def part_pool(p, pi):
    """[lo, hi) of the vertex records part pi's meshlets read."""
    part = p['parts'][pi]
    lo, hi = None, None
    for li in range(part[6], part[6] + part[7]):
        corners, _ = let_corners(p, p['lets'][li])
        a, b = min(corners), max(corners) + 1
        lo = a if lo is None else min(lo, a)
        hi = b if hi is None else max(hi, b)
    return lo, hi

