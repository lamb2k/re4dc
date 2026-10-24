"""Append-only Motion source-review/target metadata archive; no SDK, guests or RAM audit."""
from pathlib import Path
import ast, datetime, hashlib, json, subprocess

TREE = Path('/root/work/lanes/gc23-evidence-tools')
PARENT = '92f31027a1373f864a413ca78ebaeb23978e51e7'
HEAD = 'aab201ceac0e18107f64a3212398afe916793327'
RUNTIME = 'fce285ddd77ced898b40f49ae310b91a539b7b5d'
TEST = '5e6b7d8c0f76e7431f1a7787459faa41fb0b507c'
PVS = 'b93b79836f35a4a6e51ccac458d584c98e0b2073'
RAIN_PLAN = '016757886d06d431e3e4adf42b91b3be36c348a8'
C = Path('/mnt/c/Game Dev/Emulators/codex-lanes')
M = C / 'gc-motion24'
E = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024')
HERE = Path(__file__).resolve().parent
DEST = TREE / 'port/dreamcast/tools/d367/gc23_evidence/20261024-motion33-provider-followup-v1'
OLD = TREE / 'port/dreamcast/tools/d367/gc23_evidence/20261024-readiness-catalog-motion-design-v1/SHA256SUMS'
sha = lambda data: hashlib.sha256(data).hexdigest()
read = lambda path: json.loads(path.read_text())

def git(*args):
    return subprocess.check_output(['git', '-C', str(TREE), *args])

