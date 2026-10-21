#!/usr/bin/env python3
"""Verify retained QA qualification inputs without editing or copying game data."""
import argparse
import hashlib
import json
from pathlib import Path

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve existing receipts'
    root = args.evidence
    records = {}
    for name, relative in {
        'pause': 'feedback21-runtime-20261021/pause-qualification.json',
        'qa': 'feedback21-boss-qa-20261021/qa-repair-binding.json',
        'qa_off': 'feedback21-boss-qa-20261021/qa-default-off-identity.json',
    }.items():
        path = root / relative
        records[name] = {'path': str(path), 'sha256': sha(path), 'receipt': json.loads(path.read_text())}
    assert records['pause']['receipt']['candidate']['unchanged_files'] == 1728
    assert len(records['pause']['receipt']['candidate']['off_overlays_14_exact']) == 14
    assert records['qa']['receipt']['disc_program_sha256'] == records['qa']['receipt']['elf_binary_sha256']
    recipe = root / 'feedback21-boss-qa-20261021/qa-builds/qa-on-1/resolved-knobs.txt'
    flags = recipe.read_text().split()
    assert 'GAME_SH4ZAM=1' in flags and 'SKIN_SH4ZAM=0' in flags
    assert not any(x == 'SS_WINDOW_HOLD_RESTORE=1' for x in flags)
    screenshots = records['pause']['receipt']['runtime']['screenshots']
    verified_shots = {}
    for name, rec in screenshots.items():
        path = Path(rec['path'])
        if not path.exists():
            # Retained Windows receipt paths when this verifier is run from WSL.
            path = root / rec['path'].split('/re4-dreamcast/', 1)[1]
        assert sha(path) == rec['sha256'], name
        verified_shots[name] = {'path': str(path), 'sha256': sha(path)}
    result = {
        'scope': 'Retained source/fixture receipts and screenshots only; no fresh target or hardware result',
        'records': records,
        'resolved_recipe': {'path': str(recipe), 'sha256': sha(recipe), 'flags': flags},
        'verified_screenshots': verified_shots,
        'restore_policy': 'No prior-program savestate accepted by the new combined program. Start fresh cold lineage.',
        'candidate': 'Pending private combined-source builds and exact program/ELF/14-overlay binding',
        'window_restoration': 'Disabled. Prior matched inventory cycle added 102 requests and 168032 bytes.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'output': str(args.output), 'receipt_count': len(records), 'verified_screenshots': len(verified_shots)}))

if __name__ == '__main__':
    main()
