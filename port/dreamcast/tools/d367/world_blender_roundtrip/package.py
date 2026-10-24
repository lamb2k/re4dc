"""Strict, tools-only identity codec for the existing prelit R4IM v3 + R4PW v1.

Record definitions and alignment come from convert_room_bins, not a new runtime
format. Only its canonical, non-extended layout is accepted. Unknown extension
tables must acquire a validator before this tool may carry them through.
"""
from copy import deepcopy
import hashlib
import math
from pathlib import Path
import struct
import sys
import zlib

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
import convert_room_bins as crb

PW_HEAD = struct.Struct('<4s7I')
PW_PART = struct.Struct('<IIHHBBBB')
PW_PLACE = struct.Struct('<HH12f')
U32 = struct.Struct('<I')
SCHEMA = 're4dc.blender.identity/1'


def require(ok, why):
    if not ok:
        raise ValueError(why)


def crc(data):
    return zlib.crc32(data) & 0xffffffff


def sha(data):
    return hashlib.sha256(data).hexdigest()


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def float_bits(value):
    return struct.pack('<f', value).hex()


def rows(data, offset, count, fmt, label):
    require(0 <= offset <= len(data) and 0 <= count <= (len(data)-offset)//fmt.size,
            'out of bounds '+label)
    return [list(fmt.unpack_from(data, offset+i*fmt.size)) for i in range(count)]


def finite(values, label):
    require(all(math.isfinite(v) for v in values), 'nonfinite '+label)


def partition(records, first, count, expected, label):
    cursor = 0
    for rec in records:
        require(rec[first] == cursor and rec[count] >= 0, 'noncanonical '+label+' partition')
        cursor += rec[count]
    require(cursor == expected, 'incomplete '+label+' partition')


def pack_rows(fmt, records):
    return b''.join(fmt.pack(*r) for r in records)


def serialize_mesh(doc):
    """Regenerate every record, strip command, section offset, padding and CRC."""
    index = bytearray()
    for rec, command in zip(doc['meshlets'], doc['commands']):
        indexed = bool(rec[4] & 0x8000)
        if indexed and len(index) & 1:
            index.append(0)
        require(rec[1] == len(index), 'noncanonical index placement')
        if indexed:
            require(len(command['pool']) == rec[3], 'pool length')
            index.extend(struct.pack('<%dH' % rec[3], *command['pool']))
        else:
            require(command['pool'] == list(range(rec[3])), 'plain pool identity')
        start = len(index)
        for strip in command['strips']:
            index.append(len(strip)); index.extend(strip)
        require(len(index)-start == rec[2] and len(command['strips']) == (rec[4] & 0x7fff),
                'strip length/count')
    payloads = [('mesh', pack_rows(crb.MESH, doc['meshes'])),
                ('part', pack_rows(crb.PART, doc['parts'])),
                ('meshlet', pack_rows(crb.MESHLET, doc['meshlets'])),
                ('vertex', pack_rows(crb.VERTEX, doc['vertices'])),
                ('index', bytes(index)), ('palette', pack_rows(U32, [[x] for x in doc['palette']])),
                ('part_lod', pack_rows(crb.PART_LOD, doc['part_lods'])),
                ('cluster', pack_rows(crb.CLUSTER, doc['clusters'])),
                ('level', pack_rows(crb.LEVEL, doc['levels']))]
    if doc['classes'] is not None:
        payloads.append(('class', bytes(doc['classes'])))
    if doc['rules'] is not None:
        payloads.append(('rule', pack_rows(crb.CLASS_RULE, doc['rules'])))
    body, offsets = bytearray(), {}
    for name, data in payloads:
        offset = crb.align(112+len(body))
        body.extend(bytes(offset-112-len(body)))
        offsets[name] = offset
        body.extend(data)
    body.extend(bytes(crb.align(112+len(body))-112-len(body)))
    lod = crb.LOD_HEADER.pack(len(doc['clusters']), len(doc['levels']),
        offsets['part_lod'], offsets['cluster'], offsets['level'],
        offsets.get('class', 0), offsets.get('rule', 0), 0)
    body = lod+body
    header = crb.HEADER.pack(b'R4IM', 3, 80+len(body), crc(body),
        len(doc['meshes']), len(doc['parts']), len(doc['meshlets']), len(doc['vertices']),
        len(index), len(doc['palette']), *(offsets[k] for k in
        ('mesh', 'part', 'meshlet', 'vertex', 'index', 'palette')), 2, 0, 0, 0)
    return header+body


