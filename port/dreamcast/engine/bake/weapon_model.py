"""Leon's weapon models into a NAT3 pack's model catalogue (lane eng-look1). PS2 assets only.

    weapon_model.py <tree> <pack in> <pack out> [--arc wep02:6,7]
    weapon_model.py --verify <pack>        lists the weapon entries; exit 1 when the pack has none

<tree>      the little-endian game tree the engine's disc is staged from: <tree>/em/wep02.drs (the PS2 weapon models of
            lane purge-weapons24: "geometry PS2, GC joints/parts kept", pictures as R4NREF keys) and <tree>/dc/tex.pak
            (the pictures; each must be a PS2 package, "ps2-source" or "PS2 weapons <key>", else the script refuses)
--arc       the weapon archive and its model slots (the archive's own numbering, PL_ARC_PTR: wep02 slot 6 the Punisher,
            slot 7 its exclusive-upgrade model, both with the picture set of slot 5; src/wep/objRuger.cpp init)

What the engine needs and why. The weapon is a hosted object (cObjWep, made by the archive's module) with a model the
behaviour loads from the archive (modelInit(bin, tpl)) and hangs on Leon's hand. The engine draws it through the E1 actor
pass like any character, so its geometry must be in the pack's catalogue in the catalogue's own model format
(render/native_actor.inc; the layout bake/native_extra.py writes for props): bones, weight sets, positions and normals in
the position quantum, parts with their material header, strips. Nothing is converted in play.

How the engine finds the entry: each part's role word carries a tag, 0x5745SSAA ('WE', SS the weapon file slot of
read.cpp's wep_data_leon (2 for em/wep02), AA the archive slot of the model). The format is unchanged: the role word is
free for catalogue models past Leon (the actor pass reads role 8, the translucent hair run, and role 2 on model 0 only).
At pack open the engine maps (file slot, archive slot) to the catalogue index; in play it finds the archive slot of a
weapon object's model data by its address in the loaded archive (services/weapon.cpp).

The bind of each bone is what the skeleton service makes of the model data (services/skeleton/skel.cpp
setPartsOffset): identity rotation, translation minus the bone's rest position (each joint's centre added down its
parent chain); the actor pass checks it once against the live table (E1 PAL check).

Appended at the end of the texture, material header and model tables (no index already in the pack moves); the pack is
re-checked with hud_fix.verify. Run once: a pack that already holds weapon entries is refused.
"""
import struct, sys, zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from em_archive import drs_body
from geometry import actor_strips
from pack_scene import Baker, Table, block, pack
from hud_fix import blocks, verify as hud_verify

TAG = 0x57450000
FILE_SLOT = {'wep02': 2}


def arc_slots(body):
    """PL_ARC_PTR's table: word k of the archive body is slot k's offset (src include/global.h PlArc)"""
    n = struct.unpack_from('<I', body, 0)[0]
    offs = list(struct.unpack_from(f'<{n}I', body, 16))
    rel = struct.unpack_from('<I', body, 4)[0]
    ends = sorted(set(offs + [rel]))
    def slot(k):
        off = struct.unpack_from('<I', body, 4 * k)[0]
        if off not in offs: raise ValueError(f'archive slot {k}: offset {off:#x} is not an entry')
        end = min(e for e in ends if e > off)
        tag = body[16 + 4 * n + 4 * offs.index(off):][:3]
        return tag, body[off:end]
    return slot


def tpl_keys(tpl):
    """the picture key of each image of a TPL whose pixels are R4NREF records (offsets from the TPL's start)"""
    magic, count, table = struct.unpack_from('<3I', tpl, 0)
    if magic != 0x0020AF30: raise ValueError('not a little-endian TPL')
    keys = []
    for k in range(count):
        ih = struct.unpack_from('<I', tpl, table + 8 * k)[0]
        data = struct.unpack_from('<I', tpl, ih + 8)[0]
        if tpl[data:data + 6] != b'R4NREF': raise ValueError(f'TPL image {k}: no R4NREF picture identity')
        keys.append(struct.unpack_from('<2I', tpl, data + 8))
    return keys


