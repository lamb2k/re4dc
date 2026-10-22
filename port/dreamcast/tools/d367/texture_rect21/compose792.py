#!/usr/bin/env python3
"""Compose sealed alpha additions into the isolated default-off source candidate.

Reads private packages/worlds only. Writes source tables and a new qualification
receipt; it cannot write packages, images or programmes.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

from compose650 import rows, numbers, fnv
from coupled_sidecars import package, world, key

BASE = '33504b9df434b82cd92e7bab3bb4630663a72ddd'
REL = 'port/dreamcast/tools/d367/texture_rect21/'
PACKET_SEAL = '9b388f786df86266145c3d77c127036281540cd0c4d75ab8c30b26d859ca3ade'
PRIOR_RECEIPT = '2a2f585ddf427c4e16505d55fe96b2f979076053c4942d119bb97cb92af04e8b'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(spec):
    data = Path(spec['path']).read_bytes()
    require(sha(data) == spec['sha256'], 'hash drift: ' + spec['path'])
    if 'bytes' in spec:
        require(len(data) == spec['bytes'], 'size drift: ' + spec['path'])
    return data


def git_source(name):
    return subprocess.check_output(['git', 'show', BASE + ':' + REL + name])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--packet', type=Path, required=True)
    ap.add_argument('--prior-receipt', type=Path, required=True)
    ap.add_argument('--receipt', type=Path, required=True)
    a = ap.parse_args()
    here = Path(__file__).resolve().parent
    require(not a.receipt.exists(), 'preserve existing receipt')
    seal = (a.packet / 'SHA256SUMS.txt').read_bytes()
    require(sha(seal) == PACKET_SEAL, 'packet seal')
    packet_pins = {}
    for line in seal.decode().splitlines():
        digest, relative = line.split('  ', 1)
        p = a.packet / relative
        require(p.resolve().is_relative_to(a.packet.resolve()), 'packet path escape')
        require(sha(p.read_bytes()) == digest, 'packet member drift: ' + relative)
        packet_pins[relative] = digest
    additions = json.loads((a.packet / 'ADDITIONS142.json').read_text())
    lineage = json.loads((a.packet / 'WORLD792-LINEAGE.json').read_text())
    for spec in additions['producer_seals']:
        pinned(spec)
    metrics = json.loads(pinned(additions['corrected_metric_bindings']))
    policy = json.loads(pinned(additions['source_policy_proof']))
    prior_data = a.prior_receipt.read_bytes()
    require(sha(prior_data) == PRIOR_RECEIPT, 'root650 selection identity')
    prior = json.loads(prior_data)
    require(len(prior['selected']) == 27 and set(prior['held']) == {'r11f', 'r200'}, 'prior holds')
    old_text = git_source('scoped_representations.inc').decode()
    old_rows = {r.strip() for r in old_text.splitlines() if r.lstrip().startswith('{')}
    final_text = pinned(lineage['table']).decode()
    final_rows = [r.strip() for r in final_text.splitlines() if r.lstrip().startswith('{')]
    require(len(old_rows) == 650 and len(final_rows) == 792 and old_rows <= set(final_rows), '650 descriptor preservation')
    final_rows.sort(key=lambda r: tuple(numbers(r)[:2]))
    table = {tuple(numbers(r)[:2]): r for r in final_rows}
    require(len(table) == 792, 'duplicate keys')
    new_rows = set(final_rows) - old_rows
    selected = additions['selected']
    require(len(selected) == len(new_rows) == 142, 'addition census')
    metric_keys = {r['scoped_key']: r['candidate_sha256'] for r in metrics['selected']}
    require(len(metric_keys) == 142, 'corrected metric census')
    policy_keys = {r['scoped_key']: r for r in policy['records']}
    require(len(policy_keys) == 142, 'policy census')
    world_bytes = {}
    cert_rows = rows(Path(lineage['certificates']['path']))
    pinned(lineage['certificates'])
    certs = {numbers(r)[0]: r for r in cert_rows}
    require(len(certs) == len(cert_rows) == len(lineage['worlds']) == 29, 'world certificate census')
    resolved = {}
    changed_records = 0
    for spec in lineage['worlds']:
        room = Path(spec['path']).parent.name
        require(room not in resolved, 'duplicate world room')
        data = pinned(dict(path=spec['absolute_path'], sha256=spec['sha256'], bytes=spec['bytes']))
        parent = pinned(dict(path=spec['parent650_lineage'], sha256=spec['parent650_sha256']))
        prior_row = (prior['selected'] | prior['held'])[room]
        require(spec['parent650_sha256'] == prior_row['candidate_sha256'], 'unresolved650 parent: ' + room)
        h, parts, placements = world(data)
        ph, old_parts, old_placements = world(parent)
        require(h[:5] == ph[:5] and h[6:] == ph[6:] and placements == old_placements, 'world geometry/header/placement drift: ' + room)
        require((h[2], h[3], h[4], h[5]) == (spec['placements'], spec['parts'], spec['meshes'], spec['physical_body_crc']), 'world counts/CRC')
        require(fnv(data) == spec['physical_file_fnv'], 'world FNV')
        for p, q in zip(old_parts, parts):
            require(p[2:] == q[2:], 'non-key part drift: ' + room)
            changed_records += p[:2] != q[:2]
        expected = [int(room[1:], 16), len(data), h[2], h[3], h[4], h[5], fnv(data), spec['mesh_crc'], spec['mesh_bytes'], spec['canonical_source_crc']]
        require(numbers(certs[int(room[1:], 16)]) == expected, 'certificate tuple: ' + room)
        require(spec['mesh_sha256'] == prior_row['mesh_sha256'] and spec['mesh_crc'] == prior_row['mesh_crc'] and spec['mesh_bytes'] == prior_row['mesh_bytes'], 'geometry identity lineage')
        world_bytes[room] = (parts, old_parts)
        resolved[room] = dict(spec, selected_path=spec['absolute_path'], candidate_sha256=spec['sha256'])
    aliases = set()
    class_counts = Counter()
    semantic = Counter()
    for spec in selected:
        k = tuple(int(s, 16) for s in spec['scoped_key'].split('-'))
        require(k in table and table[k] in new_rows, 'addition key not new')
        expected = [*k, *spec['logical'], *spec['physical'], spec['format'], spec['flags'], spec['payload_type'], spec['payload_bytes'], spec['body_crc32']]
        require(numbers(table[k]) == expected, 'descriptor tuple: ' + spec['scoped_key'])
        scales = table[k].split('},', 1)[1].rstrip('},').split(',')
        require([float(s.rstrip('f')) for s in scales] == spec['uv_scale'], 'UV scale')
        blob = pinned(dict(path=spec['absolute_path'], sha256=spec['sha256'], bytes=spec['bytes']))
        h, t = package(blob)
        require(blob[48:144].hex() == spec['descriptor_hex'] and h[8] == spec['body_crc32'], 'actual package descriptor/CRC')
        require(list(t[1:4]) == [*spec['physical'], spec['format']] and list(t[5:8]) == [spec['payload_bytes'], spec['flags'], spec['payload_type']], 'actual package fields')
        require(metric_keys[spec['scoped_key']] == spec['sha256'], 'metric identity')
        require(sha(Path(spec['host_receipt_path']).read_bytes()) == spec['host_receipt_sha256'], 'host receipt identity')
        policy_refs = {(r['room'], r['part']): r for r in policy_keys[spec['scoped_key']]['refs']}
        require(len(policy_refs) == len(spec['aliases']), 'policy alias census')
        semantic[spec['semantic_source']] += 1
        original_key = tuple(int(s, 16) for s in spec['original_key'].split('-'))
        for alias in spec['aliases']:
            at = (alias['room'], alias['part'])
            require(at not in aliases, 'duplicate alias')
            aliases.add(at)
            parts, old_parts = world_bytes[alias['room']]
            p, q = old_parts[alias['part']], parts[alias['part']]
            require(p[:2] == original_key and q[:2] == k, 'actual world key mapping')
            require(list(q[2:]) == [*spec['logical'], alias['render_pass'], alias['cull'], alias['texture'], alias['flags']], 'actual material tuple')
            pr = policy_refs[at]
            require(pr['pass_'] == alias['render_pass'] and pr['acceptance'] == alias['policy_acceptance'], 'policy reference drift')
            if pr['shipped_class'] is None:
                require(pr['acceptance'] == 'INTENTIONAL_UNLISTED_BEHAVIOR_EQUIVALENT', 'unlisted must remain distinct')
                class_counts['intentional_unlisted'] += 1
            else:
                require(pr['selected_candidate_class'] == pr['shipped_class'], 'shipped class changed')
                class_counts['shipped'] += 1
    require(changed_records == len(aliases) == 508, 'complete key-only change census')
    require(class_counts == {'shipped': 468, 'intentional_unlisted': 40}, 'shipped/unlisted census')
    require(sorted(semantic.values()) == [7, 16, 119], 'semantic cohort census')
    chosen = {k: v for k, v in sorted(resolved.items()) if k not in {'r11f', 'r200'}}
    require(len(chosen) == 27, 'selected certificate census')
    table_text = '// Private WORLD_RECT21 candidate: 792 exact-key descriptors, sorted unsigned CRC/FNV.\n' + '\n'.join(final_rows) + '\n'
    cert_text = '// Private physical certificates: 27 rooms; r11f/r200 remain held.\n' + '\n'.join(certs[int(k[1:], 16)] for k in chosen) + '\n'
    receipt = dict(status='SOURCE_SELECTION_ONLY_NO_PACK_PROGRAMME_OR_GUEST', base_source=BASE, packet_seal_sha256=PACKET_SEAL, packet_members=packet_pins,
                   descriptors=792, prior_descriptors_unchanged=650, additions=142, semantic_sources=dict(semantic), aliases=len(aliases), class_aliases=dict(class_counts),
                   selected=chosen, held={k: resolved[k] for k in ('r11f', 'r200')}, non_key_material_geometry_placements_unchanged=True,
                   table_sha256=sha(table_text.encode()), certificate_sha256=sha(cert_text.encode()), corrected_metric_binding=additions['corrected_metric_bindings'],
                   performance_acceptance=False, physical_acceptance=False, world_rect21_default=0)
    (here / 'scoped_representations.inc').write_text(table_text)
    (here / 'provenance_certificates.inc').write_text(cert_text)
    with a.receipt.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: receipt[k] for k in ('status', 'descriptors', 'prior_descriptors_unchanged', 'aliases', 'class_aliases', 'table_sha256', 'certificate_sha256')}))


if __name__ == '__main__':
    main()
