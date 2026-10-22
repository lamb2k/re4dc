"""Prepare only R4ID/R4TC fingerprint repairs after a proved texture-key remap.

Pure bytes in/out: this module never writes assets, edits recipes or bypasses a
runtime guard. Other R4PW consumers (PCL1/runtime constants/OCCL/etc.) remain a
separate qualification gate; this result never certifies full equivalence.
"""
import hashlib
import struct
import zlib


def require(ok, why):
    if not ok:
        raise ValueError(why)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def world(blob):
    require(len(blob) >= 32, 'world header')
    h = struct.unpack_from('<4s7I', blob)
    require(h[:2] == (b'R4PW', 1) and h[6:] == (0, 0), 'world version/reserved')
    require(len(blob) == 32 + 16*h[3] + 52*h[2], 'world extent')
    require(zlib.crc32(blob[32:]) & 0xffffffff == h[5], 'world CRC')
    parts = list(struct.iter_unpack('<IIHH4B', blob[32:32+16*h[3]]))
    return h, parts, blob[32+16*h[3]:]


def package(blob):
    require(len(blob) >= 144, 'texture header')
    h = struct.unpack_from('<8s10I', blob)
    require(h[:6] == (b'RE4DCTX\0', 2, 48, 96, 1, 48), 'texture descriptor layout')
    t = struct.unpack_from('<64s8I', blob, 48)
    require(h[6] == t[4] == 144 and h[7] == t[5] and len(blob) == 144+t[5], 'texture payload extent')
    require(h[8] in (zlib.crc32(blob[48:]) & 0xffffffff,
                     zlib.crc32(blob[144:]) & 0xffffffff), 'texture CRC')
    require(t[8] == 0, 'texture reserved')
    return h, t


def key(p):
    return '%08x-%08x' % p[:2]


def changes(before, after):
    require(len(before) == len(after), 'repair extent changed')
    return [i for i, (a, b) in enumerate(zip(before, after)) if a != b]


