#!/usr/bin/env python3
"""Compile only SH4 read.o, compare disabled against HEAD, and check knob parsing."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[5]


def run(command, cwd, log):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    log.write_text(result.stdout + result.stderr)
    result.check_returncode()
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline', default='2093aeb1', help='Unmodified parent source revision')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    game = ROOT / 'port/dreamcast/game'
    results = {}
    for heap in (0, 1):
        base = out / f'heap-{heap}'
        off = base / 'off'
        obj = off / 'src/game/read.o'
        common = ['make', '-s', '-j1', f'OBJDIR={off}', f'WEAPON_HEAP4={heap}', 'WEAPON_ARCHIVE_REUSE=0']
        run(common + [str(obj)], game, out / f'build-off-{heap}.txt')
        text = run(common[:1] + ['-n', '-B'] + common[1:] + [str(obj)], game, out / f'command-{heap}.txt')
        command = next(shlex.split(line) for line in text.splitlines() if line.startswith('kos-c++ ') and 'read.cpp' in line)
        # Preserve source file identity while compiling the unmodified parent body outside the checkout.
        original = subprocess.check_output(['git', 'show', f'{args.baseline}:src/game/read.cpp'], cwd=ROOT)
        control = base / 'control/read.cpp'
        control.parent.mkdir(parents=True)
        control.write_bytes(b'#line 1 "../../../src/game/read.cpp"\n' + original)
        old_command = command.copy()
        old_command[old_command.index('-c') + 1] = str(control)
        old_obj = base / 'control/read.o'
        old_command[old_command.index('-o') + 1] = str(old_obj)
        run(old_command, game, out / f'build-parent-{heap}.txt')
        on_obj = base / 'enabled/read.o'
        on_obj.parent.mkdir(parents=True)
        on_command = command.copy()
        on_command.insert(1, '-DRE4DC_WEAPON_ARCHIVE_REUSE=1')
        on_command[on_command.index('-o') + 1] = str(on_obj)
        run(on_command, game, out / f'build-on-{heap}.txt')
        stripped = []
        for name, path in [('off', obj), ('parent', old_obj), ('on', on_obj)]:
            dst = base / f'{name}-stripped.o'
            subprocess.run(['sh-elf-objcopy', '--strip-debug', str(path), str(dst)], check=True)
            stripped.append(hashlib.sha256(dst.read_bytes()).hexdigest())
        assert stripped[0] == stripped[1], f'knob-off object mismatch heap={heap}'
        size = subprocess.check_output(['sh-elf-size', str(obj), str(on_obj)], text=True)
        results[str(heap)] = {'off_sha256': stripped[0], 'parent_sha256': stripped[1],
                              'on_sha256': stripped[2], 'size': size}
        print(f'PASS SH4 heap={heap}: stripped off object identical to parent\n{size}', end='')
    # Exercise the real Makefile guard without compiling another object.
    for value in ('2', '-1', 'yes'):
        test = subprocess.run(['make', '-s', '-n', f'OBJDIR={out}/guard', f'WEAPON_ARCHIVE_REUSE={value}'],
                              cwd=game, text=True, capture_output=True)
        assert test.returncode and 'WEAPON_ARCHIVE_REUSE must be 0 or 1' in test.stderr
    results['invalid_knobs_rejected'] = ['2', '-1', 'yes']
    results['baseline'] = subprocess.check_output(['git', 'rev-parse', args.baseline], cwd=ROOT, text=True).strip()
    (out / 'receipt.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
