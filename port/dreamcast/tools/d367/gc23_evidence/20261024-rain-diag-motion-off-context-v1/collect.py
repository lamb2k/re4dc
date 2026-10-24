"""Append-only rain source review and original Motion OFF failure metadata."""
from pathlib import Path
import ast, datetime, hashlib, json, os, subprocess

TREE = Path('/root/work/lanes/gc23-evidence-tools')
RAIN_TREE = Path('/root/work/lanes/rain-diag24')
PARENT = 'c3aacc8f1573d238f1d5fde4775d643a6533a974'
RAIN = 'da413ff058f88fa136375ecff629610fc59c0e51'
RUNTIME = 'fdb5ed4212fc78823f625ab75b78cc237cfd181a'
BASE = 'bca44d58a1fa0a51fd87ba94deba8cba925c8998'
C = Path('/mnt/c/Game Dev/Emulators/codex-lanes')
HERE = Path(__file__).resolve().parent
DEST = TREE / 'port/dreamcast/tools/d367/gc23_evidence/20261024-rain-diag-motion-off-context-v1'
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_text())

def decode_source(data, name):
    try: return data.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:
        assert name.endswith('.md'), name
        return data.decode('cp1252'), 'windows-1252 byte-preserved original'

def git(tree, *args):
    return subprocess.check_output(['git', '-C', str(tree), *args])

def stable(path):
    before = path.stat(); data = path.read_bytes(); after = path.stat()
    assert not path.is_symlink() and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), path
    return data, before.st_mtime_ns

def digest(path):
    before = path.stat()
    with path.open('rb') as stream: value = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), path
    return {'source': str(path), 'bytes': before.st_size, 'sha256': value, 'source_mtime_ns': before.st_mtime_ns}

