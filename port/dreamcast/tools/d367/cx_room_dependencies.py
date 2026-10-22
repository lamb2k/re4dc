#!/usr/bin/env python3
"""Discover and prepare private room lists, model archives, and event transports.

All dependency selection comes from the existing source tables and ESL rules.
This only prepares endian-correct files; model rendering and runtime module/audio
qualification remain separate. Existing fixture files always retain precedence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path[:0] = [str(TOOLS)]
from assetpipe.rooms import GcIso
from assetpipe.discover import Tables, ESL_FILES, esl_list_numbers, esl_entries, script_refs
from assetpipe.events import script_events
import le_mirror


def put(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def info(path):
    b = path.read_bytes()
    return dict(path=str(path), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--iso', required=True)
    ap.add_argument('--fixture-index', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    repo = HERE.parents[3]
    iso = GcIso(a.iso)
    table = Tables(repo)
    rooms = json.loads(a.fixture_index.read_text())
    cache = {}
    def convert(rel, event=False):
        if rel in cache:
            return cache[rel]
        row = {'source_rel': rel, 'qualification': 'UNPREPARED'}
        cache[rel] = row
        try:
            raw = iso.read(rel)
            src = a.out / 'source' / rel
            put(src, raw)
            mark = len(le_mirror.REPORT)
            data = bytearray(raw)
            if event:
                data, cert = le_mirror.prepare_event_reference(rel, raw)
                dst = a.out / 'prepared' / rel
                put(dst, data)
                put(Path(str(dst) + '.evq'), cert)
                row['evq'] = info(Path(str(dst) + '.evq'))
            else:
                le_mirror.convert_file(rel, data)
                records = le_mirror.REPORT[mark:]
                del le_mirror.REPORT[mark:]
                bad = [x for x in records if x.get('error') or not x.get('handled') or x.get('complete') is not True]
                if not records or bad:
                    row['conversion_errors'] = bad
                    raise ValueError('incomplete endian conversion')
                dst = a.out / 'prepared' / rel
                put(dst, data)
                row['native_binding_required'] = any(x.get('native_binding_required') for x in records)
            row.update(info(dst), qualification='PREPARED_ENDIAN_ONLY')
        except Exception as exc:
            row['error'] = str(exc)
        return row
    summary = {}
    for room in rooms:
        ident = int(room[1:], 16)
        listed = esl_list_numbers(ident)
        needed = {}
        deps, replacements = [], {}
        for number, condition in listed:
            if number is None:
                deps.append({'kind': 'enemy_list', 'condition': condition, 'status': 'inherits previous list; fresh warp state needs gameplay review'})
                continue
            rel = ESL_FILES[number]
            row = convert(rel)
            deps.append(dict(row, kind='enemy_list', condition=condition))
            if row.get('path'):
                replacements[rel] = row['path']
            source = a.out / 'source' / rel
            if source.exists():
                for e in esl_entries(source, ident):
                    needed.setdefault(e['id'], set()).add('ESL %s %s' % (rel, 'entry' if e['alive'] else 'enabled-later'))
        refs = script_refs(repo, ident)
        for eid in refs['loads']:
            needed.setdefault(eid, set()).add('source script load')
        for eid, why in sorted(needed.items()):
            spec = table.enemy(eid)
            if not spec:
                deps.append(dict(kind='enemy', enemy_id=eid, reasons=sorted(why), archive=None))
                continue
            rel = spec['archive'].lower()
            row = convert(rel)
            deps.append(dict(row, kind='enemy', enemy_id=eid, reasons=sorted(why), source_mapping=spec,
                             render_qualification='UNQUALIFIED: source archive contains GC model data; native PS2 replacement must be proved by census'))
            if row.get('path'):
                replacements[rel] = row['path']
        for name in script_events(repo, ident):
            rel = 'evd/' + name + '.evd'
            if not iso.find(rel):
                deps.append(dict(kind='event', source_rel=rel, on_disc=False))
                continue
            row = convert(rel, event=True)
            deps.append(dict(row, kind='event', on_disc=True))
            if row.get('path'):
                replacements[rel] = row['path']
                replacements[rel + '.evq'] = row['evq']['path']
        data = dict(room=room, dependencies=deps, replace_if_absent=replacements,
                    note='Endian preparation only. Never replace a reviewed fixture file with generic source model data. Runtime module, AICA bank, object/model native replacement and event gameplay acceptance remain unqualified.')
        save(a.out / 'rooms' / (room + '.json'), data)
        summary[room] = dict(path=str(a.out / 'rooms' / (room + '.json')), prepared=len(replacements),
                             errors=sum(bool(d.get('error')) for d in deps))
        save(a.out / 'index.json', summary)
        print(room, 'prepared', len(replacements), 'errors', summary[room]['errors'], flush=True)
    save(a.out / 'shared-preparation.json', cache)


if __name__ == '__main__':
    main()