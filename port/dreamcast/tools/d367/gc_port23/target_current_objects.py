"""Bounded current-profile SH4 pricing; no link, stage or guest operations."""
from pathlib import Path
import hashlib
import io
import json
import os
import shlex
import subprocess
import tarfile
import tempfile

TREE = Path('/root/work/lanes/gc-port23')
GAME = TREE / 'port/dreamcast/game'
PROFILE = Path('/root/probe/lanes/route/out-au23on5e4drP')
BASE = 'd5c1ceab9e06461462669b3ce1d28a379747a74a'
UNITS = ['coarse_actor.cpp', 'platform/native_actor_fast.cpp', 'platform/native_ui.cpp',
         'platform/native_model.cpp', 'model_bridge.cpp', 'ui_bridge.cpp', 'platform/audio_aica.cpp',
         'platform/native_movie.cpp', 'platform/native_movie_stream.c', '../../../src/game/model.cpp',
         '../../../src/game/read.cpp', '../../../src/game/dvd.cpp']
EXTRA = ['platform/gc_asset_gate.cpp', 'platform/gc_asset_members.cpp', 'platform/gc_asset_payloads.cpp',
         'platform/gc_asset_audio.cpp', 'platform/gc_asset_disc.cpp']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(TREE), *args], text=True).strip()