def serialize_policy(doc):
    body = pack_rows(PW_PART, doc['materials'])+pack_rows(PW_PLACE, doc['placements'])
    return PW_HEAD.pack(b'R4PW', 1, len(doc['placements']), len(doc['materials']),
                        len(doc['meshes']), crc(body), 0, 0)+body


def owners(doc):
    """Every stored meshlet belongs to exactly one mesh/part/cluster/LOD."""
    result = {}
    for mi, mesh in enumerate(doc['meshes']):
        for pi in range(mesh[6], mesh[6]+mesh[7]):
            first, count = doc['part_lods'][pi]
            for ci in range(first, first+count):
                c = doc['clusters'][ci]
                for ordinal, li in enumerate(range(c[6], c[6]+c[7])):
                    level = doc['levels'][li]
                    for ji in range(level[0], level[0]+level[1]):
                        require(ji not in result, 'meshlet belongs to multiple levels')
                        result[ji] = [mi, pi, ci, li, ordinal]
    require(set(result) == set(range(len(doc['meshlets']))), 'unowned meshlet')
    return result


def local_vertices(doc, ji):
    base = doc['meshlets'][ji][0]
    return [base+n for n in doc['commands'][ji]['pool']]


def triangles(doc, ji):
    """Keep every triangle, including degenerate restart/parity triangles."""
    return [list(t) for s in doc['commands'][ji]['strips'] for t in crb.strip_triangles(s)]


