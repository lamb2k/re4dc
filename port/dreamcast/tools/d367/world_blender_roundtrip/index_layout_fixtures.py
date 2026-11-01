"""Synthetic index-layout fixtures built with the existing public world tools.

No recovered game data, images, or private provenance is used. The real append
writer supplies the four-byte boundary that exposed Build11's sequential-index
assumption. Companion records below are newly generated for synthetic geometry;
no old visibility proof is rebound to changed production geometry.
"""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

import fixtures
import package as p
import ps2_world_append as append
from d367.visibility23 import metadata


MESH = 'ps2-world.re4mesh'
POLICY = 'ps2-world.r4pw'


def canonical_offsets(doc):
    """Give a synthetic document the old converter's ordinary index layout."""
    at = 0
    for rec, command in zip(doc['meshlets'], doc['commands']):
        indexed = bool(rec[4] & 0x8000)
        at += (-at % 2) if indexed else 0
        rec[1] = at
        rec[2] = sum(1 + len(strip) for strip in command['strips'])
        rec[4] = (0x8000 if indexed else 0) | len(command['strips'])
        at += rec[2] + (2 * rec[3] if indexed else 0)
    return at


def document(residue=None, first_indexed=False):
    """Rich source plus degenerate restart corners to exercise all residues."""
    doc = fixtures.document()
    if first_indexed:
        doc['meshlets'][0][4] |= 0x8000
    if residue is not None:
        p.require(residue in range(4), 'fixture residue must be 0..3')
        for extra in range(4):
            doc['commands'][-1]['strips'] = [[0, 1, 2] + [2] * extra]
            if canonical_offsets(doc) % 4 == residue:
                break
        else:
            raise AssertionError('fixture did not cover the requested residue')
    canonical_offsets(doc)
    return doc


