#!/usr/bin/env python3
"""Experimental R4IM v2/v3 prelit world -> explicit v4 emit/bounds layout.

This is a physical representation change only. No geometry, LOD, strip order,
vertex remap, material, placement or source identity is changed. The source
package remains the lineage authority. Build12/SDS1/SDO3 and appended runtime
tables are deliberately outside this format's contract.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

import convert_room_bins as crb

EMIT = struct.Struct('<IIIHH')
BOUNDS = struct.Struct('<6H')
POLICY_HEADER = struct.Struct('<4s7I')
GROUP = struct.Struct('<6HHBB')
INDEXED = 0x8000


def require(ok, message):
    if not ok:
        raise ValueError(message)


def crc(data):
    return zlib.crc32(data) & 0xffffffff


def sha(data):
    return hashlib.sha256(data).hexdigest()


def aligned(n):
    return (n + 31) & ~31


class Package:
    """Strict canonical world package, retaining exact serialized field bytes."""
    def __init__(self, data, allow_split=False):
        self.data = bytes(data)
        require(len(data) >= 112, 'short R4IM')
        self.h = h = crb.HEADER.unpack_from(data)
        self.l = l = crb.LOD_HEADER.unpack_from(data, 80)
        require(h[0] == b'R4IM' and h[1] in ((2, 3, 4) if allow_split else (2, 3)),
                'unsupported R4IM version (Build12 composition is not supported)')
        require(h[2] == len(data) and h[3] == crc(data[80:]), 'R4IM size/CRC')
        require(h[16] == 2, 'only prelit world encoding is supported')
        require(l[7] == 0, 'unsupported appended runtime tables')
        require(0 < h[4] <= 65536 and 0 < h[5] and 0 < h[6] <= 65536,
                'mesh/part/global meshlet count (Pick.let is uint16)')
        require(h[7] > 0 and 0 < h[9] <= 16, 'vertex/palette count')
        split = h[1] == 4
        if split:
            require(h[17] == aligned(h[12] + EMIT.size*h[6]), 'noncanonical emit/bounds adjacency')
            require(h[19] >= 112, 'missing original source extent')
        else:
            require(h[17:20] == (0, 0, 0),
                    'unsupported reserved extension (Build12/SDS1/SDO3 cannot be composed)')
        specs = [('mesh', h[10], h[4], crb.MESH), ('part', h[11], h[5], crb.PART),
                 ('emit' if split else 'meshlet', h[12], h[6], EMIT if split else crb.MESHLET)]
        if split:
            specs += [('bounds', h[17], h[6], BOUNDS)]
        specs += [('vertex', h[13], h[7], crb.VERTEX), ('index', h[14], h[8], struct.Struct('<B')),
                  ('palette', h[15], h[9], struct.Struct('<I')),
                  ('part_lod', l[2], h[5], crb.PART_LOD), ('cluster', l[3], l[0], crb.CLUSTER),
                  ('level', l[4], l[1], crb.LEVEL)]
        if l[5]:
            specs += [('class', l[5], h[4], struct.Struct('<B'))]
        if l[6]:
            specs += [('rule', l[6], 8, crb.CLASS_RULE)]
        self.sections, self.tables = {}, {}
        end = 112
        for name, offset, count, fmt in specs:
            require(offset == aligned(end), 'noncanonical section: ' + name)
            require(offset <= len(data) and count <= (len(data)-offset)//fmt.size,
                    'section extent: ' + name)
            require(not any(data[end:offset]), 'nonzero section padding: ' + name)
            end = offset + count*fmt.size
            self.sections[name] = bytes(data[offset:end])
            self.tables[name] = list(fmt.iter_unpack(self.sections[name]))
        require(len(data) == aligned(end) and not any(data[end:]), 'unsupported trailing data/padding')
        self.meshlets = ([(e+b) for e, b in zip(self.tables['emit'], self.tables['bounds'])]
                         if split else self.tables['meshlet'])
        self.meshes = self.tables['mesh']; self.parts = self.tables['part']
        self.vertices = [self.sections['vertex'][i:i+12] for i in range(0, 12*h[7], 12)]
        self._refs, self._strips = [], []
        self._validate()

    def _validate(self):
        h = self.h
        require(all(c[0] < 8 for c in self.tables.get('class', [])), 'invalid class')
        next_part = 0
        for m in self.meshes:
            require(m[2] == 0x50 and m[1] == 0, 'not a PS2 world source owner')
            require(m[6] == next_part and m[7] <= h[5]-next_part, 'mesh part partition')
            require(all(math.isfinite(x) for x in m[8:]) and all(x > 0 for x in m[11:14]), 'mesh grid')
            require(all(m[14+a] <= m[17+a] for a in range(3)), 'mesh bounds')
            next_part += m[7]
        require(next_part == h[5], 'unowned parts')
        for rec in self.meshlets:
            fv, fs, sb, vc, sc = rec[:5]
            ix = bool(sc & INDEXED)
            require(not ix or h[1] in (3, 4), 'indexed record in v2')
            require(0 < vc <= 256 and 0 < (sc & 0x7fff) and sb <= 65535, 'meshlet capacity')
            require(fs <= h[8] and (not ix or fs % 2 == 0), 'meshlet strip offset')
            table = 2*vc if ix else 0
            require(table+sb <= h[8]-fs, 'meshlet strip extent')
            offsets = struct.unpack_from('<%dH' % vc, self.sections['index'], fs) if ix else range(vc)
            refs = tuple(fv+k for k in offsets)
            require(all(k < h[7] for k in refs), 'meshlet vertex reference')
            require(all(rec[5+a] <= rec[8+a] for a in range(3)), 'meshlet bounds order')
            for k in refs:
                pos = struct.unpack_from('<3H', self.vertices[k])
                require(all(rec[5+a] <= pos[a] <= rec[8+a] for a in range(3)), 'meshlet bounds enclosure')
            raw = self.sections['index'][fs+table:fs+table+sb]
            strips, cursor = [], 0
            while cursor < sb:
                n = raw[cursor]
                require(n >= 3 and n+1 <= sb-cursor, 'strip length')
                strip = raw[cursor:cursor+1+n]
                require(all(k < vc for k in strip[1:]), 'strip local reference')
                strips.append(strip); cursor += len(strip)
            require(len(strips) == (sc & 0x7fff), 'strip count')
            self._refs.append(refs); self._strips.append(tuple(strips))
        next_let, previous_pool = 0, 0
        clusters, levels = self.tables['cluster'], self.tables['level']
        for pi, p in enumerate(self.parts):
            require(p[5] == 0 and all(math.isfinite(x) for x in p[8:]), 'part state/UV')
            first, count = p[6:8]
            require(first == next_let and count <= h[6]-first, 'part meshlet partition')
            next_let += count
            refs = [r for li in range(first, first+count) for r in self._refs[li]]
            if refs:
                # Match ordinary MeshPackage::part_pool, including an indexed
                # record's conservative base even if offset zero is unused.
                low = min(self.meshlets[li][0] for li in range(first, first+count))
                require(low >= previous_pool, 'part pool overlap')
                previous_pool = max(refs)+1
            fc, cc = self.tables['part_lod'][pi]
            require(fc <= len(clusters) and cc <= len(clusters)-fc, 'part cluster extent')
            budget = count
            for c in clusters[fc:fc+cc]:
                fl, lc = c[6:8]
                require(lc > 0 and fl <= len(levels) and lc <= len(levels)-fl, 'cluster level extent')
                require(all(c[a] <= c[a+3] for a in range(3)), 'cluster bounds order')
                previous, maximum = 0., 0
                for lf, ln, error in levels[fl:fl+lc]:
                    require(math.isfinite(error) and previous <= error < 3.e38, 'level error')
                    previous = error
                    require(first <= lf <= first+count and ln <= first+count-lf, 'level meshlet extent')
                    maximum = max(maximum, ln)
                    for li in range(lf, lf+ln):
                        b = self.meshlets[li][5:]
                        require(all(c[a] <= b[a] and b[a+3] <= c[a+3] for a in range(3)),
                                'cluster bounds enclosure')
                require(maximum <= budget, 'part selected Pick capacity')
                budget -= maximum
        require(next_let == h[6], 'unowned meshlets')

    def refs(self, li):
        return self._refs[li]

    def strips(self, li):
        return self._strips[li]


def policy(data, pkg):
    require(len(data) >= 32, 'short R4PW')
    p = POLICY_HEADER.unpack_from(data)
    require(p[:2] == (b'R4PW', 1) and p[3:5] == (pkg.h[5], pkg.h[4]), 'R4PW identity/counts')
    require(p[6:] == (0, 0) and p[5] == crc(data[32:]), 'R4PW reserved/CRC')
    require(0 < p[2] <= 65536 and len(data) == 32+16*p[3]+52*p[2], 'R4PW extent')
    for i in range(p[3]):
        row = struct.unpack_from('<IIHHBBBB', data, 32+16*i)
        require(0 < row[2] <= 1024 and 0 < row[3] <= 1024 and row[4] <= 2 and row[5] <= 2 and row[7] == 0,
                'R4PW material')
    seen = set()
    for i in range(p[2]):
        row = struct.unpack_from('<HH12f', data, 32+16*p[3]+52*i)
        require(row[0] < p[4] and row[1] not in seen and all(math.isfinite(v) for v in row[2:]),
                'R4PW placement/source identity')
        seen.add(row[1])
    return p


def build_groups(pkg, side, count=4):
    """Consecutive strips; same existing visibility23 preserve-order policy."""
    p = policy(side, pkg)
    require(1 <= count <= 8, 'group count must be 1..8')
    require(32+pkg.h[6]*count*16 <= 262144, 'R4SG exceeds runtime size limit')
    records = bytearray()
    for li in range(pkg.h[6]):
        strips, refs = pkg.strips(li), pkg.refs(li)
        ng = min(count, len(strips)); per = (len(strips)+ng-1)//ng
        runs = [strips[i:i+per] for i in range(0, len(strips), per)]
        end = 0
        for run in runs:
            end += sum(map(len, run))
            ks = [k for strip in run for k in strip[1:]]
            pos = [struct.unpack_from('<3H', pkg.vertices[refs[k]]) for k in ks]
            bounds = [min(v[a] for v in pos) for a in range(3)] + [max(v[a] for v in pos) for a in range(3)]
            records.extend(GROUP.pack(*bounds, end, min(ks), max(ks)))
        records.extend(GROUP.pack(0, 0, 0, 0, 0, 0, end, 1, 0)*(count-len(runs)))
    return POLICY_HEADER.pack(b'R4SG', 1, pkg.h[6], count, pkg.h[3], len(pkg.data), p[5], crc(records))+records


def validate_groups(data, pkg, side):
    p = policy(side, pkg)
    require(32 <= len(data) <= 262144, 'R4SG extent')
    g = POLICY_HEADER.unpack_from(data)
    require(g[:3] == (b'R4SG', 1, pkg.h[6]) and 1 <= g[3] <= 8, 'R4SG identity/count')
    require(g[4:7] == (pkg.h[3], len(pkg.data), p[5]), 'stale R4SG binding')
    require(len(data) == 32+g[2]*g[3]*16 and g[7] == crc(data[32:]), 'R4SG size/CRC')
    for li in range(g[2]):
        raw = b''.join(pkg.strips(li)); refs = pkg.refs(li); start = 0
        for gi in range(g[3]):
            r = GROUP.unpack_from(data, 32+16*(li*g[3]+gi)); end, lo, hi = r[6:]
            require(start <= end <= len(raw), 'R4SG group extent')
            if start == end:
                require(lo > hi, 'R4SG empty range')
                continue
            require(lo <= hi < len(refs) and all(r[a] <= r[a+3] for a in range(3)), 'R4SG bounds/range')
            cursor = start
            while cursor < end:
                n = raw[cursor]
                require(cursor+1+n <= end, 'R4SG splits a strip')
                for k in raw[cursor+1:cursor+1+n]:
                    pos = struct.unpack_from('<3H', pkg.vertices[refs[k]])
                    require(lo <= k <= hi and all(r[a] <= pos[a] <= r[a+3] for a in range(3)),
                            'R4SG does not enclose referenced corners')
                cursor += n+1
            start = end
        require(start == len(raw), 'R4SG incomplete strip coverage')
    return g


def verify_identity(source, candidate):
    require(candidate.h[1] == 4 and candidate.h[18:20] == (source.h[3], len(source.data)),
            'split source lineage mismatch')
    require(candidate.h[4:10] == source.h[4:10] and candidate.l[:2] == source.l[:2], 'split logical counts')
    require(candidate.meshlets == source.meshlets, 'split logical meshlet identity')
    for name, raw in source.sections.items():
        if name != 'meshlet':
            require(candidate.sections.get(name) == raw, 'split section identity: '+name)


def split_package(mesh):
    """Bytes in/out, exact logical identity; no files or proof side effects.

    Callers with a package bundle must separately validate/rebuild R4SG with
    convert(); this function does not approve any externally bound sidecar.
    """
    source = Package(mesh)
    chunks = [('mesh', source.sections['mesh']), ('part', source.sections['part']),
              ('emit', b''.join(EMIT.pack(*r[:5]) for r in source.meshlets)),
              ('bounds', b''.join(BOUNDS.pack(*r[5:]) for r in source.meshlets))]
    chunks += [(name, source.sections[name]) for name in
               ('vertex', 'index', 'palette', 'part_lod', 'cluster', 'level', 'class', 'rule')
               if name in source.sections]
    output = bytearray(112); offsets = {}
    for name, raw in chunks:
        output.extend(bytes(aligned(len(output))-len(output)))
        offsets[name] = len(output); output.extend(raw)
    output.extend(bytes(aligned(len(output))-len(output)))
    h, l = list(source.h), list(source.l)
    h[1:3] = [4, len(output)]
    h[10:16] = [offsets[k] for k in ('mesh', 'part', 'emit', 'vertex', 'index', 'palette')]
    h[17:20] = [offsets['bounds'], source.h[3], len(mesh)]
    l[2:7] = [offsets.get(k, 0) for k in ('part_lod', 'cluster', 'level', 'class', 'rule')]
    crb.LOD_HEADER.pack_into(output, 80, *l)
    h[3] = crc(output[80:]); crb.HEADER.pack_into(output, 0, *h)
    result = bytes(output); target = Package(result, allow_split=True)
    verify_identity(source, target)
    return result


def convert(mesh, side, groups=None, group_count=4):
    source = Package(mesh)
    policy(side, source)
    source_groups = build_groups(source, side, group_count) if groups is None else bytes(groups)
    gh = validate_groups(source_groups, source, side)
    result = split_package(mesh)
    target = Package(result, allow_split=True)
    h = target.h
    records = source_groups[32:]
    result_groups = POLICY_HEADER.pack(b'R4SG', 1, h[6], gh[3], h[3], len(result), gh[6], crc(records))+records
    validate_groups(result_groups, target, side)
    report = dict(schema='re4dc.scenery-record-split.v1', source_version=source.h[1], version=4,
                  source_bytes=len(mesh), split_bytes=len(result), resident_delta=len(result)-len(mesh),
                  source_sha256=sha(mesh), split_sha256=sha(result), policy_sha256=sha(side),
                  source_crc='%08x' % source.h[3], split_crc='%08x' % h[3],
                  meshlets=h[6], emit_offset=h[12], bounds_offset=h[17], emit_stride=16, bounds_stride=12,
                  logical_identity=True, strip_order_identity=True, source_ids_identity=True,
                  r4sg_source='generated consecutive groups' if groups is None else 'validated supplied groups',
                  group_count=gh[3], source_groups_sha256=sha(source_groups), split_groups_sha256=sha(result_groups),
                  group_records_identity=source_groups[32:] == result_groups[32:], r4sg_bytes=len(result_groups),
                  build12_composition=False, physical_proofs_rebound=False)
    return result, result_groups, report


def refuse_extra_sidecars(mesh_path):
    """The standalone tool accepts only this explicit sidecar registry.

    Neither a new CRC nor byte-identical logical geometry certifies a PVS,
    room-cell, occlusion or other proof bound to the physical source package.
    """
    path = Path(mesh_path)
    permitted = {path.with_suffix(s).name for s in ('.re4mesh', '.r4pw', '.r4sg', '.json')}
    for sibling in path.parent.glob(path.stem+'.*'):
        require(sibling.name in permitted, 'unsupported sibling sidecar: '+sibling.name)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mesh', type=Path); ap.add_argument('policy', type=Path)
    ap.add_argument('out', type=Path, help='alternate output stem; never replaces the source')
    ap.add_argument('--source-groups', type=Path)
    ap.add_argument('--groups', type=int, default=4)
    a = ap.parse_args()
    refuse_extra_sidecars(a.mesh)
    refuse_extra_sidecars(a.out.with_suffix('.re4mesh'))
    if a.source_groups is None and a.mesh.with_suffix('.r4sg').exists():
        a.source_groups = a.mesh.with_suffix('.r4sg')
    inputs = {p.resolve() for p in (a.mesh, a.policy, a.source_groups) if p}
    outputs = [a.out.with_suffix(s) for s in ('.re4mesh', '.r4sg', '.json')]
    require(not inputs.intersection(p.resolve() for p in outputs), 'output aliases a source')
    for dst in outputs:
        require(not dst.exists(), 'refusing existing output: '+str(dst))
    mesh, groups, report = convert(a.mesh.read_bytes(), a.policy.read_bytes(),
                                  a.source_groups.read_bytes() if a.source_groups else None, a.groups)
    outputs[0].write_bytes(mesh); outputs[1].write_bytes(groups)
    outputs[2].write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
