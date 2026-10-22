#!/usr/bin/env python3
"""Compose the reviewed opaque cohorts; no pack, image or programme writes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import zlib


def rows(path):
    return [s.strip() for s in path.read_text().splitlines() if s.lstrip().startswith('{')]


def numbers(row):
    return [int(s, 0) for s in re.findall(r'(0x[0-9a-fA-F]+|\d+)U', row)]


def fnv(data):
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cohort', type=Path, action='append', required=True)
    ap.add_argument('--receipt', type=Path, required=True)
    a = ap.parse_args()
    here = Path(__file__).resolve().parent
    relative = 'port/dreamcast/tools/d367/texture_rect21/scoped_representations.inc'
    original = subprocess.check_output(['git', 'show', '0425534d848973c1dae3ab960d0006ac9afcf363:' + relative], text=True)
    oldrows = {s.strip() for s in original.splitlines() if s.lstrip().startswith('{')}
    final_rows = rows(a.cohort[-1] / 'proposed_scoped_representations_combined650.inc')
    assert len(oldrows) == 36 and len(final_rows) == 650
    assert oldrows <= set(final_rows)
    final_rows.sort(key=lambda r: tuple(numbers(r)[:2]))
    keys = [tuple(numbers(r)[:2]) for r in final_rows]
    assert len(set(keys)) == 650
    resolved = {}
    certs = {}
    lineage = []
    for cohort in a.cohort:
        plan = json.loads((cohort / 'world-proposals.json').read_text())
        certrows = rows(cohort / 'proposed_provenance_certificates.inc')
        current_certs = {numbers(r)[0]: r for r in certrows}
        assert len(current_certs) == len(certrows) == len(plan['worlds'])
        for row in plan['worlds']:
            room = row['room']
            room_id = int(room[1:], 16)
            path = cohort / 'proposed-worlds' / row['path']
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            assert digest == row['candidate_sha256'] and len(data) == row['bytes']
            if room in resolved:
                assert row['parent_sha256'] == resolved[room]['candidate_sha256']
            magic, version, placements, parts, meshes, crc, zero1, zero2 = struct.unpack_from('<4s7I', data)
            assert (magic, version, zero1, zero2) == (b'R4PW', 1, 0, 0)
            assert (placements, parts, meshes) == (row['placements'], row['parts'], row['meshes'])
            assert len(data) == 32 + 16 * parts + 52 * placements
            assert zlib.crc32(data[32:]) == crc == row['physical_body_crc']
            assert fnv(data) == row['physical_file_fnv']
            expected = [room_id, len(data), placements, parts, meshes, crc, fnv(data), row['mesh_crc'], row['mesh_bytes'], row['original_source_crc']]
            assert numbers(current_certs[room_id]) == expected
            resolved[room] = dict(row, selected_path=str(path))
            certs[room_id] = current_certs[room_id]
        lineage.append(dict(cohort=str(cohort), worlds=len(plan['worlds'])))
    assert len(resolved) == 29 and len(certs) == 29
    held = {'r11f', 'r200'}
    selected = {k: v for k, v in sorted(resolved.items()) if k not in held}
    assert len(selected) == 27
    table = '// Private WORLD_RECT21 candidate: 650 exact-key descriptors, sorted unsigned CRC/FNV.\n' + '\n'.join(final_rows) + '\n'
    certificate = '// Private physical certificates: 27 rooms; r11f/r200 remain held.\n' + '\n'.join(certs[int(k[1:], 16)] for k in selected) + '\n'
    receipt = dict(status='SOURCE_SELECTION_ONLY_NO_PACK_PROGRAMME_OR_GUEST', descriptors=650, original_descriptors_unchanged=36,
                   lineage=lineage, selected=selected, held={k: resolved[k] for k in sorted(held)},
                   table_sha256=hashlib.sha256(table.encode()).hexdigest(), certificate_sha256=hashlib.sha256(certificate.encode()).hexdigest())
    assert not a.receipt.exists(), 'receipt must be new'
    (here / 'scoped_representations.inc').write_text(table)
    (here / 'provenance_certificates.inc').write_text(certificate)
    with a.receipt.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: receipt[k] for k in ('status', 'descriptors', 'original_descriptors_unchanged', 'table_sha256', 'certificate_sha256')}))


if __name__ == '__main__':
    main()
