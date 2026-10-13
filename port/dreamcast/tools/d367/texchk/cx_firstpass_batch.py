#!/usr/bin/env python3
"""Windows coordinator for owned first-pass room walks and two still views.

Uses the installed private harness and a read-only fixture tree in WSL. Each
worker retains logs, screenshots, stage metadata and hashes, then removes only
that finished scenario's disc links. No game builds, trace flags or runtime edits.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness-root', type=Path, required=True)
    parser.add_argument('--fixture-root', required=True)
    parser.add_argument('--checker', type=Path, required=True)
    parser.add_argument('--rooms', nargs='+', required=True)
    parser.add_argument('--distro', default='Ubuntu-24.04')
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--stager', default='stage-scenario.py',
                        choices=('stage-scenario.py', 'stage-scenario-v2.py'))
    parser.add_argument('--suffix', default='01')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('run with Windows Python; staging is dispatched to WSL')
    if args.workers < 1 or not re.fullmatch(r'[a-z0-9]+', args.suffix):
        parser.error('workers must be positive and suffix must be alphanumeric')
    if len(args.rooms) != len(set(args.rooms)) or any(not re.fullmatch(r'r[0-9a-f]{3}', room) for room in args.rooms):
        parser.error('rooms must be unique rXXX names')
    root = args.harness_root.resolve()
    if root.drive.lower() != 'c:':
        parser.error('this first-pass harness must stage on C:')
    linux_root = '/mnt/c/' + root.as_posix()[3:]
    native_fixtures = Path('\\\\wsl.localhost\\' + args.distro + args.fixture_root.replace('/', '\\'))
    run_script = root / 'run-emulator-novsync.py'
    stage_script = root / args.stager
    if not stage_script.is_file():
        parser.error(f'stager is missing: {stage_script}')
    harness = json.loads((root / 'cx-harness-provenance.json').read_text())
    assert harness['resolved_diagnostics']['LOGIC_TRACE'] == '0'
    assert harness['resolved_diagnostics']['GAME_DECISION_TRACE'] == '0'
    assert sha(run_script) == harness['installed_files']['run-emulator-novsync.py']
    hidden = {'creationflags': subprocess.CREATE_NO_WINDOW}

    def emit(**values):
        print(json.dumps(values), flush=True)

    def execute_room(room):
        results = []
        for view, seconds in (('walk', 60), ('left', 30), ('right', 30)):
            scenario = f'cx-{room}-{view}-{args.suffix}'
            stage = root / 'scenarios' / scenario
            fixture_name = f'cx-{room}-{view}.armed.json'
            fixture = native_fixtures / room / fixture_name
            assert fixture.is_file() and not stage.exists(), str(stage)
            inputs = {'fixture': str(fixture), 'fixture_sha256': sha(fixture),
                      'stager': args.stager, 'stager_sha256': sha(stage_script),
                      'checker_sha256_at_stage': sha(args.checker), 'room': room, 'view': view,
                      'seconds': seconds, 'traces': {'LOGIC_TRACE': 0, 'GAME_DECISION_TRACE': 0}}
            emit(scenario=scenario, status='STAGING')
            with (root / f'cx-stage-{scenario}.log').open('xb') as log:
                stage_run = subprocess.run(['wsl.exe', '-d', args.distro, '--exec', 'python3',
                    linux_root + '/' + args.stager, scenario, '--arm', harness['arm'],
                    '--programs', linux_root + '/programs-route.json',
                    '--overlay', '/mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads',
                    '--fixture', args.fixture_root + '/' + room + '/' + fixture_name],
                    stdout=log, stderr=subprocess.STDOUT, **hidden)
            if stage_run.returncode:
                emit(scenario=scenario, status='STAGE_FAILED', returncode=stage_run.returncode)
                return results + [{'scenario': scenario, 'status': 'STAGE_FAILED'}]
            meta = json.loads((stage / 'stage.json').read_text())
            assert meta['status'] == 'STAGED_PAYLOAD_IDENTITY_PASS'
            assert meta['fixture'] == json.loads(fixture.read_text()), 'fixture changed during staging'
            (stage / 'cx-inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
            (stage / 'disc.sha256').write_text(meta['disc_sha256'] + '  disc/disc.bin\n')
            (stage / 'PURPOSE.txt').write_text(f'Codex first-pass {room} {view}: source entry, native PS2 world, TEX_CHECK=2, census=1, both logic/decision traces=0. Retain {view} stills and actual gate evidence. No combined-image heap or physical-console acceptance.\n')
            with (stage / 'cx-runner.log').open('xb') as log:
                run = subprocess.run([sys.executable, str(run_script), scenario, '--seconds', str(seconds), '--period', '10'],
                                     stdout=log, stderr=subprocess.STDOUT, **hidden)
            run_result = json.loads((stage / 'capture/run-result.json').read_text())
            assert run_result['owned_emulator_exited'] is True
            capture_ok = (run.returncode == 0 and not run_result.get('errors')
                          and run_result['status'] == 'RUN_COMPLETE_AWAITING_REVIEW')
            gate_path = stage / 'cx-gate.json'
            gate_tools = stage / 'cx-gate-tools'
            gate_tools.mkdir()
            gate_sources = {}
            for source in (args.checker, args.checker.with_name('texchk.py')):
                target = gate_tools / source.name
                shutil.copyfile(source, target)
                gate_sources[source.name] = {'source': str(source), 'sha256': sha(target)}
            (stage / 'cx-gate-provenance.json').write_text(json.dumps(gate_sources, indent=2) + '\n')
            with (stage / 'cx-gate.log').open('xb') as log:
                gate_run = subprocess.run([sys.executable, '-B', str(gate_tools / args.checker.name), str(stage / 'capture/run-output.txt'),
                                           '--room', room, '--output', str(gate_path)], stdout=log, stderr=subprocess.STDOUT, **hidden)
            gates = json.loads(gate_path.read_text())
            assert gate_run.returncode in (0, 1, 2)
            for rel in ('disc/disc.bin', 'capture/disc.bin'):
                path = (stage / rel).resolve()
                assert path.is_relative_to(stage) and path.name == 'disc.bin'
                if path.exists():
                    assert sha(path) == meta['disc_sha256']
                    (path.parent / 'disc.sha256').write_text(meta['disc_sha256'] + '  disc.bin\n')
                    path.unlink()
            summary = {'scenario': scenario, 'status': run_result['status'], 'gate': gates['overall'],
                       'capture_returncode': run.returncode, 'capture_ok': capture_ok,
                       'capture_errors': run_result.get('errors', []),
                       'checks': {key: value['status'] for key, value in gates.items() if isinstance(value, dict) and 'status' in value},
                       'disc_sha256': meta['disc_sha256'], 'discs_removed': True}
            results.append(summary)
            emit(**summary)
            if not capture_ok:
                emit(room=room, status='STILL_VIEWS_DEFERRED', reason='capture did not complete successfully')
                break
            if view == 'walk' and (gates['no_fatal']['status'] != 'PASS' or gates['ps2_world_draw']['status'] != 'PASS'):
                emit(room=room, status='STILL_VIEWS_DEFERRED', reason='walk did not establish a live native room without fatal errors')
                break
        return results

    report = {'rooms': args.rooms, 'workers': args.workers, 'results': {}, 'errors': {}}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(execute_room, room): room for room in args.rooms}
        for future in as_completed(pending):
            room = pending[future]
            try:
                report['results'][room] = future.result()
                if any(result.get('capture_ok') is False for result in report['results'][room]):
                    report['errors'][room] = 'one or more captures did not complete successfully; see capture_returncode and capture_errors'
            except Exception as exc:
                report['errors'][room] = repr(exc)
                emit(room=room, status='WORKER_ERROR', error=repr(exc))
    out = root / ('cx-batch-' + '-'.join(args.rooms) + '-' + args.suffix + '.json')
    out.write_text(json.dumps(report, indent=2) + '\n')
    emit(status='BATCH_DONE', report=str(out), errors=report['errors'])
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
