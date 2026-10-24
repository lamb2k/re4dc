"""Preserve bounded GC static-target source and receipts; never run target helpers."""
from pathlib import Path
import ast, datetime, hashlib, json, subprocess

TREE = Path('/root/work/lanes/gc23-evidence-tools')
FROZEN = Path('/root/work/lanes/gc-port23')
SOURCE = '1d63cffe3a232c402418f2f2d919e7abae476957'
PRIOR = '77d8a20b2e6c6a8f3eccb6119081c27a3dd4ea22'
BASE = 'fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
C = Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23')
E = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-port23-20261023')
CURRENT = E / 'target-static1d63-current'
FAILURE = E / 'target-static77-current-failure'
DEST = TREE / 'port/dreamcast/tools/d367/gc23_evidence/20261024-static1d63-current-v1'
HELPERS = ['prepare-static-target-20261024.py', 'static-target-current-20261024.py',
    'static-target-current-20261024.sh', 'preserve-target-static77-failure-20261024.py',
    'prepare-static-target-successor-20261024.py', 'static-target-successor-20261024.py',
    'static-target-successor-20261024.sh', 'summarize-static-target-20261024.py']
sha = lambda b: hashlib.sha256(b).hexdigest()

def read(p):
    return json.loads(p.read_text())

def git(tree, *args):
    return subprocess.check_output(['git', '-C', str(tree), *args])

