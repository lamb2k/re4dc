#!/usr/bin/env python3
"""model_registry.py <spec.json> <out dir> [--tree <checkout>] [--package-room <hex room>] [--source-normal-length]
  [--player-ashley] [--wide-identity] [--ch23-facts] [--ch23-mendez-budget] [--ch22-luis-coverage] [--slots]
(D367 generic native models, 2026-10-03)

--player-ashley (default off): with --slots, exact pl01 model0/141-joint/seven-role
source blobs name player-family storage (1), matching ReadPlayerData. Requires
NATIVE_MODEL_REGISTRY_PL_ASHLEY=1. Other archives retain enemy family 2.

--slots (lane ps2cast 2026-10-14, default off: output unchanged; package only, NATIVE_MODEL_REGISTRY_SLOTS images):
a cast whose source.json lists "draw_slots" (ps2_ashley.py: Ashley's 141-joint GC skeleton, 68 joints drawn) packs
its chunks on those draw slots (header bone_count = slot count, weights name slots) while the descriptor keeps the
complete source skeleton for the runtime's full proof: descriptor word 44 bits 8..15 = source joint count S, the
parents run = S source parents (u8, 0xff = root) followed by the slot map (bones bytes, strictly increasing source
joint indices), the bind run = S rest inverses. Sections may be attachment models (head / hair / hands: a local part
table whose attach ids name distinct source joints) instead of the full skeleton. The target image is PS2_ASHLEY's
(RE4DC_NMR_ASHLEY): up to 32 source texture facts and 10 source BIN models per package and 17 texture facts per role
(pl11 TPL 5 has 17 images), and
a 256 KiB package + skin ceiling in her rooms (the loader allocates the actual size; packages without --slots keep 192 KiB).

--ch22-luis-coverage (default off, --package-room 11c only): the exact pinned
Luis conversion retains all six source identities while head/face share one
draw and the complete hair uses one masked run. Requires ROUTE_CH22=1, PACK=1
and MASK=1; allows the 83 material facts for body and gun within 192 KiB.
Replacement hair opacity still requires separately reviewed source evidence.

--ch23-facts (default off): target ROUTE_CH23=1 allows 128 source material part
facts per room package instead of 32. Closed/open em13 needs 35 facts and all
three em35 forms need 124. Default output remains unchanged.

--ch23-mendez-budget (default off): with --ch23-facts and --package-room 11f,
raise the aligned package + skin limit from 192 KiB to 640 KiB. The target's
ROUTE_CH23=1 loader allows this only in r11f and allocates the actual file and
skin size, plus 32 bytes for alignment. Other rooms retain the 192 KiB ceiling.

--wide-identity (Phase 2 A5, 2026-10-11, default off: the output is byte-identical to before): the target image is
the combined ACTOR_PL08 + NATIVE_MODEL_REGISTRY recipe, whose lifetime masks are wide (actor_material_records.inc
RE4DC_ACTOR_WIDE_IDENTITY: BlobMask u64, three role words). The capacities become 64 source blobs and 96 role rows,
and the base rows counted against them include the pl08 rows (actor_material_records_pl08_blobs.inc / _roles.inc),
as the runtime's kBaseBlobs / kBaseRoles do. The runtime pack check (coarse_actor_registry_pack_check.inc) still
bounds a room package by kRoomBlobs / kRoomRoles of the image it loads into.

--source-normal-length (2026-10-04, default off: the output is byte-identical to before): every cast normal keeps
its direction and takes the length of its SOURCE BIN's normals. GX transforms normals without renormalising and
lights with n.l, and its normal fraction is fixed by the type (s8: 6 bits, s16: 14 bits), so the source's stored
normal length is part of its lighting (the stage-1 animal BINs store s8 normals of length ~127/64 = 1.97); unit cast
normals light the same actor about half as bright. The length is measured from the source BIN (mean of every
normal, recorded per section in registry-manifest.json). Fail closed: a source BIN whose normal lengths are not
uniform (max - min > 0.05), has no normals, or whose length does not fit the s16 / 14-bit encoding (>= 1.9999)
refuses the whole generation; so does a cast normal of zero length.

Generates the private NATIVE_MODEL_REGISTRY bundle (game/native_model_registry.mk) from validated cast packs and
the original archives. PRIVATE output: never commit it or put it in a patch (it holds converted meshes).

Inputs (read only; each copied into <out>/inputs/ with sha256 before / after the copy):
  <spec>                                   descriptors: cast set name, source archive, cModel id, source types
  <cast>/<revision_overlay>/integration-bundle/catalog.json   the explicitly named revision overlay
  <cast>/<name>/<revision>/revision-manifest.json            must agree with the catalog (header sha256)
  <cast>/<name>/manifest.json, source/candidate-revisions.json  the base selection (recorded, preserved)
  <cast>/<name>/source-bindings.json, source.json             source sections, skeleton, rest matrices
  the level's runtime header and every texture package it binds (by source_info)
  the original archives named by <cast>/source/archive-audit.json (sha256 checked)
  <tree>/port/dreamcast/game/actor_material_records.inc       base rows (capacities; fact-extraction self-check)

Fail-closed rules (exit 1, no output dir left behind): catalog / manifest / header / package hash disagreement;
a section whose archive BIN differs from source-bindings (counts, parts, flags, vertex signature); sections that
disagree on the hierarchy or an attach map that is not the identity; header chunks not in source_info order or
not one per section; a weight bone outside the skeleton, a weight set that does not sum to 1, a one-bone weight
other than 1.0; a stream that is not a level-zero FE/v3 blob or does not bound-check (tools mirror of
coarse_actor_preflight.h preflight_chunk); a chunk without a texture package, a package that is paletted /
not one texture / not a supported format; two descriptors with the same (archive, BIN set, TPL) source identity;
a source TPL with a mipmapped / non-base sampler; exceeding the runtime tables' capacities (source blobs <= 32,
role rows <= 64 (64 / 96 with --wide-identity), materials per actor <= 3, chunks per actor <= 8, palette entries per chunk <= 256).
Descriptors whose SOURCE materials need a capability the flat owner path does not implement (bump, mask/alpha
pass) are NOT emitted for runtime; they are listed as contract entries in registry-manifest.json with the reason.

Outputs: native_model_registry.h (namespace nmr), native_model_registry_facts.inc / _roles.inc / _blobs.inc
(source identity rows for coarse_actor_material.inc), tex/<crc>-<fnv>.re4tex, registry-manifest.json (descriptor
<-> rooms, runtime / contract status, hashes, exact revision selections), SHA256SUMS. With --package-room also
package/r<room>/registry.re4nmr (NATIVE_MODEL_REGISTRY_PACK=1: the room-owned package, staged as
dc/native/r<room>/registry.re4nmr; layout in write_package; identical chunk geometry stored once).
"""
import hashlib, json, os, re, shutil, struct, sys, zlib

MATERIAL_ROWS = 64          # actor_lifetime.inc Info::roles mask capacity
SOURCE_BLOBS = 32           # actor_lifetime.inc Asset::templates mask capacity
CH22_LUIS_COVERAGE = False  # explicit room11c pinned source coverage; package-only
SLOTS = False               # --slots: draw-slot descriptors (source.json draw_slots), package only
ASHLEY_RIG = False          # --ashley-rig: require the original full pl11 PS2 rig source contract
WIDE_IDENTITY = False       # --wide-identity: 64 / 96 and the pl08 base rows (RE4DC_ACTOR_WIDE_IDENTITY)
ACTOR_MATERIALS = 3         # actor_native_owner.h kRe4dcActorMaterials
ACTOR_CHUNKS = 8            # Re4dcActorPlan info[8]
ROLE_TEXTURES5 = False      # --roles5: a role's TPL may have 19 images (RE4DC_NMR_ROLE_TEXTURES 19)
ROLE_TEX23 = False          # --role-tex23: 23 images (NATIVE_MODEL_REGISTRY_ROLE_TEX23, the r320 helicopter em3d TPL 6)
POOL = False                # --pool: pool descriptors (spec "pool": true), package only (NATIVE_MODEL_REGISTRY_POOL images)
POOL_SECTIONS = 48          # coarse_actor_owner_registry.inc kRegPoolSections
APPEARANCE0 = 0x200         # registry appearances 0x200 + descriptor index (Ganado 0..4, Leon 0x100)
# coarse_actor_material.inc Need bits and what the flat owner path implements for a non-Leon actor
DIFFUSE, SPECULAR, MASK, BUMP, MORPH, SOURCE_LIGHTING, SOURCE_PASS, ATLAS_SAMPLER = 1, 2, 4, 8, 16, 32, 64, 128
FLAT_IMPLEMENTED = DIFFUSE | SOURCE_LIGHTING | ATLAS_SAMPLER | SPECULAR
UNKNOWN = 1 << 16          # a source material program flag outside the certificate's known set (0..7, 0x80)
ALT_SPECULAR = 1 << 8      # material flag 0x80 (specularSetup2, GX only on the DC source path; Phase 2 A3 crow)
NEED_NAMES = {DIFFUSE: 'diffuse', SPECULAR: 'specular', MASK: 'mask/alpha pass', BUMP: 'bump', MORPH: 'morph',
              SOURCE_LIGHTING: 'source lighting', SOURCE_PASS: 'source pass', ATLAS_SAMPLER: 'atlas sampler',
              ALT_SPECULAR: 'alternate specular (flag 0x80)', UNKNOWN: 'an unknown material program (flags outside 0..7, 0x80)'}


class Fail(Exception):
    pass


def sha(b):
    return hashlib.sha256(b).hexdigest()


def digest(b):
    f = 2166136261
    for x in b:
        f = ((f ^ x) * 16777619) & 0xffffffff
    return [len(b), zlib.crc32(b) & 0xffffffff, f]


def word(b, o):
    return struct.unpack_from('>I', b, o)[0]


def half(b, o):
    return struct.unpack_from('>H', b, o)[0]


def swap16(b):
    if len(b) % 2:
        raise Fail('odd swap16 span')
    o = bytearray(b); o[::2] = b[1::2]; o[1::2] = b[::2]
    return bytes(o)


class Inputs:
    """Copies every input under <out>/inputs (hash before, after and of the copy must agree)."""
    def __init__(self, out):
        self.dir = os.path.join(out, 'inputs'); self.files = {}

    def take(self, path, rel):
        if rel in self.files:
            return self.files[rel][0]
        if not os.path.isfile(path):
            raise Fail(f'missing input {path}')
        dst = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        a = sha(open(path, 'rb').read()); shutil.copy2(path, dst)
        b = sha(open(dst, 'rb').read()); c = sha(open(path, 'rb').read())
        if not a == b == c:
            raise Fail(f'{path} changed while copying (an asset agent is writing): rerun later')
        self.files[rel] = (dst, a, path)
        return dst

    def json(self, path, rel):
        return json.load(open(self.take(path, rel)))


# ---------------------------------------------------------------- cast header (the cast's packer output)
ARRAY = re.compile(r'alignas\(32\) static (?:const )?unsigned char (i\d+)_(pos|nrm|uv|gx)\[\] = \{(.*?)\};', re.S)
WEIGHTS = re.compile(r'static const Weight (i\d+)_weights\[\] = \{(.*?)\n\};', re.S)
WROW = re.compile(r'\{\{(\d+),(\d+),(\d+)\},(\d+),\{([^}]*)\}\}')
CHUNKS = re.compile(r'static Chunk chunks\[\] = \{(.*?)\n\};', re.S)
CROW = re.compile(r'\{(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(i\d+)_pos,(i\d+)_nrm,(i\d+)_uv,(i\d+)_gx,(i\d+)_weights\}')


