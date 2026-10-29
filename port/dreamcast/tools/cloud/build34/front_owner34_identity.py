#!/usr/bin/env python3
"""EF15 absent/zero identity and affected-TU Make-selection checks."""
from pathlib import Path
import argparse
import hashlib
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import front_sources as source

BASE = '4c4794a17c96ce7f22d8c194907475014eea85a4'
PRE_LINE_FIX = '5532a2a98fda49716c9dd36e4c114890d1c36103'
ROOT = source.ROOT
GAME = source.DC / 'game'
TUS = ('trans', 'model', 'scroll', 'read', 'game', 'main')


def run(args, cwd=ROOT):
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'{args}: {result.stderr.decode()[-1800:]}')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default=BASE, help='exact pre-EF15 integration source')
    args = parser.parse_args()
    ppflags = ['g++', '-E', '-P', '-std=gnu++20', '-fpermissive', '-w',
               '-I' + str(ROOT / 'include'), '-I' + str(ROOT / 'src'),
               '-I' + str(ROOT / 'src/game'), '-I' + str(GAME / 'platform/include'),
               '-DRE4DC_GAME', '-DRE4DC_FRONT_NATIVE=1', '-DRE4DC_FRONT_TEXOBJ=1']
    with tempfile.TemporaryDirectory(prefix='front-owner34-identity-') as temp:
        tmp = Path(temp)
        for tu in TUS:
            old = tmp / (tu + '.cpp')
            old.write_bytes(run(['git', 'show', f'{args.base}:src/game/{tu}.cpp']))
            original = run(ppflags + [str(old)], GAME)
            absent = run(ppflags + [str(ROOT / 'src/game' / (tu + '.cpp'))], GAME)
            zero = run(ppflags + ['-DRE4DC_FRONT_TPL_OWNER=0',
                                  str(ROOT / 'src/game' / (tu + '.cpp'))], GAME)
            assert original == absent == zero, f'{tu} OFF preprocessing changed'
            enabled = run(ppflags + ['-DRE4DC_FRONT_TPL_OWNER=1',
                                     str(ROOT / 'src/game' / (tu + '.cpp'))], GAME)
            print(f'{tu}: base/absent/zero preprocessing identical '
                  f'({len(original)} bytes); ON preprocessing {len(enabled)} bytes')

        # The host preprocessing above does not enter frontNativeModelTrans's
        # SH-only body. Compare all affected target-conditioned source, without
        # whitespace/literal normalization, as well as checking the diagnostic
        # regression below. This uses host cpp with the target conditionals; it
        # does not replace the target compiler/full allocated-section judge.
        target_flags = ppflags + ['-D__sh__', '-U__PPC__']
        for native, texobj in ((0, 0), (1, 0), (1, 1), (2, 1)):
            profile = target_flags + [f'-DRE4DC_FRONT_NATIVE={native}',
                                      f'-DRE4DC_FRONT_TEXOBJ={texobj}']
            for tu in TUS:
                old = tmp / (tu + '.cpp')
                original = run(profile + [str(old)], GAME)
                absent = run(profile + [str(ROOT / 'src/game' / (tu + '.cpp'))], GAME)
                zero = run(profile + ['-DRE4DC_FRONT_TPL_OWNER=0',
                                      str(ROOT / 'src/game' / (tu + '.cpp'))], GAME)
                assert original == absent == zero, \
                    f'{tu} target-conditioned OFF preprocessing changed ({native=}, {texobj=})'
            print(f'target-conditioned six-TU base/absent/zero preprocessing identical: '
                  f'FRONT_NATIVE={native} FRONT_TEXOBJ={texobj}')

        # HALT expands __LINE__ through RE4DC_HALT_STORE in the SH-only body:
        # a guarded notifier had shifted the diagnostic/target OFF constant
        # even when ordinary host OFF preprocessing matched.
        def target_halts(path, extra=()):
            output = run(target_flags + list(extra) + [str(path)], GAME).decode()
            assert 'static void frontNativeModelTrans(' in output, 'target frontend path absent'
            lines = tuple(line.strip() for line in output.splitlines()
                          if 're4dc_halt("D:/Bio4/Prog/trans.cpp",' in line)
            assert len(lines) == 2 and all('OSReport("HALT %s(%d)\\n"' in line
                                           for line in lines), 'target HALT expansion changed'
            return lines

        base_trans = tmp / 'target-base-trans.cpp'
        base_trans.write_bytes(run(['git', 'show', f'{args.base}:src/game/trans.cpp']))
        pre_fix_trans = tmp / 'target-pre-fix-trans.cpp'
        pre_fix_trans.write_bytes(run(['git', 'show', f'{PRE_LINE_FIX}:src/game/trans.cpp']))
        base_halts = target_halts(base_trans)
        pre_fix_halts = target_halts(pre_fix_trans)
        absent_halts = target_halts(ROOT / 'src/game/trans.cpp')
        zero_halts = target_halts(ROOT / 'src/game/trans.cpp', ['-DRE4DC_FRONT_TPL_OWNER=0'])
        assert pre_fix_halts != base_halts and '2468' in pre_fix_halts[1], \
            'pinned pre-fix target negative control stopped detecting the line shift'
        assert absent_halts == zero_halts == base_halts and '2465' in base_halts[1], \
            'target HALT literals differ from pre-EF15 source'
        print('target __sh__ frontend HALT expansions: base/absent/zero identical; '
              'pinned pre-fix negative control differs (2468 versus 2465)')

        # The extracted real frontend consumer is also compiled to a host
        # object with identical source names and flags in all three OFF arms.
        objects = []
        for name, ref, extra in [('base', args.base, []), ('absent', None, []),
                                 ('zero', None, ['-DRE4DC_FRONT_TPL_OWNER=0'])]:
            values = source.source_values(ref)
            types = source.render((source.HERE / 'front_fixture_types.hpp.in').read_text(), values)
            cpp = source.render((source.HERE / 'front_fixture.cpp.in').read_text(), {'TYPES': types})
            directory = tmp / name
            directory.mkdir()
            (directory / 'fixture.cpp').write_text(cpp)
            obj = directory / 'fixture.o'
            run(['g++', '-std=c++20', '-O2', '-fpermissive', '-w',
                 '-DRE4DC_FRONT_TEXOBJ=1', *extra, '-c',
                 str(directory / 'fixture.cpp'), '-o', str(obj)])
            objects.append(obj.read_bytes())
        assert objects[0] == objects[1] == objects[2], 'host frontend OFF object changed'
        print('host frontend base/absent/zero object identical:',
              len(objects[0]), hashlib.sha256(objects[0]).hexdigest())

        kos = tmp / 'kos'
        kos.mkdir()
        (kos / 'Makefile.rules').write_text('')
        objdir = tmp / 'obj'
        targets = [str(objdir / 'src/game' / (tu + '.o')) for tu in TUS]
        make = ['make', '-f', 'Makefile', '-n', *targets,
                'KOS_BASE=' + str(kos), 'OBJDIR=' + str(objdir),
                'FRONT_NATIVE=1', 'FRONT_TEXOBJ=1']
        commands = {}
        for mode, extra in [('absent', []), ('zero', ['FRONT_TPL_OWNER=0']),
                            ('on', ['FRONT_TPL_OWNER=1'])]:
            output = run(make + extra, GAME).decode()
            lines = [line for line in output.splitlines()
                     if line.startswith('kos-c++') and '/src/game/' in line and line.endswith('.o')]
            selected = {tu: next(line for line in lines if f'/{tu}.o' in line) for tu in TUS}
            assert len(lines) == len(TUS), (mode, lines)
            commands[mode] = selected
        for tu in TUS:
            assert commands['absent'][tu] == commands['zero'][tu], f'{tu} Make OFF changed'
            assert '-DRE4DC_FRONT_TPL_OWNER=1' in commands['on'][tu], f'{tu} Make ON missing'
        for extra in (['FRONT_TPL_OWNER='], ['FRONT_TPL_OWNER=0 1'], ['FRONT_TPL_OWNER=2'],
                      ['FRONT_TPL_OWNER=%'], ['FRONT_TPL_OWNER=0%'], ['FRONT_TPL_OWNER=1%'],
                      ['FRONT_TPL_OWNER=1', 'FRONT_TEXOBJ=0'],
                      ['FRONT_TPL_OWNER=1', 'FRONT_NATIVE=0'],
                      ['FRONT_TPL_OWNER=1', 'RESET_RETIRE_BEFORE_HEAPS=0']):
            result = subprocess.run(make + extra, cwd=GAME, capture_output=True)
            assert result.returncode != 0, f'Make accepted invalid {extra}'
        print('Make: absent/zero identical, ON scoped to six game TUs; invalid/dependency modes rejected')


if __name__ == '__main__':
    main()
