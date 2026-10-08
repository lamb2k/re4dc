#!/usr/bin/env python3
"""Prepare inventory herb/fish color/mask pairs and add them to an existing texture pack.

prepare_inventory_pairs.py SOURCE_TREE BASE_TEX_PAK NEW_OUTPUT_DIRECTORY

The individual color and mask textures do not satisfy native_model's combined
material lookup. Keep the exact source identities and all existing pack entries.
Outputs remain private assets; the tool refuses to reuse an output directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from prepare_native_ui import prepare_model_pairs
sys.path.insert(0, str(Path(__file__).resolve().parent / 'd367'))
import texpack

PAIRS = [
    {'color': 'b13109ae-0cd95eb5', 'mask': '1831e0c4-92be8b2a'},
    {'color': 'f5450d3b-e9eaa2b7', 'mask': '1831e0c4-92be8b2a'},
    # Yellow Herb case foliage and the shared Black Bass / Large Bass case model.
    {'color': '759e896a-2b7fe2da', 'mask': '1831e0c4-92be8b2a'},
    {'color': 'bbb1a3cf-7b1f8f5b', 'mask': '9671c5c2-d80b9174'},
    # Examine models use separate, higher-resolution source textures.
    {'color': '56f9ee72-63f425d0', 'mask': '7eb7154f-ef1ce650'},
    {'color': '74f9458a-1c357ea3', 'mask': '7eb7154f-ef1ce650'},
    {'color': '63ddc827-0a23cdd0', 'mask': '7eb7154f-ef1ce650'},
    {'color': '2d1f80f9-e3b5f041', 'mask': '10592447-b81a849d'},
]
SOURCE_FILES = ['ss/eng/ss_pzzl.dat', 'ss/item/idm006.tpl', 'ss/item/idm019.tpl',
                'ss/item/idm01c.tpl', 'ss/item/idm095.tpl', 'ss/item/idm097.tpl']


def packages(blob):
    count, _ = texpack.verify(blob)
    result = {}
    for i in range(count):
        crc, fnv, offset, size = struct.unpack_from('<4I', blob, 2048 + i * 16)
        result[(crc, fnv)] = blob[offset:offset + size]
    return result


def prepare(source, base, output):
    original = base.read_bytes()
    old = packages(original)
    output.mkdir(parents=True, exist_ok=False)
    pairs = prepare_model_pairs(source, SOURCE_FILES, PAIRS, output / 'pairs')
    combined = dict(old)
    for entry in pairs:
        key = tuple(int(word, 16) for word in entry['key'].split('-'))
        texpack.add(combined, key, (output / 'pairs' / (entry['key'] + '.re4tex')).read_bytes(), 'inventory pair')
    blob, count = texpack.build(combined)
    check = packages(blob)
    assert all(check[k] == value for k, value in old.items())
    assert len(check) == count
    (output / 'tex.pak').write_bytes(blob)
    report = dict(base_sha256=hashlib.sha256(original).hexdigest(), base_count=len(old),
                  count=count, added=count-len(old), bytes=len(blob),
                  sha256=hashlib.sha256(blob).hexdigest(), pairs=pairs,
                  original_entries_byte_identical=True)
    (output / 'inventory-pairs.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('base', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = prepare(args.source, args.base, args.output)
    print('inventory pairs: %d -> %d textures; existing entries unchanged; %s' %
          (report['base_count'], report['count'], report['sha256']))


if __name__ == '__main__':
    main()