def main():
    expected = os.environ['GCGATE_SOURCE']
    source = git('rev-parse', 'HEAD')
    if not source.startswith(expected) or git('status', '--porcelain'):
        raise RuntimeError('Expected clean frozen source')
    if git('merge-base', '--is-ancestor', BASE, source):
        raise RuntimeError('Unexpected ancestry output')
    knobs = dict(line.split('=', 1) for line in (PROFILE / 'resolved-knobs.txt').read_text().splitlines()
                 if line and not line.startswith('#') and '=' in line)
    required = dict(KOS_CACHE_P2='1', KOS_CACHE_P2_DIAG='0', STAT_ROUTINE_BYTES='1', ESP_POOL_RECYCLE='1',
                    R117_EFFECT_FAILURE_SAFE='1', R10C_SPAWN_LIVE_GUARD='1', EM_READ_RETRY='1',
                    COARSE_LEON='1', ACTOR_TRANSACTION='1', LEON_HAND_PACK='1', LEON_HAND_RETAIN='0')
    if any(knobs.get(name) != value for name, value in required.items()):
        raise RuntimeError('Current actual profile no longer matches required flags')
    commands = {}
    for line in (PROFILE / 'build.log').read_text().splitlines():
        if not line.startswith(('kos-c++ ', 'kos-cc ')):
            continue
        args = shlex.split(line)
        if '-c' not in args:
            continue
        unit = args[args.index('-c') + 1]
        if unit in UNITS or unit == 'platform/audio_stub.cpp':
            if unit in commands:
                raise RuntimeError('Ambiguous compiler receipt: ' + unit)
            commands[unit] = args
    if set(UNITS + ['platform/audio_stub.cpp']) - commands.keys():
        raise RuntimeError('Missing actual compiler commands')
    scratch = Path(tempfile.mkdtemp(prefix='gc-port23-current-' + source[:9] + '-', dir='/dev/shm'))
    baseline = scratch / 'baseline';baseline.mkdir()
    # Read-only source export, not a clone/worktree or target build tree. Keep
    # all original relative include paths; private generated inputs stay pinned.
    archived = subprocess.check_output(['git', '-C', str(TREE), 'archive', BASE,
                                       'port/dreamcast/game', 'port/dreamcast/room', 'src', 'include'])
    with tarfile.open(fileobj=io.BytesIO(archived)) as archive:
        archive.extractall(baseline, filter='data')
    del archived
    sdk = Path(os.environ['KOS_BASE']) / 'lib/dreamcast/libkallisti.a'
    bins = Path(os.environ['KOS_CC_BASE']) / 'bin'
    pins = {str(path): sha(path) for path in [sdk, *(PROFILE / name for name in ['candidate.txt', 'resolved-knobs.txt', 'build.log'])]}
    report = dict(source=source, baseline=BASE, profile=str(PROFILE), pins=pins, knobs=required, objects=[],
                  note='Selected objects only; default catalog pin0. No linked heap/image/guest/provenance acceptance.')
    (scratch / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(str(scratch), flush=True)
    for unit in UNITS + EXTRA:
        results = {}
        arms = [('baseline', None), ('absent', None), ('zero', 0), ('on', 1)] if unit in UNITS else [('zero', 0), ('on', 1)]
        if unit == 'platform/gc_asset_disc.cpp':arms.append(('on-synthetic-pin', 1))
        for arm, gate in arms:
            cwd = baseline / 'port/dreamcast/game' if arm == 'baseline' else GAME
            args = commands[unit if unit in commands else 'platform/audio_stub.cpp'].copy()
            args[args.index('-c') + 1] = unit
            label = unit.replace('../', '').replace('/', '_').rsplit('.', 1)[0] + '-' + arm
            output = scratch / (label + '.o');args[args.index('-o') + 1] = str(output)
            args = [arg for arg in args if arg not in ('-MMD', '-MD', '-MP')]
            for option in ['-MF', '-MT', '-MQ']:
                while option in args:
                    at = args.index(option);del args[at:at + 2]
            if gate is not None:
                args.append('-DRE4DC_GC_ASSET_GATE=' + str(gate))
            if gate:
                pin = '1' * 64 if arm == 'on-synthetic-pin' else '0'
                args.append('-DRE4DC_GC_ASSET_CATALOG_SHA256="' + pin + '"')
                if unit == 'platform/native_ui.cpp':args.append('-DRE4DC_GC_ASSET_COARSE_LEON=1')
                if unit == 'platform/native_actor_fast.cpp':args.append('-DRE4DC_GC_ASSET_LEON_HAND_PACK=1')
            args.append('-fstack-usage')
            (scratch / (label + '-command.json')).write_text(json.dumps(args, indent=2) + '\n')
            dependencies = scratch / (label + '.d')
            with (scratch / (label + '.log')).open('w') as log:
                subprocess.run(args + ['-M', '-MF', str(dependencies), '-MT', label], cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=True)
                paths = shlex.split(dependencies.read_text().split(':', 1)[1].replace('\\\n', ' '))
                before = {str((cwd / name).resolve()): sha((cwd / name).resolve()) for name in paths}
                subprocess.run(args, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=True)
                if any(sha(Path(name)) != digest for name, digest in before.items()):
                    raise RuntimeError('Compile inputs changed: ' + label)
            (scratch / (label + '-inputs.json')).write_text(json.dumps(before, indent=2) + '\n')
            stripped = scratch / (label + '-nodebug.o')
            subprocess.run([str(bins / 'sh-elf-objcopy'), '--strip-debug', str(output), str(stripped)], check=True)
            size = subprocess.check_output([str(bins / 'sh-elf-size'), str(output)], text=True)
            undefined = subprocess.check_output([str(bins / 'sh-elf-nm'), '-u', str(output)], text=True)
            (scratch / (label + '-undefined.txt')).write_text(undefined)
            defined = subprocess.check_output([str(bins / 'sh-elf-nm'), '--defined-only', str(output)], text=True)
            if unit in EXTRA and not gate and defined.strip():raise RuntimeError('OFF helper contains definitions: ' + unit)
            row = dict(unit=unit, arm=arm, sha256=sha(output), nodebug_sha256=sha(stripped), size=size, inputs=len(before))
            results[arm] = row;report['objects'].append(row)
            print(size.strip(), flush=True)
            (scratch / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        if unit in UNITS:
            identity = len({results[arm]['nodebug_sha256'] for arm in ['baseline', 'absent', 'zero']}) == 1
            report.setdefault('off_identity', {})[unit] = identity
            print('OFF baseline/absent/zero ' + unit + ': ' + ('IDENTICAL' if identity else 'MISMATCH'), flush=True)
    if git('rev-parse', 'HEAD') != source or git('status', '--porcelain') or any(sha(Path(path)) != value for path, value in pins.items()):
        raise RuntimeError('Frozen source/profile/SDK changed')
    report['complete'] = True
    (scratch / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('SELECTED OBJECTS COMPLETE; no full-programme or GC-ASSET pass', flush=True)


if __name__ == '__main__':main()
