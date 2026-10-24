#!/usr/bin/env python3
"""Strict, read-only GC-ASSET judge; no rr production wiring is performed here."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

CONSUMERS = ('source_geometry', 'texture', 'effect_picture', 'weapon', 'font', 'ui',
             'sound_bank', 'sound_stream', 'movie')
REQUIRED = (1 << len(CONSUMERS)) - 1
TOKEN = re.compile(r'^[a-z0-9/._:-]+$')
SHA = re.compile(r'^[0-9a-f]{64}$')
ROOM = re.compile(r'^[0-9a-f]{4}$')
HERE = Path(__file__).resolve().parent


def scope_name(row):
    if 'room' in row and 'phase' not in row and isinstance(row['room'], str) and ROOM.fullmatch(row['room']):
        return row['room']
    if 'room' not in row and row.get('phase') in ('startup', 'transition'):
        return '@' + row['phase']
    raise ValueError('requires exactly one game room or named startup/transition phase')


def transition_location(row):
    if row.get('transition_reason') == 'initial-room' and row.get('from_phase') == 'startup' and 'from_room' not in row:
        return {'transition_reason': 'initial-room', 'from_phase': 'startup'}
    if row.get('transition_reason') == 'room-retire' and isinstance(row.get('from_room'), str) and ROOM.fullmatch(row['from_room']) and 'from_phase' not in row:
        return {'transition_reason': 'room-retire', 'from_room': row['from_room']}
    raise ValueError('transition requires exact reason and originating room or startup phase')


def identity(row):
    scope = scope_name(row)
    if scope == '@transition':
        metadata = transition_location(row)
        scope += '/' + '/'.join(f'{k}:{v}' for k, v in sorted(metadata.items()))
    return (scope, *(row[k] for k in ('kind', 'id', 'sha256', 'provenance')))


def read_allowlist(path, baseline):
    current = json.loads(Path(path).read_text(encoding='utf-8'))
    ceiling = json.loads(Path(baseline).read_text(encoding='utf-8'))
    for document in (current, ceiling):
        if document.get('schema') != 1 or not isinstance(document.get('entries'), list):
            raise ValueError('allowlist schema must be 1 with an entries list')
        seen = set()
        for r in document['entries']:
            scope = scope_name(r)
            location_fields = {'phase'} if scope.startswith('@') else {'room'}
            if scope == '@transition':
                location_fields |= transition_location(r).keys()
            if set(r) != {*location_fields, 'kind', 'id', 'sha256', 'provenance', 'reason', 'owner', 'evidence'}:
                raise ValueError('allowlist row fields differ from schema')
            if not TOKEN.fullmatch(r['kind']) or not TOKEN.fullmatch(r['id']):
                raise ValueError('allowlist requires exact room/kind/id; patterns are forbidden')
            if not SHA.fullmatch(r['sha256']) or r['provenance'] not in ('gc', 'unknown'):
                raise ValueError('allowlist requires exact payload SHA256 and gc/unknown provenance')
            if any(not isinstance(r[k], str) or not r[k].strip() for k in ('reason', 'owner', 'evidence')):
                raise ValueError('allowlist requires reason, owner and evidence')
            if identity(r) in seen:
                raise ValueError('duplicate allowlist identity')
            seen.add(identity(r))
    baseline_rows = {identity(r): r for r in ceiling['entries']}
    for r in current['entries']:
        if identity(r) not in baseline_rows:
            raise ValueError('allowlist growth or payload/provenance change is forbidden: ' + str(identity(r)))
    return {identity(r): r for r in current['entries']}


def fields(line, prefix):
    body = line.split(prefix, 1)[1].strip()
    values = {}
    for part in body.split():
        if '=' not in part:
            raise ValueError('malformed diagnostic token: ' + part)
        key, value = part.split('=', 1)
        if key in values or not value:
            raise ValueError('duplicate/empty diagnostic field: ' + key)
        values[key] = value
    if values.get('v') != '1':
        raise ValueError('missing/unsupported GC-ASSET diagnostic version')
    return values


def judge(logs, allowlist, requested):
    failures = []
    visits = {}
    observed = set()
    for name, content in logs:
        active = None
        file_visits = 0
        startup_visits = 0
        last_visit = 0
        previous_scope = None
        for number, line in enumerate(content.splitlines(), 1):
            if 'GC-ASSET' not in line:
                continue
            location = f'{name}:{number}'
            try:
                if 'GC-ASSET-ERROR' in line:
                    raise ValueError('runtime diagnostic error: ' + line.strip())
                prefix = next((p for p in ('GC-ASSET-BEGIN ', 'GC-ASSET-COUNTS ', 'GC-ASSET-END ', 'GC-ASSET ') if p in line), None)
                if not prefix:
                    raise ValueError('unrecognized GC-ASSET diagnostic')
                r = fields(line, prefix)
                scope = scope_name(r)
                location_field = 'phase' if scope.startswith('@') else 'room'
                if not r.get('visit', '').isdigit() or not 0 < int(r['visit']) <= 0xffffffff:
                    raise ValueError('invalid room/visit')
                key = (name, scope, int(r['visit']))
                if prefix == 'GC-ASSET-BEGIN ':
                    if active is not None or key in visits:
                        raise ValueError('nested or duplicate room visit')
                    if key[2] <= last_visit:
                        raise ValueError('visit serial must increase across startup and game rooms')
                    if scope == '@startup':
                        if file_visits or startup_visits:
                            raise ValueError('startup must be the first and only named startup visit')
                        startup_visits += 1
                    elif startup_visits != 1:
                        raise ValueError('game room requires preceding startup diagnostic coverage')
                    transition = {}
                    if scope == '@transition':
                        transition = transition_location(r)
                        origin = '@startup' if 'from_phase' in transition else transition['from_room']
                        if previous_scope != origin:
                            raise ValueError('transition origin does not match the preceding completed visit')
                    elif scope != '@startup' and previous_scope != '@transition':
                        raise ValueError('game room requires preceding completed transition coverage')
                    last_visit = key[2]
                    required = {'v', location_field, 'visit', 'wired', 'required', 'catalog', 'catalog_ok', *transition}
                    if set(r) != required or int(r['wired'], 16) != REQUIRED or int(r['required'], 16) != REQUIRED:
                        raise ValueError('missing diagnostic consumer wiring')
                    if r['catalog_ok'] != '1' or not r['catalog'].isdigit():
                        raise ValueError('invalid provenance catalog')
                    visits[key] = {'rows': set(), 'first_consumers': {c: 0 for c in CONSUMERS}, 'counts': None, 'ended': False, 'scope': scope, 'transition': transition}
                    file_visits += 1
                    active = key
                    if not scope.startswith('@'):
                        observed.add(scope)
                elif prefix == 'GC-ASSET ':
                    if active != key:
                        raise ValueError('asset emission outside its room visit')
                    if set(r) != {'v', location_field, 'visit', 'kind', 'id', 'sha256', 'provenance', 'consumer', 'action'}:
                        raise ValueError('asset diagnostic fields differ from schema')
                    if r['action'] != 'emit' or r['consumer'] not in CONSUMERS:
                        raise ValueError('load/ready/reserve is not draw/play evidence')
                    if not TOKEN.fullmatch(r['kind']) or not TOKEN.fullmatch(r['id']) or not SHA.fullmatch(r['sha256']):
                        raise ValueError('invalid asset identity/payload digest')
                    if r['provenance'] not in ('gc', 'unknown'):
                        raise ValueError('GC-ASSET row must retain gc/unknown provenance')
                    asset = identity({**r, **visits[key]['transition']})
                    if asset in visits[key]['rows']:
                        raise ValueError('duplicate asset row in room visit')
                    visits[key]['rows'].add(asset)
                    visits[key]['first_consumers'][r['consumer']] += 1
                    if asset not in allowlist:
                        raise ValueError('unreviewed draw/play asset: ' + str(asset))
                elif prefix == 'GC-ASSET-COUNTS ':
                    if active != key or visits[key]['counts'] is not None:
                        raise ValueError('duplicate/out-of-visit consumer counts')
                    if set(r) != {'v', location_field, 'visit', *CONSUMERS}:
                        raise ValueError('consumer counter fields differ from schema')
                    visits[key]['counts'] = {c: int(r[c]) for c in CONSUMERS}
                else:
                    if active != key:
                        raise ValueError('end checkpoint without matching begin')
                    required = {'v', location_field, 'visit', 'frame', 'wired', 'checked', 'required', 'unique', 'overflow', 'errors', 'catalog_ok'}
                    if set(r) != required:
                        raise ValueError('end checkpoint fields differ from schema')
                    if any(int(r[k], 16) != REQUIRED for k in ('wired', 'checked', 'required')):
                        raise ValueError('incomplete per-room consumer coverage')
                    if int(r['overflow']) or int(r['errors']) or r['catalog_ok'] != '1':
                        raise ValueError('runtime overflow/error/catalog failure')
                    if int(r['unique']) != len(visits[key]['rows']):
                        raise ValueError('asset summary does not match emitted rows')
                    counts = visits[key]['counts']
                    if counts is None:
                        raise ValueError('missing consumer counter checkpoint')
                    if sum(counts.values()) < len(visits[key]['rows']):
                        raise ValueError('consumer emission counts cannot explain asset rows')
                    if any(counts[c] < visits[key]['first_consumers'][c] for c in CONSUMERS):
                        raise ValueError('per-consumer count cannot explain its logged first-use rows')
                    if any(counts[c] < 0 for c in CONSUMERS) or int(r['frame']) < 0:
                        raise ValueError('negative counter/frame')
                    visits[key]['ended'] = True
                    previous_scope = scope
                    active = None
            except (ValueError, KeyError, TypeError) as error:
                failures.append(f'{location}: {error}')
        if active is not None:
            failures.append(f'{name}: missing end checkpoint for {active[1]} visit {active[2]}')
        if not file_visits:
            failures.append(f'{name}: missing diagnostic room coverage')
        if startup_visits != 1:
            failures.append(f'{name}: missing named startup diagnostic coverage')
    if not visits:
        failures.append('no complete diagnostic room visits; missing diagnostic coverage is not a pass')
    if not observed:
        failures.append('no diagnostic game rooms; startup alone is not route coverage')
    for room in sorted(set(requested) - observed):
        failures.append(f'{room}: requested room has no diagnostic coverage')
    for key, visit in visits.items():
        if not visit['ended']:
            failures.append(f'{key[1]} visit {key[2]}: no valid final checkpoint')
    return {'schema': 1, 'gate': 'GC-ASSET', 'pass': not failures,
            'rooms': sorted(observed), 'visits': len(visits),
            'allowed_used': len(set().union(*(v['rows'] for v in visits.values()))) if visits else 0,
            'failures': failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logs', type=Path, nargs='+')
    parser.add_argument('--allowlist', type=Path, default=HERE / 'allowlist.json')
    parser.add_argument('--baseline', type=Path, required=True,
                        help='last accepted allowlist; current entries must be its subset (not an original ceiling)')
    parser.add_argument('--room', action='append', default=[], help='required room, e.g. 0111')
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    try:
        allow = read_allowlist(args.allowlist, args.baseline)
        if any(not ROOM.fullmatch(r) for r in args.room):
            raise ValueError('--room must contain four lowercase hexadecimal digits')
        result = judge([(str(p), p.read_text(encoding='utf-8', errors='replace')) for p in args.logs], allow, args.room)
    except (ValueError, OSError, TypeError, KeyError) as error:
        result = {'schema': 1, 'gate': 'GC-ASSET', 'pass': False, 'failures': [str(error)]}
    output = json.dumps(result, indent=2) + '\n'
    if args.json:
        args.json.write_text(output, encoding='utf-8')
    print(output, end='')
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
