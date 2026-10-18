#!/usr/bin/env python3
"""Add exact runtime overlay function ranges using byte-bound pre-strip ELF sections."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess


def sections(data):
    assert data[:6] == b'\x7fELF\x01\x01'
    offset = struct.unpack_from('<I', data, 32)[0]
    size, count, names_index = struct.unpack_from('<HHH', data, 46)
    rows = [struct.unpack_from('<10I', data, offset + i * size) for i in range(count)]
    names = rows[names_index]
    names = data[names[4]:names[4] + names[5]]
    return {names[r[0]:].split(b'\0', 1)[0].decode(): r for r in rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full-elf', type=Path, required=True)
    p.add_argument('--runtime-manifest', type=Path, required=True)
    p.add_argument('--program', type=Path, required=True)
    p.add_argument('--symbols', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--nm', default='/opt/toolchains/dc/sh-elf/bin/sh-elf-nm')
    a = p.parse_args()
    assert not a.out.exists()
    data = a.full_elf.read_bytes()
    secs = sections(data)
    manifest = json.loads(a.runtime_manifest.read_text())
    all_symbols = subprocess.check_output([a.nm, '-n', '-S', '-C', str(a.full_elf)], text=True)
    original = a.symbols.read_text()
    ranges = [tuple(int(v, 16) for v in line.split('\t')[:2]) for line in original.splitlines()[1:]]
    additions, proofs = [], []
    for overlay in manifest['overlays']:
        module = overlay['module']
        payload = (a.program / (module + '.ovl')).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == overlay['program_sha256']
        header = struct.unpack_from('<16I', payload)
        matched = [(n, s) for n, s in secs.items() if n.lower() == '.ovl_' + module.lower()]
        assert len(matched) == 1
        section_name, section = matched[0]
        assert section[3] == header[4] and section[5] == header[2]
        assert data[section[4]:section[4] + section[5]] == payload[64:64 + header[2]], module
        base = int(overlay['runtime_base'], 16)
        found = {}
        for line in all_symbols.splitlines():
            fields = line.split(None, 3)
            if len(fields) == 4 and fields[2] in 'tTwW':
                address, size, _, name = fields
                address, size = int(address, 16), int(size, 16)
            elif len(fields) >= 3 and fields[1] in 'tTwW':
                address, _, name = line.split(None, 2)
                address, size = int(address, 16), 0
            else:
                continue
            if not header[4] <= address < header[4] + header[2]:
                continue
            assert address + size <= header[4] + header[2]
            start = base + address - header[4]
            assert not any(lo <= start < hi for lo, hi in ranges)
            owner = 2 if re.fullmatch(r'cEm[0-9a-fA-F]{2}::move\(\)', name) else 0
            row = dict(start=start, end=start + size, owner=owner, barrier=0, name=name, module=module)
            old = found.get(start)
            if old is None or size > old['end'] - old['start'] or owner > old['owner']:
                found[start] = row
        additions.extend(found.values())
        proofs.append(dict(module=module, section=section_name, symbols=len(found), section_bytes_exact=True))
    output = original.splitlines() + [f"{r['start']:x}\t{r['end']:x}\t{r['owner']}\t0\t{r['name']}" for r in additions]
    output = output[:1] + sorted(output[1:], key=lambda s: int(s.split('\t')[0], 16))
    assert len({int(s.split('\t')[0], 16) for s in output[1:]}) == len(output) - 1
    a.out.write_text('\n'.join(output) + '\n')
    symbol_json = json.loads(a.symbols.with_suffix('.json').read_text())
    symbol_json['symbols'] += [dict(r, size=r['end'] - r['start']) for r in additions]
    symbol_json['symbols'].sort(key=lambda r: r['start'])
    for index, row in enumerate(symbol_json['symbols']):
        row['symbol'] = index + 1
    symbol_json['runtime_overlay_symbols'] = True
    a.out.with_suffix('.json').write_text(json.dumps(symbol_json, indent=2) + '\n')
    a.out.with_suffix('.proof.json').write_text(json.dumps(dict(full_elf_sha256=hashlib.sha256(data).hexdigest(),
        runtime_manifest_sha256=hashlib.sha256(a.runtime_manifest.read_bytes()).hexdigest(),
        input_symbols_sha256=hashlib.sha256(a.symbols.read_bytes()).hexdigest(), proofs=proofs,
        added_symbols=additions, limitation='Zero-size symbols remain unknown; no guessed extents.'), indent=2) + '\n')
    print(f'Added {len(additions)} byte-bound runtime overlay symbols')


if __name__ == '__main__':
    main()
