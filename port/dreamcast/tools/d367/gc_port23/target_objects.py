"""Replay frozen standard-profile compiler commands for owned source units only."""
from pathlib import Path
import hashlib
import json
import os
import shlex
import subprocess
import tempfile

TREE = Path('/root/work/lanes/gc-port23')
GAME = TREE / 'port/dreamcast/game'
RECEIPT = Path('/root/probe/lanes/route/out-dd23stdoff542rP')
EXPECTED = os.environ['GCGATE_SOURCE']
SOURCES = ['platform/native_ui.cpp', 'platform/native_model.cpp', 'model_bridge.cpp',
           '../../../src/game/model.cpp', '../../../src/game/read.cpp', '../../../src/game/dvd.cpp', 'platform/audio_aica.cpp']
EXTRA = ['platform/gc_asset_gate.cpp', 'platform/gc_asset_members.cpp', 'platform/gc_asset_disc.cpp', 'platform/gc_asset_payloads.cpp', 'platform/gc_asset_audio.cpp']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    head = subprocess.check_output(['git', '-C', str(TREE), 'rev-parse', 'HEAD'], text=True).strip()
    if not head.startswith(EXPECTED):
        raise RuntimeError('Frozen source HEAD changed')
    subprocess.run(['git', '-C', str(TREE), 'diff', '--exit-code', 'HEAD', '--',
                    'port/dreamcast/game', 'src/game/model.cpp', 'src/game/read.cpp'], check=True)
    commands = {}
    for line in (RECEIPT / 'build.log').read_text().splitlines():
        if not line.startswith('kos-c++ '):
            continue
        args = shlex.split(line)
        if '-c' not in args:
            continue
        source = args[args.index('-c') + 1]
        if source in SOURCES or source == 'platform/audio_stub.cpp':
            if source in commands:
                raise RuntimeError('Ambiguous compiler receipt: '+source)
            commands[source] = args
    if set(SOURCES) - commands.keys() or 'platform/audio_stub.cpp' not in commands:
        raise RuntimeError('Missing compiler receipts')
    scratch = Path(tempfile.mkdtemp(prefix='gc-port23-target-'+EXPECTED[:9]+'-', dir='/dev/shm'))
    report = {'source': head, 'profile': str(RECEIPT), 'note': 'Old standard542 knobs; no link/stage/guest acceptance',
              'inputs': {name: digest(RECEIPT / name) for name in ('candidate.txt', 'resolved-knobs.txt', 'build.log')},
              'objects': []}
    (scratch / 'profile-candidate.txt').write_bytes((RECEIPT / 'candidate.txt').read_bytes())
    (scratch / 'profile-resolved-knobs.txt').write_bytes((RECEIPT / 'resolved-knobs.txt').read_bytes())
    print(str(scratch), flush=True)
    for gate in (0, 1):
        for source in SOURCES + EXTRA:
            inherited = source if source in commands else 'platform/audio_stub.cpp'
            args = commands[inherited].copy()
            args[args.index('-c') + 1] = source
            name = source.replace('../', '').replace('/', '_').replace('.cpp', '') + '-'+str(gate)
            output = scratch / (name+'.o')
            args[args.index('-o') + 1] = str(output)
            args = [arg for arg in args if arg not in ('-MMD', '-MD', '-MP')]
            for flag in ('-MF', '-MT', '-MQ'):
                while flag in args:
                    at = args.index(flag)
                    del args[at:at+2]
            args += ['-DRE4DC_GC_ASSET_GATE='+str(gate)]
            (scratch / (name+'-command.json')).write_text(json.dumps(args, indent=2)+'\n')
            deps = scratch / (name+'.d')
            scan = args + ['-M', '-MF', str(deps), '-MT', name]
            with (scratch / (name+'.log')).open('w') as log:
                subprocess.run(scan, cwd=GAME, stdout=log, stderr=subprocess.STDOUT, check=True)
                paths = shlex.split(deps.read_text().split(':', 1)[1].replace('\\\n', ' '))
                inputs = {(GAME / path).resolve() for path in paths}
                before = {str(path): digest(path) for path in inputs}
                result = subprocess.run(args, cwd=GAME, stdout=log, stderr=subprocess.STDOUT)
                if result.returncode:
                    report['failed'] = source+' gate='+str(gate)
                    (scratch / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
                    raise RuntimeError('Target compiler failed; inspect '+str(scratch / (name+'.log')))
                if before != {str(path): digest(path) for path in inputs}:
                    raise RuntimeError('Compiler inputs changed while compiling '+source)
            (scratch / (name+'-inputs.json')).write_text(json.dumps(before, indent=2)+'\n')
            size = subprocess.check_output([os.environ['KOS_CC_BASE']+'/bin/sh-elf-size', str(output)], text=True)
            undefined = subprocess.check_output([os.environ['KOS_CC_BASE']+'/bin/sh-elf-nm', '-u', str(output)], text=True)
            (scratch / (name+'-undefined.txt')).write_text(undefined)
            report['objects'].append({'source': source, 'gate': gate, 'inherited_command': inherited,
                                      'sha256': digest(output), 'size': size, 'inputs': len(before)})
            print(size.strip(), flush=True)
            (scratch / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    if report['inputs'] != {name: digest(RECEIPT / name) for name in report['inputs']}:
        raise RuntimeError('Profile receipt changed')
    (scratch / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('OBJECTS PASS; no link/image/heap/runtime claim', flush=True)


if __name__ == '__main__':
    run()
