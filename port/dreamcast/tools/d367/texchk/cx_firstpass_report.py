#!/usr/bin/env python3
"""Reassess retained first-pass evidence without rerunning or changing captures.

The selection file explicitly names current runs per room; older captures remain
listed as history. No missing run, census, or provenance is promoted to PASS.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re

import cx_firstpass_check as checker
import texchk


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def combine(values):
    return 'FAIL' if 'FAIL' in values else 'PASS' if values and all(v == 'PASS' for v in values) else 'UNPROVEN'


def memory(text):
    worlds, vram = [], []
    for line in text.splitlines():
        if 'PS2MESH open bytes=' in line:
            f = checker.fields(line)
            item = {'line': line, 'world_bytes': int(f['bytes'])}
            if re.fullmatch(r'\d+->\d+', f.get('heap', '')):
                before, after = map(int, f['heap'].split('->'))
                item.update(heap_free_before=before, heap_free_after=after, heap_consumed=before-after)
            worlds.append(item)
        if 'native UI VRAM:' in line:
            f = checker.fields(line)
            vram.append({k: int(v) for k, v in f.items() if v.isdigit()})
    return {'world_opens': worlds, 'vram_latest': vram[-1] if vram else None,
            'vram_sampled_used_max': max((r.get('used', 0) for r in vram), default=None),
            'vram_sampled_free_min': min((r['free'] for r in vram if 'free' in r), default=None),
            'scope': 'observations in this capture only; not combined-image or hardware acceptance'}


def inspect_run(path):
    stage_path, manifest_path = path/'stage.json', path/'payload-manifest.json'
    log = path/'capture/run-output.txt'
    stage, manifest, run = read(stage_path), read(manifest_path), read(path/'capture/run-result.json')
    room = stage['fixture']['provenance']['cx_room']['room']
    raw = log.read_bytes()
    text = raw.decode('latin1')
    checks = checker.assess(text, room)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        tex_pass = texchk.check(log)
    checks['tex_check'] = {'status': 'PASS' if tex_pass else 'FAIL', 'report': output.getvalue()}
    if tex_pass and checks['ps2_world_draw']['status'] != 'PASS':
        checks['tex_check'].update(status='UNPROVEN', reason='generic texture coverage does not establish a live target world')
    expected = {'status': 'RUN_COMPLETE_AWAITING_REVIEW', 'reader_exit': 0,
                'owned_emulator_exited': True, 'errors': []}
    missing = [k for k in expected if k not in run]
    bad = [k for k, v in expected.items() if k in run and run[k] != v]
    checks['capture'] = {'status': 'FAIL' if bad else 'UNPROVEN' if missing else 'PASS',
                         'missing': missing, 'mismatched': bad, 'result': run}
    identity = ('scenario', 'arm', 'elf_sha256', 'disc_sha256')
    absent = [k for k in identity if not run.get(k) or not stage.get(k)]
    mismatched = [k for k in identity if run.get(k) and stage.get(k) and run[k] != stage[k]]
    if stage.get('scenario') and stage['scenario'] != path.name:
        mismatched.append('directory_scenario')
    checks['evidence_identity'] = {'status': 'FAIL' if mismatched else 'UNPROVEN' if absent else 'PASS',
                                   'missing': absent, 'mismatched': mismatched}
    expected_stage = {'status': 'STAGED_PAYLOAD_IDENTITY_PASS', 'both_namespaces_verified': True,
                      'independent_raw_reader_verified': True, 'boot_area_preserved': True}
    absent = [k for k in expected_stage if k not in stage]
    mismatched = [k for k, v in expected_stage.items() if k in stage and stage[k] != v]
    checks['staged_payload'] = {'status': 'FAIL' if mismatched else 'UNPROVEN' if absent else 'PASS',
                               'missing': absent, 'mismatched': mismatched}
    fixture = stage['fixture']
    fixture_digest = hashlib.sha256(json.dumps(fixture, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'scenario': path.name, 'room': room, 'checks': checks, 'memory': memory(text),
            'log': str(log), 'log_sha256': hashlib.sha256(raw).hexdigest(),
            'stage_sha256': sha(stage_path), 'payload_manifest_sha256': sha(manifest_path),
            'embedded_fixture_canonical_sha256': fixture_digest,
            'embedded_fixture_hash_format': 'UTF-8 JSON sorted keys and compact separators; not original file SHA',
            'disc_sha256': stage.get('disc_sha256'), 'elf_sha256': stage.get('elf_sha256'),
            'warp_payload': manifest.get('dc/warp.txt'), 'pack_payload': manifest.get('dc/tex.pak'),
            'warp_source': fixture['replace'].get('dc/warp.txt'),
            'stills': [str(p) for p in sorted((path/'capture/shots').glob('*/frames/fb0.png'))],
            'disc_links_remaining': [str(p) for p in (path/'disc/disc.bin', path/'capture/disc.bin') if p.exists()]}


CHECKS = ('entry', 'no_fatal', 'warp_directives', 'ps2_world_draw', 'model_source_fallback',
          'model_ps2_asset_provenance', 'tex_check', 'capture', 'staged_payload', 'evidence_identity')


def unavailable(name, room):
    return {'scenario': name, 'room': room, 'checks': {key: {'status': 'UNPROVEN',
             'reason': 'selected capture is missing or incomplete'} for key in (*CHECKS, 'short_walk')},
            'memory': memory(''), 'log': None, 'disc_sha256': None, 'warp_source': None,
            'stills': [], 'unavailable': True}


def build_report(harness, readiness, texture_root, selection):
    captures = {}
    for path in sorted((harness/'scenarios').glob('cx-*')):
        required = ('capture/run-result.json', 'stage.json', 'payload-manifest.json', 'capture/run-output.txt')
        if all((path/name).is_file() for name in required):
            captures[path.name] = inspect_run(path)
    rooms = {}
    for room, fixture in readiness['rooms'].items():
        config = selection.get(room, {})
        names = config.get('scenarios', [])
        for name in names:
            if name not in captures:
                captures[name] = unavailable(name, room)
        selected = [captures[name] for name in names]
        if any(run['room'] != room for run in selected):
            raise ValueError('selection room mismatch: ' + room)
        if len(names) != len(set(names)):
            raise ValueError('duplicate selected scenario: ' + room)
        texture_path = texture_root/'rooms'/f'{room}.json'
        texture = read(texture_path)
        pack_selection = fixture.get('texture_selection')
        if config.get('pack_selection_report'):
            audit_path = Path(config['pack_selection_report'])
            audit = read(audit_path)
            row = audit['rooms'][room]
            pack_selection = {k: v for k, v in row.items() if k != 'textures'}
            pack_selection.update(report=str(audit_path), report_sha256=sha(audit_path), pack=audit['pack'])
        recommended = []
        for fixture_path in config.get('recommended_fixtures', []):
            path = Path(fixture_path)
            recommended.append({'path': str(path), 'sha256': sha(path)})
        summary = {key: combine([run['checks'][key]['status'] for run in selected])
                   for key in CHECKS}
        walk_names = config.get('walk_scenarios', [])
        if not set(walk_names).issubset(names):
            raise ValueError('walk selection must be a subset of current scenarios: ' + room)
        summary['short_walk'] = combine([captures[name]['checks']['short_walk']['status'] for name in walk_names])
        rooms[room] = {'checks': summary, 'overall': combine(list(summary.values())),
                      'blocker': config.get('blocker'), 'notes': config.get('notes', []),
                      'staging_list': str(texture_path), 'staging_list_sha256': sha(texture_path),
                      'world_texture_bytes_before': texture['standalone_world_payload_before'],
                      'world_texture_bytes_after': texture['standalone_world_payload_after'],
                      'texture_parser': texture['runtime_parser'],
                      'pack_selection': pack_selection, 'recommended_fixtures': recommended,
                      'preset_manifest': fixture['manifest'], 'standard_views': fixture['views'],
                      'runtime_fixture_blockers': fixture.get('blockers', []),
                      'selected_scenarios': names, 'walk_scenarios': walk_names,
                      'historical_scenarios': [name for name, cap in captures.items() if cap['room'] == room and name not in names],
                      'visual_review': config.get('visual_review', [])}
    return {'schema': 're4dc-firstpass-report/1', 'rooms': rooms, 'captures': captures,
            'gate_sources': {p.name: sha(p) for p in (Path(__file__), Path(checker.__file__), Path(texchk.__file__))},
            'scope': 'No STRICT/decision traces; no combined-image, physical-console, universal PS2-model or release acceptance.'}


def markdown(report):
    lines = ['# Codex room first-pass hand-back', '',
             'All numbers are bytes. World texture payload is a standalone asset total, not simultaneous resident VRAM.',
             'VQ policy: exact decoded alpha, RGB PSNR >=30 dB; preserve other native/twiddled data. No added mips.',
             'Pack precedence: matching packed key wins; otherwise selected loose file. Claude applies final pack changes.',
             'Model census PASS only covers instrumented source-fallback outcomes; universal PS2 asset provenance remains UNPROVEN.',
             'Older failing captures remain in the JSON history. Current checks use only the explicitly selected scenarios.', '', report['scope'], '']
    for room, item in report['rooms'].items():
        lines += [f'## {room}', '',
                  f"- Step 3: parser {item['texture_parser']}; world texture payload {item['world_texture_bytes_before']:,} -> {item['world_texture_bytes_after']:,}.",
                  f"- Step 4 staging list: `{item['staging_list']}`. Static selected-byte audit: {(item['pack_selection'] or {}).get('fixture_selection', 'UNPROVEN')}.",
                  f"- Step 5 preset/fixture manifest: `{item['preset_manifest']}`; standard names `cx-{room}-entry`, `cx-{room}-left`, `cx-{room}-right`, `cx-{room}-walk`.",
                  '- Steps 6-7: ' + '; '.join(f'{key}={value}' for key, value in item['checks'].items()) + '.',
                  f"- Overall: {item['overall']}." ]
        if item['blocker']:
            lines.append('- Blocker: ' + item['blocker'])
        if item['recommended_fixtures']:
            lines.append('- Current handoff fixtures: ' + ', '.join('`'+v['path']+'`' for v in item['recommended_fixtures']) + '.')
            lines.append('- Fixture variants above may add source-qualified dependencies beyond the captured views; exact tested assets are retained in each run\'s stage/payload manifest.')
        lines += ['- Note: ' + note for note in item['notes']]
        for name in item['selected_scenarios']:
            run = report['captures'][name]
            lines.append(f"- Run `{name}`; warp `{run['warp_source']}`; disc SHA-256 `{run['disc_sha256']}`.")
            for world in run['memory']['world_opens']:
                lines.append('- World heap: `' + world['line'] + '`.')
            m = run['memory']
            lines.append(f"- VRAM periodic samples: latest {m['vram_latest']}; maximum used {m['vram_sampled_used_max']}; minimum free {m['vram_sampled_free_min']}.")
            lines.append(f"- Log: `{run['log']}`. Stills: " + (', '.join('`'+p+'`' for p in run['stills']) or 'none') + '.')
            failures = [line for value in run['checks'].values() if isinstance(value, dict) for line in value.get('failures', [])]
            lines += ['- Failure evidence: `' + line + '`.' for line in failures[:4]]
        if not item['selected_scenarios']:
            lines.append('- Runtime world heap/VRAM and stills: UNMEASURED; no completed selected run.')
        lines += ['- Visual review: ' + note for note in item['visual_review']]
        lines.append('')
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--harness', type=Path, required=True)
    p.add_argument('--readiness', type=Path, required=True)
    p.add_argument('--textures', type=Path, required=True)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or args.output.with_suffix('.md').exists():
        p.error('refusing to overwrite an evidence report; use a new output name')
    report = build_report(args.harness, read(args.readiness), args.textures, read(args.selection))
    report['inputs'] = {str(path): sha(path) for path in (args.readiness, args.selection)}
    for name in ('cx-harness-provenance.json', 'cx-resolved-knobs.txt', 'programs-route.json'):
        path = args.harness/name
        report['inputs'][str(path)] = sha(path)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    args.output.with_suffix('.md').write_text(markdown(report))
    print(json.dumps({'report': str(args.output), 'rooms': len(report['rooms']), 'captures': len(report['captures'])}))


if __name__ == '__main__':
    main()
