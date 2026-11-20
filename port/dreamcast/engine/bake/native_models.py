"""Convert all body/head appearances and the standard Leon hand blobs into indexed actor models.

eng-look:
- Leon's hair as the source draws it: the hair part (role 7) with the body atlas, opaque, then the hair run (role 8
  here: the same positions and weights, the hair UVs, the hair colour image with its mask in alpha) blended in the
  translucent list with no depth write.
- Distance levels: the PS2 model levels that exist (the old port's LEON_LOD / GANADO_LOD packages: Leon A, lg65, bd70,
  u70; Ganado today, g85, g70, g55; every surviving vertex an original PS2 vertex, same skeleton and bind).
- Fewer bones far away (rigid): each vertex follows its strongest bone only, and bones that carry few positions
  follow the nearest kept bone (bind-space origin distance)."""
import struct
from geometry import actor_strips

LEON_LEVEL_BYTES = 448
HAIR_KEY = (0xfc24a99c, 0x03d13534)
LEON_ATLAS = (0xec255e66, 0x76812316)


def _leon_level(b, k):
    """(base offset, role rows, hair fields) of Leon level k in leon_lod.re4lp"""
    e = 64 + LEON_LEVEL_BYTES * k
    base = 32 * struct.unpack_from("<I", b, e + 8)[0]
    rows = [struct.unpack_from("<16I", b, e + 64 + 64 * j) for j in range(6)]
    hair = struct.unpack_from("<8I", b, e + 32)
    return base, rows, hair


def _ganado_level(b, k, model):
    apps = struct.unpack_from("<I", b, 28)[0]
    e = 64 + (24 + 128 * apps) * k
    base = 32 * struct.unpack_from("<I", b, e + 8)[0]
    rows = [struct.unpack_from("<16I", b, e + 24 + (model - 1) * 128 + 64 * j) for j in range(2)]
    return base, rows


def _assemble(parts, binds, first, bones, material, leon, texture):
    """parts: [(role, [pos, nrm, uv, gx, skin])] -> model blob (format of native_actor.inc)"""
    weights = {}; vertices = {}; normals = {}; strips = bytearray(); bindings = []
    for role, (pos, nrm, uv, gx, skin) in parts:
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
        if leon and role == 8:
            header = material(HAIR_KEY, 3)        # hair run: translucent, blended, no depth write (eng-look)
        else:
            header = material(texture, 1)         # every other part, the hair part (role 7) included: the atlas, opaque
        bindings.append((role, header, start, len(strips) - start))
    raw = struct.pack("<6I", bones, len(weights), len(vertices), len(normals), len(bindings), len(strips))
    raw += binds[first * 48:(first + bones) * 48] + b"".join(weights)
    raw += b"".join(struct.pack("<3hH", *r) for r in vertices) + b"".join(struct.pack("<3hH", *r) for r in normals)
    raw += b"".join(struct.pack("<4I", *r) for r in bindings) + strips
    return raw


def _tables(private_tables, cloth_bind):
    meta = private_tables.read_bytes()
    binds = meta[:(119 + 5 * 34) * 48]
    binds = binds[:64 * 48] + cloth_bind[64 * 48:110 * 48] + binds[110 * 48:]
    textures = list(struct.iter_unpack("<4I", meta[len(binds):len(binds) + 80]))
    enemy_hands = []
    at = len(binds) + 80
    for app in range(5):
        parts = []
        for role in (2, 3):
            pc, nc, pal, sb, uvbytes = struct.unpack_from("<5I", meta, at); at += 20
            arrays = []
            for size in (8 * pc, 8 * nc, 16 * pal, sb, uvbytes):
                arrays.append(meta[at:at + size]); at += size
            parts.append((role, [arrays[i] for i in (0, 1, 4, 3, 2)]))
        enemy_hands.append(parts)
    return binds, textures, enemy_hands


def _hand_parts(disc):
    hands = (disc / "native/pl00/leon_hands_pl00.re4hp").read_bytes()
    hrows, hblobs = struct.unpack_from("<HH", hands, 4 + 2)
    out = {}
    for i in range(hblobs):
        role, flags, pc, nc, pal, tri, *fields = struct.unpack_from("<BBHHHH5HHH", hands, 32 + 12 * hrows + 24 * i)
        if not flags & 1: continue
        at = 32 * fields[-1]; arrays = []
        for size in fields[:5]:
            arrays.append(hands[at:at + size]); at += (size + 31) & ~31
        out[role] = arrays
    return out


def _sources(disc, private_tables, cloth_bind):
    files = [(disc / "native/pl00/leon_lod.re4lp").read_bytes(), (disc / "native/ganado/ganado_lod.re4gl").read_bytes()]
    return files, _tables(private_tables, cloth_bind), _hand_parts(disc)


