#!/usr/bin/env python3
"""Audit generated private room fixtures without launching or changing the game."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def load(path):
    return json.loads(Path(path).read_text())


def archive_error_history(room_dir, manifest):
    """Associate conversion errors only with currently selected archive roots."""
    selected = set()
    for row in manifest.get('dependencies', []):
        if not row.get('destination', '').endswith(('.arc', '.dar')):
            continue
        selected.update(p for p in Path(row['source']).parents
                        if p.parent == room_dir and p.name.startswith('ancillary'))
    if not selected:
        # A failed preparation has no selected ARC/DAR yet; its exact current
        # failure path is recorded in the manifest, not inferred from mtime.
        for reason in manifest.get('blockers', []):
            for match in re.finditer(re.escape(str(room_dir)) + r'/ancillary(?:-[0-9a-f]+)?(?=/)', reason):
                selected.add(Path(match.group()))
    active, historical = [], []
    for folder in sorted(room_dir.glob('ancillary*')):
        if not folder.is_dir():
            continue
        for relative, dictionary in (('tex/native-ui-report.json', True),
                                     ('mirror/le_mirror_report.json', False)):
            p = folder / relative
            if not p.exists():
                continue
            report = load(p)
            rows = report.get('errors', []) if dictionary else [r for r in report if r.get('error')]
            target = active if folder in selected else historical
            target.extend(dict(report=str(p), **row) for row in rows)
    return active, historical, sorted(map(str, selected))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True, type=Path)
    ap.add_argument('--candidate-dir', required=True, type=Path)
    ap.add_argument('--dependencies', type=Path)
    ap.add_argument('--texture-audit', type=Path)
    ap.add_argument('--output', required=True, type=Path)
    a = ap.parse_args()
    index = load(a.root / 'index.json')
    textures = load(a.texture_audit)['rooms'] if a.texture_audit else {}
    rooms = {}
    for room in index:
        manifest_path = a.root / room / 'manifest.json'
        manifest = load(manifest_path)
        views = []
        required_archives = ['st' + room[1] + '/' + room + '.' + ext for ext in ('arc', 'dar')]
        reasons = list(manifest['blockers'])
        for view in ('entry', 'left', 'right', 'walk'):
            armed = a.root / room / ('cx-' + room + '-' + view + '.armed.json')
            diagnostic = a.root / room / ('cx-' + room + '-' + view + '.diagnostic-armed.json')
            path = armed if armed.exists() else diagnostic if diagnostic.exists() else None
            if not path:
                views.append({'view': view, 'status': 'UNARMED'})
                continue
            f = load(path)
            rep = f['replace']
            missing = [{'destination': k, 'source': p} for k, p in rep.items() if not Path(p).is_file()]
            absent = [k for k in required_archives if k not in rep]
            wrong = [k for k, p in rep.items() if re.fullmatch(r'dc/[a-z0-9_]+\.ovl', k)
                     and Path(p) != a.candidate_dir / Path(k).name]
            warp_path = Path(rep['dc/warp.txt'])
            warp_text = warp_path.read_text()
            errors = []
            if not re.search(r'^room 0x' + room[1:] + r'$', warp_text, re.M):
                errors.append('warp targets another room')
            if re.search(r'^(dead|kill) ', warp_text, re.M):
                errors.append('actor suppression in warp')
            if view == 'walk' and not re.search(r'^act \d+ fwd [1-9]\d*$', warp_text, re.M):
                errors.append('walk action missing')
            status = 'PASS_PATHS_AND_ARM' if not (missing or absent or wrong or errors) else 'BLOCKED_ASSET_OR_ARM'
            views.append(dict(view=view, status=status, fixture=str(path),
                              fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              diagnostic_only=path == diagnostic, missing_sources=missing,
                              required_archives_absent=absent, wrong_arm_overlays=wrong,
                              warp=str(warp_path), unsupported_status_requirement='status ' in warp_text,
                              errors=errors))
        dep_path = a.dependencies / 'rooms' / (room + '.json') if a.dependencies else None
        dep = load(dep_path) if dep_path and dep_path.exists() else None
        archive_errors, historical_errors, selected_roots = archive_error_history(a.root / room, manifest)
        if room[1] == '2':
            reasons.append('Common test9 arm does not provide required stage module: ' + str(manifest.get('stage_module')))
        if room == 'r11c':
            reasons.append('Required dc/pl14.ovl is absent from common arm. Full fixture stays unarmed; diagnostic removes only stale overlay.')
        selected = textures.get(room)
        if selected and selected['fixture_selection'] != 'PASS_SELECTED_RENDER_BYTES':
            reasons.append('Selected world texture bytes are shadowed by packed keys; see texture audit.')
        rooms[room] = dict(manifest=str(manifest_path), source_entry=manifest['entry_source'],
                           ancillary_status=manifest['ancillary_status'], stage_module=manifest.get('stage_module'),
                           views=views, blockers=reasons, archive_conversion_errors=archive_errors,
                           historical_archive_errors=historical_errors, selected_archive_roots=selected_roots,
                           dependency_manifest=str(dep_path) if dep_path else None,
                           dependency_errors=[d for d in dep['dependencies'] if d.get('error')] if dep else [],
                           texture_selection=selected,
                           runtime_acceptance='External first-pass logs must be associated with the exact fixture SHA; static checks never establish acceptance.')
    summary = dict(room_count=len(rooms), view_count=sum(len(r['views']) for r in rooms.values()),
                   views=dict(Counter(v['status'] for r in rooms.values() for v in r['views'])),
                   ancillary=dict(Counter(r['ancillary_status'] for r in rooms.values())),
                   diagnostic_only_views=sum(v.get('diagnostic_only', False) for r in rooms.values() for v in r['views']))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(dict(summary=summary, rooms=rooms), indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()