"""Append-only source/metadata preservation; never copies media or executes helpers."""
from pathlib import Path
import datetime, hashlib, json, subprocess

TREE = Path('/root/work/lanes/dedup23-evidence-tools')
BASE = 'fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
DEST = TREE / 'port/dreamcast/tools/d367/dedup23_evidence/20261023-fb254e82-root-landing-v1'
C = Path('/mnt/c/Game Dev/Emulators')
LANE = C / 'codex-lanes/dedup-offline23'
E = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
RAM = Path('/dev/shm/root-dedup-prefetch-review-0d30')
sha = lambda data: hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(TREE), *args])

def read(path):
    return json.loads(path.read_text())

def main():
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    assert not git('status', '--porcelain')
    assert not DEST.exists()
    selected = []
    def add(path, destination):
        assert path.is_file() and not path.is_symlink(), path
        assert path.suffix in {'.py', '.sh', '.json', '.md', '.txt', '.sha256', '.cpp', '.h'} or path.name == 'SHA256SUMS', path
        selected.append((path, destination))
    def folder(path, destination):
        for file in sorted(path.rglob('*')):
            if file.is_file(): add(file, destination / file.relative_to(path))
    for file in sorted(LANE.glob('takeover-*')):
        add(file, Path('takeover-helpers') / file.name)
    folder(LANE / 'root-review4be', Path('root-runtime-review4be'))
    folder(LANE / 'root-qa-review4be', Path('root-qa-review4be'))
    folder(E / 'root-landing', Path('root-landing'))
    folder(E / 'root-private-delivery', Path('root-private-delivery'))
    for name in ['private-qa-pair-seal-r1.json', 'qa-delivery-checksum-readback-r1.json', 'qa-programme-pins-r1.json']:
        add(E / name, Path('worker-original-receipts') / name)
    add(E / 'qa-media-r1/pair-media-identity.json', Path('worker-original-receipts/pair-media-identity.json'))
    for arm in ['Off', 'On']:
        path = C / f'RE4DC-QA23-Dedup-{arm}-4be08e01'
        for name in ['README.txt', 'STEPS.txt', 'README-tooling.txt', 'IDENTITY.json', 'SHA256SUMS.txt', 'QUALIFICATION-PENDING.txt', 'ROOT-ACCEPTANCE.json', 'MEDIA-IDENTITY.json']:
            add(path / name, Path('current-private-metadata') / arm.lower() / name)
    for path in [C / 'codex-lanes/CODEX-TAKEOVER-STATUS.md', C / 'codex-lanes/CLAUDE-CARRY23.md', C / 'CONSOLE-DISCS-TEST23.md', LANE / 'STATUS.md', LANE / 'INBOX.md']:
        add(path, Path('dated-shared-snapshots') / path.name)
    for name in ['prefetch-context-controls.json', 'prefetch.cpp', 'missing-refresh.cpp', 'stale-reset.cpp']:
        add(RAM / name, Path('prefetch-synthetic-source') / name)
    folder(RAM / 'shim', Path('prefetch-synthetic-source/shim'))
    add(Path(__file__).resolve(), Path('collect.py'))

    # Preserve both worker-original and root-accepted metadata, without treating
    # current root acceptance as a rewrite of the older independently reviewed seal.
    seal = read(E / 'private-qa-pair-seal-r1.json')
    assert sha((E / 'private-qa-pair-seal-r1.json').read_bytes()) == '4180931954be3dc47e587bea96b82a550799c898a7491a9de4df5e01a69f95be'
    acceptance = read(E / 'root-private-delivery/ROOT-ACCEPTANCE.json')
    assert acceptance['status'] == 'ACCEPTED_FOR_PRIVATE_CONSOLE_FEEDBACK'
    assert acceptance['worker_seal_sha256'] == sha((E / 'private-qa-pair-seal-r1.json').read_bytes())
    delivery = read(E / 'root-private-delivery/DELIVERY-READBACK.json')
    for arm in ['off', 'on']:
        original = E / 'root-private-delivery' / arm
        assert sha((original / 'IDENTITY.json').read_bytes()) == seal['arms'][arm]['identity_sha256']
        assert sha((original / 'SHA256SUMS.txt').read_bytes()) == seal['arms'][arm]['sha256sums_sha256']
        current = C / f'RE4DC-QA23-Dedup-{arm.title()}-4be08e01'
        assert sha((current / 'IDENTITY.json').read_bytes()) == delivery[arm]['identity_sha256']
        assert sha((current / 'SHA256SUMS.txt').read_bytes()) == delivery[arm]['sums_sha256']
        assert read(current / 'IDENTITY.json')['status'] == 'ACCEPTED_FOR_PRIVATE_CONSOLE_FEEDBACK'
        assert (current / 'ROOT-ACCEPTANCE.json').read_bytes() == (E / 'root-private-delivery/ROOT-ACCEPTANCE.json').read_bytes()
        landing = read(E / f'root-landing/landing-build-{arm}-identity.json')
        assert landing['source'] == BASE and landing['all14_identical'] and landing['production_dedup'] == 0
        assert (E / f'root-landing/kos-{arm}-before.sha256').read_bytes() == (E / f'root-landing/kos-{arm}-after.sha256').read_bytes()
    control = read(RAM / 'prefetch-context-controls.json')
    assert control['source_head'] == '0d30bd83098af2bcd5e9ca2197ffd4cd926e73c4'
    assert control['comparisons'] == 96 and control['generated_cpp_sha256'] == sha((RAM / 'prefetch.cpp').read_bytes())

    DEST.mkdir(parents=True)
    (DEST / '.gitattributes').write_text('* -text\n** -text\n')
    rows = []
    destinations = set()
    for path, relative in selected:
        assert relative not in destinations
        destinations.add(relative)
        before = path.stat(); data = path.read_bytes(); after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), path
        assert len(data) <= 300000 and b'\x00' not in data, path
        data.decode('utf-8')
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as out: out.write(data)
        assert target.read_bytes() == data
        rows.append({'source': str(path), 'destination': relative.as_posix(), 'bytes': len(data), 'sha256': sha(data), 'source_mtime_ns': before.st_mtime_ns})
    manifest = {'schema': 1, 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'base_integration': BASE,
        'branch': 'wip/dedup23-evidence-tools-20261023', 'files': rows,
        'scope': 'Source/helpers/generated synthetic C++/metadata only. No binaries, ELFs, assets, images, tracks, capture logs/dumps, compiled scratch or production changes.',
        'metadata_chain': 'Worker original exact4be seal and root backup metadata precede root-accepted current metadata. Root acceptance is private console feedback, physical/hardware acceptance remains pending.',
        'live_snapshot_limit': 'Shared STATUS/CARRY/console registry and lane STATUS/INBOX are exact observed point-in-time bytes; they can advance independently after capture.'}
    (DEST / 'SOURCE-MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (DEST / 'README.md').write_text('''# Dedup23 root landing evidence snapshot

Append-only source/metadata checkpoint from exact integration fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2. This branch preserves root takeover helpers, runtime/QA reviews, actual new-head landing receipts, root private delivery, both worker-original and root-accepted metadata, observed dated shared status/carry/console registry, and synthetic prefetch controls plus generated source/shims.

`SOURCE-MANIFEST.json` records original paths, sizes, timestamps and SHA256. Files are copied as exact bytes; local `.gitattributes` disables line-ending conversion. `SHA256SUMS` seals the snapshot. Export verification must compare committed Git blobs to every selected source byte/hash.

The original exact4be QA pair is PREFETCH0/LEAN2=0. Later source0d30's96 synthetic host controls and two rejected mutants are preserved as source-only evidence; no target/guest/performance acceptance is added. Runtime/QA limits, known baseline Mendez fault and the distinction between actual final-GDI boot and fixture-proxy warp/H2 remain in their original reports. Root private acceptance is documented separately from physical acceptance. No production recipe flip follows.

Shared snapshots are point-in-time observations, not live control files. Re-strip I-001 is active separately after the root's actual origin integration push. This preservation operation makes no runtime/source implementation, SDK, guest or media change and copies no payloads, binary/ELF/track/image/capture dump or compiled scratch.
''')
    sums = []
    for path in sorted(DEST.rglob('*')):
        if path.is_file(): sums.append(sha(path.read_bytes()) + '  ' + path.relative_to(DEST).as_posix())
    (DEST / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')
    print(json.dumps({'destination': str(DEST), 'source_files': len(rows), 'source_bytes': sum(r['bytes'] for r in rows), 'snapshot_seal_sha256': sha((DEST / 'SHA256SUMS').read_bytes())}, indent=2))

if __name__ == '__main__': main()