def _model(files, tables, hand_parts, material, model, level):
    binds, textures, enemy_hands = tables
    leon = model == 0
    b = files[0 if leon else 1]
    parts = []
    if leon:
        base, rows, hair = _leon_level(b, level)
        for r in rows:
            arrays = [b[base + o:base + o + n] for o, n in zip(r[6:11], r[11:])]
            parts.append((r[0], arrays))
            if r[0] == 7:   # the hair run over the hair part's positions and weights, with the hair UVs
                pc, tri, mat, asset, huo, hus, hro, hrs = hair
                parts.append((8, [arrays[0], arrays[1], b[base + huo:base + huo + hus], b[base + hro:base + hro + hrs], arrays[4]]))
        parts += list(hand_parts.items())
    else:
        base, rows = _ganado_level(b, level, model)
        for r in rows:
            parts.append((r[0], [b[base + o:base + o + n] for o, n in zip(r[6:11], r[11:])]))
        parts += enemy_hands[model - 1]
    texture = LEON_ATLAS if leon else textures[model - 1][:2]
    first = 0 if leon else 119 + (model - 1) * 34
    bones = 119 if leon else 34
    return _assemble(parts, binds, first, bones, material, leon, texture)


def models(disc, private_tables, cloth_bind, material):
    files, tables, hands = _sources(disc, private_tables, cloth_bind)
    return [_model(files, tables, hands, material, model, 0) for model in range(6)]


def level_models(disc, private_tables, cloth_bind, material):
    """[(base model, level, blob)] for every PS2 level past the first that exists (Leon 0, Ganado appearances 1-5)."""
    files, tables, hands = _sources(disc, private_tables, cloth_bind)
    out = []
    for model in range(6):
        n = struct.unpack_from("<I", files[0 if model == 0 else 1], 8)[0]
        for level in range(1, min(n, 4)):
            out.append((model, level, _model(files, tables, hands, material, model, level)))
    return out


def rigid(raw, keep_share=0.03):
    """Fewer bones: each weight set follows its strongest bone; a bone whose share of the positions is under
    keep_share follows the nearest kept bone (bind-space origin). Returns the converted blob, or None when it would
    not remove a weight set."""
    bones, nw, npos, nnrm, nparts, nstrip = struct.unpack_from("<6I", raw)
    at = 24
    binds = raw[at:at + 48 * bones]; at += 48 * bones
    w = [struct.unpack_from("<4B3f", raw, at + 16 * i) for i in range(nw)]; at += 16 * nw
    pos = [struct.unpack_from("<3hH", raw, at + 8 * i) for i in range(npos)]; at += 8 * npos
    nrm = [struct.unpack_from("<3hH", raw, at + 8 * i) for i in range(nnrm)]; at += 8 * nnrm
    rest = raw[at:]
    dom = []
    for b0, b1, b2, cnt, w0, w1, w2 in w:
        cnt = max(1, min(3, cnt)); ids = (b0, b1, b2)[:cnt]; ws = (w0, w1, w2)[:cnt]
        dom.append(ids[max(range(cnt), key=lambda k: ws[k])])
    share = [0] * bones
    for p in pos: share[dom[p[3]]] += 1
    kept = [b for b in range(bones) if share[b] >= keep_share * npos] or [max(range(bones), key=lambda b: share[b])]
    def origin(b):   # inverse bind (3x4 row-major): the bone origin in model space is -R^T t
        m = struct.unpack_from("<12f", binds, 48 * b)
        return [-(m[0 + c] * m[3] + m[4 + c] * m[7] + m[8 + c] * m[11]) for c in range(3)]
    org = [origin(b) for b in range(bones)]
    def nearest(b):
        if b in kept: return b
        return min(kept, key=lambda k: sum((org[b][c] - org[k][c]) ** 2 for c in range(3)))
    target = [nearest(b) for b in range(bones)]
    new_w = {}; remap = []
    for i in range(nw):
        t = target[dom[i]]
        remap.append(new_w.setdefault(t, len(new_w)))
    if len(new_w) >= nw: return None
    out = struct.pack("<6I", bones, len(new_w), npos, nnrm, nparts, nstrip) + binds
    out += b"".join(struct.pack("<4B3f", t, 0, 0, 1, 1.0, 0.0, 0.0) for t in sorted(new_w, key=new_w.get))
    out += b"".join(struct.pack("<3hH", x, y, z, remap[s]) for x, y, z, s in pos)
    out += b"".join(struct.pack("<3hH", x, y, z, remap[s]) for x, y, z, s in nrm)
    return out + rest
