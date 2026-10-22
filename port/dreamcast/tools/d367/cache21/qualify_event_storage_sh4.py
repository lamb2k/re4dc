#!/usr/bin/env python3
"""Bounded actual SH4 TU gates; no full programme, image, guest or release."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shlex
import shutil
import subprocess

REPO = Path('/root/probe/codex-cache21-integration-next')
GAME = REPO / 'port/dreamcast/game'
OUT = Path('/root/probe/cache21-event-storage-qualification-20261022-03')
BASE = '720b75381a68f51636b17031f82fd762e72e05d3'
KNOB = 'EVENT_MANAGER_STORAGE_FLAGS'
MIB = 1024 ** 2
CAP = 32 * MIB
FLOOR = 18 * 1024 ** 3 + 64 * MIB + CAP


def digest(data):
    return hashlib.sha256(data).hexdigest()


def guard():
    assert shutil.disk_usage('/mnt/c').free >= FLOOR, 'C: resource floor'
    if OUT.exists():
        assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) <= CAP, '32MiB cap'


def run(argv, name):
    guard()
    process = subprocess.Popen(list(map(str, argv)), cwd=GAME, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate(timeout=5)
        (OUT / (name + '.timeout')).write_text('Owned process group killed; no acceptance.\n')
    assert len(stdout) + len(stderr) <= 4 * MIB, 'output cap'
    (OUT / (name + '.stderr')).write_bytes(stderr)
    if process.returncode:
        (OUT / (name + '.stdout')).write_bytes(stdout)
        raise RuntimeError(f'{name}: exit {process.returncode}')
    guard()
    return stdout


def tokens(data):
    return re.findall(rb'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\w+|[^\s]', data)


def main():
    guard()
    OUT.mkdir(exist_ok=False)
    shutil.copyfile(__file__, OUT / 'qualifier-used.py')
    (OUT / 'tmp').mkdir()
    os.environ['TMPDIR'] = str(OUT / 'tmp')
    virtual = OUT / 'virtual'
    shutil.copytree(REPO / 'include', virtual / 'include')
    sources = {}
    for rel in ('include/cManager.h', 'src/game/event.cpp', 'src/game/game.cpp'):
        before = subprocess.check_output(['git', 'show', BASE + ':' + rel], cwd=REPO)
        after = (REPO / rel).read_bytes()
        sources[rel] = (before, after)
        for label, data in zip(('baseline', 'candidate'), (before, after)):
            target = OUT / 'sources' / label / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    objdir = OUT / 'obj'
    common = ['make', '--no-print-directory', f'OBJDIR={objdir}', 'CABIN_SOURCE=1',
              'ROUTE_CH21=1', 'ROUTE_CH22=1', 'ROUTE_OVL=1', 'EM10_SHARED=1',
              'WORLD_STAGE_MODULES=0', 'ROUTE_MOVIES=1', 'AICA_AUDIO=1', 'AICA_STREAMS=1',
              'NATIVE_STATIC=1', 'D349_RENDERER_STACK=1', 'PVR_STREAM=1',
              'DVD_READ_SAFE=1', 'PVR_PIPELINE=1',
              'EVD_ADMISSION_TXN=1', 'EVD_START_CLEANUP=1', 'EVD_START_ROLLBACK=1',
              'EVD_EXEC_FAILURE_CLEANUP=1']
    run(common + [str(objdir / 'cabin-source.h'), str(objdir / 'demo-presentation-knobs.txt')], 'headers')
    rows = []
    # Event's whole-object controls already passed in retained attempt02. This
    # successor qualifies game.cpp with the source Makefile's DVD_READ_SAFE
    # prerequisite, which supplies its required default-off door_probe header.
    for stem in ('game',):
        target = objdir / 'src/game' / (stem + '.o')
        target.parent.mkdir(parents=True, exist_ok=True)
        default = run(common + ['-B', '-n', str(target)], stem + '-default-command')
        zero = run(common + [KNOB + '=0', '-B', '-n', str(target)], stem + '-zero-command')
        assert default == zero, 'default vs explicit zero commands'
        variants = {}
        for label, enabled, old in [('baseline', 0, True), ('default', 0, False), ('zero', 0, False), ('on', 1, False)]:
            for rel, pair in sources.items():
                path = virtual / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(pair[0 if old else 1])
            dry = run(common + [KNOB + '=' + str(enabled), '-B', '-n', str(target)], stem + '-' + label + '-dry')
            lines = [shlex.split(line) for line in dry.decode().splitlines()
                     if line.startswith('kos-c++ ') and '../../../src/game/' + stem + '.cpp' in line]
            assert len(lines) == 1
            command = lines[0]
            assert ('-DRE4DC_' + KNOB + '=1' in command) == bool(enabled)
            for i, part in enumerate(command):
                if part == '../../../src/game/' + stem + '.cpp':
                    command[i] = str(virtual / 'src/game' / (stem + '.cpp'))
                elif part.startswith('-I') and (GAME / part[2:]).resolve() == (REPO / 'include').resolve():
                    command[i] = '-I' + str(virtual / 'include')
            forced = [Path(command[i+1]) for i, part in enumerate(command[:-1]) if part == '-include']
            missing = [str(path) for path in forced if path.is_absolute() and not path.exists()]
            if missing:
                run(common + missing, stem + '-' + label + '-forced-headers')
            (OUT / (stem + '-' + label + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
            pp = command.copy()
            pp.remove('-c')
            oi = pp.index('-o')
            del pp[oi:oi+2]
            pp += ['-E', '-P']
            preprocessed = run(pp, stem + '-' + label + '-preprocess')
            token_sha = digest(b'\0'.join(tokens(preprocessed)))
            run(command, stem + '-' + label + '-compile')
            stripped = OUT / (stem + '-' + label + '-stripped.o')
            run(['sh-elf-objcopy', '--strip-debug', target, stripped], stem + '-' + label + '-strip')
            size_text = run(['sh-elf-size', stripped], stem + '-' + label + '-size').decode().strip()
            size = list(map(int, size_text.splitlines()[-1].split()[:3]))
            variants[label] = dict(object_sha256=digest(stripped.read_bytes()), pp_token_sha256=token_sha, size=size)
        assert variants['baseline'] == variants['default'] == variants['zero'], 'whole OFF identity'
        rows.append(dict(tu=stem, variants=variants))
    platform_target = str(objdir / 'platform/modules.o')
    propagation = []
    for enabled in (0, 1):
        dry = run(common + [KNOB + '=' + str(enabled), '-B', '-n', platform_target], 'platform-propagation-' + str(enabled))
        command = [line for line in dry.decode().splitlines() if line.startswith('kos-c++ ') and 'platform/modules.cpp' in line]
        assert len(command) == 1
        assert ('-DRE4DC_' + KNOB + '=1' in command[0]) == bool(enabled)
        propagation.append(dict(enabled=enabled, command=command[0]))
    invalid = []
    for value in ('2', '-1', 'yes'):
        result = subprocess.run(common + [KNOB + '=' + value, '-n'], cwd=GAME, capture_output=True, timeout=30)
        assert result.returncode and (KNOB + ' must be 0 or 1').encode() in result.stderr
        invalid.append(value)
    guard()
    receipt = dict(scope='Actual full SH4 event/game TU token and stripped object checks only; no full programme/guest/hardware acceptance.',
                   baseline=BASE, tools_sha256=digest(Path(__file__).read_bytes()), rows=rows,
                   source_sha256={rel: dict(baseline=digest(pair[0]), candidate=digest(pair[1])) for rel,pair in sources.items()},
                   invalid_knobs_rejected=invalid, cap_bytes=CAP, floor_bytes=FLOOR,
                   platform_define_propagation=propagation,
                   event_gate_receipt='/root/probe/cache21-event-storage-qualification-20261022-02/EVENT-PARTIAL-RECEIPT.json',
                   game_gate_configuration='DVD_READ_SAFE=1 supplies source-required door_probe.h; PVR_PIPELINE=1. These are qualification inputs, not production recipe changes.',
                   output_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),
                   final_C_free_bytes=shutil.disk_usage('/mnt/c').free)
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