def prepare(old_world, new_world, old_ids, old_classes, old_mesh, new_mesh,
            old_textures, new_textures, selected, expected_mesh_sha256, expected_originals):
    """Return repaired bytes and a proof; reject everything beyond qualified key changes.

    Texture dictionaries contain the actual package bytes for every textured
    part in each world, rather than caller-supplied alpha claims. `selected`
    uses frozen original_key/scoped_key/source_sha256/candidate_sha256 rows.
    """
    require(set(expected_originals) == {'world','ids','classes'}, 'original identity manifest')
    require(all(digest(blob) == expected_originals[name] for name,blob in
                [('world',old_world),('ids',old_ids),('classes',old_classes)]),
            'original sidecar identity changed')
    a, ap, places = world(old_world)
    b, bp, new_places = world(new_world)
    require(a[:5]+a[6:] == b[:5]+b[6:] and places == new_places,
            'world counts/placements changed')
    require(old_mesh == new_mesh and digest(old_mesh) == expected_mesh_sha256,
            'geometry identity changed')
    require(len(old_mesh) >= 80, 'geometry header')
    mh = struct.unpack_from('<4s19I', old_mesh)
    require(mh[0] == b'R4IM' and mh[1] == 3 and mh[2] == len(old_mesh)
            and mh[4:6] == (a[4], a[3])
            and zlib.crc32(old_mesh[80:]) & 0xffffffff == mh[3], 'geometry header/CRC/counts')
    spec = {r['original_key']: r for r in selected}
    require(len(spec) == len(selected), 'duplicate original mapping')
    require(len({r['scoped_key'] for r in selected}) == len(selected), 'duplicate candidate mapping')
    changed = []
    for i, (p, q) in enumerate(zip(ap, bp)):
        require(p[2:] == q[2:], 'part material/dimensions/pass/flags changed')
        if p[:2] == q[:2]:
            if any(p[:2]):
                require(key(p) in old_textures and key(q) in new_textures
                        and old_textures[key(p)] == new_textures[key(q)],
                        'unchanged-part texture bytes changed/missing')
            continue
        r = spec.get(key(p))
        require(r is not None and key(q) == r['scoped_key'] and any(p[:2]), 'unqualified key remap')
        require(key(p) in old_textures and key(q) in new_textures, 'missing selected texture')
        x, y = old_textures[key(p)], new_textures[key(q)]
        require(digest(x) == r['source_sha256'] and digest(y) == r['candidate_sha256'],
                'selected texture identity changed')
        _, xt = package(x)
        yh, yt = package(y)
        require(xt[0] == yt[0] and xt[1:4] == (128, 64, 0) and yt[1:4] == (64, 64, 0)
                and xt[5:8] == (4096, 0, 2) and yt[5:8] == (3414, 4, 2),
                'selected RGB565 layout/alpha contract')
        require((p[2], p[3]) == (128, 64) and yh[8] == r['candidate_crc32'],
                'selected logical dimensions/CRC changed')
        changed.append(i)
    require(len(old_ids) >= 16 and len(old_ids) % 32 == 0, 'R4ID extent')
    ih = struct.unpack_from('<4s3I', old_ids)
    require(ih == (b'R4ID', 1, a[2], a[5]) and ih[2] <= len(old_ids)-16, 'R4ID binding')
    require(len(old_classes) >= 24, 'R4TC extent')
    th = struct.unpack_from('<4s5I', old_classes)
    require(th[:5] == (b'R4TC', 1, 1, a[3], a[5])
            and len(old_classes) == 24+((a[3]+3) & ~3), 'R4TC binding')
    cls = old_classes[24:24+a[3]]
    require(zlib.crc32(cls) & 0xffffffff == th[5] and all(c <= 10 for c in cls), 'R4TC class CRC/code')
    # tr_classify.py part_class: OP/PT ignore texels; an RGB565 TR part is
    # opaque, or VA when reserved bit0 is set. No alpha decoding is assumed.
    for i in changed:
        p = ap[i]
        expected = 1 if p[4] == 0 else 2 if p[4] == 1 else 9 if p[7] & 1 else 3
        require(p[4] <= 2 and cls[i] == expected, 'changed-part class semantics differ')
    ids = bytearray(old_ids)
    classes = bytearray(old_classes)
    struct.pack_into('<I', ids, 12, b[5])
    struct.pack_into('<I', classes, 16, b[5])
    ids, classes = bytes(ids), bytes(classes)
    require(set(changes(old_ids, ids)) <= set(range(12, 16)), 'R4ID write scope')
    require(set(changes(old_classes, classes)) <= set(range(16, 20)), 'R4TC write scope')
    require(ids[16:] == old_ids[16:] and classes[20:] == old_classes[20:], 'dependent payload changed')
    proof = dict(scope='R4ID/R4TC binding repair only',full_equivalence=False,
                 open_consumers=['PCL1 and runtime interior constant', 'OCCL/runtime fingerprint census'],
                 old_world_sha256=digest(old_world),new_world_sha256=digest(new_world),
                 geometry_sha256=expected_mesh_sha256,part_count=a[3],placement_count=a[2],
                 changed_parts=changed,unchanged_material_fields=True,placements_byte_exact=True,
                 old_world_crc=a[5],new_world_crc=b[5],
                 ids=dict(before_sha256=digest(old_ids),after_sha256=digest(ids),
                          changed_offsets=changes(old_ids,ids),payload_byte_exact=True),
                 classes=dict(before_sha256=digest(old_classes),after_sha256=digest(classes),
                              changed_offsets=changes(old_classes,classes),payload_byte_exact=True,
                              class_crc=th[5],classifier=th[2],changed_part_semantics_proved=True),
                 limits=['Unchanged textures are exact B-to-C bytes; inherited B classifier/mipmap correctness is separate.',
                         'No caller asset writes, runtime guard bypass, image generation, guest or target acceptance.'])
    return {'ids':ids,'classes':classes}, proof