def model(bin_, keys, header, tag):
    """one weapon model (ModelData, include/model.h; offsets from the model's start) -> catalogue blob, report"""
    u = lambda f, at: struct.unpack_from('<' + f, bin_, at)
    head, = u('I', 0); tex, wgt = u('2I', 0x10)
    wpal, nparts, ndl = u('BBH', 0x18); parts, flags = u('2I', 0x1C)
    shift, = u('B', 0x28); ext, = u('H', 0x2A)
    vtx, nrm, nv, nn = u('2I2H', 0x30)
    if not 0 < nparts <= 64: raise ValueError(f'model parts {nparts}')
    signed = bool(flags & 0x80000000); compact = bool(flags & 0x20000000)
    q = 16 / (2 ** shift)
    # bones: rest positions down the parent chain (skel.cpp setPartsOffset), bind = identity, minus the rest position
    rest = []
    for b in range(nparts):
        _, parent, _, _, cx, cy, cz = u('4B3f', head + 16 * b)
        if parent != 255 and parent >= b: raise ValueError(f'bone {b}: parent {parent} not before it')
        base = rest[parent] if parent != 255 else (0.0, 0.0, 0.0)
        rest.append((base[0] + cx, base[1] + cy, base[2] + cz))
    binds = b''.join(struct.pack('<12f', 1, 0, 0, -x, 0, 1, 0, -y, 0, 0, 1, -z) for x, y, z in rest)
    rigid = min(bin_[head], nparts - 1)
    weights = {}; vectors = [{}, {}]; bindings = []; strips = bytearray(); dropped = 0
    def weight(b):
        ids = [rigid, 0, 0]; num = 1; values = [1.0, 0.0, 0.0]
        if wgt and (wpal > 1 or ext > 1):
            if ext > 255:
                *ids, num = u('4H', wgt + 12 * b); pct = u('3B', wgt + 12 * b + 8)
            else:
                *ids, num = u('4B', wgt + 8 * b); pct = u('3B', wgt + 8 * b + 4)
            if not 1 <= num <= 3 or any(i >= nparts for i in ids[:num]): raise ValueError('invalid skin reference')
            ids = list(ids[:num]) + [0] * (3 - num); values = [v * .01 for v in pct]
        return weights.setdefault(struct.pack('<4B3f', *ids, num, *values), len(weights))
    def vector(kind, index):
        if not kind:
            if index >= nv: raise ValueError('position index past the model')
            x, y, z, b = u('3hH', vtx + 8 * index); scale = q
        elif compact:
            x, y, z, b = u('3bB', nrm + 4 * index); scale = 256
        else:
            x, y, z, b = u('3hH', nrm + 8 * index); scale = 1
        record = tuple(min(32767, max(-32768, round(t * scale))) for t in (x, y, z)) + (weight(b),)
        return vectors[kind].setdefault(record, len(vectors[kind]))
    at = parts
    for d in range(ndl):
        texid = bin_[at + 0xC]; size, = u('I', at + 0x18)
        stream = bin_[at + 32:at + 32 + size]; at += 32 + size
        start = len(strips); hdr = header(keys[texid])
        for strip in actor_strips(stream, 0, signed):
            pos = [u('3h', vtx + 8 * (v & 16383)) for v, _, _ in strip]
            if len(set(pos)) < 3: dropped += 1; continue   # the zero-area filler of an empty PS2 part (wep24b)
            strips += struct.pack('<I', len(strip))
            for v, n, t in strip:
                uu, vv = u('2h' if signed else '2H', tex + 4 * t)
                if signed: uu *= 128; vv *= 128
                strips += struct.pack('<4H', vector(0, v & 16383), vector(1, n & 16383), uu & 65535, vv & 65535)
        if len(strips) > start: bindings.append((tag, hdr, start, len(strips) - start))
    if not bindings: raise ValueError('no drawable part')
    if len(bindings) > 16 or len(vectors[0]) > 4000 or len(vectors[1]) > 4000 or len(weights) > 384:
        raise ValueError('model past the catalogue limits (render/native_scene.inc valid_model, native_actor_open)')
    blob = (struct.pack('<6I', nparts, len(weights), len(vectors[0]), len(vectors[1]), len(bindings), len(strips)) + binds
            + b''.join(weights) + b''.join(struct.pack('<3hH', *v) for pool in vectors for v in pool)
            + b''.join(struct.pack('<4I', *r) for r in bindings) + strips)
    return blob, dict(bones=nparts, weights=len(weights), positions=len(vectors[0]), normals=len(vectors[1]),
                      parts=len(bindings), strip_bytes=len(strips), degenerate_strips_dropped=dropped)


def weapon_entries(data):
    """[(catalogue index, file slot, archive slot)] of the weapon models in a pack"""
    magic, ver, room, n, crc = struct.unpack_from('<4s4I', data)
    if magic != b'NAT3' or zlib.crc32(data[20:]) != crc: raise ValueError('not a NAT3 pack')
    out = []
    for i, m in enumerate(blocks(blocks(data, 20)[13])):
        bones, nw, npos, nnrm, nparts, nstrip = struct.unpack_from('<6I', m)
        at = 24 + 48 * bones + 16 * nw + 8 * (npos + nnrm)
        roles = {struct.unpack_from('<I', m, at + 16 * p)[0] for p in range(nparts)}
        if any(r >> 16 == TAG >> 16 for r in roles):
            if len(roles) != 1: raise ValueError(f'catalogue model {i}: mixed weapon tags {sorted(map(hex, roles))}')
            r = roles.pop(); out.append((i, r >> 8 & 255, r & 255))
    return out


