"""Final append-only frozen source/metadata inventory. No active work/capture traversal."""
from pathlib import Path
import ast, datetime, hashlib, json, subprocess

TREE = Path('/root/work/lanes/gc23-evidence-tools')
PARENT = '47ed3ba2baaca4b4dd146a9d70128a69c3d47499'
CATALOG = 'a132648e8199b50a5ac51cec4d339fe7dbc60135'
BLOCKED = '5ec379b023a800a4e980108218b5242f4e2472ef'
RAIN = 'bca44d58a1fa0a51fd87ba94deba8cba925c8998'
RAIN_HELPERS = 'e0363d649a76a191a7b1b4b37a49abfbc2c6f072'
C = Path('/mnt/c/Game Dev/Emulators/codex-lanes')
E = Path('/mnt/c/Flycast-Evidence/re4-dreamcast')
HERE = Path(__file__).resolve().parent
DEST = TREE / 'port/dreamcast/tools/d367/gc23_evidence/20261024-readiness-catalog-motion-design-v1'
OLD = TREE / 'port/dreamcast/tools/d367/gc23_evidence/20261024-fullbuild-rain-bca44-v1/SHA256SUMS'
sha = lambda data: hashlib.sha256(data).hexdigest()
read = lambda path: json.loads(path.read_text())

def git(*args):
    return subprocess.check_output(['git', '-C', str(TREE), *args])

