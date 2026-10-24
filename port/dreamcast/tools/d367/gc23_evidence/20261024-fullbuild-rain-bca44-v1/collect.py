"""Append-only completed full-build/rain metadata preservation; no target execution."""
from pathlib import Path
import ast, datetime, hashlib, json, subprocess

TREE = Path('/root/work/lanes/gc23-evidence-tools')
PARENT = 'ee658c182d7c8d4c7a1154f220542c16ec4efd79'
GC = '1d63cffe3a232c402418f2f2d919e7abae476957'
RAIN = 'bca44d58a1fa0a51fd87ba94deba8cba925c8998'
BASE = 'fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
SH4ZAM = '33fa4850cacb30dd0ad35485ef035526ec4ce782'
C = Path('/mnt/c/Game Dev/Emulators/codex-lanes')
E = Path('/mnt/c/Flycast-Evidence/re4-dreamcast')
DEST = TREE / 'port/dreamcast/tools/d367/gc23_evidence/20261024-fullbuild-rain-bca44-v1'
OLD = TREE / 'port/dreamcast/tools/d367/gc23_evidence/20261024-static1d63-current-v1/SHA256SUMS'
GC_HELPERS = ['finalize-full-target-static1d63-20261024.py', 'full-target-static1d63-20261024.py',
    'full-target-static1d63-20261024.sh', 'full-target-static1d63-r2-20261024.py',
    'full-target-static1d63-r2-20261024.sh', 'prepare-full-target-static1d63-r2-20261024.py',
    'init-pinned-sh4zam-20261024.sh']
RAIN_HELPERS = ['finalize-full-target-rain-bca-20261024.py', 'finalize-target-rain-bca-20261024.py',
    'full-target-rain-bca-20261024.py', 'full-target-rain-bca-20261024.sh',
    'prepare-full-target-rain-bca-20261024.py', 'target-rain-bca-20261024.py',
    'target-rain-bca-20261024.sh', 'init-pinned-sh4zam-20261024.sh']
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_text())

def git(*args):
    return subprocess.check_output(['git', '-C', str(TREE), *args])