def companions(mesh, policy, groups=None):
    """Generate the shipped five-file shape and explicit all-visible controls."""
    table = append.parse(mesh)
    parts, placements, nmesh = append.read_r4pw(policy)
    hp = p.PW_HEAD.unpack_from(policy)
    mesh_crc, policy_crc = p.crc(mesh[80:]), hp[5]
    count = len(placements)
    ids = struct.pack('<4s3I', b'R4ID', 1, count, policy_crc)
    ids += bytes(([7, 7, 255] * ((count + 2) // 3))[:count])
    ids += bytes(-len(ids) % 32)
    classes = bytes(([0, 3, 10] * ((len(parts) + 2) // 3))[:len(parts)])
    tc = struct.pack('<4s5I', b'R4TC', 1, 1, len(parts), policy_crc, p.crc(classes))
    tc += classes + bytes(-len(classes) % 4)
    if groups is None:
        groups, _ = metadata.build(mesh, policy, 4)
    files = {MESH: mesh, POLICY: policy, 'ps2-world.ids': ids,
             'ps2-world.r4tc': tc, 'ps2-world.r4sg': groups}

    # Every synthetic cluster is visible. No occluder or hidden-area assertion
    # is made, and this fixture does not issue a PVS23 or lost-part certificate.
    decoded_places = [p.PW_PLACE.unpack(row) for row in placements]
    instances = sum(sum(table['part_lod'][pi][1] for pi in
                    range(table['mesh'][place[0]][6],
                          sum(table['mesh'][place[0]][6:8])))
                    for place in decoded_places)
    nbits = (instances + 7) // 8
    pvs = struct.pack('<4s7I3f5I', b'R4PV', 1, mesh_crc, len(mesh), policy_crc,
                      instances, 1, 1, 0., 0., 4000., 1, nbits, 1, 0, 0)
    pvs += struct.pack('<Hhhh', 0, -10, 100, 0)
    pvs += ((1 << instances) - 1).to_bytes(nbits, 'little')
    pvs += bytes(-len(pvs) % 32)
    files['ps2-world.pvs'] = pvs
    files['interior.cell'] = struct.pack('<4s7I', b'PCL1', 0x123,
        mesh_crc, policy_crc, len(mesh), 1, 0, 0)
    files['interior.cell'] += struct.pack('<6f2H', -10., -10., -10., 10., 10., 10., 0, 0)
    files['ps2-world.occl'] = struct.pack('<4s7I', b'R4OC', 1,
        mesh_crc, len(mesh), policy_crc, 0, 0, 0)
    header = p.crb.HEADER.unpack_from(mesh)
    triangles = [sum(len(raw)-3 for raw in strips)
                 for _, _, _, strips in metadata.meshlets(mesh, header)]
    level0 = sum(sum(triangles[first:first+count])
                 for first, count, _ in (table['level'][c[6]] for c in table['cluster']))
    report = dict(source='public:synthetic-index-layout-fixture',
        source_sha256=p.sha(b'public synthetic index-layout geometry'),
        inc_sha256=p.sha(b'public synthetic index-layout policy'),
        args={'fixture': True}, meshes=nmesh, placements=count,
        source_triangles=level0, re4mesh_bytes=len(mesh), re4mesh_sha256=p.sha(mesh),
        r4pw_bytes=len(policy), r4pw_sha256=p.sha(policy),
        level0_triangles=level0,
        summary={'fixture': True, 'triangle_counts_include_strip_degenerates': True})
    files['ps2-world.json'] = json.dumps(report, indent=1).encode()
    return files


def appended_raw(residue=None, appended_indexed=False, copies=2):
    """Run real append_tables/serialize and real R4PW rebasing on public data."""
    p.require(copies >= 2, 'append fixture needs at least two copies')
    first = document(residue)
    source = p.serialize_mesh(first)
    table = append.parse(source)
    policy = p.serialize_policy(first)
    parts, places, meshes = append.read_r4pw(policy)
    addition_doc = document(first_indexed=appended_indexed)
    addition = append.parse(p.serialize_mesh(addition_doc))
    more_parts, more_places, more_meshes = append.read_r4pw(p.serialize_policy(addition_doc))
    for _ in range(copies - 1):
        table = append.append_tables(table, addition)
        rebased = []
        for row in more_places:
            values = list(p.PW_PLACE.unpack(row))
            values[0] += meshes
            values[1] += len(places)
            rebased.append(p.PW_PLACE.pack(*values))
        parts += more_parts
        places += rebased
        meshes += more_meshes
    return append.serialize(table), append.write_r4pw(parts, places, meshes)


def append_files(residue=None, appended_indexed=False, copies=2):
    return companions(*appended_raw(residue, appended_indexed, copies))


def strip_group_files():
    """Actual append -> actual ps2_strip_groups CLI, matching the owner chain."""
    mesh, policy = appended_raw(copies=3)
    with tempfile.TemporaryDirectory(prefix='b11-index-groups-') as td:
        folder = Path(td)
        src, side = folder/'source.re4mesh', folder/'source.r4pw'
        out, groups = folder/'groups.re4mesh', folder/'groups.r4sg'
        src.write_bytes(mesh)
        side.write_bytes(policy)
        command = [sys.executable, str(p.TOOLS/'ps2_strip_groups.py'),
                   str(src), str(side), str(out), str(groups), '--groups', '4']
        subprocess.run(command, check=True, capture_output=True)
        p.require(src.read_bytes() == mesh and side.read_bytes() == policy,
                  'strip-group fixture mutated its source')
        result = out.read_bytes()
        before, after = append.parse(mesh), append.parse(result)
        p.require([r[1] for r in before['meshlet']] == [r[1] for r in after['meshlet']],
                  'strip-group fixture unexpectedly moved index spans')
        return companions(result, policy, groups.read_bytes())


def reordered_files():
    """Build13's disjoint-span permutation principle, with distinct commands."""
    doc = document()
    doc['commands'][2]['strips'][0] = [4, 3, 2, 2, 1, 0]
    mesh, policy = p.serialize_mesh(doc), p.serialize_policy(doc)
    table = append.parse(mesh)
    i, j = 0, 2
    first, second = table['meshlet'][i], table['meshlet'][j]
    p.require(not (first[4] & 0x8000 or second[4] & 0x8000) and first[2] == second[2],
              'permutation fixture needs equal plain spans')
    a, b, size = first[1], second[1], first[2]
    data = bytearray(table['index'])
    p.require(data[a:a+size] != data[b:b+size], 'permutation commands must be distinct')
    data[a:a+size], data[b:b+size] = data[b:b+size], data[a:a+size]
    first[1], second[1] = b, a
    table['index'] = bytes(data)
    return companions(append.serialize(table), policy)


def zero_gap_files():
    """Leading, interior and trailing zero gaps with unchanged typed records."""
    doc = document()
    table = append.parse(p.serialize_mesh(doc))
    # Preserve even starts for indexed pools; all offsets move by four bytes.
    table['index'] = bytes(4) + table['index'] + bytes(7)
    for rec in table['meshlet']:
        rec[1] += 4
    return companions(append.serialize(table), p.serialize_policy(doc))


def suites():
    """Small representative real-Blender gates; host tests cover the sweep."""
    return [('append_plain', append_files),
            ('append_indexed', lambda: append_files(residue=1, appended_indexed=True)),
            ('append_strip_groups', strip_group_files),
            ('reordered_spans', reordered_files),
            ('zero_gaps', zero_gap_files)]


def spans(mesh):
    table = append.parse(mesh)
    return [(r[1], r[1] + r[2] + (2*r[3] if r[4] & 0x8000 else 0))
            for r in table['meshlet']]


def gaps(mesh):
    table = append.parse(mesh)
    at, result = 0, []
    for lo, hi in sorted(spans(mesh)):
        if lo > at:
            result.append((at, lo))
        at = max(at, hi)
    if at < len(table['index']):
        result.append((at, len(table['index'])))
    return result