def parse_header(path):
    text = open(path).read()
    arrays = {}
    for prefix, kind, body in ARRAY.findall(text):
        vals = [int(x) for x in body.replace('\n', ',').split(',') if x.strip()]
        if any(v < 0 or v > 255 for v in vals):
            raise Fail(f'{path}: {prefix}_{kind} is not a byte array')
        arrays[(prefix, kind)] = bytes(vals)
    weights = {}
    for prefix, body in WEIGHTS.findall(text):
        rows = []
        for b0, b1, b2, n, vals in WROW.findall(body):
            v = [float.fromhex(x.strip().rstrip('f')) for x in vals.split(',')]
            if len(v) != 3:
                raise Fail(f'{path}: {prefix} weight row has {len(v)} values')
            rows.append(((int(b0), int(b1), int(b2)), int(n), v))
        weights[prefix] = rows
    m = CHUNKS.search(text)
    if not m:
        raise Fail(f'{path}: no chunk table')
    chunks = []
    for row in CROW.findall(m.group(1)):
        info, npos, nnrm, npal, tris, sbytes = (int(x) for x in row[:6])
        prefix = row[6]
        if set(row[6:]) != {prefix}:
            raise Fail(f'{path}: chunk arrays of different infos')
        chunks.append(dict(source_info=info, position_count=npos, normal_count=nnrm, palette_count=npal,
                           triangles=tris, stream_bytes=sbytes, prefix=prefix))
    bm = re.search(r'static constexpr unsigned bone_count=(\d+);', text)
    if not bm:
        raise Fail(f'{path}: no bone_count')
    for c in chunks:
        p = c['prefix']
        for k in ('pos', 'nrm', 'uv', 'gx'):
            if (p, k) not in arrays:
                raise Fail(f'{path}: {p}_{k} missing')
        if p not in weights:
            raise Fail(f'{path}: {p}_weights missing')
        c['positions'], c['normals'] = arrays[(p, 'pos')], arrays[(p, 'nrm')]
        c['uv'], c['stream'], c['weights'] = arrays[(p, 'uv')], arrays[(p, 'gx')], weights[p]
        if len(c['stream']) != c['stream_bytes']:
            raise Fail(f'{path}: {p} stream {len(c["stream"])} B != {c["stream_bytes"]}')
    return chunks, int(bm.group(1))


def u16(b, o):
    return b[o] | (b[o + 1] << 8)


def f32le(b, o):
    return struct.unpack_from('<f', b, o)[0]


def preflight_chunk(c, bones):
    """tools mirror of coarse_actor_preflight.h preflight_chunk (the runtime proof runs again on target)"""
    np_, nn, npal = c['position_count'], c['normal_count'], c['palette_count']
    if not (0 < np_ <= 65535 and 0 < nn <= 65535 and 0 < npal <= 256 and 0 < bones <= 256):
        return 'Array'
    if len(c['positions']) < np_ * 8 or len(c['normals']) < nn * 8 or not c['uv'] or len(c['uv']) % 4 or len(c['weights']) != npal:
        return 'Array'
    for (bs, n, v) in c['weights']:
        if not 1 <= n <= 3:
            return 'Weights'
        s = 0.0
        for k in range(n):
            if bs[k] >= bones or not (0.0 <= v[k] <= 1.0):
                return 'Weights'
            s += v[k]
        if abs(struct.unpack('<f', struct.pack('<f', s))[0] - 1.0) > 0.0001:
            return 'Weights'
    if any(u16(c['positions'], i * 8 + 6) >= npal for i in range(np_)):
        return 'Palette'
    if any(u16(c['normals'], i * 8 + 6) >= npal for i in range(nn)):
        return 'Palette'
    s = c['stream']
    if len(s) < 32 or len(s) > 1 << 20:
        return 'Header'
    if s[0] != 0xfe or s[1] != 3 or (s[2] & 0x83) or s[3] or u16(s, 12) or u16(s, 14):
        return 'Header'
    if f32le(s, 28) < 0:
        return 'Header'
    nm, rec, idx = u16(s, 4), u16(s, 8) * 4, u16(s, 10) * 4
    if not nm or len(s) < 32 + nm * 8 or rec < 32 + nm * 8 or idx < rec or idx > len(s):
        return 'Table'
    records = indices = triangles = 0
    for m in range(nm):
        t = 32 + m * 8
        counts = struct.unpack_from('<I', s, t)[0]
        nv, ni, nt = counts & 255, (counts >> 8) & 4095, counts >> 20
        if not nv or nv > 128 or not ni or ni > 1024 or not nt or u16(s, t + 4) != records or u16(s, t + 6) != indices:
            return 'Table'
        if (records + nv) * 6 > idx - rec or idx + indices + ni > len(s):
            return 'Table'
        for v in range(nv):
            r = rec + (records + v) * 6
            if u16(s, r) >= np_ or u16(s, r + 2) >= nn or u16(s, r + 4) * 4 >= len(c['uv']):
                return 'Record'
        ln = tris = 0
        for j in range(ni):
            index = s[idx + indices + j]
            ln += 1
            if (index & 127) >= nv or ln > 64:
                return 'Strip'
            if index & 128:
                if ln < 3:
                    return 'Strip'
                tris += ln - 2; ln = 0
        if ln or tris != nt:
            return 'Count'
        records += nv; indices += ni; triangles += nt
    if triangles != c['triangles']:
        return 'Count'
    return None


def skin_stream_bytes(weights):
    """coarse_skin.h coarse_group_build's stream size (16 B per group header, 24 B per entry)"""
    if len(weights) > 256:
        raise Fail('more than 256 palette entries')
    done, groups, entries = [False] * len(weights), 0, 0
    for j, (bj, nj, vj) in enumerate(weights):
        if done[j]:
            continue
        groups += 1
        for i in range(j, len(weights)):
            bi, ni, vi = weights[i]
            if done[i] or ni != nj or bi[:nj] != bj[:nj]:
                continue
            if nj == 1 and vi[0] != 1.0:
                raise Fail('a one-bone palette entry with weight != 1 (coarse_group_build copies it)')
            done[i] = True; entries += 1
    return groups * 16 + entries * 24


# ---------------------------------------------------------------- original archives (identity facts)
def archive_facts(tree):
    sys.path[:0] = [os.path.join(tree, 'tools'), os.path.join(tree, 'port/dreamcast/tools')]
    from motion import archive  # noqa: E402  (repo tools)
    from convert_tpl import parse_tpl  # noqa: E402
    import le_mirror  # noqa: E402
    return archive, parse_tpl, le_mirror


def bin_facts(arc, le_mirror, name, no):
    """actor-material-r1 inspect_archives.py model() + actor-lifetime-r2 normalized digest, verbatim rules"""
    ent = arc.entry(no - 4)
    if ent.tag != 'BIN':
        raise Fail(f'{name} entry {no} is {ent.tag}, not BIN')
    b = ent.data
    flags = word(b, 32); nv = half(b, 56); nn = half(b, 58); nw = b[24]; ext = half(b, 42)
    if ext > 255:
        raise Fail(f'{name}/{no}: weight_ext_num {ext} (extended palettes unsupported)')
    pos = swap16(b[word(b, 48):word(b, 48) + nv * 8])
    nrm = b[word(b, 52):word(b, 52) + nn * (4 if flags & 0x20000000 else 8)]
    if not flags & 0x20000000:
        nrm = swap16(nrm)
    # The stored normal length (GX's fixed normal fraction: s8 6 bits, s16 14 bits), for --source-normal-length.
    if flags & 0x20000000:
        lens = [((nrm[i] ^ 128) - 128) ** 2 + ((nrm[i + 1] ^ 128) - 128) ** 2 + ((nrm[i + 2] ^ 128) - 128) ** 2
                for i in range(0, nn * 4, 4)]
        lens = [l ** 0.5 / 64.0 for l in lens]
    else:
        lens = [sum(v * v for v in struct.unpack_from('<3h', nrm, i)) ** 0.5 / 16384.0 for i in range(0, nn * 8, 8)]
    normal_length = [sum(lens) / len(lens), min(lens), max(lens)] if lens else None
    w = b[word(b, 20):word(b, 20) + nw * 8]
    parts = []; at = word(b, 28); maxuv = -1
    for _ in range(half(b, 26)):
        h = b[at:at + 32]; n = word(h, 24); stream = b[at + 32:at + 32 + n]; x = 0
        stride = 8 if flags & 0x80000000 else 6
        while x < n:
            op = stream[x]; x += 1
            if op == 0:
                continue
            if op not in (0x80, 0x90, 0x98):
                raise Fail(f'{name}/{no}: display list opcode {op:#x}')
            count = half(stream, x); x += 2
            for v in range(count):
                maxuv = max(maxuv, half(stream, x + v * stride + stride - 2))
            x += count * stride
        parts.append([h[11:24].hex(), n, word(h, 28), *digest(stream)[1:]])
        at += 32 + n
    uv = swap16(b[word(b, 16):word(b, 16) + (maxuv + 1) * 4])
    nb = bytearray(b); s = le_mirror.Swapper(nb, f'{name}/{no}')
    with s.bounded(0, len(nb)):
        le_mirror.fmt_bin(s, 0, len(nb), f'{name}/{no}')
    return {'sha256': sha(b), 'header': [flags, b[40], b[25], nv, nn, word(b, 36), nw, ext, half(b, 26), word(b, 60)],
            'positions': digest(pos), 'normals': digest(nrm), 'weights': digest(w), 'uv': digest(uv), 'parts': parts,
            'normalized': digest(bytes(nb)), 'normalized_sha256': sha(bytes(nb)), 'positions_le_first64': pos[:64],
            'normal_length': normal_length}


def tpl_facts(arc, parse_tpl, name, no):
    ent = arc.entry(no - 4)
    if ent.tag != 'TPL':
        raise Fail(f'{name} entry {no} is {ent.tag}, not TPL')
    b = ent.data; desc = word(b, 8); rows = []
    for k, im in enumerate(parse_tpl(b)):
        th = word(b, desc + 8 * k); pal = im.palette_data or b''
        key = digest(struct.pack('<5I', im.width, im.height, im.format,
                                 im.palette_format if im.palette_format is not None else 0xffffffff, len(pal)) + im.data + pal)[1:]
        rows.append({'key': key, 'whf': [im.width, im.height, im.format],
                     'sampler': [word(b, th + 12), word(b, th + 16), word(b, th + 20), word(b, th + 24), word(b, th + 28),
                                 b[th + 32], b[th + 33], b[th + 34]],
                     'palette': None if not pal else [im.palette_format, *digest(pal)]})
    return {'sha256': sha(b), 'textures': rows}


def material_needs(model, texture_count):
    """coarse_actor_material.inc info(): the Need bits a section's part materials require (or a Fail reason)"""
    need = 0
    for material, *_ in model['parts']:
        mat = bytes.fromhex(material); f = mat[0]
        if mat[1] >= texture_count:
            return None, 'colour texture index outside the TPL'
        if f & 4:
            if mat[3] >= texture_count:
                return None, 'mask texture index outside the TPL'
            need |= MASK | SOURCE_PASS
        if f & 1:
            if mat[2] >= texture_count:
                return None, 'bump texture index outside the TPL'
            need |= BUMP
        if f & 0x13:
            need |= SPECULAR
        if f & 0x80:
            need |= ALT_SPECULAR  # a contract unless dropped (source_drops "alt-specular")
        if f & ~0x87:
            need |= UNKNOWN   # the runtime certificate declines (Error::Material): a contract, not a data fault
    return need, None


def need_names(bits):
    return [n for b, n in sorted(NEED_NAMES.items()) if bits & b]


# ---------------------------------------------------------------- base tables (capacities, self-check)
def pl08_rows(tree):
    """--wide-identity: the pl08 role / blob rows the combined recipe adds to the base tables."""
    g = os.path.join(tree, 'port/dreamcast/game')
    n = lambda f: len(re.findall(r'^\{', open(os.path.join(g, f)).read(), re.M))
    return n('actor_material_records_pl08_roles.inc'), n('actor_material_records_pl08_blobs.inc')


def base_records(tree):
    text = open(os.path.join(tree, 'port/dreamcast/game/actor_material_records.inc')).read()
    roles = re.search(r'static const Role roles\[\] = \{(.*?)\n\};', text, re.S).group(1)
    blobs = re.search(r'static const SourceBlob source_blobs\[\] = \{(.*?)\n\};', text, re.S).group(1)
    nroles = len(re.findall(r'^\{', roles, re.M)); nblobs = len(re.findall(r'^\{', blobs, re.M))
    tex = {}
    for name, body in re.findall(r'static const Texture t_(\w+)\[\] = \{(.*?)\n\};', text, re.S):
        tex[name] = [[int(x) for x in re.findall(r'(\d+)u', row)] for row in body.strip().splitlines()]
    models = {}
    for name, body in re.findall(r'static const Model m_(\w+) = \{(.*?)\};', text):
        models[name] = [int(x) for x in re.findall(r'(\d+)u', body)]
    blobrows = {m: [int(x) for x in re.findall(r'(\d+)u', rest)] for m, rest in re.findall(r'^\{&m_(\w+),(.*)\},$', blobs, re.M)}
    return nroles, nblobs, tex, models, blobrows


