"""Bounded FE3 producer/validator helpers for opt-in ACTOR_FORMAT32 assets.

This is the existing FE3 layout. A new certificate is computed from freshly
assembled, referenced quantized UV values; an old flags field is never input
to certificate(). Unknown/legacy tags remain without certificate authority.
"""
import math
import struct


def certificate(pairs, signed=False):
    """Match actor_format32_uv.hpp: |raw| <= 2**e, code = 15+e, e=1..16."""
    exponent = 1
    low, high = (-32768, 32767) if signed else (0, 65535)
    seen = False
    for pair in pairs:
        if len(pair) != 2:
            raise ValueError('one quantized UV pair required')
        for value in pair:
            if type(value) is not int or not low <= value <= high:
                raise ValueError('UV component outside declared 16-bit encoding')
            while 1 << exponent < abs(value):
                exponent += 1
            seen = True
    if not seen:
        raise ValueError('empty referenced UV set')
    return 15 + exponent


def source(gx, positions, normals, uv, small_normals=False):
    """Exact packed input allocations, with no inference from maximum indices."""
    ns = 4 if small_normals else 8
    if not positions or len(positions) % 8 or not normals or len(normals) % ns or not uv or len(uv) % 4:
        raise ValueError('truncated or empty attribute allocation')
    if len(gx) < 3 or gx[0] != 0x90:
        raise ValueError('one GX triangle list required')
    count = struct.unpack_from('>H', gx, 1)[0]
    end = 3 + count * 6
    # pack_coarse_actor.py stores one command, optionally zero padded to 32.
    if not count or count % 3 or len(gx) not in (end, (end + 31) & ~31) or any(gx[end:]):
        raise ValueError('truncated/trailing/nontriangle GX input')
    corners = list(struct.iter_unpack('>3H', gx[3:end]))
    counts = (len(positions) // 8, len(normals) // ns, len(uv) // 4)
    if counts[0] > 65535 or counts[1] > 65535:
        raise ValueError('attribute count exceeds native owner capability')
    if any(c[a] >= counts[a] for c in corners for a in range(3)):
        raise ValueError('source corner outside declared allocation')
    return dict(corners=corners, counts=counts, position_bytes=len(positions),
                normal_bytes=len(normals), uv_bytes=len(uv), stream_bytes=len(gx),
                position_stride=8, normal_stride=ns, uv_encoding='u16q15')


def split_strips(indices):
    """Keep the runtime's <=64-corner bound, triangle parity and strip order."""
    out, run = [], []
    for value in indices:
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('invalid index byte')
        run.append(value & 127)
        if value & 128:
            if len(run) < 3:
                raise ValueError('short strip')
            while len(run) > 64:
                out.extend(run[:63]); out.append(run[63] | 128)
                run = run[62:]  # even advance retains the original winding
            out.extend(run[:-1]); out.append(run[-1] | 128)
            run = []
    if run:
        raise ValueError('unterminated strip')
    return out


def validate(blob, position_bytes, normal_bytes, uv, small_normals=False, signed=False):
    """Check the FE3 plain-record capability using exact source allocations.

    Every stored LOD references a level-zero record prefix. Mutable bake,
    vertex-colour and pending-LOD formats have no offline capability here.
    The existing charbake Blob reader remains the triangle decoder.
    """
    ns = 4 if small_normals else 8
    if not position_bytes or position_bytes % 8 or not normal_bytes or normal_bytes % ns or not uv or len(uv) % 4:
        raise ValueError('invalid exact attribute spans')
    if len(blob) < 32 or len(blob) > 1024 * 1024:
        raise ValueError('invalid stream extent')
    magic, version, flags, levels, meshlets, color, rec4, idx4, lod4, bake4 = struct.unpack_from('<4B6H', blob)
    if magic != 254 or version != 3 or flags & 0x83 or levels > 3 or not meshlets or bake4:
        raise ValueError('unsupported FE3 capability')
    sphere = struct.unpack_from('<4f', blob, 16)
    if not all(math.isfinite(f) for f in sphere) or sphere[3] < 0:
        raise ValueError('invalid bounds')
    rec, idx = rec4 * 4, idx4 * 4
    if not 32 + meshlets * 8 <= rec <= idx <= len(blob):
        raise ValueError('invalid record/table extents')
    counts = (position_bytes // 8, normal_bytes // ns, len(uv) // 4)
    if counts[0] > 65535 or counts[1] > 65535:
        raise ValueError('attribute count exceeds native owner capability')
    pairs = list(struct.iter_unpack('<2h' if signed else '<2H', uv))
    records, referenced = [], []
    tables = []
    if levels:
        at = lod4 * 4
        if not idx <= at <= len(blob) or levels * 8 > len(blob) - at:
            raise ValueError('truncated LOD table')
        for level in range(levels):
            error, t4, l4 = struct.unpack_from('<fHH', blob, at + level * 8)
            ta, lists = t4 * 4, l4 * 4
            if not math.isfinite(error) or error < 0 or not idx <= ta <= len(blob) or meshlets * 8 > len(blob) - ta or not idx <= lists <= len(blob):
                raise ValueError('invalid LOD spans')
            tables.append((ta, lists))
    elif lod4:
        raise ValueError('unexpected LOD table')

    def check_list(word, lists, offset, prefix):
        nv, ni, nt = word & 255, (word >> 8) & 4095, word >> 20
        if not nv and not ni and not nt:
            return 0, 0, 0
        if not 0 < nv <= prefix or nv > 128 or not 0 < ni <= 1024 or offset > len(blob) - lists or ni > len(blob) - lists - offset:
            raise ValueError('invalid meshlet index extent/prefix')
        length = triangles = strips = 0
        for value in blob[lists + offset:lists + offset + ni]:
            length += 1
            if value & 127 >= nv or length > 64:
                raise ValueError('index/strip outside runtime limits')
            if value & 128:
                if length < 3:
                    raise ValueError('short strip')
                triangles += length - 2
                length = 0
                strips += 1
        if length or triangles != nt:
            raise ValueError('unterminated strip or triangle count')
        return triangles, ni, strips

    triangles = indices = strips = 0
    for m in range(meshlets):
        word, first, offset = struct.unpack_from('<IHH', blob, 32 + m * 8)
        nv = word & 255
        if not 0 < nv <= 128 or first * 6 > idx - rec or nv * 6 > idx - rec - first * 6:
            raise ValueError('record outside stream extent')
        current = [struct.unpack_from('<3H', blob, rec + (first + v) * 6) for v in range(nv)]
        if any(r[a] >= counts[a] for r in current for a in range(3)):
            raise ValueError('record outside attribute allocation')
        records.extend(current); referenced.extend(pairs[r[2]] for r in current)
        nt, ni, nstrips = check_list(word, idx, offset, nv)
        triangles += nt; indices += ni; strips += nstrips
        for ta, lists in tables:
            w, off, reserved = struct.unpack_from('<IHH', blob, ta + m * 8)
            if reserved:
                raise ValueError('unsupported LOD extension')
            check_list(w, lists, off, nv)
    code = (flags >> 2) & 31
    present = code >= 16
    if present and certificate(referenced, signed) > code:
        raise ValueError('UV interval certificate disagrees with referenced data')
    return dict(meshlets=meshlets, records=len(records), triangles=triangles, indices=indices, strips=strips,
                stream_bytes=len(blob), position_bytes=position_bytes, normal_bytes=normal_bytes,
                uv_bytes=len(uv), uv_encoding='s16q8' if signed else 'u16q15',
                certificate=code if present else None, levels=levels)