def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    assert git('rev-parse', 'HEAD').decode().strip() == PARENT and not git('status', '--porcelain')
    assert digest(OLD) == '2266022c265062c54d044f718c094540413b59773c5ecef8fcb13db96c4fb980'
    assert not DEST.exists()
    selected = []; hash_only = []; verified = {}; shared = []
    def add(path, relative):
        assert path.is_file() and not path.is_symlink(), path
        allowed = path.suffix in {'.py', '.sh', '.json', '.md', '.txt', '.d', '.su'} or '.py.v' in path.name
        assert allowed and path.stat().st_size < 1000000, path
        selected.append((path, relative))
    def member(path, relative, pin=None):
        before = path.stat(); actual = digest(path); after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        if pin: assert before.st_size == pin['bytes'] and actual == pin['sha256'], path
        if path.suffix in {'.log', '.diff'}:
            hash_only.append({'source': str(path), 'bytes': before.st_size, 'sha256': actual,
                'source_mtime_ns': before.st_mtime_ns, 'copied': False,
                'scope': 'Private host/compiler log or already-Git-pinned runtime diff; identity only, payload excluded.'})
        else: add(path, relative)
    def manifest(root, label):
        pinpath = root / 'SHA256-MANIFEST.json'; pins = read(pinpath)
        for name, pin in pins.items(): member(root / name, Path(label) / name, pin)
        add(pinpath, Path(label) / pinpath.name)
        verified[label] = {'sha256': digest(pinpath), 'members': len(pins)}
        return pins
    def explicit_folder(root, label, names):
        for name in names: member(root / name, Path(label) / name)

    docs = read(HERE / 'stable-dated-inputs/CAPTURED-DOCS.json')
    for row in docs['files']:
        path = HERE / 'stable-dated-inputs' / row['snapshot']; assert digest(path) == row['sha256']
        add(path, Path('dated-20261024-root-snapshots') / row['snapshot'])
    add(HERE / 'stable-dated-inputs/CAPTURED-DOCS.json', Path('dated-20261024-root-snapshots/CAPTURED-DOCS.json'))
    for name in ['integration-readiness-motion-20261024.py', 'ROOT-INTEGRATION-READINESS-MOTION-20261024.json']:
        add(C / name, Path('dated-motion-integration-preview') / name)
    for name in ['ROOT-FINER-VISIBILITY-PLAN-20261024.md', 'ROOT-FINER-VISIBILITY-PLAN-v2-20261024.md']:
        add(C / 'interior-discovery24' / name, Path('dated-root-finer-visibility-plans') / name)
    root_names = ['run-target-motion24.py', 'run-target-motion24.sh', 'finalize-target-motion24.py',
        'check-wrap-providers.py', 'check-wrap-providers.py.v1', 'check-wrap-providers.py.v2', 'check-wrap-providers.sh',
        'root-host-receipt-readback.py', 'root-host-receipt-readback.py.v1', 'ROOT-HOST-RECEIPT-READBACK.json',
        'ROOT-TARGET-FINAL-RECEIPT.json', 'ROOT-TARGET-GRANT.json', 'ROOT-WRAP-PROVIDER-FAILURE-1.json',
        'ROOT-WRAP-PROVIDER-FAILURE-2.json', 'ROOT-WRAP-PROVIDER-RESULT.json']
    explicit_folder(M, 'motion-root-helpers-receipts', root_names)
    prep = manifest(M / 'target-prep', 'motion-target-preparation')
    assert len(prep) == 6
    explicit_folder(M / 'target-readback', 'motion-author-readback', ['READBACK.json', 'readback_target.py'])

    review = C / 'gc-port23/review-motion24'; review_receipt = read(review / 'REVIEW-CLEAR.json')
    assert review_receipt['observed_metadata_only_head'] == HEAD and review_receipt['runtime_source'] == RUNTIME
    for row in review_receipt['review_files']: member(review / row['path'], Path('motion-source-host-review') / row['path'], row)
    add(review / 'REVIEW-CLEAR.json', Path('motion-source-host-review/REVIEW-CLEAR.json'))
    host_pins = []
    manifest(E / 'source-5e6b7d8c0', 'motion-source-host-5e6')
    explicit_folder(E / 'source-fce285ddd', 'motion-source-host-fce',
        ['failed-sweep-sha256.json', 'focused.txt', 'host.log', 'result.json', 'source-pins.json', 'source.diff'])
    for directory in ['source-5e6b7d8c0', 'source-fce285ddd']:
        sourcepins = read(E / directory / 'source-pins.json')
        for row in sourcepins['files']:
            data = git('show', sourcepins['source'] + ':' + row['path'])
            assert len(data) == row['bytes'] and sha(data) == row['sha256']
            host_pins.append({'source': sourcepins['source'], 'path': row['path'], 'sha256': sha(data)})

    target = E / 'target-fce-current'; target_pins = manifest(target, 'motion-target33-root')
    assert len(target_pins) == 405
    independent = E / 'target-independent-readback-v1'; independent_pins = read(independent / 'SHA256-MANIFEST.json')
    assert len(independent_pins) == 410
    for name, pin in independent_pins.items():
        path = independent / name; assert path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256']
        if name in target_pins and pin == target_pins[name]:
            shared.append({'source': str(path), 'bytes': pin['bytes'], 'sha256': pin['sha256'],
                'canonical_source': str(target / name),
                'archive_destination': 'motion-target33-root/' + name if path.suffix != '.log' else 'HASH-ONLY-ARTIFACTS.json',
                'disposition': 'identical target metadata already copied' if path.suffix != '.log' else 'identical target log hash receipt; payload not copied'})
        else: member(path, Path('motion-independent-target-readback') / name, pin)
    add(independent / 'SHA256-MANIFEST.json', Path('motion-independent-target-readback/SHA256-MANIFEST.json'))
    verified['motion-independent-target-readback'] = {'sha256': digest(independent / 'SHA256-MANIFEST.json'),
        'members': len(independent_pins), 'identical_target_members_referenced': len(shared),
        'new_members_copied': len(independent_pins) - len(shared)}
    assert len(shared) == 397

    # Preserve the original incomplete provider report and later wrap semantics
    # as separate immutable evidence, never rewriting the earlier failure.
    failed = read(target / 'report.json'); summary = read(target / 'SUMMARY.json')
    assert failed['source'] == summary['source'] == HEAD and failed['runtime'] == RUNTIME
    assert not failed['complete'] and len(failed['objects']) == 33
    assert summary['compiled_arms'] == 33
    wrap = read(M / 'ROOT-WRAP-PROVIDER-RESULT.json')
    assert wrap['failed_run_report_sha256'] == digest(target / 'report.json')
    assert (independent / 'failed-report-original.json').read_bytes() == (target / 'report.json').read_bytes()
    assert set(failed['provider_closure']['missing']) == {r['reference'] for r in wrap['rewrites']}
    assert len(wrap['rewrites']) == 6 and all(wrap['synthetic_controls'].values())
    assert wrap['recompiled_game_objects'] == 0 and not wrap['actual_game_aliases_or_stubs_added']
    follow = read(independent / 'ROOT-FOLLOWUP-READBACK.json')
    assert follow['root_metadata_files'] == 405 and follow['root_manifest_sha256'] == digest(target / 'SHA256-MANIFEST.json')
    assert follow['initial_failed_report_preserved'] and follow['genuinely_new_unresolved_imports'] == 0
    assert read(independent / 'READBACK.json')['original_failed_report_sha256'] == digest(target / 'report.json')
    for source in [HEAD, RUNTIME, TEST, PVS, RAIN_PLAN]: assert git('rev-parse', source).decode().strip() == source
    add(Path(__file__).resolve(), Path('collect.py'))
    assert len({r for _, r in selected}) == len(selected)
    assert sum(p.stat().st_size for p, _ in selected) < 12 * 1024**2

    DEST.mkdir(parents=True)
    (DEST / '.gitattributes').write_text('* -text\n** -text\n')
    rows = []; syntax = []
    for path, relative in selected:
        before = path.stat(); data = path.read_bytes(); after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        assert b'\x00' not in data; data.decode('utf-8')
        if path.suffix == '.py' or '.py.v' in path.name: ast.parse(data.decode(), filename=str(path)); syntax.append(relative.as_posix())
        if path.suffix == '.sh': subprocess.run(['bash', '-n', str(path)], check=True); syntax.append(relative.as_posix())
        out = DEST / relative; out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('xb') as stream: stream.write(data)
        rows.append({'source': str(path), 'destination': relative.as_posix(), 'bytes': len(data), 'sha256': sha(data),
            'lf_sha256': sha(data.replace(b'\r\n', b'\n')), 'crlf_count': data.count(b'\r\n'), 'source_mtime_ns': before.st_mtime_ns})
    inventory = {'schema': 1, 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'parent_evidence_commit': PARENT, 'files': rows, 'root_moving_docs_captured_utc': docs['captured_utc'],
        'scope': 'Exact named source/review/compact dependency/stack/symbol metadata only. No runtime source export payloads, objects, SDK/game binaries, assets, programmes, capture/game logs, mutable discovery/DIAG work or unfrozen RAM audit.'}
    (DEST / 'SOURCE-MANIFEST.json').write_text(json.dumps(inventory, indent=2) + '\n')
    (DEST / 'HASH-ONLY-ARTIFACTS.json').write_text(json.dumps({'scope': 'Private log/runtime-diff payloads excluded; exact identities only.', 'files': hash_only}, indent=2) + '\n')
    (DEST / 'INDEPENDENT-SHARED-METADATA-REFERENCES.json').write_text(json.dumps({'scope': 'Exact independent bundle members shared with target33 metadata; reconstruct by canonical destination/hash receipt.', 'files': shared}, indent=2) + '\n')
    (DEST / 'REFERENCES.json').write_text(json.dumps({'GC_current_metadata_source': HEAD, 'GC_runtime_source': RUNTIME,
        'GC_host_test_source': TEST, 'PVS_reference_only': PVS, 'Rain_plan_reference_only': RAIN_PLAN,
        'PVS_discovery_or_Rain_DIAG_implementation_duplicated': False, 'RAM_audit_included': False}, indent=2) + '\n')
    validation = {'status': 'SOURCE_AND_METADATA_CHAIN_PRESERVATION_PASS', 'verified_metadata_manifests': verified,
        'host_source_pins_verified': host_pins, 'syntax_only_checked': syntax, 'target_arms_recorded': 33,
        'root405_metadata_members_verified': 405, 'independent410_members_verified': 410,
        'independent_identical_metadata_references': 397, 'independent_new_metadata_members': 13,
        'original_provider_incomplete_report_preserved': True, 'real_existing_wrap_followup_separate': True,
        'six_rewrite_references_match_original_missing': True, 'SDK_or_guest_runs': 0,
        'prior_snapshot_seal': digest(OLD), 'scope': 'Preservation checks only. No provider SDK recheck, recompilation, full-link, runtime heap/KOS/H2, stack-chain/IRQ, producer terminal, configured catalog, Motion positive provenance or full I001 acceptance.'}
    (DEST / 'VALIDATION.json').write_text(json.dumps(validation, indent=2) + '\n')
    (DEST / 'README.md').write_text('''# Motion33/provider-follow-up dated preservation milestone

Append-only successor to evidence92f. Moving root STATUS/updater/CARRY were frozen at07:33:28Z20261024 and remain independent live files. Preserves the Motion textual integration-readiness preview and root finer-visibility plansv1/v2 as dated planning records, not runtime/data acceptance.

GC metadata sourceaab201ce, runtimefce285dd and host-test5e6b7d8c are referenced to their immutable Git commits. Full bounded source/host review and receipts, root runner/wrapper/finalizer/wrap helpers with earlier failure versions, source/export preparation metadata, all405 target33 metadata identities and all independent410 readback identities are retained. Actual compile/dependency command arrays, dependency identities, sections, symbols and compiler self-frames are preserved; no object or full runtime-source exports are copied.

The original report remains incomplete with six existing ___real_pvr imports unresolved in its limited provider inventory. It is retained unchanged alongside the later real-existing-link-wrap/SDK-provider rewrite receipt and independent follow-up; no stub/alias or rebuilt-game-object substitute is inferred. Selected compile/disabled-identity results are not full-programme/provider runtime acceptance. Self-frames do not establish stack-chain/IRQ high-water. Motion remains a partial UNKNOWN-only detector, not positive lineage, wired completeness or full I001 acceptance.

To keep readback metadata compact,397 byte-identical independent members reference their canonical target metadata or log-hash receipt; all13 new independent members and its original manifest are copied. `INDEPENDENT-SHARED-METADATA-REFERENCES.json` gives exact source/path/size/hash reconstruction. Private host/compiler log and already-Git-pinned runtime diff payloads are hash-only in `HASH-ONLY-ARTIFACTS.json`.

PVSb93b79836 and Rain plan016757886 are references only. Mutable discovery, Rain-DIAG implementation, unfrozen RAM audit, assets, game/SDK binaries, programmes, objects, captures and raw game logs are excluded. No SDK/guest/integration operation occurs.

`SOURCE-MANIFEST.json` inventories exact copied bytes and diagnostic LF hashes; `.gitattributes` prevents CRLF normalization. `VALIDATION.json` records source/metadata and syntax-only checks. `SHA256SUMS` seals this milestone. Full committed Git export and reference reconstruction must pass before origin push; prior archives remain immutable.
''')
    lines = [sha(p.read_bytes()) + '  ' + p.relative_to(DEST).as_posix() for p in sorted(DEST.rglob('*')) if p.is_file()]
    (DEST / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')
    assert digest(OLD) == '2266022c265062c54d044f718c094540413b59773c5ecef8fcb13db96c4fb980'
    print(json.dumps({'snapshot': str(DEST), 'copied_inputs': len(rows), 'copied_bytes': sum(r['bytes'] for r in rows),
        'hash_only_artifacts': len(hash_only), 'independent_references': len(shared), 'host_source_checks': len(host_pins),
        'syntax_checks': len(syntax), 'seal_sha256': digest(DEST / 'SHA256SUMS')}, indent=2))

if __name__ == '__main__': main()