def self_check(tree, archive, parse_tpl, le_mirror, audit, inputs, cast):
    """Re-derive the committed em12 appearance-0 rows with this tool's extraction: identical or fail."""
    _, _, tex, models, blobrows = base_records(tree)
    a = audit['em12']
    path = a['source']
    if sha(open(path, 'rb').read()) != a['sha256']:
        raise Fail(f'{path}: sha256 differs from archive-audit.json')
    arc = archive.Archive(path)
    for no in (472, 474, 448, 453):
        f = bin_facts(arc, le_mirror, 'em12', no)
        want = models[f'em12_{no}']
        got = f['header'] + f['positions'] + f['normals'] + f['weights'] + f['uv']
        if want != got:
            raise Fail(f'self-check: em12/{no} model row differs from actor_material_records.inc')
        if blobrows[f'em12_{no}'][-3:] != f['normalized'] or blobrows[f'em12_{no}'][:2] != [2, no]:
            raise Fail(f'self-check: em12/{no} normalized digest differs from source_blobs')
    t = tpl_facts(arc, parse_tpl, 'em12', 473)
    got = [x['key'] + x['whf'] + x['sampler'] + [(x['palette'] or [0xffffffff])[0]] + (x['palette'] or [0, 0, 0, 0])[1:] for x in t['textures']]
    if got != tex['em12_473']:
        raise Fail('self-check: em12/473 texture rows differ from actor_material_records.inc')
    return 'em12 BIN 472/474/448/453 + TPL 473 re-derived identically (model rows, normalized digests, texture rows)'


LUIS_NORMALIZED = {
    4: [74336, 0x1a039939, 0xf6f94446], 6: [21312, 0x112854f5, 0xbba97c84],
    8: [29792, 0x49657759, 0xb6a55fe7], 9: [81312, 0x109e7365, 0x32a1c659],
    10: [13312, 0xefcc04b2, 0xe438fb43], 11: [13120, 0x01e766c0, 0x671da641]}


# Each complete source map is paired with its exact proved native header.
# Keep the sealed first candidate reproducible; the second corrects character
# TPL orientation without changing geometry, weights, bones, or source roles.
LUIS_COVERAGE_HEADERS = {
    'd994ab69fcd9ca9a28723858f8919a4d7658be4500db043cd8892706865c4488':
        '90812064b25cc7305eb58a0c528fb020fa4ef600495b0f4b18599512460308e8',
    '75c2655ee619f800e921850edcea9e0dffcc3af379996cfe9472f89929c36aa0':
        '6fc181444d83b784780d2724732520e71b3c111eb7a7d7e77f35024659c92846'}


def luis_coverage(inputs, descriptor, source, bindings, arc, archive_name):
    """The exact offline six-info/five-draw mapping, never a generic alias option."""
    manifest = descriptor.get('source_coverage_manifest')
    if not manifest:
        return None
    if not CH22_LUIS_COVERAGE or archive_name != 'pl14' or source.get('source_model_id') != 4 or \
       descriptor.get('name') != 'luis-actor' or source.get('source_archive_sha256') != \
       '2b5b554d45a67f12612474a9ed0a1bbeb7cf5882d16a7c67ce7ff25018676f27':
        raise Fail('Luis coverage requires the explicit pinned CH22 source descriptor')
    coverage = inputs.json(manifest, 'coverage/luis-actor.json')
    manifest_sha = sha(open(manifest, 'rb').read())
    if manifest_sha not in LUIS_COVERAGE_HEADERS:
        raise Fail('Luis coverage manifest differs from the reviewed source triangle map')
    source_input = dict(source); source_input.pop('source_model_id')
    if sha(json.dumps(source_input).encode()) != coverage['source_sha256']:
        raise Fail('Luis source skeleton and coverage identities differ from the pinned conversion')
    if [(b['bin'],b['tpl']) for b in bindings] != [(4,5),(6,7),(8,7),(9,5),(10,5),(11,5)]:
        raise Fail('Luis six source BIN/TPL identities differ')
    from motion import modelbin
    for binding in bindings:
        model = modelbin.parse(arc.entry(binding['bin']-4).data)
        expected = [dict(id=p.no,parent=p.parent,attach=p.attach,translation=list(p.pos)) for p in model.parts]
        if binding['part_bindings'] != expected:
            raise Fail('Luis sparse part table differs from its exact source BIN')
    return dict(coverage, reviewed_manifest_sha256=manifest_sha)


# ---------------------------------------------------------------- main
PLAYER_ASHLEY = False
def main():
    args = sys.argv[1:]
    tree = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
    if '--tree' in args:
        i = args.index('--tree'); tree = os.path.abspath(args[i + 1]); del args[i:i + 2]
    package_room = None
    if '--package-room' in args:
        i = args.index('--package-room'); package_room = int(args[i + 1], 16); del args[i:i + 2]
        if not 0x100 <= package_room <= 0x7ff:
            sys.exit('model_registry: --package-room is the hex room number, e.g. 103')
    global PACK_BONES
    if '--pack-bones' in args:
        # NATIVE_MODEL_REGISTRY_BONES (native_model_registry.mk): the loader's skeleton capacity of the target image
        i = args.index('--pack-bones'); PACK_BONES = int(args[i + 1]); del args[i:i + 2]
        if PACK_BONES not in (48, 64, 80, 96, 128):
            sys.exit('model_registry: --pack-bones takes 48, 64, 80, 96 or 128 (NATIVE_MODEL_REGISTRY_BONES)')
    global PLAYER_ASHLEY
    if '--player-ashley' in args:
        args.remove('--player-ashley')
        if '--slots' not in args or package_room is None:
            sys.exit('model_registry: --player-ashley needs --slots and --package-room')
        PLAYER_ASHLEY = True
    global CH22_LUIS_COVERAGE
    if '--ch22-luis-coverage' in args:
        args.remove('--ch22-luis-coverage')
        if package_room != 0x11c:
            sys.exit('model_registry: --ch22-luis-coverage requires --package-room 11c')
        CH22_LUIS_COVERAGE = True
        PACK_CAPACITY['fpart'] = 83  # exact room11c Luis body + independent gun
    global SLOTS, PACK_MAX_BYTES
    global ASHLEY_RIG
    if '--ashley-rig' in args:
        args.remove('--ashley-rig')
        if '--slots' not in args:
            sys.exit('model_registry: --ashley-rig needs --slots')
        ASHLEY_RIG = True
    if '--slots' in args:
        args.remove('--slots')
        if package_room is None:
            sys.exit('model_registry: --slots is package only (--package-room)')
        SLOTS = True
        PACK_CAPACITY['ftex'] = 32  # the PS2_ASHLEY image (RE4DC_NMR_ASHLEY): pl11 TPLs 5 + 8 + 0xB = 28 images
        PACK_CAPACITY['fmodel'] = 10  # and 10 source BIN models (5 shared + the hands 0xC..0x10 of three hand sets)
        # RE4DC_NMR_ASHLEY: a 256 KiB package + skin ceiling (Ashley + her mask runs) in every room she follows Leon to
        # (r117, then the chapter 2 rooms; coarse_actor_registry_pack_check.inc RE4DC_NMR_PACK_KIB applies to every room).
        PACK_MAX_BYTES = 256 * 1024
    if '--fact-parts' in args:
        # --fact-parts N (lane ps2cast 2026-10-15): the image's part-fact capacity RE4DC_NMR_FACTS (native_model_registry.mk:
        # 40 with PS2_CAST_MERCHANT, 72 with PS2_ASHLEY); a room package with more source parts than 32 (the r104 robed em13)
        i = args.index('--fact-parts'); n = int(args[i + 1]); del args[i:i + 2]
        if n not in (40, 72):
            sys.exit('model_registry: --fact-parts takes 40 or 72 (RE4DC_NMR_FACTS)')
        PACK_CAPACITY['fpart'] = n
    if '--ch23-facts' in args:
        args.remove('--ch23-facts')
        PACK_CAPACITY['fpart'] = 128  # RE4DC_ROUTE_CH23, coarse_actor_registry_pack_check.inc
    if '--ch23-mendez-budget' in args:
        args.remove('--ch23-mendez-budget')
        if package_room != 0x11f or PACK_CAPACITY['fpart'] != 128:
            sys.exit('model_registry: --ch23-mendez-budget requires --package-room 11f and --ch23-facts')
        PACK_MAX_BYTES = 640 * 1024
    immutable_arrays = '--immutable-array-alias' in args
    if immutable_arrays:
        args.remove('--immutable-array-alias')
        if package_room != 0x11f or PACK_CAPACITY['fpart'] != 128:
            sys.exit('model_registry: --immutable-array-alias requires --package-room 11f and --ch23-facts')
    source_normal_length = '--source-normal-length' in args
    if source_normal_length:
        args.remove('--source-normal-length')
        if ASHLEY_RIG:
            sys.exit('model_registry: PS2 Ashley rig must keep PS2 normals; --source-normal-length is forbidden')
    global MATERIAL_ROWS, SOURCE_BLOBS, WIDE_IDENTITY, ROLE_TEXTURES5, ROLE_TEX23
    if '--wide-identity' in args:
        args.remove('--wide-identity')
        WIDE_IDENTITY = True; MATERIAL_ROWS = 96; SOURCE_BLOBS = 64   # RE4DC_ACTOR_WIDE_IDENTITY
    global POOL
    if '--pool' in args:
        # --pool (lane ps2cast 2026-10-15, default off: output unchanged): descriptors whose spec says "pool": true are
        # emitted as pool descriptors (word 44 bit 24; NATIVE_MODEL_REGISTRY_POOL images only, which also widen the
        # identity rows to 128 and the package capacities: chunks / geometries 64, 48 source BIN models, 64 texture
        # facts, 160 part facts, 256 KiB). Package only; needs --wide-identity.
        args.remove('--pool')
        if package_room is None or not WIDE_IDENTITY:
            sys.exit('model_registry: --pool is package only (--package-room) and needs --wide-identity')
        POOL = True; MATERIAL_ROWS = 128
        global ACTOR_MATERIALS
        ACTOR_MATERIALS = 4  # RE4DC_ACTOR_MATERIALS=4 (native_model_registry.mk with the pool): atlas + three mask pairs
        PACK_CAPACITY.update(ref=64, geom=64, fmodel=48, fpart=160, ftex=64)
        PACK_MAX_BYTES = 256 * 1024
    if '--roles5' in args:
        # --roles5 (lane cast16 2026-10-16): NATIVE_MODEL_REGISTRY_ROLES5 images (Info::roles 5 words, 160 role bits).
        args.remove('--roles5')
        if not POOL:
            sys.exit('model_registry: --roles5 needs --pool')
        MATERIAL_ROWS = 160
        PACK_CAPACITY.update(ref=96)  # RE4DC_NMR_CHUNKS 96 with RE4DC_NMR_ROLES5 (coarse_actor_owner_registry.inc)
        PACK_CAPACITY.update(tex=32)  # kRegTextures 32 with RE4DC_NMR_ROLES5 (coarse_actor_owner_registry.inc)
        SOURCE_BLOBS = 128  # kBlobMaskBits 128 with RE4DC_NMR_ROLES5 (actor_material_records.inc two-word BlobMask)
        PACK_CAPACITY.update(fmodel=64, fpart=224)  # coarse_actor_registry_pack_check.inc with RE4DC_NMR_ROLES5
        PACK_MAX_BYTES = 416 * 1024  # RE4DC_NMR_PACK_KIB with RE4DC_NMR_ROLES5
        ROLE_TEXTURES5 = True  # RE4DC_NMR_ROLE_TEXTURES 19 with RE4DC_NMR_ROLES5 (coarse_actor_registry_pack_check.inc)
    if '--role-tex23' in args:
        args.remove('--role-tex23')
        if not ROLE_TEXTURES5:
            sys.exit('model_registry: --role-tex23 needs --roles5')
        ROLE_TEX23 = True
    if len(args) != 2:
        sys.exit(__doc__)
    spec_path, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    if os.path.exists(out):
        sys.exit(f'model_registry: {out} exists (a bundle is never rewritten in place: new selection, new dir)')
    tmp = out + '.tmp-%d' % os.getpid()
    os.makedirs(tmp)
    try:
        report = generate(spec_path, tmp, tree, package_room, source_normal_length, immutable_arrays)
    except Fail as e:
        shutil.rmtree(tmp)
        sys.exit(f'model_registry: FAIL {e}')
    os.rename(tmp, out)
    print(json.dumps(report, indent=1))


