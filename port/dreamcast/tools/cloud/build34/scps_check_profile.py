#!/usr/bin/env python3
"""Qualify the separately scoped Build34 SCPS header-check composition.

Reuse the existing Make-derived full-C++-TU gate, then expand and compile the
actual room_file.c Make C recipe. No source/guard/recipe/data is changed. This
is compilation, explicit symbol/definition and rejection evidence, not a
whole-game link, executed cache comparison, private-data or console result.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CONFIG = HERE / 'scps_check_profiles.json'
BASELINE = '7085a2d73d6a3211e3fc6686ed092153bcd76f69'
spec = importlib.util.spec_from_file_location('scps34_controls', HERE / 'build_controls.py')
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)
ROOT, DC, profile = controls.ROOT, controls.DC, controls.profile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, directory, log):
    result = subprocess.run([str(x) for x in command], cwd=directory, capture_output=True)
    log.write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, (command, result.returncode, log.read_text()[-6000:])
    return result.stdout.decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'sh4-cxx', 'kos-root', 'sdk-root', 'toolchain-receipt'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    assert str(cxx).endswith('g++')
    prefix = str(cxx).removesuffix('g++')
    gcc = Path(prefix + 'gcc')
    config = json.loads(CONFIG.read_text())
    owned = [Path(__file__), CONFIG, DC / 'game/platform/room_file.c',
             DC / 'game/platform/include/room_file.h']
    frozen = {str(p.relative_to(ROOT)): digest(p) for p in owned}
    target = out / 'target'
    command = [sys.executable, HERE / 'build_controls.py', '--only', 'on',
               '--config', CONFIG, '--baseline', BASELINE, '--output', target,
               '--sh4-cxx', cxx, '--kos-root', kos, '--sdk-root', sdk,
               '--toolchain-receipt', args.toolchain_receipt.resolve()]
    run(command, ROOT, out / 'target-gate.log')
    target_report = json.loads((target / 'target-controls.json').read_text())
    assert target_report['status'] == 'PASS' and len(target_report['enabled_compiles']) == 3
    frozen.update(target_report['source_sha256'])
    evidence = {}
    for name, options in config['on_profiles'].items():
        directory = out / name
        directory.mkdir()
        planned = directory / 'obj/platform/room_file.o'
        make, recipe = profile.make_command(directory, ROOT, kos, sdk, options, planned)
        text = run(make, DC / 'game', directory / 'make-c.log')
        commands = [shlex.split(line) for line in text.replace('\\\n', ' ').splitlines()
                    if line.startswith('kos-cc ')]
        assert len(commands) == 1, commands
        original = commands[0]
        assert original[-4:] == ['-c', 'platform/room_file.c', '-o', str(planned)], original
        flags = original[1:-4]
        expected = 0 if name.endswith('-control') else 1
        assert ('-DRE4DC_ROOMFILE_SCPS=1' in flags) == bool(expected)
        assert '-DRE4DC_ROOMFILE_OCCL=1' in flags
        assert not any(word.startswith('-std=c++') for word in flags)
        obj, dep = directory / 'room_file.o', directory / 'room_file.d'
        actual = [gcc, *flags, '-fstack-usage', '-MMD', '-MF', dep,
                  '-c', 'platform/room_file.c', '-o', obj]
        run(actual, DC / 'game', directory / 'compile-c.log')
        closure = controls.shared.dependencies(dep, ROOT, DC / 'game')
        for path, value in {**recipe['source_sha256'], **closure}.items():
            assert frozen.get(path, value) == value, (path, 'input changed')
            frozen[path] = value
        cpp = [target / ('on-' + name + '-' + unit + '.o') for unit in config['units']]
        linked = directory / 'combined.o'
        link = [prefix + 'ld', '-m', 'shlelf', '-r', *cpp, obj, '-o', linked]
        run(link, ROOT, directory / 'partial-link.log')
        undefined = run([prefix + 'nm', '-u', '-C', linked], ROOT, directory / 'undefined.log')
        required = ('re4dc_ps2_piece_slot', 're4dc_room_file_enter',
                    're4dc_room_file_leave', 're4dc_room_file_room', 're4dc_room_section')
        assert not any(symbol in undefined for symbol in required), undefined
        symbols = run([prefix + 'nm', '-C', target / ('on-' + name + '-native_ui.o')],
                      ROOT, directory / 'ui-symbols.log')
        checking = name.endswith('-check')
        for symbol in ('ps2_hdr_checked', 'ps2_hdr_bad'):
            assert (symbol in symbols) == checking, (name, symbol)
        assert ('ps2_piece_hits' in symbols) == bool(expected), name
        state = target_report['make_states']['on-' + name]['state']
        wanted = dict(SCENERY_SUBMIT_BATCH='0', PS2_PVS_BATCH_COMPOSE='0', PS2_PVS='0',
                      SCENERY_PIECE_STATE=str(expected), PS2_WORLD_HDR_CACHE='2' if checking else '1',
                      SCENERY_STREAM='1', SCENERY_CHUNK='1', SCENERY_SELECT_ONLY='1',
                      SCENERY_REPLAY_LEAN='1', TA_DIRECT='1', MESH_DIRECT='1',
                      PS2_WORLD_MESH='1', PS2_INTERIOR_CULL='1', TA_GUARD='0')
        assert all(state.get(key) == value for key, value in wanted.items()), (name, state)
        evidence[name] = dict(make_command=make, original_c_command=original,
                              actual_c_command=[str(x) for x in actual], c_flags=flags,
                              roomfile_scps=expected, resolved=wanted,
                              c_object=dict(sha256=digest(obj), **profile.sections(obj)),
                              local_frames=profile.stack_usage(obj.with_suffix('.su')),
                              dependencies_sha256=controls.compact_hash(closure),
                              partial_link=dict(command=[str(x) for x in link], sha256=digest(linked),
                                                checked_symbols=list(required), all_resolved=True,
                                                ordinary_game_references_remain=True),
                              check_counters_compiled=checking, piece_counter_compiled=bool(expected))
        print('PASS actual C parser and four-TU partial link:', name, flush=True)
    assert all(digest(ROOT / path) == value for path, value in frozen.items()), 'inputs changed during gate'
    report = dict(status='PASS', scope=__doc__, baseline=BASELINE,
                  compiler=target_report['compiler'], compiler_path=str(cxx), c_compiler_path=str(gcc),
                  kos=target_report['kos'], sdk=target_report['sdk'],
                  toolchain_receipt=target_report['toolchain_receipt'], source_sha256=frozen,
                  target_receipt=dict(path='target/target-controls.json', sha256=digest(target / 'target-controls.json'),
                                      cpp_profiles=3, cpp_tus_per_profile=3,
                                      make_rejections=len(target_report['make_rejections']),
                                      make_acceptances=len(target_report['make_acceptances'])),
                  profiles=evidence,
                  limits=['Public NMR_POOL_LOD=0 and missing-private-character fallbacks are fixture-only.',
                          'Actual C parser and C++ sources compile; ordinary external game/KOS references remain.',
                          'No complete game/overlay/image link, runtime header comparison, game data or console run.',
                          'Batching is off in every validation arm; this does not qualify batching1 with cache2.',
                          'Cache2 logs checked/mismatched instead of piece_hits; use the matched cache1-on arm for admissions.'])
    (out / 'scps-check-profile.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', profiles=3, full_c_compiles=3,
                          full_cpp_compiles=9, receipt=str(out / 'scps-check-profile.json'))))


if __name__ == '__main__':
    main()