def main():
    assert git(TREE, 'rev-parse', 'HEAD').decode().strip() == PARENT
    assert not git(TREE, 'status', '--porcelain') and not DEST.exists()
    assert os.statvfs('/mnt/c').f_bavail * os.statvfs('/mnt/c').f_frsize > 24 * 1024**3
    selected = []; hash_only = []; checks = {}
    def add(path, relative, pin=None):
        data, mtime = stable(path)
        assert len(data) < 3 * 1024**2 and b'\0' not in data
        decode_source(data, str(path))
        if pin: assert len(data) == pin['bytes'] and sha(data) == pin['sha256'], path
        selected.append((str(path), relative, data, mtime))
    docs = read(HERE / 'stable-dated-inputs/CAPTURED-DOCS.json')
    for row in docs['files']:
        add(HERE / 'stable-dated-inputs' / row['snapshot'], 'dated-root-docs/' + row['snapshot'], row)
    add(HERE / 'stable-dated-inputs/CAPTURED-DOCS.json', 'dated-root-docs/CAPTURED-DOCS.json')

    rain = C / 'rain-diag24'; review = rain / 'review'; manifest = read(review / 'MANIFEST.json')
    assert sha((review / 'MANIFEST.json').read_bytes()) == 'f11c0ad62ae97c4efd0349b0ca32cecd7d44da0d325dc467dce54d533007e4f8'
    assert manifest['source'] == RAIN and manifest['runtime_tested'] == RUNTIME and len(manifest['files']) == 17
    for row in manifest['files']: add(review / row['path'], 'rain-independent-review/' + row['path'], row)
    add(review / 'MANIFEST.json', 'rain-independent-review/MANIFEST.json')
    for name in ['ROOT-FINAL-SOURCE-READBACK.json', 'root-final-source-readback.py', 'HANDBACK.md', 'STATUS.md']:
        add(rain / name, 'dated-rain-root/' + name)
    rootreadback = read(rain / 'ROOT-FINAL-SOURCE-READBACK.json')
    assert sha((rain / 'ROOT-FINAL-SOURCE-READBACK.json').read_bytes()) == '1dbe67ad94a2fdc0612f4eff8c0fc804ca42f1e776b4c3a02ed92b5b49cb8e5f'
    sourcepins = read(review / 'source-pins-final.json')
    changed = git(RAIN_TREE, 'diff-tree', '--no-commit-id', '--name-only', '-r', BASE, RAIN).decode().splitlines()
    assert sorted(changed) == sorted(row['path'] for row in sourcepins['changed_files']) and len(changed) == 11
    for row in sourcepins['changed_files']:
        data = git(RAIN_TREE, 'show', RAIN + ':' + row['path'])
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
        assert git(RAIN_TREE, 'rev-parse', RAIN + ':' + row['path']).decode().strip() == row['git_blob']
        if row['path'] in rootreadback['runtime_pins']:
            assert sha(data) == rootreadback['runtime_pins'][row['path']]
            assert data == git(RAIN_TREE, 'show', RUNTIME + ':' + row['path'])
        selected.append(('git:' + RAIN + ':' + row['path'], 'frozen-rain-source/' + row['path'], data, None))
    assert len(rootreadback['runtime_pins']) == 3
    for name in ['integration-readiness-motion-rain-diag-20261024.py', 'ROOT-INTEGRATION-READINESS-MOTION-RAIN-DIAG-20261024.json']:
        add(C / name, 'dated-integration-preview/' + name)
    preview = read(C / 'ROOT-INTEGRATION-READINESS-MOTION-RAIN-DIAG-20261024.json')
    assert sha((C / 'ROOT-INTEGRATION-READINESS-MOTION-RAIN-DIAG-20261024.json').read_bytes()) == '5e2a54ee49dccdf7617abad95e9f7338508645035b6b699d62e9501adf136cda'
    assert preview['preview_tree'] == rootreadback['integration_preview_tree'] == 'e0e692656194343054a83ae0787bed66475f568d'
    checks['rain_review_members'] = 17; checks['frozen_rain_changed_files'] = 11
    checks['actual_runtime_files_matching_fdb'] = 3

    prep = C / 'gc-motion24/full-link-prep'; prepmanifest = read(prep / 'SHA256-MANIFEST.json')
    assert len(prepmanifest) == 7
    for name, pin in prepmanifest.items(): add(prep / name, 'motion-original-preparation/' + name, pin)
    for name in ['SHA256-MANIFEST.json', 'ROOT-GRANT.json']: add(prep / name, 'motion-original-preparation/' + name)
    plan = read(prep / 'PREPARATION.json'); original = Path(plan['root'])
    assert str(original) == '/dev/shm/gc-motion24-full-pair-wrf50x14'
    faildata, _ = stable(original / 'receipt.json'); failure = json.loads(faildata)
    assert not failure['complete'] and set(failure['arms']) == {'off'} and failure['failure'] == 'AssertionError()'
    assert failure['runner_sha256'] == sha((prep / 'run_full_pair.py').read_bytes()) == '7251d227586634ef2654180791597de68282e3087ce0c3fe5a2fe097bc1890e6'
    assert failure['preparation_sha256'] == sha((prep / 'PREPARATION.json').read_bytes())
    add(original / 'receipt.json', 'motion-original-failed-OFF/receipt.json')
    for name in ['command.json', 'size.txt', 'sections.txt']:
        add(original / 'off' / name, 'motion-original-failed-OFF/off/' + name)
    add(original / 'off/out/resolved-knobs.txt', 'motion-original-failed-OFF/off/resolved-knobs.txt')
    # No SDK invocation: extract already-sealed root validator facts with JSON pointers.
    continuation = prep.parent / 'full-link-continuation/CONTINUATION.json'
    cdata, _ = stable(continuation); parent_sha = sha(cdata); cj = json.loads(cdata)
    assert parent_sha == 'd989ea016a0e19a349780d75d491e7a4efae258f39a0a38a9f85377bcf5c46a6'
    assert cj['original_failed_receipt_sha256'] == sha(faildata)
    assert cj['original_runner_sha256'] == failure['runner_sha256']
    off = cj['off']; assert off['helper']['allocated_bytes'] == 0 and off['helper']['meaningful_symbols'] == []
    assert off['raw_object_count'] == 448 and off['linked_motion_objects'] == [] and len(off['compiled_motion']) == 1
    assert off['raw_sha256'] == '49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b'
    assert len(off['OFF_overlay_identity']) == 14 and all(off['OFF_overlay_identity'].values())
    for name, pin in off['files'].items():
        path = original / 'off' / ('program.bin' if name == 'program.bin' else 'out/' + name)
        row = digest(path); assert row['bytes'] == pin['bytes'] and row['sha256'] == pin['sha256']
        hash_only.append(dict(row, payload_copied=False, scope='Original immutable OFF programme/ELF/overlay hash only; no bytes archived.'))
    for path, expected in [(original / 'off/build.log', off['build_log_sha256']),
            (original / 'off/out/obj/platform/gc_asset_motion_unknown.o', off['helper']['sha256'])]:
        row = digest(path); assert row['sha256'] == expected
        hash_only.append(dict(row, payload_copied=False, scope='Bulk build log or helper object identity only.'))
    extract = {'parent_source': str(continuation), 'parent_bytes': len(cdata), 'parent_sha256': parent_sha,
        'extracted_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'JSON_pointers': {'/source': cj['source'], '/scope': cj['scope'], '/original_failed_receipt_sha256': cj['original_failed_receipt_sha256'],
            '/original_runner_sha256': cj['original_runner_sha256'], '/preparation_sha256': cj['preparation_sha256'],
            '/off': off, '/negative_controls': cj['negative_controls'], '/result': cj['result'], '/no_execution': cj['no_execution']},
        'disclosure': 'Exact JSON field extraction from frozen root validator metadata; full continuation preparation/9013 preservation hash list and active runner/output are excluded. Existing helper ELF facts are root evidence, not a new SDK analysis. Independently rehashed OFF files, build log and helper object read-only; no payload copied. Original failed runner never finished acceptance. ON was not run by that original runner; no statement about later independent active continuation.'}
    add(prep.parent / 'full-link-continuation/READBACK.json', 'motion-root-validated-OFF-extract/READBACK.json')
    checks['original_failed_runner_preserved'] = True
    checks['OFF_existing_root_validator_extracted_separately'] = True
    checks['OFF_main_all14_hashes_independently_verified'] = True
    add(Path(__file__).resolve(), 'collect.py')
    assert len({row[1] for row in selected}) == len(selected)
    assert sum(len(row[2]) for row in selected) < 8 * 1024**2
    DEST.mkdir(parents=True); (DEST / '.gitattributes').write_text('* -text\n** -text\n')
    rows = []; syntax = []
    for source, relative, data, mtime in selected:
        assert b'\0' not in data; text, encoding = decode_source(data, relative)
        if relative.endswith('.py'): ast.parse(text, filename=source); syntax.append(relative)
        if relative.endswith('.sh'):
            subprocess.run(['bash', '-n'], input=data, check=True); syntax.append(relative)
        out = DEST / relative; out.parent.mkdir(parents=True, exist_ok=True); out.open('xb').write(data)
        rows.append({'source': source, 'destination': relative, 'bytes': len(data), 'sha256': sha(data),
            'lf_sha256': sha(data.replace(b'\r\n', b'\n')), 'crlf_count': data.count(b'\r\n'), 'text_encoding': encoding, 'source_mtime_ns': mtime})
    def emit(name, obj): (DEST / name).write_text(json.dumps(obj, indent=2) + '\n')
    emit('SOURCE-MANIFEST.json', {'schema': 1, 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'parent_evidence_commit': PARENT, 'root_docs_frozen_utc': docs['captured_utc'], 'files': rows})
    emit('HASH-ONLY-ARTIFACTS.json', {'files': hash_only, 'payloads_archived': False})
    emit('ROOT-VALIDATED-OFF-EXTRACT.json', extract)
    emit('VALIDATION.json', dict(checks, source_preservation_only=True, syntax_only_checked=syntax,
        SDK_or_guest_runs=0, active_source_or_runner_mutated=False, integration_or_recipe_mutated=False,
        remaining=['Rain target/cache/programme/heap/guest/source-lifecycle-look acceptance',
            'Motion full OFF/ON pair acceptance and ON pricing', 'Integrated runtime/heap/KOS/H2/catalog/consumer/terminal/hardware acceptance']))
    (DEST / 'README.md').write_text('''# Rain diagnostic source review and original Motion OFF failure context

Append-only successor of evidence c3aacc8f. Root updater/STATUS/CARRY are dated copies frozen at 08:04:03.232177Z on 2026-10-24; live files remain independent. Frozen rain da413ff metadata/runtime fdb5 has eleven changed source/test/receipt files; the three actual runtime files match reviewed fdb5 exactly. Independent seventeen-member final review includes original 94f HOLD and executable counterexamples. Small host JSON-result logs are deliberately retained as review evidence; no raw game logs or bulk build logs are copied. Root final readback and textual integration preview e0e692 are source-only records, not integration or target acceptance.

Motion original OFF compiled and linked. Its runner then failed line89 by incorrectly requiring no OFF compilation of the empty Motion helper. Original AssertionError receipt and exact runner remain unchanged. The separately extracted frozen root validator records an empty helper (allocated bytes0, no meaningful symbols), not linked among448 OFF objects, production main49a4173a and all14 overlays identical. OFF identities were independently rehashed without copying binaries or invoking SDK tools. The original runner did not start ON. Active later continuation files and outputs are excluded; this dated record makes no claim about their later progress or acceptance. Root validator facts are labelled as an exact JSON extraction with parent SHA and pointers, not newly generated SDK analysis.

Source metadata only: includes original full-pair preparation/dependency hash inventories, commands and root allocation contract. Actual private source export/SDK/game objects/programmes/ELF/media/assets/captures/raw game logs are absent. Bulk build log and original OFF binary identities are hash-only. No SDK, build, guest, source/runner mutation, integration push, default change, positive provenance, rain look, or full Motion pair acceptance. Original incomplete target33 provider receipt and later existing-wrap followup remain preserved separately in prior immutable snapshots. All previous archive paths remain unchanged.
''')
    files = sorted(p for p in DEST.rglob('*') if p.is_file())
    (DEST / 'SHA256SUMS').write_text(''.join(sha(p.read_bytes()) + '  ' + p.relative_to(DEST).as_posix() + '\n' for p in files))
    print(json.dumps({'snapshot': str(DEST), 'selected_inputs': len(rows), 'selected_bytes': sum(r['bytes'] for r in rows),
        'files': len(files) + 1, 'hash_only_artifacts': len(hash_only), 'seal': sha((DEST / 'SHA256SUMS').read_bytes()),
        'CRLF_inputs': sum(bool(r['crlf_count']) for r in rows), 'syntax_only_checks': len(syntax)}, indent=2))

if __name__ == '__main__': main()