def decode(mesh, policy):
    require(len(mesh) >= 112, 'short R4IM')
    h = crb.HEADER.unpack_from(mesh)
    require(h[:2] == (b'R4IM', 3) and h[2] == len(mesh), 'R4IM v3 identity/size')
    require(h[3] == crc(mesh[80:]), 'R4IM CRC')
    require(h[16:] == (2, 0, 0, 0), 'unsupported R4IM color/extension (SDO3/SDS1 included)')
    lh = crb.LOD_HEADER.unpack_from(mesh, 80)
    require(lh[7] == 0, 'unsupported appended runtime tables (impostors/textures)')
    d = dict(schema=SCHEMA,
        meshes=rows(mesh,h[10],h[4],crb.MESH,'meshes'),
        parts=rows(mesh,h[11],h[5],crb.PART,'parts'),
        meshlets=rows(mesh,h[12],h[6],crb.MESHLET,'meshlets'),
        vertices=rows(mesh,h[13],h[7],crb.VERTEX,'vertices'),
        palette=[r[0] for r in rows(mesh,h[15],h[9],U32,'palette')],
        part_lods=rows(mesh,lh[2],h[5],crb.PART_LOD,'part LOD'),
        clusters=rows(mesh,lh[3],lh[0],crb.CLUSTER,'clusters'),
        levels=rows(mesh,lh[4],lh[1],crb.LEVEL,'levels'),
        classes=list(mesh[lh[5]:lh[5]+h[4]]) if lh[5] else None,
        rules=rows(mesh,lh[6],8,crb.CLASS_RULE,'class rules') if lh[6] else None,
        commands=[])
    require(1 <= len(d['palette']) <= 16, 'palette count')
    if d['classes'] is not None:
        require(len(d['classes']) == h[4] and all(x < 8 for x in d['classes']), 'class codes')
    partition(d['meshes'],6,7,h[5],'mesh parts')
    partition(d['parts'],6,7,h[6],'part meshlets')
    partition(d['part_lods'],0,1,lh[0],'part clusters')
    partition(d['clusters'],6,7,lh[1],'cluster levels')
    partition(d['levels'],0,1,h[6],'level meshlets')
    for m in d['meshes']:
        finite(m[8:],'mesh parameters')
        require(m[1] in (0,1) and all(x > 0 for x in m[11:14]), 'mesh common/grid')
        require(all(a <= b for a,b in zip(m[14:17],m[17:20])), 'mesh bounds')
    for p in d['parts']:
        finite(p[8:],'UV parameters')
        require(not p[5] and all(x > 0 for x in p[10:12]), 'part state/UV scale')
    for c in d['clusters']:
        require(c[7] > 0 and all(a <= b for a,b in zip(c[:3],c[3:6])), 'cluster bounds/levels')
        prev = 0.0
        for level in d['levels'][c[6]:c[6]+c[7]]:
            require(prev <= level[2] < 3e38, 'LOD error ordering')
            prev = level[2]
    require(h[14]+h[8] <= len(mesh), 'index table extent')
    indices = mesh[h[14]:h[14]+h[8]]
    for m in d['meshlets']:
        fv, start, size, vc, flags = m[:5]
        ix = bool(flags & 0x8000)
        require(0 < vc <= 256 and (not ix or start % 2 == 0), 'meshlet vertex count/alignment')
        require(0 <= start <= len(indices) and size+2*vc*ix <= len(indices)-start, 'strip extent')
        pool = list(struct.unpack_from('<%dH'%vc,indices,start)) if ix else list(range(vc))
        require(all(fv+v < h[7] for v in pool), 'pool reference')
        start += 2*vc*ix
        end, strips = start+size, []
        while start < end:
            n = indices[start]; start += 1
            require(n >= 3 and n <= end-start, 'strip size')
            strip = list(indices[start:start+n]); start += n
            require(all(v < vc for v in strip), 'strip local index')
            strips.append(strip)
        require(len(strips) == flags & 0x7fff, 'strip count')
        require(all(a <= b for a,b in zip(m[5:8],m[8:11])), 'meshlet bounds')
        d['commands'].append(dict(pool=pool,strips=strips))
    ownership = owners(d)
    used, previous = set(), 0
    for pi,p in enumerate(d['parts']):
        pool = set()
        for ji in range(p[6],p[6]+p[7]):
            require(ownership[ji][1] == pi, 'part/LOD ownership')
            pool.update(local_vertices(d,ji))
        if pool:
            require(min(pool) >= previous, 'overlapping part pools')
            previous = max(pool)+1
        used.update(pool)
    require(used == set(range(h[7])), 'unrepresented/orphan vertex pool data')
    require(len(policy) >= PW_HEAD.size, 'short R4PW')
    p = PW_HEAD.unpack_from(policy)
    require(p[:2] == (b'R4PW',1) and p[3:5] == (h[5],h[4]) and p[6:] == (0,0), 'R4PW header/counts')
    require(len(policy) == 32+16*p[3]+52*p[2] and crc(policy[32:]) == p[5], 'R4PW size/CRC')
    d['materials'] = rows(policy,32,p[3],PW_PART,'materials')
    d['placements'] = rows(policy,32+16*p[3],p[2],PW_PLACE,'placements')
    for m in d['materials']:
        require(m[2] > 0 and m[3] > 0 and m[4] <= 2 and m[5] <= 2 and m[7] <= 1, 'material fields')
    for place in d['placements']:
        require(place[0] < h[4], 'placement mesh')
        finite(place[2:],'placement')
    require(serialize_mesh(d) == mesh, 'noncanonical R4IM layout/padding/unknown trailing bytes')
    require(serialize_policy(d) == policy, 'noncanonical R4PW')
    return d


def clone(doc):
    return deepcopy(doc)
