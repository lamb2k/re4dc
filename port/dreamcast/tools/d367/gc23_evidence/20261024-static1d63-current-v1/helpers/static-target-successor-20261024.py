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
PROFILE = Path('/root/probe/lanes/route/out-rrfb254e8rP')
BASE = 'fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
UNITS = ['coarse_actor.cpp', 'platform/native_actor_fast.cpp', 'platform/native_ui.cpp',
         'platform/native_model.cpp', 'model_bridge.cpp', 'ui_bridge.cpp', 'platform/audio_aica.cpp',
         'platform/native_movie.cpp', 'platform/native_movie_stream.c', '../../../src/game/model.cpp',
         '../../../src/game/read.cpp', '../../../src/game/dvd.cpp', 'platform/native_static.cpp', 'platform/room_file.c']
EXTRA = ['platform/gc_asset_gate.cpp', 'platform/gc_asset_members.cpp', 'platform/gc_asset_payloads.cpp',
         'platform/gc_asset_audio.cpp', 'platform/gc_asset_disc.cpp']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(TREE), *args], text=True).strip()


def main():
    expected = os.environ['GCGATE_SOURCE']
    source = git('rev-parse', 'HEAD')
    if expected != '1d63cffe3a232c402418f2f2d919e7abae476957':raise RuntimeError('Unreviewed source')
    if os.environ.get('GCGATE_PRIOR_REPORT') != '/dev/shm/gc-port23-current-77d8a20b2-jx_x05a2/report.json':raise RuntimeError('Only exact failed current-profile receipt allowed')
    free=os.statvfs('/mnt/c');free=free.f_bavail*free.f_frsize
    if free < 24*1024**3:raise RuntimeError('C below24GiB')
    if source != expected or git('status', '--porcelain'):
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
                                       'port/dreamcast/game', 'port/dreamcast/room', 'port/dreamcast/tools', 'src', 'include'])
    with tarfile.open(fileobj=io.BytesIO(archived)) as archive:
        archive.extractall(baseline, filter='data')
    del archived
    sdk = Path(os.environ['KOS_BASE']) / 'lib/dreamcast/libkallisti.a'
    bins = Path(os.environ['KOS_CC_BASE']) / 'bin'
    pins = {str(path): sha(path) for path in [sdk, *(PROFILE / name for name in ['candidate.txt', 'resolved-knobs.txt', 'build.log'])]}
    reused = {}
    prior_name = os.environ.get('GCGATE_PRIOR_REPORT')
    if prior_name:
        prior_path = Path(prior_name).resolve()
        if prior_path.parent.parent != Path('/dev/shm') or not prior_path.parent.name.startswith('gc-port23-current-'):
            raise RuntimeError('Prior receipt must be this bounded RAM harness output')
        if sha(prior_path) != '666759f4e9019398d854d959244c19080ffeee1edf323f8611ef5e874a679979':raise RuntimeError('Prior receipt changed')
        prior = json.loads(prior_path.read_text())
        if prior['source'] != '77d8a20b2e6c6a8f3eccb6119081c27a3dd4ea22' or prior.get('complete') or prior['harness_source_sha256'] != '6f8f984ed689ee8c0c0701d054f15c7a276b0f8d9d59c475cf3f15e4322935ba':raise RuntimeError('Unrecognized prior attempt')
        if len(prior['objects']) != 51 or len(prior['off_identity']) != 12 or not all(prior['off_identity'].values()):raise RuntimeError('Prior attempt not expected partial matrix')
        if prior['baseline'] != BASE or prior['profile'] != str(PROFILE) or prior['pins'] != pins:
            raise RuntimeError('Prior source/profile/SDK contract changed')
        for row in prior['objects']:
            origin = Path(row.get('reused_from', str(prior_path)))
            label = row['unit'].replace('../', '').replace('/', '_').rsplit('.', 1)[0] + '-' + row['arm']
            inputs = json.loads((origin.parent / (label + '-inputs.json')).read_text())
            if any(not Path(path).is_file() or sha(Path(path)) != value for path, value in inputs.items()):continue
            if sha(origin.parent / (label + '.o')) != row['sha256'] or sha(origin.parent / (label + '-nodebug.o')) != row['nodebug_sha256']:
                raise RuntimeError('Prior object changed')
            prior_args = json.loads((origin.parent / (label + '-command.json')).read_text())
            reused[row['unit'], row['arm']] = (dict(row, compiled_source=row.get('compiled_source', prior['source']), reused_from=str(origin)), prior_args)
    report = dict(source=source, baseline=BASE, profile=str(PROFILE), pins=pins, knobs=required, objects=[],
                  harness_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), scope_version='STATIC1D63_CURRENT_FB_PINNED_CONTINUATION', note='Selected objects only; actual current fb254 commands/profile and baseline, default catalog pin0. No linked heap/image/guest/provenance acceptance.')
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
            if gate and not unit.endswith('.c') and not unit.startswith('../../../src/') and unit not in ('model_bridge.cpp','ui_bridge.cpp','coarse_actor.cpp'):
                pin = '1' * 64 if arm == 'on-synthetic-pin' else '0'
                args.append('-DRE4DC_GC_ASSET_CATALOG_SHA256="' + pin + '"')
            if gate:
                if unit == 'platform/native_ui.cpp':args.append('-DRE4DC_GC_ASSET_COARSE_LEON=1')
                if unit == 'platform/native_actor_fast.cpp':args.append('-DRE4DC_GC_ASSET_LEON_HAND_PACK=1')
            args.append('-fstack-usage')
            if (unit, arm) in reused:
                row, prior_args = reused[unit, arm]
                def normalized(command):
                    command = command.copy();command[command.index('-o') + 1] = '@output';return command
                if normalized(args) == normalized(prior_args):
                    results[arm] = row;report['objects'].append(row)
                    print('REUSED pinned ' + unit + ' ' + arm, flush=True);continue
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
            used=sum(p.stat().st_size for root in [scratch,Path('/dev/shm/gc-port23-current-77d8a20b2-jx_x05a2/report.json').parent] for p in root.rglob('*') if p.is_file())
            if used>256*1024**2:raise RuntimeError('Owned RAM output exceeds256MiB; retained for review')
            if os.statvfs('/mnt/c').f_bavail*os.statvfs('/mnt/c').f_frsize<24*1024**3:raise RuntimeError('C below24GiB')
            (scratch / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        if unit in UNITS:
            identity = len({results[arm]['nodebug_sha256'] for arm in ['baseline', 'absent', 'zero']}) == 1
            report.setdefault('off_identity', {})[unit] = identity
            print('OFF baseline/absent/zero ' + unit + ': ' + ('IDENTICAL' if identity else 'MISMATCH'), flush=True)
    if git('rev-parse', 'HEAD') != source or git('status', '--porcelain') or any(sha(Path(path)) != value for path, value in pins.items()):
        raise RuntimeError('Frozen source/profile/SDK changed')
    if len(report.get('off_identity',{})) !=14 or not all(report['off_identity'].values()):raise RuntimeError('OFF target mismatch')
    report['prior_report_sha256']='666759f4e9019398d854d959244c19080ffeee1edf323f8611ef5e874a679979'
    report['complete'] = True
    (scratch / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('SELECTED OBJECTS COMPLETE; no full-programme or GC-ASSET pass', flush=True)


if __name__ == '__main__':main()
