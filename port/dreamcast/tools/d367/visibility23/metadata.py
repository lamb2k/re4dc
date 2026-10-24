"""Consecutive R4SG records; input buffers are immutable and never repacked."""
import hashlib
import json
from pathlib import Path
import struct
import zlib


def require(ok, message):
    if not ok:
        raise ValueError(message)


def crc(data):
    return zlib.crc32(data) & 0xffffffff


def span(data, offset, count, stride, label):
    require(0 <= offset <= len(data) and 0 <= count <= (len(data) - offset) // stride,
            'out of bounds ' + label)


def headers(mesh, side):
    require(len(mesh) >= 100, 'short R4IM')
    h = struct.unpack_from('<4s19I', mesh)
    require(h[0:2] == (b'R4IM', 3) and h[2] == len(mesh), 'R4IM identity/size')
    require(h[3] == crc(mesh[80:]), 'R4IM CRC')
    for offset, count, stride, label in ((h[10], h[4], 68, 'meshes'),
            (h[11], h[5], 36, 'parts'), (h[12], h[6], 28, 'meshlets'),
            (h[13], h[7], 12, 'vertices'), (h[14], h[8], 1, 'strips')):
        span(mesh, offset, count, stride, label)
    ncl, nlv, oplod, ocl, olv = struct.unpack_from('<5I', mesh, 80)
    for offset, count, stride, label in ((oplod, h[5], 8, 'part LOD'),
            (ocl, ncl, 20, 'clusters'), (olv, nlv, 12, 'levels')):
        span(mesh, offset, count, stride, label)
    require(len(side) >= 32, 'short R4PW')
    p = struct.unpack_from('<4s7I', side)
    require(p[0:2] == (b'R4PW', 1) and p[3] == h[5] and p[4] == h[4],
            'R4PW identity/counts')
    require(p[6:8] == (0, 0) and len(side) == 32 + 16*p[3] + 52*p[2], 'R4PW size/reserved')
    require(p[5] == crc(side[32:]), 'R4PW CRC')
    return h, p


def meshlets(mesh, h):
    """Yield exact original strip bytes and each original corner's grid value."""
    for li in range(h[6]):
        fv, fs, sb, vc, sc, *_ = struct.unpack_from('<IIIHH6H', mesh, h[12] + 28*li)
        require(vc <= 256 and sb <= 65535, 'R4SG range capacity')
        indexed = bool(sc & 0x8000)
        start = h[14] + fs
        span(mesh, start, (2*vc if indexed else 0) + sb, 1, 'meshlet strip bytes')
        require(fs + (2*vc if indexed else 0) + sb <= h[8], 'meshlet exceeds strip table')
        offsets = struct.unpack_from('<%dH' % vc, mesh, start) if indexed else range(vc)
        start += 2*vc if indexed else 0
        positions = []
        for offset in offsets:
            require(fv + offset < h[7], 'meshlet vertex reference')
            positions.append(struct.unpack_from('<3H', mesh, h[13] + 12*(fv+offset)))
        strips, cursor = [], 0
        while cursor < sb:
            n = mesh[start + cursor]
            require(n >= 3 and cursor + 1 + n <= sb, 'short/truncated strip')
            raw = mesh[start+cursor:start+cursor+1+n]
            require(all(k < vc for k in raw[1:]), 'strip corner reference')
            strips.append(raw)
            cursor += 1+n
        require(len(strips) == (sc & 0x7fff), 'meshlet strip count')
        yield li, vc, positions, strips


def build(mesh, side, groups=4):
    require(1 <= groups <= 8, 'groups must be 1..8')
    h, p = headers(mesh, side)
    records = bytearray()
    stats = dict(meshlets=h[6], groups=groups, nonempty_groups=0, range_sum=0,
                 vertex_sum=0, group_count_histogram={}, preserve_order=True,
                 mesh_crc_in='%08x' % h[3], mesh_crc_out='%08x' % h[3],
                 sidecar_crc='%08x' % p[5], mesh_sha256=hashlib.sha256(mesh).hexdigest(),
                 source_policy_sha256=hashlib.sha256(side).hexdigest())
    for _, vc, positions, strips in meshlets(mesh, h):
        ng = min(groups, len(strips))
        per = (len(strips) + ng - 1) // ng if ng else 1
        runs = [strips[i:i+per] for i in range(0, len(strips), per)]
        end = 0
        for run in runs:
            end += sum(map(len, run))
            ks = [k for raw in run for k in raw[1:]]
            lo = [min(positions[k][a] for k in ks) for a in range(3)]
            hi = [max(positions[k][a] for k in ks) for a in range(3)]
            records.extend(struct.pack('<6HHBB', *lo, *hi, end, min(ks), max(ks)))
            stats['nonempty_groups'] += 1
            stats['range_sum'] += max(ks)-min(ks)+1
        for _ in range(groups-len(runs)):
            records.extend(struct.pack('<6HHBB', 0, 0, 0, 0, 0, 0, end, 1, 0))
        hist = stats['group_count_histogram']
        hist[len(runs)] = hist.get(len(runs), 0) + 1
        stats['vertex_sum'] += vc
    result = struct.pack('<4s7I', b'R4SG', 1, h[6], groups, h[3], len(mesh), p[5], crc(records)) + records
    require(len(result) <= 262144, 'R4SG exceeds runtime size limit')
    stats.update(r4sg_bytes=len(result), r4sg_sha256=hashlib.sha256(result).hexdigest())
    return result, stats


def write_metadata(args):
    require(args.out_mesh == '-', 'preserve-order requires OUT.re4mesh = - (no mesh output)')
    inputs = {Path(args.mesh).resolve(), Path(args.sidecar).resolve()}
    outputs = [Path(args.out_groups).resolve()]
    if args.report:
        outputs.append(Path(args.report).resolve())
    require(len(set(outputs)) == len(outputs) and not inputs.intersection(outputs),
            'metadata/report output aliases an input or another output')
    existing = [p for p in [*inputs, *outputs] if p.exists()]
    require(all(not a.samefile(b) for i, a in enumerate(existing) for b in existing[i+1:]),
            'metadata/report paths alias through hard links')
    result, stats = build(Path(args.mesh).read_bytes(), Path(args.sidecar).read_bytes(), args.groups)
    Path(args.out_groups).write_bytes(result)
    if args.report:
        Path(args.report).write_text(json.dumps(stats, indent=2) + '\n')
    print(json.dumps(stats, sort_keys=True))
