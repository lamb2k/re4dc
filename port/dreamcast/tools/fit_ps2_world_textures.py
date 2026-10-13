#!/usr/bin/env python3
"""Choose conservative PS2 world texture overlays and emit exact pack winners.

Consumes existing private handback indices, never changes source packages or packs.
The existing vq_native_ui CLI remains unchanged. All generated output is private.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import convert_tpl as tpl
import vq_native_ui as vq
from d367.ps2world import world_registry

SCHEMA = 're4dc-world-texture-fit/1'
POLICY = 'alpha-exact-rgb30-base-only-v1'


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(Path(path).read_bytes())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def metadata(path):
    data = Path(path).read_bytes()
    if len(data) < 144:
        raise ValueError('short RE4DCTX: ' + str(path))
    h = tpl.HEADER.unpack_from(data)
    d = tpl.TEXTURE.unpack_from(data, 48)
    _, w, height, fmt, offset, size, flags, kind, reserved = d
    if (h[:7] != (tpl.MAGIC, tpl.VERSION, 48, 96, 1, 48, 144) or
            len(data) != 144 + size or h[7] != size or
            zlib.crc32(data[48:]) != h[8] or offset != 144 or reserved):
        raise ValueError('noncanonical or corrupt RE4DCTX: ' + str(path))
    why, rule = world_registry.tex_package_error(data, w, height)
    if why is not None or rule != 'header':
        raise ValueError('runtime parser rejected ' + str(path) + ': ' + str(why))
    if flags & tpl.FLAG_MIPMAP:
        raise ValueError('mipmapped input needs an explicit runtime-qualified policy: ' + str(path))
    return dict(path=str(Path(path).resolve()), sha256=sha_bytes(data), package_bytes=len(data),
                body_crc32=f'{h[8]:08x}', render_sha256=sha_bytes(data[112:]),
                payload_sha256=sha_bytes(data[offset:offset + size]), width=w, height=height,
                format=fmt, format_name=vq.FORMAT_NAMES[fmt], payload_bytes=size,
                payload_kind=kind, layout={0: 'linear16', 1: 'twiddled16', 2: 'vq'}[kind],
                flags=flags, mips=False, mip_levels=1, runtime_parser='PASS')


def decode(path):
    """Decode actual native/VQ payload bytes, independent of pvrtex PNG previews."""
    data = Path(path).read_bytes()
    _, w, h, fmt, offset, size, flags, kind, _ = tpl.TEXTURE.unpack_from(data, 48)
    if flags & tpl.FLAG_MIPMAP:
        raise ValueError('base-only decoder')
    payload = data[offset:offset + size]
    if kind == tpl.PAYLOAD_VQ:
        book = struct.unpack_from('<1024H', payload)
        # Each byte selects four consecutive twiddled 16-bit texels.
        texels = [value for index in payload[2048:] for value in book[index * 4:index * 4 + 4]]
    else:
        texels = struct.unpack('<%dH' % (w * h), payload)
    if len(texels) != w * h:
        raise ValueError('decoded texel count mismatch')
    if kind != tpl.PAYLOAD_LINEAR:
        texels = vq.detwiddle(texels, w, h)
    return [vq.expand(value, fmt) for value in texels]


def compare(a, b):
    if len(a) != len(b):
        raise ValueError('changed image dimensions')
    alpha_changed = sum(p[3] != q[3] for p, q in zip(a, b))
    rgb_error = sum(sum((p[c] - q[c]) ** 2 for c in range(3)) for p, q in zip(a, b))
    rgb_visible_error = sum(max(p[3], q[3]) / 255 * sum((p[c] - q[c]) ** 2 for c in range(3))
                            for p, q in zip(a, b))
    def psnr(error):
        mse = error / (len(a) * 3)
        return 99.0 if mse == 0 else 10 * math.log10(255 * 255 / mse)
    return dict(alpha_changed_pixels=alpha_changed, alpha_exact=alpha_changed == 0,
                alpha_max_error=max(abs(p[3] - q[3]) for p, q in zip(a, b)),
                coverage_changed_pixels=sum((p[3] > 0) != (q[3] > 0) for p, q in zip(a, b)),
                rgb_psnr_db=round(psnr(rgb_error), 6),
                coverage_weighted_rgb_psnr_db=round(psnr(rgb_visible_error), 6),
                pixels=len(a))


def read_inputs(indices):
    rooms = {}
    for index in indices:
        for room, entry in json.loads(index.read_text()).items():
            if room in rooms:
                raise ValueError('duplicate room: ' + room)
            handback = Path(entry['handback'])
            raw = json.loads(handback.read_text())
            root = Path(raw.get('output', raw.get('runtime_dir', '')))
            textures = raw['textures']
            if isinstance(textures, list):
                rows = textures
            else:
                rows = [dict(key=Path(name).stem, path=str(root / 'tex' / name), **record)
                        for name, record in textures.items()]
            files = raw.get('package_files', raw.get('packages', {}))
            packages = {}
            for name, record in files.items():
                path = Path(record.get('path', root / name))
                if sha(path) != record['sha256']:
                    raise ValueError('package changed since handback: ' + str(path))
                packages[name] = dict(path=str(path), sha256=record['sha256'], bytes=path.stat().st_size)
            for row in rows:
                row['baseline'] = metadata(row['path'])
                if row['baseline']['sha256'] != row['sha256']:
                    raise ValueError('texture changed since handback: ' + row['path'])
            rooms[room] = dict(handback=str(handback), handback_sha256=sha(handback),
                               output=str(root), packages=packages, textures=rows,
                               baseline_validation=entry.get('validation', {}))
    return rooms


def fit_key(key, sources, args, converter_pin):
    baseline = min(sources, key=lambda row: row['baseline']['path'])['baseline']
    chosen = baseline
    result = dict(key=key, baseline=baseline, chosen=chosen, candidate=None,
                  reason='preserve_existing_vq' if baseline['payload_kind'] == 2 else 'below_native_candidate_threshold',
                  filename_policy='preserve_original_runtime_lookup_key', content_key_invariant='baseline_only',
                  pack_precedence='chosen bytes must replace this key in the final authoritative pack; no stale pack fallback')
    if baseline['payload_kind'] != tpl.PAYLOAD_TWIDDLED:
        return result
    if baseline['payload_bytes'] < args.min_bytes or min(baseline['width'], baseline['height']) < args.min_side:
        return result
    cache_id = sha_bytes(json.dumps(dict(source=baseline['sha256'], tools=converter_pin), sort_keys=True).encode())
    directory = args.output / 'cache' / cache_id
    record_path = directory / 'comparison.json'
    if record_path.exists():
        candidate_record = json.loads(record_path.read_text())
        candidate = metadata(candidate_record['candidate']['path'])
        if candidate != candidate_record['candidate']:
            raise ValueError('cached candidate changed: ' + key)
        quality = candidate_record['quality']
    else:
        directory.mkdir(parents=True, exist_ok=True)
        source_path = Path(baseline['path'])
        encoded = vq.encode(key, source_path.parent, directory, args.pvrtex,
                            (baseline['width'], baseline['height']), directory)
        variant_path = directory / (key + '.re4tex')
        variant = bytearray(variant_path.read_bytes())
        # The encoder uses generic material/alpha flags; preserve the input's
        # descriptor label and flags so this overlay changes payload layout only.
        original = source_path.read_bytes()
        variant[48:112] = original[48:112]
        struct.pack_into('<I', variant, 132, baseline['flags'])
        struct.pack_into('<I', variant, 36, zlib.crc32(variant[48:]))
        variant_path.write_bytes(variant)
        candidate = metadata(variant_path)
        if any(candidate[field] != baseline[field] for field in ('width', 'height', 'format', 'flags', 'mips')):
            raise ValueError('VQ changed texture sampling contract: ' + key)
        before, after = decode(source_path), decode(candidate['path'])
        quality = compare(before, after)
        # pvrtex's preview decoder must agree with actual emitted bytes after
        # quantizing the preview back into the source's native color precision.
        from PIL import Image
        preview = list(Image.open(directory / (key + '-vq.png')).convert('RGBA').getdata())
        quality['preview_alpha_exact'] = all(p[3] == q[3] for p, q in zip(preview, after))
        quality['preview_rgb_max_error'] = max(abs(p[c] - q[c]) for p, q in zip(preview, after) for c in range(3))
        if not quality['preview_alpha_exact'] or quality['preview_rgb_max_error'] > 1:
            raise ValueError('emitted VQ decode disagrees with pvrtex preview: ' + key)
        candidate_record = dict(candidate=candidate, quality=quality, encoder_report=encoded)
        write_json(record_path, candidate_record)
    result['candidate'] = dict(**candidate, quality=quality)
    if not quality['alpha_exact']:
        result['reason'] = 'preserve_native_alpha_changed'
    elif quality['rgb_psnr_db'] < args.min_rgb_psnr:
        result['reason'] = 'preserve_native_rgb_quality_below_threshold'
    elif candidate['payload_bytes'] >= baseline['payload_bytes']:
        result['reason'] = 'preserve_native_no_payload_saving'
    else:
        result.update(chosen=candidate, reason='vq_alpha_exact_rgb_quality_pass',
                      content_key_invariant='intentionally_not_applicable_to_overlay_payload')
    return result


def write_room(room, info, decisions, args):
    textures = []
    for row in sorted(info['textures'], key=lambda row: row['key']):
        result = decisions[row['key']]
        textures.append(dict(key=row['key'], source_baseline=row['baseline'],
                             chosen=result['chosen'], reason=result['reason'],
                             candidate=result['candidate'],
                             content_key_invariant=result['content_key_invariant'],
                             pack_precedence=result['pack_precedence']))
    before = sum(row['source_baseline']['payload_bytes'] for row in textures)
    after = sum(row['chosen']['payload_bytes'] for row in textures)
    value = dict(schema=SCHEMA, room=room, policy=POLICY, source_handback=info['handback'],
                 source_handback_sha256=info['handback_sha256'], packages=info['packages'], textures=textures,
                 standalone_world_payload_before=before, standalone_world_payload_after=after,
                 standalone_world_payload_saved=before - after,
                 whole_room_budget=dict(status='UNKNOWN', room_vram_bytes=None, measured_headroom_bytes=None,
                    reason='No matched complete-room residency census was supplied. World-only payload excludes actors, UI, effects, framebuffers, allocator alignment/fragmentation, and transient overlap.'),
                 criteria=dict(min_native_bytes=args.min_bytes, min_side=args.min_side,
                    alpha_changed_pixels=0, minimum_rgb_psnr_db=args.min_rgb_psnr,
                    mip_policy='Preserve base level only; no added mips. Mips require square VQ and CAST_MIPMAP; increase payload and are not a fit optimization.',
                    visual_review='Offline metrics qualify test candidates; final room stills and human appearance acceptance remain pending.'),
                 runtime_parser='PASS', pack_winner_check='PENDING_FINAL_PACK',
                 runtime_fit='UNMEASURED', reason_counts=dict(Counter(row['reason'] for row in textures)))
    write_json(args.output / 'rooms' / (room + '.json'), value)
    print(f'{room} world payload {before} -> {after}; saved {before-after}; {value["reason_counts"]}', flush=True)
    return {k: value[k] for k in ('standalone_world_payload_before', 'standalone_world_payload_after',
                                'standalone_world_payload_saved', 'reason_counts')}


def verify_output(output):
    index = json.loads((output / 'index.json').read_text())
    rows = json.loads((output / 'winners.json').read_text())['textures']
    by_key = {row['key']: row for row in rows}
    if len(by_key) != len(rows):
        raise ValueError('duplicate winning texture keys')
    inventory = '\n'.join('{} {} {}'.format(row['key'], row['chosen']['sha256'], row['chosen']['body_crc32']) for row in rows) + '\n'
    if sha_bytes(inventory.encode()) != index['inventory_sha256']:
        raise ValueError('winning inventory digest mismatch')
    for row in rows:
        if metadata(row['chosen']['path']) != row['chosen']:
            raise ValueError('winner bytes changed: ' + row['key'])
    for room, record in index['rooms'].items():
        path = output / 'rooms' / (room + '.json')
        if sha(path) != record['staging_sha256']:
            raise ValueError('staging list changed: ' + room)
        data = json.loads(path.read_text())
        for package in data['packages'].values():
            if sha(package['path']) != package['sha256']:
                raise ValueError('world package changed: ' + room)
        for row in data['textures']:
            if row['chosen'] != by_key[row['key']]['chosen']:
                raise ValueError('room disagrees with central winner: ' + room + ':' + row['key'])
            if sha(row['source_baseline']['path']) != row['source_baseline']['sha256']:
                raise ValueError('baseline changed: ' + row['key'])
    print(f'PASS {len(index["rooms"])} rooms, {len(rows)} unique exact winners')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--index', type=Path, action='append', default=[], help='stage-1/castle handback index; repeatable')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--priority', nargs='*', default=['r117', 'r112', 'r200'])
    parser.add_argument('--pvrtex', default=vq.PVRTEX)
    parser.add_argument('--min-bytes', type=int, default=32768)
    parser.add_argument('--min-side', type=int, default=32)
    parser.add_argument('--min-rgb-psnr', type=float, default=30.0)
    parser.add_argument('--verify', action='store_true', help='verify existing winners and immutable inputs without encoding')
    args = parser.parse_args(argv)
    args.output = args.output.resolve()
    if args.verify:
        verify_output(args.output)
        return 0
    if not args.index:
        parser.error('at least one --index is required')
    rooms = read_inputs(args.index)
    sources = {}
    for room, info in sorted(rooms.items()):
        for row in info['textures']:
            sources.setdefault(row['key'], []).append(dict(**row, room=room))
    collisions = [dict(key=key, sources=[dict(room=row['room'], **row['baseline']) for row in rows])
                  for key, rows in sorted(sources.items())
                  if len({row['baseline']['render_sha256'] for row in rows}) != 1]
    write_json(args.output / 'collisions.json', collisions)
    if collisions:
        raise ValueError('incompatible baseline keys; see collisions.json')
    pin = dict(pvrtex=dict(path=args.pvrtex, sha256=sha(args.pvrtex)),
               vq_native_ui=sha(HERE / 'vq_native_ui.py'), convert_tpl=sha(HERE / 'convert_tpl.py'))
    order = [room for room in args.priority if room in rooms] + sorted(set(rooms) - set(args.priority))
    decisions, summaries = {}, {}
    for room in order:
        for row in sorted(rooms[room]['textures'], key=lambda row: row['key']):
            key = row['key']
            if key not in decisions:
                decisions[key] = fit_key(key, sources[key], args, pin)
        summaries[room] = write_room(room, rooms[room], decisions, args)
    winners = [dict(**decisions[key], rooms=sorted({row['room'] for row in sources[key]})) for key in sorted(decisions)]
    inventory = '\n'.join(f'{row["key"]} {row["chosen"]["sha256"]} {row["chosen"]["body_crc32"]}' for row in winners) + '\n'
    write_json(args.output / 'winners.json', dict(schema=SCHEMA, policy=POLICY, collisions=[], textures=winners,
                                               inventory_sha256=sha_bytes(inventory.encode())))
    (args.output / 'winner-inventory.txt').write_text(inventory)
    for room in summaries:
        summaries[room]['staging_path'] = str(args.output / 'rooms' / (room + '.json'))
        summaries[room]['staging_sha256'] = sha(summaries[room]['staging_path'])
    report = dict(schema=SCHEMA, policy=POLICY, tools=pin,
                  cli_tool_sha256=sha(__file__), room_count=len(rooms), unique_key_count=len(winners),
                  shared_key_count=sum(len(row['rooms']) > 1 for row in winners), collisions=[],
                  inventory_sha256=sha_bytes(inventory.encode()), rooms=summaries,
                  unique_baseline_payload=sum(row['baseline']['payload_bytes'] for row in winners),
                  unique_chosen_payload=sum(row['chosen']['payload_bytes'] for row in winners),
                  reason_counts=dict(Counter(row['reason'] for row in winners)),
                  whole_room_fit='UNMEASURED', final_pack_winner_check='PENDING')
    write_json(args.output / 'index.json', report)
    verify_output(args.output)
    print(json.dumps({k: v for k, v in report.items() if k != 'rooms'}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())