def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    assert git('rev-parse', 'HEAD').decode().strip() == PARENT and not git('status', '--porcelain')
    assert digest(OLD) == 'ebe7b73e4033b11b3c0809a299fb732159c3140609fcf084e740114a839aa4e9'
    assert not DEST.exists()
    selected = []; log_rows = []; checked_manifests = {}
    def add(path, relative):
        assert path.is_file() and not path.is_symlink(), path
        assert path.suffix in {'.py', '.sh', '.json', '.md', '.txt', '.cpp', '.d', '.su'}, path
        assert path.stat().st_size < 300000, path
        selected.append((path, relative))
    def member(path, relative, pin=None):
        before = path.stat(); actual = digest(path); after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        if pin:
            assert before.st_size == pin['bytes'] and actual == pin['sha256'], path
        if path.suffix == '.log':
            log_rows.append({'source': str(path), 'bytes': before.st_size, 'sha256': actual,
                'source_mtime_ns': before.st_mtime_ns, 'copied': False,
                'scope': 'Original retained privately; hash only, no log payload in source snapshot.'})
        else: add(path, relative)
    def mapping_manifest(root, label):
        path = root / 'SHA256-MANIFEST.json'; pins = read(path)
        for name, pin in pins.items(): member(root / name, Path(label) / name, pin)
        add(path, Path(label) / path.name)
        checked_manifests[label] = {'sha256': digest(path), 'members': len(pins), 'logged_members_hash_only': sum(Path(n).suffix == '.log' for n in pins)}
    def list_manifest(root, label, name='MANIFEST.json'):
        path = root / name; manifest = read(path)
        for pin in manifest['files']: member(root / pin['path'], Path(label) / pin['path'], pin)
        add(path, Path(label) / name)
        checked_manifests[label] = {'sha256': digest(path), 'members': len(manifest['files'])}
        return manifest

    stable = HERE / 'stable-dated-inputs'; docs = read(stable / 'CAPTURED-DOCS.json')
    for pin in docs['files']:
        assert digest(stable / pin['snapshot']) == pin['sha256']
        add(stable / pin['snapshot'], Path('dated-20261024-root-snapshots') / pin['snapshot'])
    add(stable / 'CAPTURED-DOCS.json', Path('dated-20261024-root-snapshots/CAPTURED-DOCS.json'))
    assert next(r['sha256'] for r in docs['files'] if r['snapshot'] == 'CLAUDE-CARRY23.md') == '7ca73aa8e2739283bda5be2541e5c345757dd032e3f91f549845fa085aae3436'

    interior = C / 'interior-vis23/triangle-shadow-next'
    for name in ['ROOT-CONNECTED-PATCH-REFINEMENT-20261024.md', 'review-connected-patch-plan.md',
                 'review-boundary-kernel.md', 'review-connected-implementation.md']:
        add(interior / name, Path('dated-crosslane-connected-notes') / name)
    for name in ['LOCATION-NOTE.md', 'READBACK.json']:
        add(C / 'water-rain24/river-location-audit' / name, Path('river-location-audit') / name)
    motion = list_manifest(C / 'gc-port23/motion-unknown-census', 'motion-frozen-design-census', 'SOURCE-SEAL.json')
    assert motion['source'] == CATALOG and motion['status'] == 'FROZEN_DESIGN_ONLY'
    assert len(motion['files']) == 7 and motion['total_member_bytes'] == 56636
    add(C / 'gc-port23/review-motion24/INITIAL-PLAN-REVIEW.md', Path('motion-initial-plan-review/INITIAL-PLAN-REVIEW.md'))
    for name in ['review-cataloga132', 'review-catalog5ec']:
        list_manifest(C / 'gc-port23' / name, name)
    cat_e = E / 'gc-catalog24-20261024'
    public_pins = []
    for directory, source in [('source-a132648e8', CATALOG), ('source-5ec379b02', BLOCKED)]:
        root = cat_e / directory; mapping_manifest(root, directory)
        receipt = read(root / 'receipt.json'); assert receipt['source'] == source
        assert receipt['host_log_sha256'] == digest(root / 'host.log')
        for path, expected in receipt['source_pins'].items():
            data = git('show', source + ':' + path); assert sha(data) == expected
            public_pins.append({'source': source, 'path': path, 'sha256': expected})
    assert read(cat_e / 'source-5ec379b02/receipt.json')['full_suite']['errors'] == 1
    assert read(cat_e / 'source-a132648e8/receipt.json')['full_suite']['errors'] == 0
    target = cat_e / 'target-a132-current'; mapping_manifest(target, 'target-a132-current')
    assert checked_manifests['target-a132-current']['members'] == 133
    report = read(target / 'report.json'); summary = read(target / 'SUMMARY.json')
    assert report['source'] == summary['source'] == CATALOG and report['complete']
    assert report['arm_count'] == 16 and summary['all16_complete'] and all(summary['off_identity'].values())
    target_helpers = ['catalog-target-a132-attempt1.py', 'catalog-target-a132.py', 'catalog-target-a132.sh', 'CATALOG24-TARGET-PREPARATION.json']
    for name in target_helpers: add(C / 'gc-catalog24' / name, Path('catalog-target-source-helpers') / name)
    assert report['harness_sha256'] == digest(C / 'gc-catalog24/catalog-target-a132.py')
    rain_root = E / 'water-rain24/rain-bca44-console55-20261024'
    for name in ['ROOT-PREFLIGHT-DECISION.json', 'ROOT-OFF-CANARY-REVIEW.json', 'ROOT-PAIR-RESULT.json']:
        add(rain_root / name, Path('rain-root-decisions-metadata-only') / name)
    assert read(rain_root / 'ROOT-PAIR-RESULT.json')['source'] == RAIN
    assert read(rain_root / 'ROOT-PREFLIGHT-DECISION.json')['grant']['source'] == RAIN
    assert git('rev-parse', RAIN_HELPERS).decode().strip() == RAIN_HELPERS
    add(Path(__file__).resolve(), Path('collect.py'))
    assert len({relative for _, relative in selected}) == len(selected)
    assert sum(p.stat().st_size for p, _ in selected) < 2 * 1024**2

    DEST.mkdir(parents=True)
    (DEST / '.gitattributes').write_text('* -text\n** -text\n')
    rows = []; syntax = []
    for path, relative in selected:
        before = path.stat(); data = path.read_bytes(); after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        assert b'\x00' not in data; data.decode('utf-8')
        if path.suffix == '.py': ast.parse(data.decode(), filename=str(path)); syntax.append(relative.as_posix())
        if path.suffix == '.sh': subprocess.run(['bash', '-n', str(path)], check=True); syntax.append(relative.as_posix())
        out = DEST / relative; out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('xb') as stream: stream.write(data)
        rows.append({'source': str(path), 'destination': relative.as_posix(), 'bytes': len(data),
            'sha256': sha(data), 'lf_sha256': sha(data.replace(b'\r\n', b'\n')),
            'crlf_count': data.count(b'\r\n'), 'source_mtime_ns': before.st_mtime_ns})
    manifest = {'schema': 1, 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'parent_evidence_commit': PARENT, 'files': rows, 'log_hash_only_count': len(log_rows),
        'scope': 'Only named frozen/explicitly dated source and compact metadata. No active motion/PVS/Y work traversal, capture/image/game log/track/programme/grant/attempt payload or runtime/object/private asset copy.',
        'dated_root_snapshot_time': docs['captured_utc'],
        'file_name_mapping': {'requested_rootintegration_readiness': 'integration-readiness-20261024.py', 'requested_review_connected_plan': 'review-connected-patch-plan.md'}}
    (DEST / 'SOURCE-MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (DEST / 'LOG-HASHES.json').write_text(json.dumps({'scope': 'Hash receipts only; all original log payloads remain private.', 'files': log_rows}, indent=2) + '\n')
    (DEST / 'REFERENCES.json').write_text(json.dumps({'rain_helpers_commit': RAIN_HELPERS,
        'rain_helpers_branch': 'origin/wip/water-rain24-canary-evidence-20261024', 'rain_helpers_duplicated': False,
        'prior_evidence_commit': PARENT, 'prior_snapshot_seal': digest(OLD)}, indent=2) + '\n')
    validation = {'status': 'FROZEN_SOURCE_METADATA_PRESERVATION_PASS', 'verified_manifests': checked_manifests,
        'public_source_pins_verified': public_pins, 'syntax_only_checks': syntax,
        'target133_members_verified': 133, 'target16_arms_recorded_only': True,
        'motion7_members_verified': 7, 'log_payloads_copied': 0, 'log_hash_receipts': len(log_rows),
        'SDK_or_guest_runs': 0, 'limits': ['Archival preservation only; source/target/design/canary reports retain their original limited qualification.',
            '5ec remains blocked; a132 host source and selected16 target arms do not establish full-link/runtime/producer-terminal/I001 acceptance.',
            'Motion census is frozen design-only; initial motion review is not acceptance of active implementation.',
            'Connected notes and river audit are dated source/offline records, not runtime/data/look/speed admission.',
            'Rain three ROOT decisions do not authorize further guest runs or establish full lifecycle/heap/physical acceptance.']}
    (DEST / 'VALIDATION.json').write_text(json.dumps(validation, indent=2) + '\n')
    (DEST / 'README.md').write_text('''# Final dated readiness/catalog/motion-design metadata successor

Append-only successor to evidence47ed. Root updater, takeover STATUS and CLAUDE carry were frozen at06:55:37Z20261024, including exact carry7ca73aa8; they are dated snapshots, never live replacements. Readiness helper/receipt preserves a textual preview only and does not land its obsolete1d63/rain preview.

Preserves connected-plan refinement and source/offline implementation reviews, river-location audit, exact sealed seven-member motion-unknown design census plus initial plan review, original blocked5ec and bounded source-clear a132 catalog receipts/reviews, and133 authenticated target-a132 metadata identities. Sixteen selected target arms are not a new full-link or runtime gate. Compiler/host log payloads are excluded; their exact sizes/hashes are in `LOG-HASHES.json`, while original manifests retain their original identities.

Only the three requested rain ROOT decision JSONs are copied. No captures, images, raw game logs, tracks, programmes, separate grant or attempts files are read/copied. Rain helpers already preserved at e0363d649a76a191a7b1b4b37a49abfbc2c6f072 are referenced only. Active GC-motion/PVS/Y work and other author files remain untouched. Original runtime, objects and assets remain private.

`SOURCE-MANIFEST.json` records exact copied paths/bytes/raw and diagnostic LF hashes. `.gitattributes` prevents normalization. `VALIDATION.json` records manifest and frozen public-source checks and syntax parsing only; no script/helper is executed, SDK acquired or guest run. No new source/runtime/data/look/performance acceptance follows. `SHA256SUMS` seals the snapshot; committed Git export must match every exact byte before origin push. Prior archives are immutable.
''')
    sums = [sha(p.read_bytes()) + '  ' + p.relative_to(DEST).as_posix() for p in sorted(DEST.rglob('*')) if p.is_file()]
    (DEST / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')
    assert digest(OLD) == 'ebe7b73e4033b11b3c0809a299fb732159c3140609fcf084e740114a839aa4e9'
    print(json.dumps({'snapshot': str(DEST), 'copied_inputs': len(rows), 'copied_bytes': sum(r['bytes'] for r in rows),
        'log_hash_only': len(log_rows), 'source_checks': len(public_pins), 'syntax_checks': len(syntax),
        'seal_sha256': digest(DEST / 'SHA256SUMS')}, indent=2))

if __name__ == '__main__': main()
