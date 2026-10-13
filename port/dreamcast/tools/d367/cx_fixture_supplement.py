#!/usr/bin/env python3
"""Add qualified composite texture dependencies to new immutable fixture variants."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

import texpack


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--supplement', type=Path, required=True)
    ap.add_argument('--fixture', type=Path, action='append', required=True)
    ap.add_argument('--suffix', default='pairfixed')
    ap.add_argument('--arm-tool', type=Path, required=True)
    ap.add_argument('--candidate-dir', type=Path, required=True)
    ap.add_argument('--arm-label', required=True)
    ap.add_argument('--report', type=Path, required=True)
    a = ap.parse_args()
    supplement = json.loads(a.supplement.read_text())
    if supplement['schema'] != 're4dc-composite-pair-staging/1':
        raise ValueError('unsupported supplement schema')
    if not re.fullmatch(r'[a-z0-9-]+', a.suffix):
        raise ValueError('invalid variant suffix')
    pairs = {p['disc_path']: p for p in supplement['pairs']}
    for destination, path in supplement['replace'].items():
        if not re.fullmatch(r'dc/tex/[0-9a-f]/[0-9a-f]{8}-[0-9a-f]{8}\.re4tex', destination):
            raise ValueError('supplement is not a texture dependency')
        pair = pairs[destination]
        if sha(path) != pair['sha256'] or pair['chosen']['runtime_parser'] != 'PASS':
            raise ValueError('unqualified or changed composite: ' + destination)
    results = []
    for source in a.fixture:
        data = json.loads(source.read_text())
        room = data.get('provenance', {}).get('cx_room', {}).get('room')
        if room != supplement['room']:
            raise ValueError('fixture/supplement room mismatch')
        pack = Path(data['replace']['dc/tex.pak'])
        blob = pack.read_bytes()
        count, _ = texpack.verify(blob)
        index = {'%08x-%08x' % struct.unpack_from('<2I', blob, 2048+i*16):
                 struct.unpack_from('<2I', blob, 2048+i*16+8) for i in range(count)}
        winners = []
        for destination, path in supplement['replace'].items():
            pair = pairs[destination]
            member = index.get(pair['key'])
            if member:
                offset, size = member
                if blob[offset:offset+size] != Path(path).read_bytes():
                    raise ValueError('shared pack shadows selected composite: ' + destination)
            data['replace'][destination] = path
            if destination in data.get('remove', []):
                data['remove'].remove(destination)
            winners.append(dict(destination=destination, source=path, sha256=sha(path),
                                winner='packed-identical' if member else 'loose'))
        data.setdefault('provenance', {})['cx_texture_supplement'] = dict(
            source_fixture=str(source), source_fixture_sha256=sha(source),
            supplement=str(a.supplement), supplement_sha256=sha(a.supplement),
            acceptance=supplement['acceptance'])
        stem = source.name.removesuffix('.unarmed.json')
        unarmed = source.with_name(stem+'.'+a.suffix+'.unarmed.json')
        armed = source.with_name(stem+'.'+a.suffix+'.armed.json')
        if unarmed.exists() or armed.exists():
            raise ValueError('variant already exists; use a new suffix')
        unarmed.write_text(json.dumps(data, indent=2)+'\n')
        subprocess.run([sys.executable, str(a.arm_tool), str(unarmed), str(armed),
                        a.arm_label, '--candidate-dir', str(a.candidate_dir)], check=True,
                       stdout=subprocess.DEVNULL)
        final = json.loads(armed.read_text())
        missing = [k for k,p in final['replace'].items() if not Path(p).is_file()]
        if missing:
            raise ValueError('missing fixture sources: '+str(missing))
        results.append(dict(fixture=str(armed), sha256=sha(armed), winners=winners,
                            all_replace_sources_present=True, pack=str(pack), pack_sha256=sha(pack)))
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(dict(room=supplement['room'], fixtures=results,
        acceptance='STATIC_PATHS_ARM_AND_TEXTURE_WINNERS_ONLY'), indent=2)+'\n')
    print(a.report)


if __name__ == '__main__':
    main()
