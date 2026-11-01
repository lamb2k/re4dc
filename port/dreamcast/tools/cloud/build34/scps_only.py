#!/usr/bin/env python3
"""Add only an optional SCPS hint table bound to an unchanged R4IM package.

Default --scps-only34=0 performs no file I/O. Enabled output is a new R4RC
file; mesh, policy, strip groups and every non-SCPS section remain untouched.
This validates container/identity extents, not geometry or console behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def crc(data):
    return zlib.crc32(data) & 0xffffffff


def mesh_identity(mesh):
    require(len(mesh) >= 80, 'short R4IM header')
    h = struct.unpack_from('<4s19I', mesh)
    require(h[0] == b'R4IM' and h[1] in (1, 2, 3), 'unsupported R4IM header')
    require(h[2] == len(mesh) and h[3] == crc(mesh[80:]), 'R4IM length/CRC')
    head = 80 if h[1] == 1 else 112
    require(len(mesh) >= head, 'short R4IM LOD header')
    # A hint for existing parts needs their bounded table, not an invented placement list.
    count, offset = h[5], h[11]
    require(offset % 4 == 0 and head <= offset <= len(mesh), 'R4IM part offset')
    require(count <= (len(mesh) - offset) // 36, 'R4IM part extent')
    require(16 + count * 4 <= 1048576, 'SCPS exceeds room-file limit')
    return dict(version=h[1], bytes=h[2], crc=h[3], parts=count, sha256=sha(mesh))


def read_room(data):
    require(64 <= len(data) <= 1048576, 'R4RC size')
    magic, version, head, room, count, size = struct.unpack_from('<4sHHIII', data)
    require((magic, version, head) == (b'R4RC', 1, 64), 'R4RC header')
    require(room <= 0xfff and size == len(data), 'R4RC room/length')
    require(1 <= count <= 8 and 64 + 32 * count <= size, 'R4RC directory')
    require(struct.unpack_from('<I', data, 48)[0] == crc(data[64:]), 'R4RC CRC')
    rows, occupied, tags = [], [], set()
    for i in range(count):
        row = list(struct.unpack_from('<4sHH6I', data, 64 + 32 * i))
        tag, _, _, offset, length, _, _, alignment, _ = row
        require(tag not in tags, 'duplicate R4RC section')
        tags.add(tag)
        require(alignment == 16 and offset % 16 == 0, 'R4RC section alignment')
        require(64 + 32 * count <= offset <= size and length <= size - offset,
                'R4RC section extent')
        if length:
            require(all(offset + length <= lo or offset >= hi for lo, hi in occupied),
                    'overlapping R4RC sections')
            occupied.append((offset, offset + length))
        rows.append((row, data[offset:offset + length]))
    return room, rows


def convert(mesh, room_file):
    identity = mesh_identity(mesh)
    room, sections = read_room(room_file)
    payload = struct.pack('<4I', identity['crc'], identity['bytes'], identity['parts'], 0)
    payload += bytes(4 * identity['parts'])
    payload += bytes(-len(payload) % 16)
    replacement = ([b'SCPS', 1, 0, 0, len(payload), identity['parts'], 4, 16, 0], payload)
    rows, replaced = [], False
    for metadata, data in sections:
        if metadata[0] == b'SCPS':
            rows.append(replacement)
            replaced = True
        else:
            rows.append((metadata[:], data))
    if not replaced:
        rows.append(replacement)
    require(len(rows) <= 8, 'SCPS would exceed runtime MAXSEC=8')
    result = bytearray(room_file[:64] + bytes(32 * len(rows)))
    for i, (metadata, data) in enumerate(rows):
        result.extend(bytes(-len(result) % 16))
        metadata[3] = len(result)
        struct.pack_into('<4sHH6I', result, 64 + 32 * i, *metadata)
        result.extend(data)
    result.extend(bytes(-len(result) % 16))
    require(len(result) <= 1048576, 'output exceeds runtime room-file limit')
    struct.pack_into('<II', result, 12, len(rows), len(result))
    struct.pack_into('<I', result, 48, crc(result[64:]))
    output = bytes(result)
    _, checked = read_room(output)
    def other(values):
        return [(tuple(m[:3] + m[4:]), d) for m, d in values if m[0] != b'SCPS']
    require(other(sections) == other(checked), 'non-SCPS section changed')
    report = dict(status='PASS', room=f'r{room:03x}', mesh=identity,
                  input_room_sha256=sha(room_file), output_room_sha256=sha(output),
                  input_bytes=len(room_file), output_bytes=len(output),
                  scps_bytes=len(payload), runtime_scps_block_contribution=(len(payload) + 31) & ~31,
                  replaced=replaced, preserved_sections=[m[0].decode('ascii', 'backslashreplace')
                      for m, _ in sections if m[0] != b'SCPS'],
                  scope='Only SCPS added/replaced; other payloads and directory metadata except offsets preserved. '
                        'The 32B-rounded contribution is part of the existing shared room block, excluding allocator overhead/eviction. '
                        'Mesh/policy/strip-group files are not written. Geometry and console acceptance not established.')
    return output, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scps-only34', type=int, choices=(0, 1), default=0)
    for name in ('mesh', 'room-file', 'out', 'report'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args(argv)
    if not args.scps_only34:
        print('scps-only34=0: no files read or written')
        return 0
    if any(getattr(args, name) is None for name in ('mesh', 'room_file', 'out', 'report')):
        parser.error('enabled conversion requires --mesh, --room-file, --out and --report')
    try:
        paths = [p.resolve() for p in (args.mesh, args.room_file, args.out, args.report)]
        require(len(set(paths)) == 4, 'input/output paths must be distinct')
        require(not args.out.exists() and not args.report.exists(), 'use new output/report paths')
        output, report = convert(args.mesh.read_bytes(), args.room_file.read_bytes())
        for p in (args.out, args.report):
            p.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('xb') as f:
            f.write(output)
        with args.report.open('x') as f:
            f.write(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print('SCPS-only conversion refused: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
