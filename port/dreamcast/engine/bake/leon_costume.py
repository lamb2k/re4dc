"""Leon's chapter-2 costume (pl08) for the actor catalogue (eng-boss, E2).

From chapter 2 the game loads Leon's pl08 archive: the PS2 costume package dc/native/pl08/leon_pl08_ps2.re4cp
(RE4PL08, tools/d367/pl08_pack.py layout) holds the three pl08-only chunks (roles 0, 1, 8); every other part (head,
hair, knife, hands) is the pl00 one. This builds catalogue model 0 like native_models.py does for pl00, with those
three roles taken from the package.
"""
import struct
from geometry import actor_strips


def pl08_chunks(data):
    if data[:8] != b"RE4PL08\0":
        raise ValueError("not an RE4PL08 package")
    version, header, total, count = struct.unpack_from("<4I", data, 8)
    if version != 1 or total != len(data):
        raise ValueError("RE4PL08 header")
    out = {}
    for k in range(count):
        (role, info, pc, nc, palc, tris, stream, pos_off, pos_bytes, nrm_off, nrm_bytes, uv_off, uv_bytes, gx_off, w_off,
         _) = struct.unpack_from("<16I", data, 64 + 64 * k)
        out[role] = [data[pos_off:pos_off + pos_bytes], data[nrm_off:nrm_off + nrm_bytes], data[uv_off:uv_off + uv_bytes],
                     data[gx_off:gx_off + stream], data[w_off:w_off + 16 * palc]]
    return out


def leon_model(disc, private_tables, cloth_bind, material, costume):
    """Catalogue model 0 (Leon) with the pl08 roles from `costume` (RE4PL08 bytes); native_models.models() layout."""
    meta = private_tables.read_bytes()
    binds = meta[:(119 + 5 * 34) * 48]
    binds = binds[:64 * 48] + cloth_bind[64 * 48:110 * 48] + binds[110 * 48:]
    b = (disc / "native/pl00/leon_lod.re4lp").read_bytes()
    hands = (disc / "native/pl00/leon_hands_pl00.re4hp").read_bytes()
    hrows, hblobs = struct.unpack_from("<HH", hands, 4 + 2)
    hand_parts = {}
    for i in range(hblobs):
        role, flags, pc, nc, pal, tri, *fields = struct.unpack_from("<BBHHHH5HHH", hands, 32 + 12 * hrows + 24 * i)
        if not flags & 1: continue
        at = 32 * fields[-1]; arrays = []
        for size in fields[:5]:
            arrays.append(hands[at:at + size]); at += (size + 31) & ~31
        hand_parts[role] = arrays
    base = 32 * struct.unpack_from("<I", b, 72)[0]
    parts = []
    for j in range(6):
        r = struct.unpack_from("<16I", b, 128 + 64 * j)
        parts.append((r[0], [b[base + o:base + o + n] for o, n in zip(r[6:11], r[11:])]))
    swap = pl08_chunks(costume)
    replaced = []
    out_parts = []
    for role, arrays in parts:
        if role in swap:
            out_parts.append((role, swap.pop(role))); replaced.append(role)
        else:
            out_parts.append((role, arrays))
    for role in sorted(swap):
        out_parts.append((role, swap[role])); replaced.append(role)
    out_parts += list(hand_parts.items())
    texture = (0xec255e66, 0x76812316)
    weights = {}; vertices = {}; normals = {}; strips = bytearray(); bindings = []
    for role, (pos, nrm, uv, gx, skin) in out_parts:
        mats = [weights.setdefault(w, len(weights)) for w in (skin[i:i + 16] for i in range(0, len(skin), 16))]

        def vector(records, buf, index):
            x, y, z, bone = struct.unpack_from("<3hH", buf, index * 8)
            return records.setdefault((x, y, z, mats[bone]), len(records))
        start = len(strips)
        for strip in actor_strips(gx, 0, False):
            strips += struct.pack("<I", len(strip))
            for v, n, t in strip:
                u, vv = struct.unpack_from("<2H", uv, t * 4)
                strips += struct.pack("<4H", vector(vertices, pos, v & 16383), vector(normals, nrm, n & 16383), u, vv)
        key = (0xfc24a99c, 0x03d13534) if role == 7 else texture
        header = material(key, 2 if role == 7 else 1)
        bindings.append((role, header, start, len(strips) - start))
    bones = 119
    raw = struct.pack("<6I", bones, len(weights), len(vertices), len(normals), len(bindings), len(strips))
    raw += binds[0:bones * 48] + b"".join(weights)
    raw += b"".join(struct.pack("<3hH", *r) for r in vertices) + b"".join(struct.pack("<3hH", *r) for r in normals)
    raw += b"".join(struct.pack("<4I", *r) for r in bindings) + strips
    return raw, dict(replaced_roles=replaced, parts=len(bindings), positions=len(vertices), weights=len(weights))