def add(data, tree, archive='wep02', slots=(6, 7), tpl_slot=5, log=print):
    magic, ver, room, n, crc = struct.unpack_from('<4s4I', data)
    if magic != b'NAT3' or zlib.crc32(data[20:]) != crc: raise ValueError('not a NAT3 pack')
    if weapon_entries(data): raise ValueError('the pack holds weapon models already (run once)')
    secs = blocks(data, 20)
    if len(secs) != 15: raise ValueError('pack sections')
    texpak = (tree / 'dc' / 'tex.pak').read_bytes()
    count, idx = struct.unpack_from('<2I', texpak, 12)
    lookup = {(a, b): (c, d) for a, b, c, d in struct.iter_unpack('<4I', texpak[idx:idx + 16 * count])}
    class Into:   # Baker.header's inputs: the pack's own texture and header tables (rows kept, new rows appended)
        pass
    into = Into(); into.lookup = lookup; into.texpack = texpak
    into.textures = Table(); into.headers = Table()
    for r in blocks(secs[0]): into.textures.rows.append(r); into.textures.ids.setdefault(r, len(into.textures.rows) - 1)
    for r in blocks(secs[1]): into.headers.rows.append(r); into.headers.ids.setdefault(r, len(into.headers.rows) - 1)
    n_tex, n_hdr = len(into.textures.rows), len(into.headers.rows)
    def header(key):
        if key not in lookup: raise ValueError(f'picture {key[0]:08x}-{key[1]:08x} not in tex.pak')
        off, size = lookup[key]; pkg = texpak[off:off + size]
        at = struct.unpack_from('<I', pkg, 24)[0]; name = pkg[at:at + 64].split(b'\0')[0]
        # PS2 pictures only: the bake's "ps2-source" packages, or lane purge-weapons24's "PS2 weapons <key>"
        # (tools/d367/ps2cast/ps2_items_tex.py --classes weapons)
        if name != b'ps2-source' and not name.startswith(b'PS2 weapons '): raise ValueError(f'picture {key[0]:08x}-{key[1]:08x}: tex.pak holds {name!r}, not a PS2 picture')
        return Baker.header(into, key, 1, fog=True)   # as the props (native_extra.py): opaque list, fogged
    slot = arc_slots(drs_body(tree / 'em' / f'{archive}.drs'))
    tag_t, tpl = slot(tpl_slot)
    if tag_t != b'TPL': raise ValueError(f'{archive} slot {tpl_slot} is {tag_t!r}, not a TPL')
    keys = tpl_keys(tpl)
    models = blocks(secs[13]); first = len(models)
    for s in slots:
        tag_b, bin_ = slot(s)
        if tag_b != b'BIN': raise ValueError(f'{archive} slot {s} is {tag_b!r}, not a BIN')
        blob, rep = model(bin_, keys, header, TAG | FILE_SLOT[archive] << 8 | s)
        models.append(blob)
        log(f'{archive} slot {s}: catalogue {len(models) - 1}, {rep}')
    log(f'textures {n_tex} -> {len(into.textures.rows)}, headers {n_hdr} -> {len(into.headers.rows)}, '
        f'models {first} -> {len(models)}')
    secs[0], secs[1], secs[13] = block(into.textures.rows), block(into.headers.rows), block(models)
    body = block(secs)
    out = pack('4s4I', b'NAT3', ver, room, len(body), zlib.crc32(body)) + body
    hud_verify(out)
    if len(weapon_entries(out)) != len(slots): raise ValueError('weapon entries not found after the write')
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['--verify'] and len(a) == 2:
        e = weapon_entries(Path(a[1]).read_bytes())
        for i, f, s in e: print(f'{a[1]}: catalogue {i}: weapon file slot {f}, archive slot {s}')
        print(f'{a[1]}: {len(e)} weapon models: {"PASS" if e else "FAIL"}')
        sys.exit(0 if e else 1)
    if len(a) < 3: sys.exit(__doc__)
    arc, slots = 'wep02', (6, 7)
    if '--arc' in a:
        v = a[a.index('--arc') + 1]; arc, s = v.split(':'); slots = tuple(int(x) for x in s.split(','))
    out = add(Path(a[1]).read_bytes(), Path(a[0]), arc, slots)
    Path(a[2]).write_bytes(out); print('wrote', a[2], len(out))
