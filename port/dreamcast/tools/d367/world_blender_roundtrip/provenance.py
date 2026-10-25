"""Policy-source CRC remap, a Python mirror of the runtime's provenance lookup.

The runtime binds the world companions (R4ID, R4TC, R4SG, PVS/room VIS/OCCL)
to a "policy source CRC", not to the physical R4PW header CRC. For a world
whose R4PW was rekeyed by a texture data line (mip22 / rect21: key-only part
remaps, geometry/placements/pass/cull exact), the runtime looks the physical
file up in texture_rect21/provenance_certificates.inc and uses the certified
original policy CRC; every other world uses its own header CRC.
(port/dreamcast/tools/d367/texture_rect21/world_rect_provenance.h,
native_static.cpp policySourceCrc.)

This module repeats that lookup field for field, so the identity adapter checks
the shipped bundles against the same binding the runtime admits. It never
rewrites a header or a companion: an unchanged world keeps its certified CRC;
an edited world (new body CRC / FNV) matches no certificate and binds to its
actual CRC, exactly as the runtime would. Lane world-blender25, 2026-10-25.
"""
from pathlib import Path
import re
import struct

INC = Path(__file__).resolve().parents[1]/'texture_rect21'/'provenance_certificates.inc'
_ROW = re.compile(r'^\{(.*)\},?\s*$')


def certificates(path=INC):
    rows = []
    for line in Path(path).read_text().splitlines():
        m = _ROW.match(line.strip())
        if not m:
            continue
        v = [int(x.strip().rstrip('Uu'), 0) for x in m.group(1).split(',')]
        if len(v) != 10:
            raise ValueError('certificate row needs 10 fields: '+line)
        rows.append(dict(zip(('room','world_bytes','placements','parts','meshes','physical_body_crc',
                              'physical_file_fnv','mesh_crc','mesh_bytes','source_crc'), v)))
    return rows


def fnv(b):
    h = 2166136261
    for x in b:
        h = ((h ^ x)*16777619) & 0xffffffff
    return h


def policy_crc(mesh, side, certs=None):
    """(crc, room or None): the CRC the runtime binds companions to for this mesh+R4PW."""
    if len(side) < 32:
        return 0, None
    w = struct.unpack_from('<4s7I', side)
    actual = w[5]
    mh = struct.unpack_from('<4s19I', mesh)
    # Runtime passes the mesh header crc/bytes (non-dedup3 path) and part/mesh counts.
    mesh_crc, mesh_bytes, mesh_count, mesh_parts = mh[3], mh[2], mh[4], mh[5]
    hit = []
    for c in (certs if certs is not None else certificates()):
        if (len(side), mesh_crc, mesh_bytes, mesh_parts, mesh_count, actual) != (
                c['world_bytes'], c['mesh_crc'], c['mesh_bytes'], c['parts'], c['meshes'], c['physical_body_crc']):
            continue
        if (w[0] != b'R4PW' or w[1] != 1 or w[2] != c['placements'] or w[3] != c['parts'] or
                w[4] != c['meshes'] or w[6] or w[7] or
                len(side) != 32+16*c['parts']+52*c['placements'] or fnv(side) != c['physical_file_fnv']):
            continue
        hit.append(c)
    if not hit:
        return actual, None
    if len({c['source_crc'] for c in hit}) != 1:
        raise ValueError('ambiguous provenance certificates')
    return hit[0]['source_crc'], hit[0]['room']