def main():
    assert git(TREE, 'rev-parse', 'HEAD').decode().strip() == SOURCE
    assert git(FROZEN, 'rev-parse', 'HEAD').decode().strip() == SOURCE
    assert git(TREE, 'status', '--porcelain') == git(FROZEN, 'status', '--porcelain') == b''
    assert not DEST.exists()
    current = read(CURRENT / 'report.json')
    summary = read(CURRENT / 'SUMMARY.json')
    prior = read(FAILURE / 'report.json')
    failure = read(FAILURE / 'FAILURE.json')
    prep = read(C / 'STATIC-TARGET-PREPARATION.json')
    successor = read(C / 'STATIC-TARGET-SUCCESSOR-PREPARATION.json')
    assert current['source'] == SOURCE and current['baseline'] == BASE and current['complete']
    assert len(current['objects']) == 67 and len(current['off_identity']) == 14 and all(current['off_identity'].values())
    assert current['prior_report_sha256'] == sha((FAILURE / 'report.json').read_bytes()) == '666759f4e9019398d854d959244c19080ffeee1edf323f8611ef5e874a679979'
    assert prior['source'] == PRIOR and not prior.get('complete')
    assert len(prior['objects']) == 51 and len(prior['off_identity']) == 12 and all(prior['off_identity'].values())
    assert failure['status'] == 'TARGET_COMPILE_FAILED' and failure['source'] == PRIOR
    assert summary['source'] == SOURCE and summary['objects'] == 67 and summary['off14_identical'] and summary['helpers5_off_empty']
    assert summary['reused'] == sum('reused_from' in row for row in current['objects']) == 49
    assert prep['new_harness_sha256'] == sha((C / 'static-target-current-20261024.py').read_bytes()) == prior['harness_source_sha256']
    assert prep['wrapper_sha256'] == sha((C / 'static-target-current-20261024.sh').read_bytes())
    assert successor['harness_sha256'] == sha((C / 'static-target-successor-20261024.py').read_bytes()) == current['harness_source_sha256']
    assert successor['wrapper_sha256'] == sha((C / 'static-target-successor-20261024.sh').read_bytes())
    old_harness = git(FROZEN, 'show', PRIOR + ':port/dreamcast/tools/d367/gc_port23/target_current_objects.py')
    assert sha(old_harness) == prep['old_harness_sha256']
    metadata = read(CURRENT / 'METADATA-MANIFEST.json')
    assert len(metadata) == 335
    for name, pin in metadata.items():
        data = (CURRENT / name).read_bytes()
        assert len(data) == pin['bytes'] and sha(data) == pin['sha256'], name
    assert {p.name for p in CURRENT.iterdir() if p.is_file()} == set(metadata) | {'report.json', 'SUMMARY.json', 'METADATA-MANIFEST.json'}
    for name, digest in failure['preserved'].items():
        assert sha((FAILURE / name).read_bytes()) == digest
    for name in HELPERS:
        path = C / name
        if path.suffix == '.py': ast.parse(path.read_text(), filename=name)
        else: subprocess.run(['bash', '-n', str(path)], check=True)
        # The preparation intentionally emits LF Python/shell helpers on Windows.
        assert b'\r' not in path.read_bytes(), ('helper not intentional LF', name)

    selected = [(C / name, Path('helpers') / name) for name in HELPERS]
    selected += [(p, Path('preparation') / p.name) for p in sorted(C.glob('STATIC-TARGET*.json'))]
    for directory, label in [(CURRENT, 'target-static1d63-current'), (FAILURE, 'target-static77-current-failure')]:
        selected += [(p, Path(label) / p.relative_to(directory)) for p in sorted(directory.rglob('*')) if p.is_file()]
    selected.append((Path(__file__).resolve(), Path('collect.py')))
    assert sum(p.stat().st_size for p, _ in selected) <= 5 * 1024**2
    assert not any('STATUS' in p.name for p, _ in selected)
    DEST.mkdir(parents=True)
    (DEST / '.gitattributes').write_text('* -text\n** -text\n')
    rows = []
    for path, relative in selected:
        assert not path.is_symlink() and path.suffix in {'.py', '.sh', '.json', '.log', '.su', '.txt', '.d'}
        before = path.stat(); data = path.read_bytes(); after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), path
        assert len(data) < 250000 and b'\x00' not in data, path
        data.decode('utf-8')
        target = DEST / relative; target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as out: out.write(data)
        assert target.read_bytes() == data
        rows.append({'source': str(path), 'destination': relative.as_posix(), 'bytes': len(data), 'sha256': sha(data),
            'lf_sha256': sha(data.replace(b'\r\n', b'\n')), 'crlf_count': data.count(b'\r\n'),
            'lf_count': data.count(b'\n'), 'source_mtime_ns': before.st_mtime_ns})
    manifest = {'schema': 1, 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'runtime_source': SOURCE, 'prior_failed_source': PRIOR, 'baseline': BASE, 'files': rows,
        'scope': 'Root helpers/preparation and bounded compiler reports/commands/input hashes/stack/undefined/dependency diagnostics only; no object, ELF, binary, media, image, catalog, private asset or frozen runtime source mutation.',
        'line_endings': 'Exact original bytes retained. Eight generated/helper Python/shell files are intentional LF and match raw preparation hashes. Other Windows-authored receipts may be CRLF; lf_sha256 diagnoses differences only, never normalizes stored bytes.'}
    (DEST / 'SOURCE-MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    validation = {'status': 'SOURCE_AND_METADATA_CHAIN_PASS_NO_TARGET_EXECUTION',
        'current_report_sha256': sha((CURRENT / 'report.json').read_bytes()),
        'summary_sha256': sha((CURRENT / 'SUMMARY.json').read_bytes()),
        'metadata_manifest_sha256': sha((CURRENT / 'METADATA-MANIFEST.json').read_bytes()),
        'failure_receipt_sha256': sha((FAILURE / 'FAILURE.json').read_bytes()),
        'prior_report_sha256': sha((FAILURE / 'report.json').read_bytes()),
        'current_arms': 67, 'current_off_identical': 14, 'reused_arms': 49,
        'prior_partial_arms': 51, 'prior_off_identical': 12,
        'metadata_files_verified': 335, 'helper_AST_or_shell_syntax_checks': len(HELPERS),
        'objects_read_or_copied': 0, 'SDK_or_guest_runs': 0,
        'compiler_summary_only': {'delta': summary['delta'], 'delta_total': summary['delta_total'], 'synthetic_pin': summary['synthetic_catalog_pin_text_data_bss']},
        'limits': summary['limits']}
    (DEST / 'VALIDATION.json').write_text(json.dumps(validation, indent=2) + '\n')
    (DEST / 'README.md').write_text('''# GC23 selected-target preservation

Append-only source and compact compiler metadata snapshot. Current runtime source1d63cffe3a232c402418f2f2d919e7abae476957 continues the retained failed77d8a20b2e6c6a8f3eccb6119081c27a3dd4ea22 attempt against actual currentfb254e82 baseline/profile. The original failure remains a failure:51 completed arms/12 OFF identities before native_static ON compilation rejected an undeclared macro. Current67-arm matrix completes14 existing units plus five helpers and one synthetic catalog-pin arm, including49 explicitly pinned reused arms. The source/profile/SDK/input/normalized-command/object identity chain is recorded in the original reports; no objects are archived here.

The preserved summary reports selected-object text/data/BSS delta45,656/128/17,408 =63,192 bytes, with synthetic pin +445 text bytes separately. These are source receipts, not a new independent compiler run or final-link/heap/KOS/H2/guest/provenance qualification. Compiler self-frames do not establish call-chain/IRQ high-water. Coverage3ff/wired1f6 remains incomplete.

`helpers/` preserves the eight requested root preparation/failure/continuation/summary helpers; they are not executed by preservation. `preparation/` preserves exact STATIC-TARGET JSONs. The two evidence subdirectories contain only bounded reports, command arrays, dependency/input hashes, compiler diagnostic logs, stack and undefined-symbol metadata. STATUS, runtime source edits, object/ELF bytes, private catalogs/assets, media, images and guest captures are excluded.

`SOURCE-MANIFEST.json` pins every selected original byte, size, timestamp, raw SHA256 and diagnostic LF-normalized SHA256. Helpers were intentionally emitted as LF and match their preparation hashes; CRLF metadata remains exact. Local `.gitattributes` prevents Git line-ending conversion. `VALIDATION.json` records syntax and receipt-chain checks only. `SHA256SUMS` seals the snapshot. A Git archive export must match every stored byte before origin push.
''')
    sums = [sha(p.read_bytes()) + '  ' + p.relative_to(DEST).as_posix() for p in sorted(DEST.rglob('*')) if p.is_file()]
    (DEST / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')
    assert git(FROZEN, 'rev-parse', 'HEAD').decode().strip() == SOURCE and git(FROZEN, 'status', '--porcelain') == b''
    print(json.dumps({'snapshot': str(DEST), 'inputs': len(rows), 'input_bytes': sum(r['bytes'] for r in rows),
        'seal_sha256': sha((DEST / 'SHA256SUMS').read_bytes()), 'metadata_chain': validation['status']}, indent=2))

if __name__ == '__main__': main()
