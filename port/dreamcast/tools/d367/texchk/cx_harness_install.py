#!/usr/bin/env python3
"""Install a private copy of the legacy first-pass stage/capture harness.

Run in WSL with an output root on /mnt/c. Staging runs in WSL; the copied
run-emulator-novsync.py runs in Windows. Neither command executes here.
The stage utility, media manifest, independent reader and base ISO remain
read-only at their original locations; scenarios and programs are private.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


SOURCE_HASHES = {
    'stage-scenario.py': '5c3d19e1e6cc3b5d627335a3f8212a791271bd5a32cc489cc734f87d292d1d7b',
    'run-emulator-novsync.py': '715a35ce9eb9f5568557d405cc23d02354fcf46c73a8dd14aa0b65009fe6b259',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-harness', type=Path, required=True)
    parser.add_argument('--candidate-dir', type=Path, required=True)
    parser.add_argument('--programs-json', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    source, candidate, output = (p.resolve() for p in
                                 (args.source_harness, args.candidate_dir, args.output_root))
    if not output.is_relative_to('/mnt/c') or output.is_relative_to(source):
        parser.error('output-root must be a private /mnt/c path outside the source harness')
    arm = candidate.name
    if not arm.startswith('candidate-routecx'):
        parser.error('candidate-dir must name a candidate-routecx arm')
    report = {'source_harness': str(source), 'output_root': str(output), 'arm': arm,
              'source_files': {}, 'read_only_dependencies': {}, 'installed_files': {}}
    for name, expected in SOURCE_HASHES.items():
        actual = sha(source / name)
        if actual != expected:
            parser.error('source harness changed; inspect before adapting: ' + name)
        report['source_files'][name] = {'path': str(source / name), 'sha256': actual}
    registry = json.loads(args.programs_json.read_text())
    program = registry[arm]
    resolved_path = Path(program['resolved_knobs'])
    resolved = dict(line.split('=', 1) for line in resolved_path.read_text().splitlines() if '=' in line)
    required = {'TEX_CHECK': '2', 'NATIVE_MODEL_REGISTRY_CENSUS': '1', 'LOGIC_TRACE': '0',
                'GAME_DECISION_TRACE': '0', 'DBG_WARP': '1', 'PC_SAMPLER': '1'}
    if any(resolved.get(key) != value for key, value in required.items()):
        parser.error('candidate must resolve to the authorized untraced first-pass diagnostics')
    report['resolved_diagnostics'] = {key: resolved[key] for key in required}
    report['resolved_knobs_source'] = str(resolved_path)
    report['installer_sha256'] = sha(Path(__file__))
    for name, meta in program['files'].items():
        path = candidate / name
        if path.name != name or not path.is_file() or sha(path) != meta['sha256']:
            parser.error('candidate file identity mismatch: ' + name)
    for name in ('renderer/inventory-uiorder-r1/stage-iso.py',
                 'integration-source-r11/MEDIA.json', 'gameplay/verify_cost_inputs.py'):
        path = source.parent / name
        report['read_only_dependencies'][name] = {'path': str(path), 'sha256': sha(path)}
    output.mkdir(parents=True, exist_ok=False)
    snapshots = output / 'source-snapshots'
    snapshots.mkdir()
    for name in SOURCE_HASHES:
        shutil.copyfile(source / name, snapshots / name)
        text = (source / name).read_text()
        if name == 'stage-scenario.py':
            old = 'HERE=Path(__file__).resolve().parent;ROOT=HERE.parent'
            assert text.count(old) == 1
            text = text.replace(old, 'HERE=Path(__file__).resolve().parent;ROOT=Path(' + repr(str(source.parent)) + ')')
            (output / name).write_text(text)
        else:
            # Keep capture behavior byte-identical; its __file__ supplies private HERE.
            shutil.copyfile(source / name, output / name)
        compile((output / name).read_text(), str(output / name), 'exec')
        report['installed_files'][name] = sha(output / name)
    program_dir = output / 'programs' / arm
    program_dir.mkdir(parents=True)
    for name in program['files']:
        shutil.copyfile(candidate / name, program_dir / name)
        report['installed_files']['programs/' + arm + '/' + name] = sha(program_dir / name)
    (output / 'programs-route.json').write_text(json.dumps({arm: program}, indent=2) + '\n')
    report['installed_files']['programs-route.json'] = sha(output / 'programs-route.json')
    shutil.copyfile(resolved_path, output / 'cx-resolved-knobs.txt')
    report['installed_files']['cx-resolved-knobs.txt'] = sha(output / 'cx-resolved-knobs.txt')
    report['stage_script_change'] = 'ROOT points to read-only source continuation; HERE derives from private copy'
    report['run_script_change'] = 'none; byte-identical copy derives private HERE from __file__'
    (output / 'cx-harness-provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'PRIVATE_HARNESS_READY', 'output_root': str(output), 'arm': arm,
                      'provenance': str(output / 'cx-harness-provenance.json')}, indent=2))


if __name__ == '__main__':
    main()