def main():
    assert git('rev-parse', 'HEAD').decode().strip() == PARENT and not git('status', '--porcelain')
    assert sha(OLD.read_bytes()) == 'f22ca3784095544b5b5f117b0f465f94bda1697e6d2c076bb59df61534aa05ec'
    assert not DEST.exists()
    selected = []
    def add(path, relative):
        assert path.is_file() and not path.is_symlink(), path
        assert path.suffix in {'.py', '.sh', '.json', '.md', '.txt', '.ld', '.cpp', '.log', '.d', '.su'}, path
        assert path.stat().st_size < 1000000, path
        if path.suffix == '.log': assert path.stat().st_size < 32768, ('build log bulk excluded', path)
        selected.append((path, relative))
    def folder(path, relative):
        for p in sorted(path.rglob('*')):
            if p.is_file(): add(p, relative / p.relative_to(path))
    for name in GC_HELPERS: add(C / 'gc-port23' / name, Path('gc-root-helpers') / name)
    for name in RAIN_HELPERS: add(C / 'water-rain24' / name, Path('rain-root-helpers') / name)
    roots = {
        'gc-full-current': E / 'gc-port23-20261023/full-target-static1d63-current',
        'gc-full-attempt1': E / 'gc-port23-20261023/full-target-static1d63-attempt1',
        'gc-full-link-readback': E / 'gc-port23-20261023/full-link-readback1d63',
        'rain-selected-target': E / 'water-rain24/rain-target-bca44-current',
        'rain-full-target': E / 'water-rain24/rain-full-target-bca44-current',
        'rain-review-bca': C / 'water-rain24/review-rain-bca',
        'rain-target-followup': C / 'water-rain24/rain-r10c-target-followup'}
    manifests_checked = {}
    for label, root in roots.items():
        assert root.is_dir(), root
        folder(root, Path(label))
        manifest = root / 'SHA256-MANIFEST.json'
        if manifest.exists():
            pins = read(manifest)
            for name, pin in pins.items():
                data = (root / name).read_bytes()
                assert len(data) == pin['bytes'] and sha(data) == pin['sha256'], (label, name)
            assert set(pins) == {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != manifest}
            manifests_checked[label] = {'sha256': sha(manifest.read_bytes()), 'members': len(pins)}
    add(C / 'water-rain24/verify-full-target-and-fixtures.py', Path('rain-readback-helper/verify-full-target-and-fixtures.py'))
    terminal = C / 'gc-port23/terminal-next-audit'
    assert sha((terminal / 'MANIFEST.json').read_bytes()) == '8e1fc89a474c186abd8d4366471e79905b768a0584ccd47d0d77cc528ba433c1'
    term = read(terminal / 'MANIFEST.json')
    assert term['source'] == GC and len(term['files']) == 15
    assert sum(row['bytes'] for row in term['files']) == 58444
    for row in term['files']:
        data = (terminal / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
        add(terminal / row['path'], Path('terminal-frozen1d63-audit') / row['path'])
    add(terminal / 'MANIFEST.json', Path('terminal-frozen1d63-audit/MANIFEST.json'))
    for name in ['takeover-refresh-20261024.py', 'CODEX-TAKEOVER-STATUS.md']:
        add(C / name, Path('dated-20261024-shared-snapshots') / name)
    proposal = C / 'interior-vis23/triangle-shadow-next/ROOT-CONNECTED-PATCH-PLAN-20261024.md'
    assert sha(proposal.read_bytes()) == 'e06087c1b0c877242ef2836f1e4bd937be93061aa0c6f0a91e96f7ffd6720f18'
    for path in [proposal, proposal.with_name('review-patch-union-implementation.md')]:
        add(path, Path('dated-20261024-crosslane-proposals/interior-vis23') / path.name)
    add(Path(__file__).resolve(), Path('collect.py'))

    # Revalidate only public source/text inputs. Do not read/copy SDK archives,
    # programme/overlay/object bytes, active rain trees or new canary outputs.
    checked_source = []
    tp = read(terminal / 'source-pins.json')
    assert tp['source'] == GC and tp['runtime_edited'] is False
    for row in tp['source_rows']:
        data = git('show', GC + ':' + row['path'])
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
        checked_source.append({'source': GC, 'path': row['path'], 'sha256': sha(data)})
    rain_readback = read(roots['rain-review-bca'] / 'READBACK.json')
    assert rain_readback['source_commit'] == RAIN
    for path, pin in rain_readback['files'].items():
        if 'git_blob_sha256' not in pin:
            # Historical external logs/status receipts remain reported pins;
            # they are outside this source-only revalidation and copy scope.
            continue
        relative = path.removeprefix('/root/work/lanes/water-rain24/')
        assert relative != path
        data = git('show', RAIN + ':' + relative)
        assert sha(data) == pin['git_blob_sha256'] == pin['physical_sha256']
        checked_source.append({'source': RAIN, 'path': relative, 'sha256': sha(data)})
    receipts = {label: read(roots[label] / 'receipt.json') for label in ['gc-full-current', 'rain-full-target']}
    for label, source, helper in [('gc-full-current', GC, C / 'gc-port23/full-target-static1d63-r2-20261024.py'),
                                  ('rain-full-target', RAIN, C / 'water-rain24/full-target-rain-bca-20261024.py')]:
        receipt = receipts[label]
        assert receipt['source'] == source and receipt['baseline'] == BASE and receipt['complete']
        assert set(receipt['arms']) == {'off', 'on'}
        assert receipt['source_script_sha256'] == sha(helper.read_bytes())
        summary = read(roots[label] / 'SUMMARY.json')
        assert summary['source'] == source and summary['off_programme_and_all14_identical'] and summary['missing_symbols_both'] == 0
        assert not summary['GC_alias_or_stub']
        assert summary['raw_hashes']['off'] == '49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b'
        for path, digest in receipt['pins'].items():
            marker = '/port/dreamcast/game/third_party/sh4zam/'
            if marker in path:
                relative = path.split(marker, 1)[1]
                data = subprocess.check_output(['git', '-C', '/root/work/lanes/rr/port/dreamcast/game/third_party/sh4zam', 'show', SH4ZAM + ':' + relative])
                assert sha(data) == digest
                checked_source.append({'source': SH4ZAM, 'path': relative, 'sha256': digest})
            elif path.endswith(('candidate.txt', 'resolved-knobs.txt')):
                assert sha(Path(path).read_bytes()) == digest
    prior = read(roots['gc-full-attempt1'] / 'receipt.json')
    assert prior['source'] == GC and not prior.get('complete')
    selected_report = read(roots['rain-selected-target'] / 'report.json')
    assert selected_report['source'] == RAIN and selected_report['complete']
    assert selected_report['baseline_absent_zero_identical']
    assert selected_report['harness_sha256'] == sha((C / 'water-rain24/target-rain-bca-20261024.py').read_bytes())
    assert sum(p.stat().st_size for p, _ in selected) < 8 * 1024**2
    assert len({r for _, r in selected}) == len(selected)

    DEST.mkdir(parents=True)
    (DEST / '.gitattributes').write_text('* -text\n** -text\n')
    rows = []
    syntax = []
    for path, relative in selected:
        before = path.stat(); data = path.read_bytes(); after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), path
        assert b'\x00' not in data; data.decode('utf-8')
        if path.suffix == '.py': ast.parse(data.decode(), filename=str(path)); syntax.append(relative.as_posix())
        if path.suffix == '.sh': subprocess.run(['bash', '-n', str(path)], check=True); syntax.append(relative.as_posix())
        out = DEST / relative; out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('xb') as stream: stream.write(data)
        rows.append({'source': str(path), 'destination': relative.as_posix(), 'bytes': len(data), 'sha256': sha(data),
            'lf_sha256': sha(data.replace(b'\r\n', b'\n')), 'crlf_count': data.count(b'\r\n'),
            'lf_count': data.count(b'\n'), 'source_mtime_ns': before.st_mtime_ns})
    manifest = {'schema': 1, 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'parent_evidence_commit': PARENT, 'gc_frozen_source': GC, 'rain_frozen_source': RAIN, 'baseline': BASE,
        'files': rows, 'scope': 'Source/JSON/markdown/text/symbol/section/alias metadata only. No objects/binaries/assets/raw game logs/build-log bulk, frozen tree mutation, SDK/guest or integration operation.',
        'rain_path_correction': 'Requested full-target-bca44-current does not exist; authenticated finalizer actual path rain-full-target-bca44-current is preserved.',
        'dated_snapshot_scope': 'takeover updater/summary are observed20261024 snapshots, not live replacements. Terminal snapshot uses exact frozen1d63 manifest; mutable later catalog-successor outputs and active rain canary trees/outputs are excluded.'}
    manifest['crosslane_proposal_scope'] = 'Connected-patch proposal and latest union implementation review are dated source/host/offline records only. No proposal, runtime/data or performance admission follows; no wait for pending connected-plan review.'
    (DEST / 'SOURCE-MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    validation = {'status': 'SOURCE_AND_METADATA_PRESERVATION_CHECKS_PASS', 'metadata_manifests': manifests_checked,
        'source_inputs_verified': checked_source, 'syntax_checked_not_executed': syntax,
        'terminal_manifest_sha256': sha((terminal / 'MANIFEST.json').read_bytes()),
        'prior_snapshot_seal_unchanged': sha(OLD.read_bytes()), 'objects_or_binaries_read_or_copied': 0,
        'SDK_or_guest_runs': 0, 'limits': ['Preserves prior full-build and selected-target receipts; not a new build/readback/runtime acceptance.',
            'Binary/SDK pins are retained as reported hashes only, without binary reads or copies.',
            'GC catalog0 only and rain lifecycle/ancestry/appearance/heap/KOS/H2/guest/hardware limitations remain in original reports.']}
    (DEST / 'VALIDATION.json').write_text(json.dumps(validation, indent=2) + '\n')
    (DEST / 'README.md').write_text('''# GC and rain completed-target evidence successor

Append-only successor to evidence ee658c182d7c8d4c7a1154f220542c16ec4efd79. GC metadata is frozen1d63, rain metadata frozenbca44, both against actualfb254 normal rP. Preserves root full-target/init-pinned helpers, original failed GC full attempt, completed GC/rain full-link receipts, selected rain target metadata, independent GC full-link readback, rain review/readback/follow-up plan, and frozen1d63 terminal counterexample source/control audit. The actual rain full-target path is `rain-full-target-bca44-current`.

Original reports distinguish selected objects, full normal rP links and independent readback. GC catalog0 adds reported61,032 linked section bytes; rain adds672 text bytes. OFF reproduces production main/all14. These are preserved prior results, not new SDK/guest, heap, KOS/H2, live rain ownership, provenance, appearance or hardware acceptance. Terminal counterexamples and catalog limitations remain explicit; no mutable catalog-successor result is admitted.

Updater and takeover summary are explicitly dated observed snapshots, not live control replacements. No active rain source/canary tree/output, runtime source mutation, object/ELF/overlay/SDK binary, asset, media, image, raw game log or build-log bulk is copied. Small link/compile diagnostic receipts and public symbol/section/alias text are retained.

The dated interior connected-patch proposal and latest union implementation review are preserved as crosslane source/host/offline records only. The proposal is not source/runtime accepted, and no data/runtime/performance admission or pending connected-plan review result is inferred.

`SOURCE-MANIFEST.json` is the exact inventory with raw SHA256, diagnostic LF-normalized SHA256, sizes and source timestamps. `.gitattributes` prevents line-ending conversion. `VALIDATION.json` records frozen public Git-source/SH4ZAM inputs, completed metadata manifests and syntax-only checks. `SHA256SUMS` seals this successor. Committed Git archive export must match every exact byte before origin push. Existing earlier archive remains unchanged.
''')
    lines = [sha(p.read_bytes()) + '  ' + p.relative_to(DEST).as_posix() for p in sorted(DEST.rglob('*')) if p.is_file()]
    (DEST / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')
    assert sha(OLD.read_bytes()) == 'f22ca3784095544b5b5f117b0f465f94bda1697e6d2c076bb59df61534aa05ec'
    print(json.dumps({'snapshot': str(DEST), 'inputs': len(rows), 'input_bytes': sum(r['bytes'] for r in rows),
        'source_checks': len(checked_source), 'syntax_checks': len(syntax), 'seal_sha256': sha((DEST / 'SHA256SUMS').read_bytes())}, indent=2))

if __name__ == '__main__': main()
