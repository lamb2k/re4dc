#!/usr/bin/env python3
"""Prepare source-selected inventory color/mask pairs and add them to an existing texture pack.

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
    # Remaining source-selected pairs in the shipped case and Examine models.
    {'color': 'f31bdbc6-7a0e3b6b', 'mask': '336e45ac-57bc48ba'},  # ss/item/cap01.bin
    {'color': 'c99f0f7f-5d5d86d6', 'mask': '6ec92a00-e226f4ec'},  # ss/item/cap23.bin
    {'color': '9a934c76-66cee147', 'mask': 'ecdd9ea2-9e2d3131'},  # ss/item/idm00b.bin
    {'color': '805d1fd6-bf0f6c37', 'mask': '1eb96ee2-995437ed'},  # ss/item/idm0c9.bin
    {'color': 'aaa99386-c1bdc08d', 'mask': 'd2fce100-0cc9bbb1'},  # ss/item/idm0b9.bin
    {'color': '6bac9246-306c7737', 'mask': '2c5c6053-634e1bd1'},  # ss/item/idm012.bin
    {'color': '65a56d3b-152383d7', 'mask': '8875d0c1-43b14af9'},  # ss/item/idm083.bin
    {'color': '8af428a3-bd605103', 'mask': 'a34b1796-e3351b12'},  # ss/item/idm03d.bin
    {'color': '8583356d-86058f97', 'mask': '606d1783-cb908851'},  # ss/item/idm059.bin
    {'color': '59673067-85291d3f', 'mask': '83355e33-fe19f9ba'},  # ss/item/idm0c5.bin
    {'color': 'f8cf554c-6bd29597', 'mask': 'f34014af-6c86e97d'},  # ss/item/cap11.bin
    {'color': '0306756a-1dce75e1', 'mask': 'f5ff28e7-28f8d426'},  # ss/item/idm0a1.bin
    {'color': '85aa005c-95547029', 'mask': '6d09f151-29377e3c'},  # ss/item/cap13.bin
    {'color': 'b0d7774b-fb67a222', 'mask': 'def060b5-39932b29'},  # ss/item/cap04.bin
    {'color': 'd2d9b629-cf64d421', 'mask': 'df38bbdf-fe39d54f'},  # ss/item/idm056.bin
    {'color': '2e297834-f2f17c12', 'mask': 'be92de2c-4e1bdfdd'},  # ss/item/idm084.bin
    {'color': 'd0c4e7bb-64ada653', 'mask': '6ce67052-569cb5d7'},  # ss/item/idm093.bin
    {'color': '759774a3-d6e07998', 'mask': '85e3c61b-d0dc68b1'},  # ss/item/idm056.bin
    {'color': '0c053cea-f4312fb7', 'mask': '2c5c6053-634e1bd1'},  # ss/item/idm0d2.bin
    {'color': '3e9eb2f6-46b0243d', 'mask': '78153f4a-143a1bb1'},  # ss/item/idm060.bin
    {'color': '59def6bd-9c29fe8f', 'mask': '5eeecb43-c78ebb5f'},  # ss/item/idm057.bin
    {'color': 'd1a24207-6bd51d77', 'mask': '1a9c1add-af3ccd11'},  # ss/item/cap19.bin
    {'color': 'a12222d2-61130364', 'mask': '0d467a3e-6e8767a4'},  # ss/item/idm060.bin
    {'color': '815b3ef2-14b89777', 'mask': '606d1783-cb908851'},  # ss/item/idm05a.bin
    {'color': '953c0c44-e285a3de', 'mask': '07272ed5-596670cd'},  # ss/item/idm077.bin
    {'color': 'dc992a69-9f93ad93', 'mask': '55967e0e-09da0839'},  # ss/item/idm00c.bin
    {'color': 'f3664879-23dfb1d0', 'mask': '359d5ccd-f483ee01'},  # ss/item/idm0ba.bin
    {'color': '4b3506e5-235a23d5', 'mask': '6365df3a-4c98c215'},  # ss/item/cap24.bin
    {'color': '2ca6776b-da36ae34', 'mask': 'a10c3d6e-c0714001'},  # case:00c
    {'color': 'd2146a26-96788573', 'mask': '606d1783-cb908851'},  # ss/item/idm08a.bin
    {'color': 'd70585fe-4d6618c6', 'mask': '1773e961-7f839d31'},  # ss/item/idm02f.bin
    {'color': '7cebcdb5-9fb65cb7', 'mask': 'f80ff823-e41f9c51'},  # ss/item/idm012.bin
    {'color': 'd6bdebf7-6a9fcfed', 'mask': '43ddb5ec-34e2a4bb'},  # ss/item/idm061.bin
    {'color': '5b1a1461-fa5e3c28', 'mask': '2b28fdd5-71168a17'},  # ss/item/idm05f.bin
    {'color': '1cc133e5-41ddaa85', 'mask': '0d467a3e-6e8767a4'},  # ss/item/idm061.bin
    {'color': 'f6c7f258-0d5d2bb2', 'mask': '1e4d8a8c-15debbb1'},  # ss/item/idm0bb.bin
    {'color': 'babf0855-d6facda7', 'mask': '5b2ed733-0f75ee51'},  # ss/item/idm076.bin
    {'color': '21756192-53ddb102', 'mask': 'e187ff11-f5f63a54'},  # ss/item/idm0b8.bin
    {'color': 'd509b828-be4fe423', 'mask': '1eb96ee2-995437ed'},  # ss/item/idm0c7.bin
    {'color': '846b0a73-7f9dfd82', 'mask': '8875d0c1-43b14af9'},  # ss/item/idm074.bin
    {'color': '844f672a-4346bcc7', 'mask': '499eebd7-eab8c951'},  # ss/item/idm00b.bin
    {'color': 'e1928f6a-8e56fc50', 'mask': 'ea5e397a-fb7a12d6'},  # ss/item/idm00c.bin
    {'color': '0116e813-f738fba0', 'mask': '0d467a3e-6e8767a4'},  # ss/item/idm05f.bin
    {'color': '13bef74a-54010254', 'mask': 'cfa09746-346f9c73'},  # ss/item/cap15.bin
    {'color': '4f9681c1-0e2ba86b', 'mask': '359d5ccd-f483ee01'},  # ss/item/idm0b9.bin
    {'color': '784217d8-78f36373', 'mask': '78153f4a-143a1bb1'},  # ss/item/idm05f.bin
    {'color': 'fc5c505b-beab54c3', 'mask': '8b33a0ff-4f7d302b'},  # ss/item/cap03.bin
    {'color': '6661403e-78c3ad11', 'mask': '359d5ccd-f483ee01'},  # ss/item/idm0bb.bin
    {'color': '50a52f55-0ce01633', 'mask': '78153f4a-143a1bb1'},  # ss/item/idm061.bin
    {'color': '19115ce3-3f8adc77', 'mask': '606d1783-cb908851'},  # ss/item/idm05d.bin
    {'color': 'b91df28b-7d01d8b1', 'mask': '50a1d645-3b5e3fdb'},  # ss/item/idm092.bin
    {'color': '65533fe8-3ba3ab1f', 'mask': '052cbce7-40138a3d'},  # ss/item/cap05.bin
    {'color': 'aca156f9-b1cc5a53', 'mask': '9b493acb-01eefe27'},  # ss/item/cap22.bin
    {'color': '31b56d6f-e2d2f26f', 'mask': '4e8e07a6-7243cf12'},  # case:00c
    {'color': '237ce925-3825e6de', 'mask': '11c01640-5a8ff820'},  # ss/item/cap21.bin
    {'color': 'd765330e-f33b4113', 'mask': '1eb96ee2-995437ed'},  # ss/item/idm0c8.bin
    {'color': 'd9bc1cf6-9723d657', 'mask': '9cdf731a-7a764374'},  # ss/item/idm0a1.bin
    {'color': '6822e575-ed9b1eb7', 'mask': '2c5c6053-634e1bd1'},  # ss/item/idm0d3.bin
    {'color': '433d469b-6fee34e2', 'mask': 'b310c742-30ab0fd0'},  # ss/item/idm082.bin
    {'color': '42c73632-7e69a797', 'mask': '6727b719-66232948'},  # ss/item/cap04.bin
    {'color': '2fda884d-62f1fff7', 'mask': '2c5c6053-634e1bd1'},  # ss/item/idm0d4.bin
    {'color': '6935e9cd-7679ca78', 'mask': '322135f4-4dd1989e'},  # ss/item/idm060.bin
    {'color': 'bc8df84e-cbe84d06', 'mask': 'ce376214-c87c31af'},  # ss/item/idm093.bin
    {'color': '44abadcc-b9c12412', 'mask': 'b4a454c6-ec039bb1'},  # ss/item/idm0ba.bin
    {'color': 'd7b12975-0bdbc437', 'mask': '20f7d86b-e40ed511'},  # ss/item/idm096.bin
]
SOURCE_FILES = [
    'ss/eng/ss_pzzl.dat',
    'ss/item/cap01.tpl',
    'ss/item/cap03.tpl',
    'ss/item/cap04.tpl',
    'ss/item/cap05.tpl',
    'ss/item/cap11.tpl',
    'ss/item/cap13.tpl',
    'ss/item/cap15.tpl',
    'ss/item/cap19.tpl',
    'ss/item/cap21.tpl',
    'ss/item/cap22.tpl',
    'ss/item/cap23.tpl',
    'ss/item/cap24.tpl',
    'ss/item/idm006.tpl',
    'ss/item/idm00b.tpl',
    'ss/item/idm00c.tpl',
    'ss/item/idm012.tpl',
    'ss/item/idm019.tpl',
    'ss/item/idm01c.tpl',
    'ss/item/idm02f.tpl',
    'ss/item/idm03d.tpl',
    'ss/item/idm056.tpl',
    'ss/item/idm057.tpl',
    'ss/item/idm059.tpl',
    'ss/item/idm05a.tpl',
    'ss/item/idm05d.tpl',
    'ss/item/idm05f.tpl',
    'ss/item/idm060.tpl',
    'ss/item/idm061.tpl',
    'ss/item/idm074.tpl',
    'ss/item/idm076.tpl',
    'ss/item/idm077.tpl',
    'ss/item/idm082.tpl',
    'ss/item/idm083.tpl',
    'ss/item/idm084.tpl',
    'ss/item/idm08a.tpl',
    'ss/item/idm092.tpl',
    'ss/item/idm093.tpl',
    'ss/item/idm095.tpl',
    'ss/item/idm096.tpl',
    'ss/item/idm097.tpl',
    'ss/item/idm0a1.tpl',
    'ss/item/idm0b8.tpl',
    'ss/item/idm0b9.tpl',
    'ss/item/idm0ba.tpl',
    'ss/item/idm0bb.tpl',
    'ss/item/idm0c5.tpl',
    'ss/item/idm0c7.tpl',
    'ss/item/idm0c8.tpl',
    'ss/item/idm0c9.tpl',
    'ss/item/idm0d2.tpl',
    'ss/item/idm0d3.tpl',
    'ss/item/idm0d4.tpl',
]


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
