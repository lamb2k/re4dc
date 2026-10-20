#!/usr/bin/env python3
"""Prepare an opt-in complete ammo-digit preload set using existing resident.bin tooling.

Inputs and generated data stay private. Does not modify source lists, source disc or recipes.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[5]
TOOLS = ROOT / 'port/dreamcast/tools'
sys.path.insert(0, str(TOOLS))
import vq_native_ui


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def records(data):
    if len(data) % 512:
        raise ValueError('resident file must use complete 512-byte pieces')
    out = []
    for off in range(0, len(data), 16):
        row = struct.unpack_from('<4H2I', data, off)
        if any(row):
            if not row[1] or not row[2]:
                raise ValueError('non-padding record has no dimensions')
            out.append(row)
    return out


def prepare(resident, pack, audit, output):
    report = json.loads(audit.read_text())
    if report.get('schema') != 're4-transition-read-audit-v1':
        raise ValueError('unexpected selected-source audit schema')
    required_sources = {'src/game/cockpit.cpp', 'src/game/id_tex.cpp', 'src/game/id_sys.cpp', 'include/id_sys.h'}
    pins = {r['path']: r['sha256'] for r in report['source']}
    for source in sorted(required_sources):
        if source not in pins or sha(ROOT / source) != pins[source]:
            raise ValueError(f'HUD source differs from audited identity: {source}')
    digit_rows = {r['pattern']: r for r in report['effect_texture_keys']
                  if r.get('role') == 'hud-ammo-digit' and r['archive'] == 'etc/core.das'
                  and r['tex_id'] == 0x27 and r['source_uses_pattern'] and 0 <= r['pattern'] <= 9}
    if set(digit_rows) != set(range(10)):
        raise ValueError('audit does not resolve all ten decimal digit patterns')
    before = resident.read_bytes()
    base = records(before)
    core = {(r[4], r[5]) for r in base if r[0] == 0}
    extras, verified = [], []
    with pack.open('rb') as stream:
        head = stream.read(2048)
        if head[:8] != b'RE4PAK1\0':
            raise ValueError('invalid texture pack magic')
        version, count, index_at, data_at, checksum = struct.unpack_from('<5I', head, 8)
        if version != 1 or not 1 <= count <= 8192 or index_at != 2048:
            raise ValueError('invalid texture pack bounds')
        index_size = ((count * 16 + 2047) // 2048) * 2048
        index = stream.read(index_size)
        if len(index) != index_size or zlib.crc32(index) != checksum:
            raise ValueError('texture pack index CRC mismatch')
        entries = [struct.unpack_from('<4I', index, i * 16) for i in range(count)]
        keys = [(r[0], r[1]) for r in entries]
        if keys != sorted(set(keys)) or data_at < 2048 + index_size:
            raise ValueError('invalid sorted texture index')
        by_key = {r[:2]: r[2:] for r in entries}
        for digit in range(10):
            row = digit_rows[digit]
            key = tuple(int(x, 16) for x in row['key'].split('-'))
            off, size = by_key[key]
            if off < data_at or off % 2048 or off + size > pack.stat().st_size:
                raise ValueError('digit texture extent outside pack')
            if (off, size) != (row['texture_pack']['offset'], row['texture_pack']['bytes']):
                raise ValueError('digit texture extent differs from selected audit')
            stream.seek(off)
            blob = stream.read(size)
            pw, ph, fmt, flags, texels = vq_native_ui.read_package(blob)
            if (row['width'], row['height'], row['format']) != (16, 24, 9) or (pw, ph) != (16, 32):
                raise ValueError('unexpected source/native digit dimensions')
            verified.append({'digit': digit, 'key': row['key'], 'package_sha256': hashlib.sha256(blob).hexdigest(),
                             'payload_bytes': len(texels) * 2, 'already_core': key in core})
            if key not in core:
                extras.append((0, row['width'], row['height'], row['format'], *key))
    if len(core) + len(extras) > 16:
        raise ValueError('expanded core list exceeds current runtime core-key capacity')
    output.mkdir(parents=True, exist_ok=False)
    lists = output / 'lists'
    lists.mkdir()
    grouped = defaultdict(list)
    for row in base:
        grouped[row[0]].append(row)
    grouped[0].extend(extras)
    for room, rows in grouped.items():
        (lists / f'r{room:03x}.tsv').write_text('key\twidth\theight\tfmt\truns\n' + ''.join(
            f'{crc:08x}-{fnv:08x}\t{w}\t{h}\t{fmt}\t1\n' for _, w, h, fmt, crc, fnv in rows))
    spec = importlib.util.spec_from_file_location('existing_resident_keys', TOOLS / 'd367/vram/resident_keys.py')
    existing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(existing)
    candidate = output / 'resident.bin'
    existing.cmd_pack([str(candidate), *(str(p) for p in sorted(lists.glob('r*.tsv')))])
    after = records(candidate.read_bytes())
    if Counter(after) != Counter(base) + Counter(extras):
        raise AssertionError('candidate changed records other than the missing core digits')
    if resident.read_bytes() != before:
        raise AssertionError('source resident file changed')
    receipt = {'schema': 're4-hud-digit-residency-v1', 'source_resident_sha256': hashlib.sha256(before).hexdigest(),
               'audit_sha256': sha(audit), 'source_index_sha256': hashlib.sha256(index).hexdigest(),
               'candidate_sha256': sha(candidate), 'source_bytes': len(before), 'candidate_bytes': candidate.stat().st_size,
               'added_records': len(extras), 'added_vram_payload_bytes': sum(v['payload_bytes'] for v in verified if not v['already_core']),
               'core_key_count': len(core) + len(extras), 'digits': verified,
               'scope': 'offline optional candidate only; actual entry admission, texture-slot/VRAM/memory and target gates remain open'}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('digits',)}, indent=2))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resident', type=Path, required=True)
    parser.add_argument('--tex-pack', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.resident, args.tex_pack, args.audit, args.out)
