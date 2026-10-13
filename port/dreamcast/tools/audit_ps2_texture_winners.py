#!/usr/bin/env python3
"""Read-only comparison of texture staging lists with a sampled fixture pack.

No pack writes. Render equality is bytes[112:] (dimensions, format, layout and
payload); label-only differences retain their actual winning body CRC in output.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import sys
import zlib

from fit_ps2_world_textures import metadata, sha, sha_bytes, write_json, world_registry
sys.path.insert(0, str(Path(__file__).resolve().parent / 'd367'))
import texpack


def audit(pack_path, room_paths, output, fixtures=None):
    fixtures = fixtures or {}
    before = pack_path.stat()
    blob = pack_path.read_bytes()
    count, crc = texpack.verify(blob)
    index = {'%08x-%08x' % struct.unpack_from('<2I', blob, 2048 + i * 16):
             struct.unpack_from('<2I', blob, 2048 + i * 16 + 8) for i in range(count)}
    rooms = {}
    for room_path in room_paths:
        staging = json.loads(room_path.read_text())
        fixture_path = fixtures.get(staging['room'])
        fixture_bytes = fixture_path.read_bytes() if fixture_path else None
        fixture = json.loads(fixture_bytes) if fixture_bytes else None
        if fixture and 'dc/tex.pak' in fixture.get('remove', []):
            raise ValueError('fixture removes audited texture pack')
        if fixture and Path(fixture['replace']['dc/tex.pak']).resolve() != pack_path.resolve():
            raise ValueError('fixture pack differs from audited pack')
        rows = []
        for row in staging['textures']:
            chosen = row['chosen']
            source = Path(chosen['path']).read_bytes()
            if sha_bytes(source) != chosen['sha256']:
                raise ValueError('selected source changed: ' + row['key'])
            entry = index.get(row['key'])
            record = dict(key=row['key'], chosen=chosen, reason=row['reason'])
            if entry is None:
                record['status'] = 'ABSENT_FROM_PACK'
            else:
                offset, size = entry
                packed = blob[offset:offset + size]
                why, rule = world_registry.tex_package_error(packed, chosen['width'], chosen['height'])
                record['packed'] = dict(offset=offset, bytes=size, sha256=sha_bytes(packed),
                    body_crc32=f'{struct.unpack_from("<I", packed, 36)[0]:08x}' if len(packed) >= 40 else None,
                    body_crc_valid=(len(packed) >= 48 and struct.unpack_from('<I', packed, 36)[0] == zlib.crc32(packed[48:])),
                    render_sha256=sha_bytes(packed[112:]), runtime_parser='PASS' if why is None else 'FAIL',
                    runtime_reason=why)
                if why is not None:
                    record['status'] = 'INVALID_PACKED_PACKAGE'
                elif packed == source:
                    record['status'] = 'EXACT_WINNER'
                elif packed[112:] == source[112:]:
                    record['status'] = 'RENDER_EQUIVALENT_LABEL_ONLY'
                else:
                    record['status'] = 'STALE_PACK_SHADOWS_CHOICE'
            if fixture:
                disc_path = 'dc/tex/' + row['key'][0] + '/' + row['key'] + '.re4tex'
                loose_path = fixture.get('replace', {}).get(disc_path)
                if entry is None and loose_path and disc_path not in fixture.get('remove', []):
                    actual = Path(loose_path)
                    if not actual.is_absolute():
                        actual = fixture_path.parent / actual
                    actual_meta = metadata(actual)
                    record['loose'] = actual_meta
                    record['selected_origin'] = 'fixture_loose'
                    record['selected_render_match'] = actual_meta['render_sha256'] == chosen['render_sha256']
                    record['selected_body_crc32'] = actual_meta['body_crc32']
                elif entry is not None:
                    record['selected_origin'] = 'fixture_pack'
                    record['selected_render_match'] = record['status'] in ('EXACT_WINNER', 'RENDER_EQUIVALENT_LABEL_ONLY')
                    record['selected_body_crc32'] = record['packed']['body_crc32']
                else:
                    record['selected_origin'] = 'UNRESOLVED'
                    record['selected_render_match'] = False
                low_path = 'dc/texlow/' + row['key'][0] + '/' + row['key'] + '.re4tex'
                if low_path in fixture.get('replace', {}) and low_path not in fixture.get('remove', []):
                    raise ValueError('matching texlow override requires explicit mode resolution: ' + low_path)
            rows.append(record)
        counts = dict(Counter(row['status'] for row in rows))
        blocked = any(row['status'] not in ('EXACT_WINNER', 'RENDER_EQUIVALENT_LABEL_ONLY') for row in rows)
        if fixture_path and fixture_path.read_bytes() != fixture_bytes:
            raise ValueError('fixture changed during audit; retry')
        rooms[staging['room']] = dict(staging_list=str(room_path), staging_sha256=sha(room_path), counts=counts,
            fixture=str(fixture_path) if fixture_path else None, fixture_sha256=sha_bytes(fixture_bytes) if fixture_bytes else None,
            canonical_body_crc_mismatches=sum(row.get('selected_body_crc32') != row['chosen']['body_crc32'] for row in rows) if fixture else None,
            fixture_selection=('PASS_SELECTED_RENDER_BYTES' if all(row['selected_render_match'] for row in rows) else 'FAIL_SELECTED_RENDER_BYTES') if fixture else 'UNRESOLVED_WITHOUT_FIXTURE',
            final_pack_application='PENDING' if blocked else 'RENDER_BYTES_MATCH',
            status='PACK_INCOMPLETE_REQUIRES_LOOSE_RESOLUTION' if blocked else 'PACK_RENDER_BYTES_MATCH', textures=rows)
    after = pack_path.stat()
    stable = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns) and sha(pack_path) == sha_bytes(blob)
    if not stable:
        raise ValueError('pack changed during read; retry after pack owner finishes')
    report = dict(schema='re4dc-texture-pack-winner-audit/1', pack=dict(path=str(pack_path), sha256=sha_bytes(blob),
        bytes=len(blob), index_crc32=f'{crc:08x}', entries=count, stable_during_read=stable,
        mtime_ns=after.st_mtime_ns, mutable=True), rooms=rooms,
        scope='Static sampled pack bytes only. Absent keys can select verified fixture loose files; stale packed keys shadow loose files. Final pack application is separate. No live TEXCHECK, runtime fit or headroom claim.')
    write_json(output, report)
    for room, row in rooms.items():
        print(room, row['fixture_selection'], row['status'], row['counts'])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--room', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixture', action='append', default=[], help='ROOM=armed-fixture.json; resolve absent packed keys from exact loose mappings')
    args = parser.parse_args(argv)
    fixtures = {item.split('=', 1)[0]: Path(item.split('=', 1)[1]) for item in args.fixture}
    audit(args.pack, args.room, args.output, fixtures)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())