def source_length_normals(name, c, src):
    """--source-normal-length: the chunk's s16 / 14-bit normals rescaled to the source BIN's stored normal length
    (direction kept, palette word untouched). Returns (normals, manifest record)."""
    if not src:
        raise Fail(f'{name} chunk {c["source_info"]}: the source BIN has no normals (no source length to keep)')
    mean, lo, hi = src
    if hi - lo > 0.05:
        raise Fail(f'{name} chunk {c["source_info"]}: source normal lengths {lo:.4f}..{hi:.4f} are not uniform '
                   '(one stored length per BIN is the only supported source mode)')
    if not 0.0 < mean < 1.9999:
        raise Fail(f'{name} chunk {c["source_info"]}: source normal length {mean:.4f} does not fit s16 / 14 bits')
    out = bytearray(c['normals']); cast = []
    for i in range(c['normal_count']):
        x, y, z = struct.unpack_from('<3h', out, i * 8)
        l = (x * x + y * y + z * z) ** 0.5
        if not l:
            raise Fail(f'{name} chunk {c["source_info"]}: cast normal {i} has zero length')
        cast.append(l / 16384.0)
        k = mean * 16384.0 / l
        v = [int(round(t * k)) for t in (x, y, z)]
        if any(abs(t) > 32767 for t in v):
            raise Fail(f'{name} chunk {c["source_info"]}: rescaled normal {i} overflows s16')
        struct.pack_into('<3h', out, i * 8, *v)
    return bytes(out), dict(source_mean=round(mean, 6), source_min=round(lo, 6), source_max=round(hi, 6),
                            cast_mean_before=round(sum(cast) / len(cast), 6), mode='source BIN mean length')


