#!/usr/bin/env python3
"""Full release-chain Make and actual native_static C++ guards for mutation31.

The public release recipe is parsed with inert existence-only paths. This
qualifies selected source flags and refusals; it does not compile a target ELF.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
GAME = ROOT / 'port/dreamcast/game'
NATIVE = GAME / 'platform/native_static.cpp'


def make(output, assignments, target, *, dry=True):
    obj = output / 'obj'
    obj.mkdir(exist_ok=True)
    modules = obj / 'modules.mk'
    modules.touch()
    kos = output / 'kos-stub'
    kos.mkdir(exist_ok=True)
    (kos / 'Makefile.rules').touch()
    cmd = ['make', '--no-print-directory', '-f', 'Makefile', '-n' if dry else '-s',
           f'--assume-old={modules}', f'KOS_BASE={kos}',
           f'KOS_LDFLAGS=-T{kos}/utils/ldscripts/shlelf.xc',
           *assignments, str(obj / target)]
    return subprocess.run(cmd, cwd=GAME, text=True, capture_output=True)


def args_of(output, source='platform/native_static.cpp'):
    commands = [shlex.split(line) for line in output.splitlines()
                if line.startswith('kos-c++ ')]
    matches = [words for words in commands if '-c' in words and
               words[words.index('-c') + 1] == source]
    assert len(matches) == 1, (source, len(matches))
    return matches[0]


def accepted(output, assignments):
    result = make(output, assignments, 'platform/native_static.o')
    assert result.returncode == 0, result.stderr[-4000:]
    return args_of(result.stdout)


def source_guard(args, expected, movie_header):
    source = NATIVE.read_text()
    begin = source.index('#ifndef RE4DC_WORLD_MUTATION31')
    end = source.index('#if defined(RE4DC_ACTOR_LIGHT_FAST_ONLY)', begin)
    guard = source[begin:end]
    defs = [arg for arg in args if arg.startswith('-DRE4DC_')]
    result = subprocess.run(['g++', '-E', '-P', '-x', 'c++', '-I', str(GAME / 'platform'),
                             '-include', str(movie_header),
                             *defs, '-'], input=guard, text=True, capture_output=True)
    assert (result.returncode == 0) == expected, result.stderr
    return result.stderr.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--profile-builder', type=Path,
                        default=HERE / 'stream_portal_profile.py',
                        help='Build31 release profile builder; an explicit reviewed path is allowed before EF08 integrates')
    opts = parser.parse_args()
    builder = opts.profile_builder.resolve()
    if not builder.is_file():
        parser.error('Build31 stream_portal_profile.py is required; provide --profile-builder from the reviewed EF08 delivery')
    spec = importlib.util.spec_from_file_location('stream_portal_profile31', builder)
    profile = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profile)
    # A recovered builder may reside in a separate worktree. Bind its recipe
    # reads to this candidate so source-guard checks cannot quietly use stale
    # feature settings from the helper's original checkout.
    profile.ROOT = ROOT
    profile.DC = ROOT / 'port/dreamcast'
    profile.PROFILE = HERE / 'portal_completion_profiles.json'
    output = opts.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    release = profile.release_chain(output)
    assert len(release) > 500
    base = profile.candidate(output, profile.source_only_paths(output))
    current = profile.resolved(base)
    pacing = {name: current.get(name) for name in ('PVR_PIPELINE', 'PACE_CATCHUP',
              'PACE_TRANS_SKIP', 'PACE_STEADY', 'PACE_HOLD_LOG', 'COARSE')}
    assert pacing == {'PVR_PIPELINE': '2', 'PACE_CATCHUP': '2',
                      'PACE_TRANS_SKIP': '4063', 'PACE_STEADY': '1',
                      'PACE_HOLD_LOG': None, 'COARSE': '1'}, pacing
    assert current['SCENERY_STREAM'] == '0' and current['WORLD_PORTAL_COMPLETION'] == '1'
    absent = accepted(output, base)
    zero = accepted(output, [*base, 'WORLD_MUTATION31=0'])
    assert absent == zero
    assert not any('RE4DC_WORLD_MUTATION31' in arg for arg in absent)
    required = ['WORLD_PART_PLAN29=1', 'WORLD_PREPARED09=1', 'WORLD_PAGES31=1',
                'MOVIE_WORLD_ARENA=1', 'STATIC_OBJ_LIFETIME05=1',
                'WORLD_MUTATION31=1']
    on = [*base, *required]
    generated = make(output, on, 'movie-world-arena.h', dry=False)
    assert generated.returncode == 0, generated.stderr[-4000:]
    movie_header = output / 'obj/movie-world-arena.h'
    assert '#define RE4DC_MOVIE_WORLD_ARENA 1\n' in movie_header.read_text()
    enabled = accepted(output, on)
    assert enabled.count('-DRE4DC_WORLD_MUTATION31=1') == 1
    for knob in ('WORLD_PREPARED09', 'WORLD_PAGES31', 'WORLD_PART_PLAN29',
                 'STATIC_OBJ_LIFETIME05', 'WORLD_PORTAL_COMPLETION',
                 'PS2_PVS_BATCH_COMPOSE', 'SCENERY_CHUNK'):
        assert enabled.count('-DRE4DC_' + knob + '=1') == 1, knob
    source_guard(enabled, True, movie_header)
    cases = []
    for name, changes in [('invalid-empty', ['WORLD_MUTATION31=']),
                          ('invalid-two', ['WORLD_MUTATION31=2']),
                          ('invalid-percent', ['WORLD_MUTATION31=%']),
                          ('invalid-zero-percent', ['WORLD_MUTATION31=0%']),
                          ('invalid-one-percent', ['WORLD_MUTATION31=1%']),
                          ('invalid-zero-space', ['WORLD_MUTATION31=0 ']),
                          ('invalid-one-space', ['WORLD_MUTATION31=1 ']),
                          ('missing-page', ['WORLD_PAGES31=0']),
                          ('missing-prepared', ['WORLD_PREPARED09=0']),
                          ('missing-plan', ['WORLD_PART_PLAN29=0']),
                          ('missing-movie', ['MOVIE_WORLD_ARENA=0']),
                          ('missing-cell', ['STATIC_OBJ_LIFETIME05=0']),
                          ('missing-chunk', ['SCENERY_CHUNK=0'])]:
        result = make(output, [*on, *changes], 'platform/native_static.o')
        assert result.returncode != 0, name
        cases.append({'name': name, 'error': result.stderr[-500:]})
    # If Make's gate is bypassed, the actual TU still refuses the dependency.
    bad = [arg for arg in enabled if arg != '-DRE4DC_WORLD_PAGES31=1']
    source_guard(bad, False, movie_header)
    manifest = {
        'status': 'PASS', 'scope': __doc__, 'release_assignments': len(release),
        'pacing': pacing, 'absent_zero_native_compile_args_equal': True,
        'enabled_definitions': [arg for arg in enabled if arg.startswith('-DRE4DC_')],
        'refusals': cases, 'target_compiled': False,
        'source_sha256': hashlib.sha256(NATIVE.read_bytes()).hexdigest(),
        'profile_sha256': hashlib.sha256(builder.read_bytes()).hexdigest(),
    }
    (output / 'receipt.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('mutation31 release-chain Make/C++ guards:', len(cases), 'refusals PASS')
    print('release pacing:', pacing)


if __name__ == '__main__':
    main()
