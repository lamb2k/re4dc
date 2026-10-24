#!/usr/bin/env python3
"""Static texture provenance and mip eligibility, without claiming runtime use.

Existing command line is retained. Optional --textrefs adds provenance hints.
A mip-chain row is a format-eligible candidate with a route-bound static
reference, not proof of drawing, minification, memory fit or visual quality.

GC archive names and package labels identify origins. A shared/global archive
alone does not establish the selected renderer's consumers. Such rows are held
as consumer-unresolved, never inferred dead merely because PS2 actors are used.
R4PW references come from material records; incidental byte matches in other
native files remain explicitly unverified hints. No output authorizes pruning.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import zlib

FMT = {0: 'RGB565', 1: 'ARGB1555', 2: 'ARGB4444', 3: 'YUV422', 4: 'PAL4', 5: 'PAL8', 6: 'BUMP'}
LAY = {0: 'linear', 1: 'twiddled', 2: 'vq'}
KEY = re.compile(r'[0-9a-f]{8}-[0-9a-f]{8}')
CLASS_ORDER = ('hud', 'weapon', 'effect', 'character', 'enemy', 'item',
               'world-object', 'cutscene', 'world', 'other', 'unreferenced')


def route_room(room):
    """The existing staged chapter 1-3 range; reject labels and partial matches."""
    if not re.fullmatch(r'r[0-9a-f]{3}', room):
        return False
    number = int(room[1:], 16)
    return 0x100 <= number <= 0x120 or 0x200 <= number <= 0x22f


def read_pak(path, blob=None):
    # Reuse the packer's existing index, extent and identity validation.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import texpack
    blob = Path(path).read_bytes() if blob is None else blob
    texpack.verify(blob)
    _, _, count, index_at, _ = struct.unpack_from('<8s4I', blob)
    out = {}
    for index in range(count):
        crc, fnv, offset, size = struct.unpack_from('<4I', blob, index_at + 16 * index)
        out['%08x-%08x' % (crc, fnv)] = blob[offset:offset + size]
    return out


def desc(blob):
    if len(blob) < 48:
        raise ValueError('truncated texture header')
    head = struct.unpack_from('<8s10I', blob)
    if head[:4] != (b'RE4DCTX\0', 2, 48, 96) or not head[4] or head[5] != 48:
        raise ValueError('unsupported texture descriptor header')
    table_end = 48 + 96 * head[4]
    if table_end > len(blob) or head[6] < table_end or head[6] + head[7] != len(blob):
        raise ValueError('invalid texture descriptor extent')
    images = []
    for index in range(head[4]):
        row = struct.unpack_from('<64s8I', blob, head[5] + 96 * index)
        if not row[1] or not row[2] or row[4] < head[6] or row[4] + row[5] > len(blob):
            raise ValueError('invalid texture image extent')
        images.append(dict(name=row[0].split(b'\0')[0].decode('latin-1'),
                           w=row[1], h=row[2], fmt=FMT.get(row[3], str(row[3])),
                           mip=bool(row[6] & 4), layout=LAY.get(row[7], str(row[7]))))
    return images


def gc_class(file, context):
    """Classify source provenance, not archive activation."""
    file, context = file.lower(), context.lower()
    match = re.match(r'st\d/(r[0-9a-f]{3})(?:[^0-9a-f]|$)', file)
    if match:
        kind = 'effect' if '.eff' in context or 'esp' in context else 'weapon' if 'wep' in context else 'world'
        return kind, [match.group(1)]
    match = re.match(r'evd/(r[0-9a-f]{3})(?:[^0-9a-f]|$)', file)
    if match:
        return 'cutscene', [match.group(1)]
    if file.startswith('evd/'):
        return 'cutscene', ['archive:' + file]
    if file.startswith('em/'):
        base = os.path.basename(file)
        if base.startswith(('pl', 'emwp', 'wep')) or 'wep' in base:
            return ('weapon' if 'wep' in base or base.startswith('emwp') else 'character'), ['archive:' + file]
        return 'enemy', ['archive:' + file]
    if file.startswith('etc/') and ('efm' in context or 'eff' in context):
        return 'effect', ['archive:' + file]
    if file.startswith(('ss/', 'fnt/', 'font', 'etc/title', 'title', 'mes/', 'file/')):
        return 'hud', ['archive:' + file]
    if file.startswith('etc/') and file.endswith(('.eff', '.esp')):
        return 'effect', ['archive:' + file]
    if file.startswith('omk/'):
        return 'unreferenced', ['extra']
    return 'other', ['archive:' + file]


def name_class(name):
    match = re.match(r'PS2 (r[0-9a-f]{3}) (texture|object)', name)
    if match:
        return 'world', [match.group(1)]
    if name.startswith('PS2 items'):
        return 'item', []
    if name.startswith('PS2 breakables'):
        return 'world-object', []
    if name.startswith('hud-'):
        return 'hud', []
    if name.startswith(('leon', 'cast_human', 'ps2_luis', 'ps2cast_luis')) or 'ashley' in name:
        return 'character', []
    if name.startswith('cast_animal') or re.search(r'_(fish|bat|crow|dog|cow|chicken)', name):
        return 'enemy', []
    if name.startswith(('ps2mask_', 'ps2cast_', 'ganado')):
        return 'enemy', []
    return None, []


def world_material_keys(blob):
    """Use the R4PW v1 material layout validated by rect21/world_bindings.py.

    Placements contain arbitrary integer/float words and must not become keys.
    """
    if len(blob) < 32:
        raise ValueError('truncated R4PW header')
    magic, version, placements, parts, meshes, crc, reserved0, reserved1 = struct.unpack_from('<4s7I', blob)
    if magic != b'R4PW' or version != 1 or len(blob) != 32 + 16 * parts + 52 * placements:
        raise ValueError('unsupported R4PW extent')
    if zlib.crc32(blob[32:]) & 0xffffffff != crc:
        raise ValueError('R4PW body checksum mismatch')
    return {'%08x-%08x' % row[:2]
            for row in struct.iter_unpack('<IIHH4B', blob[32:32 + 16 * parts])}


def source_aliases(keys, origin_text):
    """Each scoped identity may map to only one original."""
    aliases = {key: key for key in keys}
    for line in origin_text.splitlines():
        words = re.findall(r'0x([0-9a-fA-F]{8})U', line)
        if len(words) < 4:
            continue
        scoped = '-'.join(words[:2]).lower()
        original = '-'.join(words[2:4]).lower()
        if original not in keys:
            continue
        previous = aliases.get(scoped)
        if previous is not None and previous != original:
            raise ValueError('ambiguous scoped origin: ' + scoped)
        aliases[scoped] = original
    return aliases


def native_refs(native_dir, aliases, *, identities=None):
    """Return proved R4PW material bindings and separate byte-search hints."""
    bindings, hints = collections.defaultdict(set), collections.defaultdict(set)
    wanted = {struct.pack('<II', *(int(word, 16) for word in key.split('-'))): original
              for key, original in aliases.items()}
    for room in sorted(Path(native_dir).iterdir()):
        if not room.is_dir():
            continue
        for path in sorted(room.iterdir()):
            if not path.is_file():
                continue
            blob = path.read_bytes()
            source = room.name + '/' + path.name
            if identities is not None:
                identities['native/' + source] = hashlib.sha256(blob).hexdigest()
            if path.suffix.lower() == '.r4pw' or blob.startswith(b'R4PW'):
                for key in world_material_keys(blob):
                    if key in aliases:
                        bindings[aliases[key]].add(source)
                continue
            # Other native formats need their own material parsers. These hits
            # remain useful provenance, but do not admit a conversion or prune.
            for offset in range(0, len(blob) - 7, 4):
                original = wanted.get(blob[offset:offset + 8])
                if original:
                    hints[original].add(source)
    return bindings, hints


def classify_key(key, images, gc_sources=(), package_refs=(), resident_refs=(),
                 text_refs=(), raw_refs=(), old_decision='-'):
    """Combine all sources; source order cannot hide a HUD/shared consumer."""
    if not images:
        raise ValueError('texture has no images')
    image = images[0]
    sources, classes, source_rooms = [], set(), set()
    gc_rooms, archive_sources = set(), []
    for source in gc_sources:
        kind, rooms = gc_class(source['file'], source.get('context', ''))
        classes.add(kind)
        source_rooms.update(rooms)
        gc_rooms.update(room for room in rooms if re.fullmatch(r'r[0-9a-f]{3}', room))
        archive_sources.extend(room for room in rooms if room.startswith('archive:'))
        sources.append('gc:%s:%s' % (source['file'], source.get('context', '')))
    for item in images:
        kind, rooms = name_class(item['name'])
        if kind:
            classes.add(kind)
        source_rooms.update(rooms)
        sources.append('pak:' + item['name'])
    binding_rooms = {ref.split('/')[0] for ref in package_refs} | set(resident_refs)
    source_rooms.update(binding_rooms)
    sources.extend('pkg:' + ref for ref in sorted(package_refs))
    sources.extend('resident:' + room for room in sorted(resident_refs))
    sources.extend('text:' + path.replace('/mnt/c/Game Dev/Emulators/', 'C:/').replace('/root/', '~/')
                   for path in sorted(text_refs))
    sources.extend('raw-unverified:' + ref for ref in sorted(raw_refs))
    classes = classes or {'unreferenced'}
    ordered = [kind for kind in CLASS_ORDER if kind in classes]
    cls = ordered[0]
    if len(classes - {'other', 'unreferenced'}) > 1:
        cls = 'mixed'
    bound_route = sorted(room for room in binding_rooms if route_room(room))
    archive_route = sorted(room for room in gc_rooms if route_room(room))
    route_origins = sorted(room for room in source_rooms if route_room(room))
    unknown_consumer = bool(archive_sources or text_refs or raw_refs or
                            any(not re.fullmatch(r'r[0-9a-f]{3}', room) for room in binding_rooms))
    if bound_route:
        status = 'bound-on-route'
    elif archive_route:
        status = 'archive-on-route'
    elif unknown_consumer:
        status = 'consumer-unresolved'
    elif binding_rooms or gc_rooms:
        status = 'outside-route'
    else:
        status = 'no-static-binding'
    semantic_known = bool(classes - {'other', 'unreferenced'})
    if bound_route and not semantic_known:
        status = 'bound-consumer-unresolved'
    square = image['w'] == image['h'] and image['w'] > 0 and image['w'] & (image['w'] - 1) == 0
    generator = ((image['fmt'] in ('RGB565', 'ARGB1555', 'ARGB4444') and image['layout'] in ('twiddled', 'vq'))
                 or (image['fmt'] == 'PAL4' and image['layout'] == 'twiddled'))
    if 'hud' in classes:
        decision, reason = 'exclude', 'HUD/UI source alias; preserve the shared package'
    elif len(images) > 1:
        decision, reason = 'convert-blocked', 'multi-image package (%d): split per image first' % len(images)
    elif image['mip']:
        decision, reason = 'already-mipped', 'pack carries a chain'
    elif status == 'bound-consumer-unresolved':
        decision, reason = 'consumer-unresolved', 'route binding present; semantic/shared consumer role is not established'
    elif status == 'consumer-unresolved':
        decision, reason = 'consumer-unresolved', 'source identified; active/shared consumer is not established'
    elif status in ('outside-route', 'no-static-binding'):
        decision, reason = 'not-reachable', ('no route binding in supplied static inputs; not a pruning proof'
                                             if status == 'no-static-binding' else
                                             'supplied bindings are outside ch1-3; not a pruning proof')
    elif max(image['w'], image['h']) <= 16:
        decision, reason = 'exclude', 'tiny (<=16): retain base under this candidate policy'
    elif not square or not 8 <= image['w'] <= 1024:
        decision, reason = 'convert-blocked', 'unsupported dimensions %dx%d: needs a qualified representation' % (image['w'], image['h'])
    elif not generator:
        decision, reason = 'convert-blocked', '%s %s: no selected chain generator' % (image['fmt'], image['layout'])
    else:
        decision, reason = 'mip-chain', 'format-eligible static candidate; actual drawing/minification not measured'
    contradiction = ''
    if old_decision == 'not-on-route' and (bound_route or archive_route):
        contradiction = 'not seen in texclass22 runs; static route reference exists'
    elif old_decision in ('convert', 'not-worth', 'needs-work') and status in ('outside-route', 'no-static-binding'):
        # Positive runtime evidence is not disproved by incomplete static inputs.
        contradiction = 'texclass22 observed drawing; static consumer closure is incomplete'
        if decision == 'not-reachable':
            decision, reason = 'consumer-unresolved', 'prior positive drawing evidence conflicts with missing static bindings'
            status = 'consumer-unresolved'
    return dict(key=key, cls=cls, classes=','.join(ordered), decision=decision, reason=reason,
                w=image['w'], h=image['h'], fmt=image['fmt'], layout=image['layout'],
                rooms=','.join(sorted(source_rooms)) or '-', route_rooms=len(route_origins),
                binding_rooms=','.join(sorted(binding_rooms)) or '-',
                consumer_status=status, minification='unmeasured',
                source_count=len(sources), sources=' | '.join(sources),
                texclass22=old_decision, contradiction=contradiction)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('keys', 'pack', 'gc', 'data', 'origins', 'resident', 'texclass', 'out_tsv', 'out_json'):
        parser.add_argument('--' + name.replace('_', '-'), required=True)
    parser.add_argument('--textrefs')
    args = parser.parse_args()
    input_paths = {name: Path(getattr(args, name)) for name in
                   ('keys', 'pack', 'gc', 'origins', 'texclass')}
    if args.textrefs:
        input_paths['textrefs'] = Path(args.textrefs)
    outputs = [Path(args.out_tsv), Path(args.out_json)]
    if len({path.resolve() for path in outputs}) != 2:
        parser.error('output TSV and JSON must be different paths')
    for path in outputs:
        if path.exists() or path.resolve() in {p.resolve() for p in input_paths.values()}:
            parser.error('use a new output path: ' + str(path))
    resident_dir = Path(args.resident)
    if not resident_dir.is_dir():
        parser.error('--resident must identify an existing directory; missing evidence cannot mean no references')
    inputs = {name: path.read_bytes() for name, path in input_paths.items()}
    identities = {name: hashlib.sha256(blob).hexdigest() for name, blob in inputs.items()}
    keys = [line.strip().lower() for line in inputs['keys'].decode().splitlines() if line.strip()]
    if len(set(keys)) != len(keys) or any(not KEY.fullmatch(key) for key in keys):
        parser.error('keys must be unique crc-fnv identities')
    packages = read_pak(args.pack, inputs['pack'])
    missing = sorted(set(keys) - packages.keys())
    if missing:
        parser.error('keys absent from pack: ' + ', '.join(missing))
    gc_sources = json.loads(inputs['gc'])
    aliases = source_aliases(set(keys), inputs['origins'].decode())
    package_refs, raw_refs = native_refs(Path(args.data) / 'native', aliases, identities=identities)
    resident_refs = collections.defaultdict(set)
    for path in sorted(resident_dir.glob('*.tsv')):
        blob = path.read_bytes()
        identities['resident/' + path.name] = hashlib.sha256(blob).hexdigest()
        for line in blob.decode().splitlines():
            key = line.split('\t')[0].strip().lower()
            if key in aliases:
                resident_refs[aliases[key]].add(path.stem)
    text_refs = json.loads(inputs['textrefs']) if args.textrefs else {}
    old = {row['key']: row['decision'] for row in csv.DictReader(inputs['texclass'].decode().splitlines(), delimiter='\t')}
    rows = []
    for key in keys:
        row = classify_key(key, desc(packages[key]), gc_sources.get(key, ()),
                           package_refs.get(key, ()), resident_refs.get(key, ()),
                           text_refs.get(key, ()), raw_refs.get(key, ()), old.get(key, '-'))
        row['bytes'] = len(packages[key])
        rows.append(row)
    columns = ['key', 'sources', 'rooms', 'cls', 'decision', 'reason', 'w', 'h', 'fmt', 'layout', 'bytes',
               'route_rooms', 'texclass22', 'contradiction', 'classes', 'binding_rooms', 'consumer_status',
               'minification', 'source_count']
    with open(args.out_tsv, 'x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(schema='re4dc-texsrc22-static-2', keys=len(rows),
                   input_sha256=dict(sorted(identities.items())),
                   classifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   by_class=collections.Counter(row['cls'] for row in rows),
                   by_decision=collections.Counter(row['decision'] for row in rows),
                   class_decision=collections.Counter('%s/%s' % (row['cls'], row['decision']) for row in rows),
                   consumer_status=collections.Counter(row['consumer_status'] for row in rows),
                   contradictions=collections.Counter(row['contradiction'] for row in rows if row['contradiction']),
                   limits=['Static provenance and candidate eligibility, not runtime use or measured minification.',
                           'Global/shared archives, text mentions and unparsed native byte matches require consumer review.',
                           'No decision authorizes texture pruning or release adoption.'])
    with Path(args.out_json).open('x') as handle:
        handle.write(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