def generate(spec_path, out, tree, package_room=None, source_normal_length=False, immutable_arrays=False):
    inputs = Inputs(out)
    spec = inputs.json(spec_path, 'spec.json')
    cast = spec['cast_dir']; level = spec['level']; overlay_rel = spec['revision_overlay'].strip('/')
    archive, parse_tpl, le_mirror = archive_facts(tree)
    audit = inputs.json(os.path.join(cast, spec['archive_audit']), 'cast/' + spec['archive_audit'])
    selfcheck = self_check(tree, archive, parse_tpl, le_mirror, audit, inputs, cast)
    catalog = {e['name']: e for e in inputs.json(os.path.join(cast, overlay_rel, 'integration-bundle/catalog.json'),
                                                   f'cast/{overlay_rel}/integration-bundle/catalog.json')}
    base_revisions = inputs.json(os.path.join(cast, 'source/candidate-revisions.json'), 'cast/source/candidate-revisions.json')
    nroles0, nblobs0, _, _, _ = base_records(tree)
    if WIDE_IDENTITY:
        r8, b8 = pl08_rows(tree); nroles0 += r8; nblobs0 += b8
    arcs, bins, tpls = {}, {}, {}
    runtime, contracts, seen_identity = [], [], {}
    textures = []  # (crc, fnv, w, h, package path)
    for d in spec['descriptors']:
        name = d['name']
        if name not in catalog:
            raise Fail(f'{name}: not in the {overlay_rel} catalog (no implicit fallback to an older revision)')
        e = catalog[name]; rev = e['revision']
        rm = inputs.json(os.path.join(cast, name, rev, 'revision-manifest.json'), f'cast/{name}/{rev}/revision-manifest.json')
        L, RL = e['levels'][level], rm['levels'][level]
        if rm['revision'] != rev or RL['header_sha256'] != L['header_sha256'] or RL['runtime_header'] != L['runtime_header']:
            raise Fail(f'{name}: catalog and revision manifest disagree (mid-publish?)')
        if rm['texture_packages'] != e['texture_packages']:
            raise Fail(f'{name}: catalog and revision manifest texture packages disagree')
        base = inputs.json(os.path.join(cast, name, 'manifest.json'), f'cast/{name}/manifest.json')
        base_rev = base_revisions.get(name, {}).get('revision', base['revision'])
        if e.get('previous_revision') not in (None, base_rev):
            raise Fail(f'{name}: overlay {rev} follows {e.get("previous_revision")}, the base selection is {base_rev}')
        hdr = inputs.take(os.path.join(cast, L['runtime_header']), 'cast/' + L['runtime_header'])
        if sha(open(hdr, 'rb').read()) != L['header_sha256']:
            raise Fail(f'{name}: {L["runtime_header"]} sha256 differs from the catalog')
        binds = inputs.json(os.path.join(cast, name, 'source-bindings.json'), f'cast/{name}/source-bindings.json')
        src = inputs.json(os.path.join(cast, name, 'source.json'), f'cast/{name}/source.json')
        if source_normal_length and src.get('ps2_rig'):
            raise Fail(f'{name}: PS2 rig must keep PS2 normals; source-derived normal length is forbidden')
        # The spec's model id / source types are the cast's own, not a label: a descriptor never claims another
        # appearance's selection (the cow type 0 vs type 1 TPLs share one BIN).
        if int(d['model_id'], 16) != src.get('source_model_id') or sorted(d['source_types'] or []) != sorted(src.get('types') or []):
            raise Fail(f'{name}: spec model_id/source_types {d["model_id"]}/{d["source_types"]} differ from source.json '
                       f'{src.get("source_model_id")}/{src.get("types")}')
        arcname = d['archive']
        if arcname not in audit or src.get('source_archive_sha256', audit[arcname]['sha256']) != audit[arcname]['sha256']:
            raise Fail(f'{name}: archive {arcname} not in archive-audit.json or source.json names another archive')
        if arcname not in arcs:
            p = audit[arcname]['source']
            if sha(open(p, 'rb').read()) != audit[arcname]['sha256']:
                raise Fail(f'{p}: sha256 differs from archive-audit.json')
            arcs[arcname] = archive.Archive(p)
        arc = arcs[arcname]
        luis = luis_coverage(inputs, d, src, binds, arc, arcname)
        if luis and L['header_sha256'] != LUIS_COVERAGE_HEADERS[luis['reviewed_manifest_sha256']]:
            raise Fail('Luis native header differs from the proved complete source triangle set')
        # ---- skeleton (one per model; every section's bone table agrees)
        pb = binds[0]['part_bindings']
        bones = len(pb)
        if any(p['id'] != i or p['attach'] != i for i, p in enumerate(pb)):
            raise Fail(f'{name}: attach map is not the identity (a local attachment index needs its own map)')
        parents = [p['parent'] for p in pb]
        draw_slots = src.get('draw_slots')
        if draw_slots is not None and not SLOTS:
            raise Fail(f'{name}: source.json has draw_slots (needs --slots, a NATIVE_MODEL_REGISTRY_SLOTS package)')

        def attachment(b):
            # --slots: an attachment model's local part table (fewer parts, distinct attach ids naming source joints)
            a = [p['attach'] for p in b['part_bindings']]
            return draw_slots is not None and len(a) == b['parts'] < bones and len(set(a)) == len(a) and all(0 <= x < bones for x in a)
        # partial_sections (descriptor opt-in; lane ps2cast-st3, the stage-3 soldiers): a head / hand BIN may carry
        # only the parts it weights (or repeat a hand root by attach id: em11 type 7), each attached to the body part of its attach id (GC calcWeightMat); its parents
        # name body parts (a section root: -1). The registry skins every section from the body's parts either way.
        partial = set()
        if d.get('partial_sections'):
            for k, b in enumerate(binds[1:], 1):
                q = b['part_bindings']
                if len(q) == bones:
                    continue
                at = [p['attach'] for p in q]
                if any(not (0 <= a < bones) for a in at) or \
                        any(p['id'] != i or p['parent'] not in (-1, parents[p['attach']]) for i, p in enumerate(q)):
                    raise Fail(f'{name} section {k}: partial skeleton is not a subset of the body hierarchy')
                partial.add(k)
        if not luis and any([p['parent'] for p in b['part_bindings']] != parents and not attachment(b)
                            for k, b in enumerate(binds) if k not in partial):
            raise Fail(f'{name}: sections disagree on the hierarchy')
        if parents[0] != -1 or any(not (-1 <= q < i) for i, q in enumerate(parents)):
            raise Fail(f'{name}: parents are not a forest in index order')
        sbones = src.get('bones') or []
        if len(sbones) != bones or any(b.get('id') != i or 'rest' not in b or b.get('parent') != parents[i] for i, b in enumerate(sbones)):
            raise Fail(f'{name}: source.json skeleton differs from source-bindings ({len(sbones)} vs {bones})')
        bind = []
        for b in sbones:
            m = b['rest']; R = [row[:3] for row in m[:3]]; t = [m[0][3], m[1][3], m[2][3]]
            det = (R[0][0] * (R[1][1] * R[2][2] - R[1][2] * R[2][1]) - R[0][1] * (R[1][0] * R[2][2] - R[1][2] * R[2][0])
                   + R[0][2] * (R[1][0] * R[2][1] - R[1][1] * R[2][0]))
            if abs(det) < 1e-6:
                raise Fail(f'{name}: singular rest matrix')
            inv = [[(R[(j + 1) % 3][(i + 1) % 3] * R[(j + 2) % 3][(i + 2) % 3] - R[(j + 1) % 3][(i + 2) % 3] * R[(j + 2) % 3][(i + 1) % 3]) / det
                    for j in range(3)] for i in range(3)]
            ti = [-sum(inv[r][k] * t[k] for k in range(3)) for r in range(3)]
            bind.append([inv[0][0], inv[0][1], inv[0][2], ti[0], inv[1][0], inv[1][1], inv[1][2], ti[1],
                         inv[2][0], inv[2][1], inv[2][2], ti[2]])
        draw = bones
        if draw_slots is not None:
            if (not draw_slots or bones > 255 or any(not isinstance(x, int) for x in draw_slots) or
                    any(not 0 <= x < bones for x in draw_slots) or draw_slots != sorted(set(draw_slots))):
                raise Fail(f'{name}: draw_slots must be strictly increasing source joints < {bones} (<= 255 joints)')
            draw = len(draw_slots)
        if ASHLEY_RIG and not (src.get('ps2_rig', {}).get('schema') == 'ashley-ps2-rig-1' and
                src['ps2_rig'].get('ps2_bones') == 81 and arcname == 'pl11' and
                int(d['model_id'], 0) == 3 and bones == 141 and len(binds) == 7 and draw_slots is not None):
            raise Fail(f'{name}: --ashley-rig requires the full pl11 PS2 rig 141-joint seven-role partner')
        # ---- sections against the archive
        sections, need, contract = [], 0, []
        for i, b in enumerate(binds):
            key = (arcname, b['bin'])
            if key not in bins:
                bins[key] = bin_facts(arc, le_mirror, arcname, b['bin'])
            f = bins[key]
            h = f['header']
            if (h[3], h[4], h[6], h[2], h[1]) != (b['positions'], b['normals'], b['palettes'], b['parts'], b['shift']) or \
                    int(b['flags'], 16) != h[0]:
                raise Fail(f'{name} section {i}: archive BIN {b["bin"]} differs from source-bindings (counts/flags)')
            if luis and f['normalized'] != LUIS_NORMALIZED[b['bin']]:
                raise Fail(f'{name} section {i}: pinned normalized source BIN differs')
            if not luis and b['parts'] != bones and not attachment(b) and i not in partial:
                raise Fail(f'{name} section {i}: BIN has {b["parts"]} parts, the skeleton {bones}')
            # the runtime signature (coarse_ganado_cast.cpp fingerprint): FNV-1a of the first 64 bytes of the LE positions
            if '%08x' % digest(f['positions_le_first64'])[2] != b['source_vertex_fnv64_le']:
                raise Fail(f'{name} section {i}: vertex signature {b["source_vertex_fnv64_le"]} does not match BIN {b["bin"]}')
            tkey = (arcname, b['tpl'])
            if tkey not in tpls:
                tpls[tkey] = tpl_facts(arc, parse_tpl, arcname, b['tpl'])
            t = tpls[tkey]
            for x in t['textures']:
                if x['sampler'] != [1, 1, 1, 1, 0, 0, 0, 0]:
                    raise Fail(f'{name}: TPL {b["tpl"]} has a non-base / mipmapped sampler {x["sampler"]}')
            n, why = material_needs(f, len(t['textures']))
            if why:
                raise Fail(f'{name} section {i}: {why}')
            if 'bump' in d.get('source_drops', []) and n & BUMP:
                # A texture the source path only binds as a bump map (bumpSetup, GX stubs) is never drawn, so the disc
                # keeps its raw pixels instead of the texture pipeline's R4NREF reference: its row keeps the exact
                # header / sampler facts and carries key 0-0, which a NATIVE_MODEL_REGISTRY_DROP_BUMP image proves by
                # those facts alone (coarse_actor_material.inc texture()).
                used, bumps = set(), set()
                for material, *_ in f['parts']:
                    mat = bytes.fromhex(material)
                    used.add(mat[1])
                    if mat[0] & 4:
                        used.add(mat[3])
                    if mat[0] & 1:
                        bumps.add(mat[2])
                for k in sorted(bumps - used):
                    if t['textures'][k]['palette']:
                        raise Fail(f'{name}: bump-only texture {k} is paletted')
                    t['textures'][k]['key'] = [0, 0]
            need |= n
            sections.append(dict(role=i, kind=b['role'], bin=b['bin'], tpl=b['tpl'], bin_sha256=f['sha256'],
                                 normalized_sha256=f['normalized_sha256'], tpl_sha256=t['sha256'], needs=need_names(n), need_bits=n))
        identity = (arcname, tuple(s['bin'] for s in sections), tuple(s['tpl'] for s in sections))
        if d.get('lod_of'):
            # a gameplay level shares its full descriptor's source identity by design (see lod_of below)
            if seen_identity.get(identity) != d['lod_of']:
                raise Fail(f'{name}: lod_of {d["lod_of"]} must be an earlier descriptor with the same source identity')
        elif identity in seen_identity:
            raise Fail(f'{name}: source identity {identity} is ambiguous with {seen_identity[identity]}')
        if not d.get('lod_level'):   # NMR_POOL_LOD: numbered levels all name the full descriptor
            seen_identity[identity] = name
        # ---- chunks
        chunks, hbones = parse_header(hdr)
        if hbones != draw:
            raise Fail(f'{name}: header bone_count {hbones} != skeleton {bones}' + (f' draw slots {draw}' if draw_slots else ''))
        expected_roles = [0,1,3,4,5] if luis else list(range(len(sections)))
        if [c['source_info'] for c in chunks] != expected_roles:
            raise Fail(f'{name}: header chunks {[c["source_info"] for c in chunks]} are not one per source section in order')
        pool = bool(d.get('pool'))
        if pool and not POOL:
            raise Fail(f'{name}: a pool descriptor needs --pool (a NATIVE_MODEL_REGISTRY_POOL package)')
        if pool and (len(chunks) < 2 or draw_slots is not None or luis):
            raise Fail(f'{name}: a pool needs 2+ sections and no draw slots')
        if len(chunks) > (POOL_SECTIONS if pool else ACTOR_CHUNKS):
            raise Fail(f'{name}: {len(chunks)} chunks > {POOL_SECTIONS if pool else ACTOR_CHUNKS}')
        skin = 0
        for c in chunks:
            err = preflight_chunk(c, draw)
            if err:
                raise Fail(f'{name} chunk {c["source_info"]}: preflight {err}')
            if source_normal_length:
                c['normals'], sections[c['source_info']]['normal_length'] = source_length_normals(
                    name, c, bins[(arcname, sections[c['source_info']]['bin'])]['normal_length'])
            c['skin_bytes'] = skin_stream_bytes(c['weights']); skin += c['skin_bytes']
            tp = e['texture_packages'].get(str(c['source_info']))
            if not tp:
                raise Fail(f'{name} chunk {c["source_info"]}: no texture package bound to this source_info')
            # 'VQ RGB565' (ps2_cast.py packs): the runtime binds a package by its key like any other (the Ganado cast
            # atlases are VQ); only paletted / unknown formats are refused.
            if tp['format'] not in ('RGB565', 'ARGB4444', 'ARGB1555', 'VQ RGB565'):
                raise Fail(f'{name}: texture format {tp["format"]} unsupported (paletted or unknown)')
            pkg = inputs.take(tp['package'], 'cast/' + tp['package'].split('/cast-20260925/', 1)[-1])
            if sha(open(pkg, 'rb').read()) != tp['package_sha256']:
                raise Fail(f'{name}: texture package {tp["key"]} sha256 differs from the manifest')
            crc, fnv = (int(x, 16) for x in tp['key'].split('-'))
            w, h_ = tp['rectangle'][2], tp['rectangle'][3]
            tk = (crc, fnv, w, h_)
            if tk not in [x[:4] for x in textures]:
                textures.append(tk + (pkg, tp['package_sha256'], tp['format']))
            c['texture'] = [x[:4] for x in textures].index(tk)
        # "mask_runs": {"<source_info>": "<tools/ps2_mask_runs.py output dir>"} (lane ps2cast-3, NATIVE_MODEL_REGISTRY_MASK
        # packages only): the section draws its opaque triangles with the chunk texture and its hair cards with a
        # colour + I4 mask pair (the pair package is staged; the colour / mask keys are texture records that key the
        # runtime's pair tokens). The runs' streams index the chunk's own positions / normals / palettes.
        mask_sections = set()
        for si, mdir in (d.get('mask_runs') or {}).items():
            si = int(si)
            c = [x for x in chunks if x['source_info'] == si]
            if not c:
                raise Fail(f'{name}: mask_runs names section {si}, the header has none')
            c = c[0]
            mj = inputs.json(os.path.join(mdir, 'mask-runs.json'), f'mask/{name}/{si}/mask-runs.json')
            same_as_full = False
            if d.get('lod_level') and mj['header_sha256'] != L['header_sha256']:
                # NMR_POOL_LOD: a numbered level keeps a masked section whole (glod_rung keep_roles); the full
                # descriptor's mask runs index that section's arrays, so they apply when its chunk is byte-identical.
                fe = [x for x in runtime if x['name'] == d.get('lod_of')]
                fc = [x for x in fe[0]['chunks'] if x['source_info'] == si] if fe else []
                same_as_full = bool(fc) and fe[0]['header_sha256'] == mj['header_sha256'] and all(
                    fc[0][k] == c[k] for k in ('positions', 'normals', 'uv', 'stream', 'weights'))
            if (mj['header_sha256'] != L['header_sha256'] and not same_as_full) or mj['section'] != si or \
                    mj['triangles']['chunk'] != c['triangles']:
                raise Fail(f'{name} section {si}: mask runs were made from another header / section')
            mask_only = bool(mj.get('mask_only'))
            # mask-only: the complete pinned Luis hair, or (--pool) a pool section whose every triangle is a hair card
            pool_only = pool and mj['runs']['opaque']['triangles'] == 0 and mj['runs']['hair']['triangles'] == c['triangles']
            if mask_only and not ((luis and si == 3 and mj['runs']['opaque']['triangles'] == 0 and
                                   mj['runs']['hair']['triangles'] == c['triangles'] == 1273) or pool_only):
                raise Fail('mask-only is restricted to the complete pinned Luis hair and whole pool sections')
            rb = {}
            for k in ('opaque.blob', 'hair.blob', 'hair.uv'):
                rb[k] = open(inputs.take(os.path.join(mdir, k), f'mask/{name}/{si}/{k}'), 'rb').read()
            if sha(rb['opaque.blob']) != mj['runs']['opaque']['sha256'] or sha(rb['hair.blob']) != mj['runs']['hair']['sha256']:
                raise Fail(f'{name} section {si}: run blobs differ from mask-runs.json')
            if mask_only and rb['opaque.blob']:
                raise Fail('mask-only opaque payload must be absent')
            if mask_only and luis:
                # A complete source hair run retains triangle order and every
                # original corner; undo only its colour-atlas cell transform.
                aw, ah = luis['atlas']['size']; x, y, cw, ch = luis['atlas']['cells']['(5, 3)']
                expected_uv = bytearray()
                for u, v in struct.iter_unpack('<2H', c['uv']):
                    un, vn = u*aw-x*32768, v*ah-y*32768
                    if un%cw or vn%ch or not (0 <= un//cw <= 32768 and 0 <= vn//ch <= 32768):
                        raise Fail('Luis source hair UV cannot be reversed exactly')
                    expected_uv += struct.pack('<2H', un//cw, vn//ch)
                if rb['hair.blob'] != bytes(c['stream']) or rb['hair.uv'] != bytes(expected_uv) or \
                   (mj['texture']['width'], mj['texture']['height']) != (cw, ch):
                    raise Fail('Luis hair stream/UV/texture size differs from the complete source mapping')
            for k in ('opaque.blob', 'hair.blob'):
                if mask_only and k == 'opaque.blob':
                    continue
                cc_ = dict(c, stream=rb[k], stream_bytes=len(rb[k]), triangles=mj['runs'][k.split('.')[0]]['triangles'])
                if k == 'hair.blob':
                    cc_['uv'] = rb['hair.uv']
                err = preflight_chunk(cc_, draw)
                if err:
                    raise Fail(f'{name} section {si} {k}: preflight {err}')
            tw, th = mj['texture']['width'], mj['texture']['height']
            ppath = inputs.take(os.path.join(mdir, mj['pair_package']['file']), f'mask/{name}/{si}/{mj["pair_package"]["file"]}')
            if sha(open(ppath, 'rb').read()) != mj['pair_package']['sha256']:
                raise Fail(f'{name} section {si}: pair package sha256 differs')
            idx = []
            for kk in ('colour', 'mask'):
                crc, fnv = (int(x, 16) for x in mj['keys'][kk].split('-'))
                tk = (crc, fnv, tw, th)
                if tk not in [x[:4] for x in textures]:
                    textures.append(tk + (None, None, 'key only (pair token, ' + kk + ')'))
                idx.append([x[:4] for x in textures].index(tk))
            c['mask'] = dict(mask_only=mask_only, opaque=rb['opaque.blob'], hair=rb['hair.blob'], hair_uv=rb['hair.uv'],
                             opaque_triangles=mj['runs']['opaque']['triangles'], hair_triangles=mj['runs']['hair']['triangles'],
                             colour_texture=idx[0], mask_texture=idx[1], pair=mj['keys']['pair'], pair_package=ppath)
            mask_sections.add(si)
        if luis:
            # Face source info keeps its own immutable source identity; its draw
            # is covered by the complete merged head, with no duplicate run.
            head = next(c for c in chunks if c['source_info'] == 1)
            chunks.insert(2, dict(head, source_info=2, draw_owner=1))
            skin += head['skin_bytes']
            if not any(c['source_info'] == 3 and c.get('mask',{}).get('mask_only') for c in chunks):
                raise Fail('Luis requires the complete mask-only source hair run')
        materials = sorted({c['texture'] for c in chunks} | {c['mask']['colour_texture'] for c in chunks if 'mask' in c})
        need_materials = len(materials)
        if pool:
            # A pool actor draws one section per source info, and one info is one BIN: sections that share a BIN under
            # different TPLs (em10SetAccesory's alternative colours, e.g. 0x217 with TPL 0x218 or 0x219) never meet in
            # one actor. The runtime plan counts materials per actor (coarse_actor_owner_registry.inc kRwPlan), so the
            # bound is the chunk textures plus, per BIN, its masked sections' colour textures at most one of which an
            # actor carries. Unchanged for a pool whose BINs are all distinct.
            per_bin = {}
            for c in chunks:
                if 'mask' in c:
                    per_bin.setdefault(sections[c['source_info']]['bin'], set()).add(c['mask']['colour_texture'])
            base = {c['texture'] for c in chunks}
            need_materials = min(need_materials, len(base) + sum(1 for v in per_bin.values() if v - base))
        if need_materials > ACTOR_MATERIALS:
            raise Fail(f'{name}: {need_materials} materials > {ACTOR_MATERIALS}')
        entry = dict(name=name, revision=rev, base_revision=base_rev, level=level, archive=arcname,
                     archive_sha256=audit[arcname]['sha256'], model_id=int(d['model_id'], 16), source_types=d['source_types'],
                     bones=draw, parents=parents, bind=bind, sections=sections, chunks=chunks, skin_bytes=skin,
                     header=L['runtime_header'], header_sha256=L['header_sha256'], rooms=e.get('rooms', []),
                     needs=need_names(need), category=e.get('category'), status=e.get('status'), spec=d,
                     position_shift=int(e.get('position_shift', 4)))
        if luis:
            entry['source_coverage_manifest_sha256'] = luis['reviewed_manifest_sha256']
        if pool:
            entry['pool'] = True
        if d.get('lod_of'):
            # NATIVE_MODEL_REGISTRY_LOD (lane cast16 2026-10-16): a gameplay level of the descriptor named by lod_of (same
            # archive, BINs, TPLs and skeleton; reduced mesh). Package word 44 bit 25 + bits 16..23 = that descriptor's
            # package index + 1; the runtime draws it outside in-engine events only.
            entry['lod_of'] = d['lod_of']
            if d.get('lod_level'):
                # NMR_POOL_LOD (lane lod26b 2026-10-26): a numbered pool level (word 44 bits 26..29; GANADO_LOD order)
                lv = int(d['lod_level'])
                if not 1 <= lv <= 15 or not pool:
                    raise Fail(f'{name}: lod_level {lv} needs 1..15 and a pool descriptor')
                entry['lod_level'] = lv
        elif d.get('lod_level'):
            raise Fail(f'{name}: lod_level needs lod_of')
        if draw_slots is not None:
            entry.update(source_bones=bones, slots=list(draw_slots))
        if not 1 <= entry['position_shift'] <= 4:
            raise Fail(f'{name}: position_shift {entry["position_shift"]} outside 1..4')
        # "source_drops": ["bump"] (lane ps2cast-2): the source path itself never draws the bump stage (trans.cpp
        # bumpSetup only feeds the GX stubs; model_bridge binds the colour texture alone), so the owner path drawing
        # no bump is the same image; the image needs NATIVE_MODEL_REGISTRY_DROP_BUMP (the certificate's twin rule).
        # "alt-specular" (Phase 2 A3, PS2_CROW): material flag 0x80 (specularSetup2) is GX only on the DC source path too,
        # so the owner path drawing none is the same image (the image needs RE4DC_NMR_CROW, the certificate's twin rule).
        # "mask" (Phase 2 A3, user decision 2026-10-11: the solid PS2 crow wing): the section's I4 mask pass is replaced by
        # the opaque PS2 section (a visible approximation the user accepted; RE4DC_NMR_CROW), never with mask_runs.
        drops = 0
        for x in d.get('source_drops', []):
            if x == 'bump':
                drops |= BUMP
            elif x == 'alt-specular':
                drops |= ALT_SPECULAR
            elif x == 'mask':
                if d.get('mask_runs'):
                    raise Fail(f'{name}: source_drops "mask" and mask_runs exclude each other')
                drops |= MASK | SOURCE_PASS
            else:
                raise Fail(f'{name}: source_drops takes only "bump", "alt-specular", "mask"')
        if mask_sections:
            # every section whose source materials need the mask pass draws its pair run (NATIVE_MODEL_REGISTRY_MASK)
            for s in sections:
                if s['need_bits'] & MASK and s['role'] not in mask_sections:
                    raise Fail(f'{name}: section {s["role"]} needs the mask pass and has no mask_runs')
            drops |= MASK | SOURCE_PASS
            entry['mask_runs'] = sorted(mask_sections)
        entry['source_drops'] = need_names(need & drops)
        missing = need & ~(FLAT_IMPLEMENTED | drops)
        if missing:
            entry['contract'] = (f'source materials need {", ".join(need_names(missing))}; the flat owner path implements '
                                 f'{", ".join(need_names(FLAT_IMPLEMENTED))} only: needs a renderer material contract '
                                 '(and a user look decision for any approximation)')
            contracts.append(entry)
        else:
            runtime.append(entry)
    # ---- capacities
    blobs = sorted({(s_arc, s_bin) for r in runtime for (s_arc, s_bin) in [(r['archive'], s['bin']) for s in r['sections']]})
    nrows = sum(len(r['sections']) for r in runtime)
    if nblobs0 + len(blobs) > SOURCE_BLOBS:
        raise Fail(f'source blobs {nblobs0}+{len(blobs)} > {SOURCE_BLOBS} (actor_lifetime.inc templates mask)')
    if nroles0 + nrows > MATERIAL_ROWS:
        raise Fail(f'role rows {nroles0}+{nrows} > {MATERIAL_ROWS} (actor_lifetime.inc Info::roles mask)')
    if not runtime:
        raise Fail('no descriptor is admissible for the flat owner path: ' +
                   '; '.join(f'{c["name"]}: {c["contract"]} (sections: ' +
                             ', '.join(f'{x["kind"]} BIN {x["bin"]} {"/".join(x["needs"])}' for x in c['sections']) + ')'
                             for c in contracts))
    for i, r in enumerate(runtime):
        r['appearance'] = APPEARANCE0 + i
    used_tex = sorted({c['texture'] for r in runtime for c in r['chunks']} |
                      {c['mask'][k] for r in runtime for c in r['chunks'] if 'mask' in c for k in ('colour_texture', 'mask_texture')})
    write_outputs(out, spec, runtime, contracts, textures, used_tex, bins, tpls, blobs, nroles0, nblobs0)
    package = None
    if package_room is not None:
        # spec "room_packages" (optional): {"<hex room>": {"descriptors": [names], "evidence": "..."}} names the runtime
        # descriptors the room's own source spawns (its enemy list / script, by model type); each must be a runtime
        # descriptor whose cast lists the room. Appearances are renumbered from APPEARANCE0 in runtime order (they are
        # scoped to one room generation). Without an entry for the room every runtime descriptor is packaged (as before).
        sel = spec.get('room_packages', {}).get('%x' % package_room)
        if sel is None:
            pr, pk_tex, pk_blobs = runtime, used_tex, blobs
        else:
            names = sel['descriptors']; known = {r['name'] for r in runtime}; rname = 'r%x%02x' % (package_room >> 8, package_room & 255)
            for n in names:
                if n not in known:
                    cs = [c for c in contracts if c['name'] == n]
                    why = 'unknown'
                    if cs:
                        secs = ', '.join('%s BIN %s %s' % (x['kind'], x['bin'], '/'.join(x['needs'])) for x in cs[0]['sections'])
                        why = '%s (sections: %s)' % (cs[0]['contract'], secs)
                    raise Fail(f'room package {rname}: {n} is not a runtime descriptor: {why}')
            pr = [dict(r, appearance=APPEARANCE0 + i) for i, r in enumerate(x for x in runtime if x['name'] in names)]
            for r in pr:
                if rname not in r['rooms']:
                    raise Fail(f'room package {rname}: the cast of {r["name"]} does not list {rname} ({r["rooms"]})')
            if len(pr) != len(set(names)):
                raise Fail(f'room package {rname}: duplicate names in {names}')
            pk_tex = sorted({c['texture'] for r in pr for c in r['chunks']} |
                            {c['mask'][k] for r in pr for c in r['chunks'] if 'mask' in c for k in ('colour_texture', 'mask_texture')})
            pk_blobs = sorted({(r['archive'], s['bin']) for r in pr for s in r['sections']})
        package = write_package(out, package_room, spec, pr, textures, pk_tex, bins, tpls, pk_blobs, immutable_arrays)
        package['descriptors'] = [dict(name=r['name'], appearance='0x%x' % r['appearance'], archive=r['archive'],
                                       source_types=r['source_types'], sections=[dict(bin=s['bin'], tpl=s['tpl']) for s in r['sections']])
                                  for r in pr]
        if sel is not None:
            package['selection_evidence'] = sel.get('evidence')
    manifest = dict(registry=spec['registry'], generator=os.path.relpath(__file__, tree), generator_sha256=sha(open(__file__, 'rb').read()),
                    tree_head=os.popen(f'git -C "{tree}" rev-parse HEAD').read().strip(), cast_dir=cast,
                    revision_overlay=overlay_rel, level=level, lighting=spec.get('lighting'), self_check=selfcheck,
                    capacities=dict(role_rows=f'{nroles0}+{nrows}/{MATERIAL_ROWS}', source_blobs=f'{nblobs0}+{len(blobs)}/{SOURCE_BLOBS}'),
                    inputs={rel: dict(sha256=v[1], source=v[2]) for rel, v in sorted(inputs.files.items())},
                    **({'normals': 'source BIN normal length (--source-normal-length; per section in descriptors[].sections)'}
                       if source_normal_length else {}),
                    descriptors=[summary(r, 'runtime') for r in runtime] + [summary(c, 'contract') for c in contracts],
                    textures=[dict(key=f'{t[0]:08x}-{t[1]:08x}', width=t[2], height=t[3], format=t[6], package_sha256=t[5],
                                   runtime=i in used_tex) for i, t in enumerate(textures)])
    if package:
        manifest['room_package'] = package
    json.dump(manifest, open(os.path.join(out, 'registry-manifest.json'), 'w'), indent=1)
    sums = []
    for root, _, files in os.walk(out):
        for f in sorted(files):
            p = os.path.join(root, f)
            sums.append(f'{sha(open(p, "rb").read())}  {os.path.relpath(p, out)}')
    open(os.path.join(out, 'SHA256SUMS'), 'w').write('\n'.join(sorted(sums, key=lambda s: s[66:])) + '\n')
    return dict(runtime=[(r['name'], hex(r['appearance']), r['bones'], [c['triangles'] for c in r['chunks']]) for r in runtime],
                contracts=[(c['name'], c['contract']) for c in contracts], textures=len(used_tex), self_check=selfcheck,
                package={k: package[k] for k in ('disc_path', 'bytes', 'arena', 'geometry')} if package else None)


def summary(r, status):
    s = dict(name=r['name'], status=status, revision=r['revision'], base_revision=r['base_revision'], level=r['level'],
             archive=r['archive'], archive_sha256=r['archive_sha256'], model_id=hex(r['model_id']), source_types=r['source_types'],
             bones=r['bones'], sections=r['sections'], header=r['header'], header_sha256=r['header_sha256'], rooms=r['rooms'],
             source_needs=r['needs'], cast_status=r['status'],
             chunks=[dict(source_info=c['source_info'], triangles=c['triangles'], palettes=c['palette_count'],
                          positions=c['position_count'], normals=c['normal_count'], stream_bytes=c['stream_bytes'],
                          skin_bytes=c['skin_bytes'], texture=c['texture']) for c in r['chunks']])
    if status == 'runtime':
        s['appearance'] = hex(r['appearance'])
    else:
        s['contract'] = r['contract']
    return s


def cbytes(b):
    rows = [','.join(str(x) for x in b[i:i + 24]) for i in range(0, len(b), 24)]
    return ',\n'.join(rows)


def cfloat(v):
    return float(v).hex() + 'f' if v else '0.0f'


def write_outputs(out, spec, runtime, contracts, textures, used_tex, bins, tpls, blobs, nroles0, nblobs0):
    L = ['// Private generated asset (tools/d367/model_registry.py, registry %s). Do not commit.' % spec['registry'],
         '#pragma once', 'namespace nmr {',
         'struct Weight { unsigned char bone[3], count; float value[3]; };',
         'struct Chunk { unsigned source_info, position_count, normal_count, palette_count, triangles, stream_bytes; '
         'const unsigned char *positions, *normals, *uv; unsigned char *stream; const Weight *weights; unsigned uv_bytes, texture, skin_bytes; };',
         'struct Texture { unsigned crc, fnv, width, height; };',
         'struct Descriptor { const char* name; unsigned appearance, model_id, bones, sections, first_chunk, skin_bytes; '
         'const signed char* parents; const float (*bind)[12]; };']
    if any(r.get('slots') for r in runtime):
        L[:0] = ['#if !RE4DC_NATIVE_MODEL_REGISTRY_PACK', '#error draw-slot descriptors (--slots) require the room package loader', '#endif']
    if any(r.get('source_coverage_manifest_sha256') for r in runtime):
        L[:0] = ['#if !RE4DC_NATIVE_MODEL_REGISTRY_PACK', '#error Luis source coverage requires the room package loader', '#endif']
    tex_index = {t: i for i, t in enumerate(used_tex)}
    chunk_rows, desc_rows, first = [], [], 0
    for di, r in enumerate(runtime):
        ns = f'd{di}'
        L.append(f'namespace {ns} {{  // {r["name"]} {r["revision"]} {r["level"]}')
        for c in r['chunks']:
            p = f'i{c["source_info"]}'
            L.append(f'alignas(32) static const unsigned char {p}_pos[] = {{\n{cbytes(c["positions"])}\n}};')
            L.append(f'alignas(32) static const unsigned char {p}_nrm[] = {{\n{cbytes(c["normals"])}\n}};')
            L.append(f'alignas(32) static const unsigned char {p}_uv[] = {{\n{cbytes(c["uv"])}\n}};')
            L.append(f'alignas(32) static unsigned char {p}_gx[] = {{\n{cbytes(c["stream"])}\n}};')
            L.append(f'static const Weight {p}_weights[] = {{')
            for bs, n, v in c['weights']:
                L.append('{{%d,%d,%d},%d,{%s}},' % (bs[0], bs[1], bs[2], n, ','.join(cfloat(x) for x in v)))
            L.append('};')
            chunk_rows.append('{%d,%d,%d,%d,%d,%d,%s::%s_pos,%s::%s_nrm,%s::%s_uv,%s::%s_gx,%s::%s_weights,%d,%d,%d},' % (
                c['source_info'], c['position_count'], c['normal_count'], c['palette_count'], c['triangles'], c['stream_bytes'],
                ns, p, ns, p, ns, p, ns, p, ns, p, len(c['uv']), tex_index[c['texture']], c['skin_bytes']))
        L.append('static const signed char parents[] = {%s};' % ','.join(str(x) for x in ([-1] if r.get('slots') else r['parents'])))
        L.append('static const float bind[][12] = {')
        for row in r['bind']:
            L.append('{%s},' % ','.join(cfloat(x) for x in row))
        L.append('};')
        L.append('}')
        desc_rows.append('{"%s",%du,%du,%du,%du,%du,%du,%s::parents,%s::bind},' % (
            r['name'], r['appearance'], r['model_id'], r['bones'], len(r['sections']), first, r['skin_bytes'], ns, ns))
        first += len(r['chunks'])
    L.append('static Chunk chunks[] = {'); L += chunk_rows; L.append('};')
    L.append('static const Texture textures[] = {')
    for t in used_tex:
        crc, fnv, w, h = textures[t][:4]
        L.append('{0x%08xu,0x%08xu,%du,%du},' % (crc, fnv, w, h))
    L.append('};')
    L.append('static const Descriptor descriptors[] = {'); L += desc_rows; L.append('};')
    L.append(f'constexpr unsigned descriptor_count={len(runtime)}, chunk_count={first}, texture_count={len(used_tex)}, '
             f'skin_stream_bytes={sum(r["skin_bytes"] for r in runtime)}, max_bones={max(r["bones"] for r in runtime)}, '
             f'appearance_first=0x{APPEARANCE0:x}u;')
    L.append(f'constexpr unsigned base_role_rows={nroles0}, base_source_blobs={nblobs0};')
    L.append('}')
    open(os.path.join(out, 'native_model_registry.h'), 'w').write('\n'.join(L) + '\n')
    # ---- source identity rows (coarse_actor_material.inc types; names prefixed g_)
    F = ['// Private generated source identity rows (tools/d367/model_registry.py, registry %s). Do not commit.' % spec['registry']]
    done_t, done_m = set(), set()
    for r in runtime:
        for s in r['sections']:
            tk = (r['archive'], s['tpl'])
            if tk not in done_t:
                done_t.add(tk)
                F.append('static const Texture t_g_%s_%d[] = {' % tk)
                for x in tpls[tk]['textures']:
                    pal = x['palette'] or [0xffffffff, 0, 0, 0]
                    F.append('{' + ','.join(str(v) + 'u' for v in x['key'] + x['whf']) + ',{' + ','.join(str(v) + 'u' for v in x['sampler']) +
                             '},' + str(pal[0]) + 'u,{' + ','.join(str(v) + 'u' for v in pal[1:]) + '}},')
                F.append('};')
            mk = (r['archive'], s['bin'])
            if mk not in done_m:
                done_m.add(mk); m = bins[mk]
                F.append('static const Part p_g_%s_%d[] = {' % mk)
                for material, size, poly, crc, fnv in m['parts']:
                    F.append('{{' + ','.join(str(v) + 'u' for v in bytes.fromhex(material)) + '},' + ','.join(str(v) + 'u' for v in (size, poly, crc, fnv)) + '},')
                F.append('};')
                F.append('static const Model m_g_%s_%d = {' % mk + ','.join(
                    '{' + ','.join(str(v) + 'u' for v in m[k]) + '}' for k in ('header', 'positions', 'normals', 'weights', 'uv')) +
                    ',p_g_%s_%d};' % mk)
    open(os.path.join(out, 'native_model_registry_facts.inc'), 'w').write('\n'.join(F) + '\n')
    R = ['// Private generated role rows: appearance, role (source info order), source BIN, source TPL.']
    for r in runtime:
        for s in r['sections']:
            R.append('{%du,%du,%du,%du,&m_g_%s_%d,t_g_%s_%d,%du},' % (r['appearance'], s['role'], s['bin'], s['tpl'], r['archive'], s['bin'],
                                                                 r['archive'], s['tpl'], len(tpls[(r['archive'], s['tpl'])]['textures'])))
    open(os.path.join(out, 'native_model_registry_roles.inc'), 'w').write('\n'.join(R) + '\n')
    B = ['// Private generated source blobs (family 2: enemy archives): normalized BIN digests.']
    for a, b in blobs:
        B.append('{&m_g_%s_%d,2u,%du,{%s}},' % (a, b, b, ','.join(str(v) + 'u' for v in bins[(a, b)]['normalized'])))
    open(os.path.join(out, 'native_model_registry_blobs.inc'), 'w').write('\n'.join(B) + '\n')
    os.makedirs(os.path.join(out, 'tex'))
    for t in used_tex:
        crc, fnv, w, h, pkg = textures[t][:5]
        if pkg is None:
            continue  # a pair token's key only (mask_runs): the pair package below is what the disc stages
        shutil.copy2(pkg, os.path.join(out, 'tex', f'{crc:08x}-{fnv:08x}.re4tex'))
    for r in runtime:
        for c in r['chunks']:
            if 'mask' in c:
                shutil.copy2(c['mask']['pair_package'], os.path.join(out, 'tex', c['mask']['pair'] + '.re4tex'))


# ---------------------------------------------------------------- room package (NATIVE_MODEL_REGISTRY_PACK=1)
# package/r<room>/registry.re4nmr: the same runtime descriptors, chunks, textures and source identity rows as the
# compiled outputs above, as one versioned little-endian file with no pointers (coarse_actor_registry_pack.inc
# validates every field below before it publishes anything). Identical chunk geometry (positions, normals, UV, stream,
# weights, counts and bone count, compared as exact bytes) is stored once and referenced by every descriptor section
# that uses it; textures and source identity rows stay per descriptor.
PACK_MAGIC = b'RE4NMR1\0'
PACK_VERSION = 1
PACK_HEADER = 64
PACK_SECTIONS = ('desc', 'ref', 'geom', 'blob', 'tex', 'parents', 'bind', 'fmodel', 'fpart', 'ftex', 'role', 'sblob')
PACK_RECORD = dict(desc=48, ref=16, geom=64, blob=1, tex=16, parents=1, bind=48, fmodel=96, fpart=32, ftex=68, role=32, sblob=32)
PACK_MAX_BYTES = 192 * 1024  # coarse_actor_registry_pack_check.inc kPackMaxBytes (package + skin arena)
# coarse_actor_owner_registry.inc kReg* and coarse_actor_registry_pack_check.inc kPack* capacities; role rows and
# source blobs are bounded by the lifetime masks (MATERIAL_ROWS / SOURCE_BLOBS minus the reviewed rows, checked above).
PACK_BONES = 48
PACK_CAPACITY = dict(desc=16, ref=32, geom=32, tex=16, fmodel=8, fpart=32, ftex=16)


def align32(n):
    return (n + 31) & ~31


def pack_crc_fnv(b):
    d = digest(b)
    return d[1], d[2]


def weights_bytes(rows):
    return b''.join(struct.pack('<3BB3f', bs[0], bs[1], bs[2], n, *v) for bs, n, v in rows)


def lod_word(r, runtime):
    if not r.get('lod_of'):
        return 0
    names = [x['name'] for x in runtime]
    if r['lod_of'] not in names:
        raise Fail(f'{r["name"]}: lod_of {r["lod_of"]} is not in the room package')
    full = names.index(r['lod_of'])
    if full >= names.index(r['name']) or full > 254:
        raise Fail(f'{r["name"]}: lod_of {r["lod_of"]} must come earlier in the room package')
    f = runtime[full]
    if r.get('lod_level'):
        # NMR_POOL_LOD: a numbered pool level of a pool full descriptor, the same sections in the same order
        same = [(s['bin'], s['tpl']) for s in f['sections']] == [(s['bin'], s['tpl']) for s in r['sections']]
        if (f['model_id'], f['bones']) != (r['model_id'], r['bones']) or not same or not f.get('pool') or not r.get('pool') \
                or f.get('lod_of'):
            raise Fail(f'{r["name"]}: a numbered pool level needs its pool full descriptor\'s model id, bones and sections')
        return (r['lod_level'] << 26) | (1 << 25) | ((full + 1) << 16)
    if (f['model_id'], f['bones'], len(f['sections'])) != (r['model_id'], r['bones'], len(r['sections'])) or f.get('pool') or r.get('pool'):
        raise Fail(f'{r["name"]}: a gameplay level needs its full descriptor\'s model id, bones and sections (no pool)')
    return (1 << 25) | ((full + 1) << 16)


def write_package(out, room, spec, runtime, textures, used_tex, bins, tpls, blobs, immutable_arrays=False):
    if immutable_arrays and room != 0x11f:
        raise Fail("immutable-array alias package is qualified only for room 11f")
    tex_index = {t: i for i, t in enumerate(used_tex)}
    geoms, gkey, refs, desc, parents, bind = [], {}, [], [], bytearray(), []
    blob = bytearray()

    arrays = {}

    def put_array(b, kind, count, stride, palette, bones):
        # Exact bytes plus semantic context, never a hash-only alias. Streams always own storage.
        key = (kind, count, stride, palette, bones, bytes(b))
        if not immutable_arrays or kind == 3:
            return put(b)
        if key not in arrays:
            arrays[key] = put(b)
        return arrays[key]

    def put_arrays(c, uv, stream, w, bones):
        return [put_array(b, kind, count, stride, c["palette_count"], bones) for kind, b, count, stride in (
            (0, c["positions"], c["position_count"], 8), (1, c["normals"], c["normal_count"], 8),
            (2, uv, len(uv) // 4, 4), (3, stream, len(stream), 1), (4, w, c["palette_count"], 16))]

    def put(b):
        nonlocal blob
        at = len(blob); blob += b; blob += bytes(align32(len(blob)) - len(blob)); return at
    for r in runtime:
        first_ref, parents_at, bind_first = len(refs), len(parents), len(bind)
        for c in r['chunks']:
            w = weights_bytes(c['weights'])
            key = (r['bones'], c['position_count'], c['normal_count'], c['palette_count'], c['triangles'], c['skin_bytes'],
                   bytes(c['positions']), bytes(c['normals']), bytes(c['uv']), bytes(c['stream']), w)
            if key not in gkey:
                gkey[key] = len(geoms)
                at = put_arrays(c, c['uv'], c['stream'], w, r['bones'])
                crc, fnv = pack_crc_fnv(bytes(c['positions']) + bytes(c['normals']) + bytes(c['uv']) + bytes(c['stream']) + w)
                geoms.append(dict(counts=(c['position_count'], c['normal_count'], c['palette_count'], c['triangles'],
                                          len(c['stream']), len(c['uv']), c['skin_bytes'], r['bones']), at=at, crc=crc, fnv=fnv,
                                  bytes=len(c['positions']) + len(c['normals']) + len(c['uv']) + len(c['stream']) + len(w),
                                  users=[]))
            g = gkey[key]; geoms[g]['users'].append(f'{r["name"]}/{c["source_info"]}'); geoms[g]['primary'] = True
            word12 = 0
            if 'mask' in c:
                # NATIVE_MODEL_REGISTRY_MASK: the two run geometries (the chunk's arrays with each run's stream; the pair run
                # with its own UV words) and ref word 12 = opaque + 1 | pair + 1 << 8 | colour tex << 16 | mask tex << 24
                mk_ = c['mask']; rg = []
                for stream, uvb, tris in ((mk_['opaque'], bytes(c['uv']), mk_['opaque_triangles']),
                                          (mk_['hair'], mk_['hair_uv'], mk_['hair_triangles'])):
                    if mk_.get('mask_only') and tris == 0:
                        rg.append(-1);continue
                    k2 = ('run', r['bones'], c['position_count'], c['normal_count'], c['palette_count'], tris, c['skin_bytes'],
                          bytes(c['positions']), bytes(c['normals']), uvb, stream, w)
                    if k2 not in gkey:
                        gkey[k2] = len(geoms)
                        at = put_arrays(c, uvb, stream, w, r['bones'])
                        crc, fnv = pack_crc_fnv(bytes(c['positions']) + bytes(c['normals']) + uvb + stream + w)
                        geoms.append(dict(counts=(c['position_count'], c['normal_count'], c['palette_count'], tris, len(stream),
                                                  len(uvb), c['skin_bytes'], r['bones']), at=at, crc=crc, fnv=fnv,
                                          bytes=len(c['positions']) + len(c['normals']) + len(uvb) + len(stream) + len(w),
                                          users=[], primary=False))
                    rg.append(gkey[k2]); geoms[gkey[k2]]['users'].append(f'{r["name"]}/{c["source_info"]}/run')
                if max(rg) > 254 or tex_index[mk_['colour_texture']] > 255 or tex_index[mk_['mask_texture']] > 255:
                    raise Fail('mask run indices exceed ref word 12')
                word12 = (rg[0] + 1) | ((rg[1] + 1) << 8) | (tex_index[mk_['colour_texture']] << 16) | (tex_index[mk_['mask_texture']] << 24)
            ownership = (0x80000000 | c['draw_owner']) if 'draw_owner' in c else c['source_info']
            refs.append((g, tex_index[c['texture']], ownership, word12))
        if r.get('slots'):
            # --slots: S source parents (u8, 0xff root) then the slot map; S binds; word 44 bits 8..15 = S
            parents += bytes(0xff if p < 0 else p for p in r['parents']) + bytes(r['slots'])
        else:
            parents += bytes(p & 0xff for p in r['parents'])
        bind += r['bind']
        name = r['name'].encode()
        if len(name) > 15:
            raise Fail(f'{r["name"]}: descriptor name longer than 15 bytes')
        desc.append(name.ljust(16, b'\0') + struct.pack('<8I', r['appearance'], r['model_id'], r['bones'], len(r['sections']),
                                                         first_ref, parents_at, bind_first,
                                                         # word 44: the position shift read by NATIVE_MODEL_REGISTRY_SHIFT=1
                                                         # images (0 = 4, what every image assumes)
                                                         (0 if r['position_shift'] == 4 else r['position_shift']) |
                                                         (r['source_bones'] << 8 if r.get('slots') else 0) |
                                                         # word 44 bit 24: a pool descriptor (--pool)
                                                         (1 << 24 if r.get('pool') else 0) |
                                                         # word 44 bit 25 + bits 16..23: a gameplay level (lod_of) of
                                                         # package descriptor (bits 16..23) - 1 (NATIVE_MODEL_REGISTRY_LOD)
                                                         lod_word(r, runtime)))
    # source identity facts, in first-use order
    fmodel, fpart, ftex, fm_index, ft_index, roles = [], [], [], {}, {}, []
    for r in runtime:
        for s in r['sections']:
            mk, tk = (r['archive'], s['bin']), (r['archive'], s['tpl'])
            role_texture_max = 9 if room == 0x11f and PACK_CAPACITY['fpart'] == 128 else 8
            if POOL:
                role_texture_max = 17  # RE4DC_NMR_ROLE_TEXTURES 17 in NATIVE_MODEL_REGISTRY_POOL images (pack_check)
                if ROLE_TEXTURES5:
                    role_texture_max = 19  # RE4DC_NMR_ROLE_TEXTURES 19 with RE4DC_NMR_ROLES5 (the island U-3 em32 TPL 5)
                if ROLE_TEX23:
                    role_texture_max = 23  # RE4DC_NMR_ROLE_TEX23 (the r320 helicopter em3d TPL 6)
            if SLOTS:
                role_texture_max = 17  # the PS2_ASHLEY image (RE4DC_NMR_ASHLEY): GC pl11 TPL 5 has 17 images
            if len(tpls[tk]['textures']) > role_texture_max:
                raise Fail(f'package {r["name"]}: source TPL has {len(tpls[tk]["textures"])} images > {role_texture_max}')
            if mk not in fm_index:
                m = bins[mk]; fm_index[mk] = len(fmodel)
                fmodel.append(struct.pack('<24I', *m['header'], *m['positions'], *m['normals'], *m['weights'], *m['uv'],
                                          len(fpart), len(m['parts'])))
                if len(m['parts']) != m['header'][8]:
                    raise Fail(f'{mk}: {len(m["parts"])} part rows, header displist_num {m["header"][8]}')
                for material, size, poly, crc, fnv in m['parts']:
                    fpart.append(bytes.fromhex(material).ljust(16, b'\0') + struct.pack('<4I', size, poly, crc, fnv))
            if tk not in ft_index:
                ft_index[tk] = (len(ftex), len(tpls[tk]['textures']))
                for x in tpls[tk]['textures']:
                    pal = x['palette'] or [0xffffffff, 0, 0, 0]
                    ftex.append(struct.pack('<17I', *x['key'], *x['whf'], *x['sampler'], *pal))
            roles.append(struct.pack('<8I', r['appearance'], s['role'], s['bin'], s['tpl'], fm_index[mk], *ft_index[tk], 0))
    # The player archive is adopted with family 1; partner/enemy archives use 2.
    # Only the reviewed playable-Ashley source owner can request player facts.
    player_archives = set()
    for r in runtime:
        if not PLAYER_ASHLEY or r['archive'] != 'pl01':
            continue
        if not (r['model_id'] == 0 and r.get('source_bones') == 141 and
                r.get('slots') and len(r['sections']) == 7 and not r.get('pool')):
            raise Fail('pl01 player facts require the full 141-joint seven-role draw-slot owner')
        player_archives.add(r['archive'])
    sblob = [struct.pack('<8I', fm_index[(a, b)], 1 if a in player_archives else 2,
                         b, *bins[(a, b)]['normalized'], 0, 0) for a, b in blobs]
    tex = [struct.pack('<4I', *textures[t][:4]) for t in used_tex]
    geom = [struct.pack('<16I', *g['counts'], *g['at'], g['crc'], g['fnv'], 0) for g in geoms]
    body = dict(desc=b''.join(desc), ref=b''.join(struct.pack('<4I', *x) for x in refs), geom=b''.join(geom), blob=bytes(blob),
                tex=b''.join(tex), parents=bytes(parents), bind=b''.join(struct.pack('<12f', *row) for row in bind),
                fmodel=b''.join(fmodel), fpart=b''.join(fpart), ftex=b''.join(ftex), role=b''.join(roles), sblob=b''.join(sblob))
    counts = dict(desc=len(desc), ref=len(refs), geom=len(geoms), blob=len(blob), tex=len(tex), parents=len(parents),
                  bind=len(bind), fmodel=len(fmodel), fpart=len(fpart), ftex=len(ftex), role=len(roles), sblob=len(sblob))
    for k, cap in PACK_CAPACITY.items():
        if counts[k] > cap:
            raise Fail(f'package {k}: {counts[k]} records > the loader capacity {cap} (coarse_actor_registry_pack_check.inc)')
    if max(r['bones'] for r in runtime) > PACK_BONES:
        raise Fail(f'package: {max(r["bones"] for r in runtime)} bones > the loader capacity {PACK_BONES}')
    at = align32(PACK_HEADER + 16 * len(PACK_SECTIONS)); table, payload = [], bytearray()
    for i, k in enumerate(PACK_SECTIONS):
        if len(body[k]) != counts[k] * PACK_RECORD[k]:
            raise Fail(f'package section {k}: {len(body[k])} B for {counts[k]} records')
        table.append(struct.pack('<4I', i + 1, at, len(body[k]), counts[k]))
        payload += body[k] + bytes(align32(len(body[k])) - len(body[k])); at += align32(len(body[k]))
    skin = sum(g['counts'][6] for g in geoms if g.get('primary', True))  # mask run geometries build no skin stream
    after = b''.join(table); after += bytes(align32(PACK_HEADER + len(after)) - PACK_HEADER - len(after))
    rest = after + bytes(payload)
    total = PACK_HEADER + len(rest)
    if align32(total) + skin > PACK_MAX_BYTES:
        raise Fail(f'package {total} B + skin {skin} B > {PACK_MAX_BYTES} (runtime arena capacity)')
    pcrc, pfnv = pack_crc_fnv(rest)
    version, flags = (2, 1) if immutable_arrays else (PACK_VERSION, 0)
    head = bytearray(PACK_MAGIC + struct.pack('<14I', version, PACK_HEADER, total, len(PACK_SECTIONS), PACK_HEADER, skin, room,
                                                pcrc, pfnv, 0, APPEARANCE0, max(r['bones'] for r in runtime), flags, 0))
    struct.pack_into('<I', head, 44, zlib.crc32(bytes(head)) & 0xffffffff)
    data = bytes(head) + rest
    d = os.path.join(out, 'package', 'r%x%02x' % (room >> 8, room & 255))
    os.makedirs(d)
    open(os.path.join(d, 'registry.re4nmr'), 'wb').write(data)
    chunk_bytes = sum(len(c['positions']) + len(c['normals']) + len(c['uv']) + len(c['stream']) + len(weights_bytes(c['weights']))
                      for r in runtime for c in r['chunks'])
    return dict(path=os.path.relpath(os.path.join(d, 'registry.re4nmr'), out), disc_path='dc/native/r%x%02x/registry.re4nmr' % (room >> 8, room & 255),
                room='%04x' % room, version=version, bytes=total, sha256=sha(data), skin_arena=skin,
                arena=align32(total) + skin, capacity=PACK_MAX_BYTES, counts=counts,
                sections=[dict(kind=k, offset=struct.unpack_from('<4I', t)[1], bytes=struct.unpack_from('<4I', t)[2]) for k, t in zip(PACK_SECTIONS, table)],
                geometry=dict(chunk_refs=len(refs), unique=len(geoms), chunk_bytes=chunk_bytes,
                              unique_bytes=sum(g['bytes'] for g in geoms), saved_bytes=chunk_bytes - sum(g['bytes'] for g in geoms),
                              shared=[g['users'] for g in geoms if len(g['users']) > 1]))


if __name__ == '__main__':
    main()
