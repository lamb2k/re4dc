#!/usr/bin/env python3
"""Reusable Make-derived SH-4 compilation and disabled byte-identity gate.

The default matrix qualifies the existing-switch fixes in Build34. --config accepts the same JSON shape as
--print-config for later isolated builds. Every changed existing translation
unit is compiled from the archived integration tree and current source with
changed existing controls absent and explicitly zero. Complete preprocessed files and
objects must match byte for byte. Enabled arms compile production source and
perform a relocatable link; this does not build a whole game or prove visuals.
Debug records and preprocessor line markers are consistently omitted. No game
data, console, emulator, target cache timing or full-image PASS is claimed.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = 'ac154934df7ddf14fc5c6b6932a24a99a253f8e6'
spec = importlib.util.spec_from_file_location('cloud34_previous_controls', HERE.parent / 'build26/build_controls.py')
previous = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = previous
spec.loader.exec_module(previous)
shared, profile = previous.shared, previous.profile
QA = previous.QA + ['QA_LINK=1', 'QA_LINK_REVIEW28=1']
# These are existing switches: no new runtime opt-in or recipe promotion.
CONE = ['SCENERY_CONE=1', 'SCENERY_CONE_SIGN=1']
PIECE = ['SCENERY_PIECE_STATE=1', 'PS2_WORLD_HDR_CACHE=1']
FRONT = ['FRONT_TEXOBJ=1']
CHUNK = ['CHAR_CHUNK=1', 'CHAR_CHUNK_BACKEND=1', 'CHUNK_SUBMIT=1', 'COARSE_ONE_SUBMIT=1']
COMBINED = QA + CONE + PIECE + FRONT + CHUNK
DEFAULT = {
    'knobs': ['SCENERY_CONE', 'SCENERY_PIECE_STATE', 'FRONT_TEXOBJ',
              'CHAR_CHUNK', 'CHAR_CHUNK_BACKEND'],
    'units': {'native_static': ['platform/native_static.o', 'platform/native_static.cpp'],
              'trans': ['src/game/trans.o', '../../../src/game/trans.cpp'],
              'native_actor_fast': ['platform/native_actor_fast.o', 'platform/native_actor_fast.cpp'],
              'native_ui': ['platform/native_ui.o', 'platform/native_ui.cpp'],
              'chunk_submit': ['platform/chunk_submit.o', 'platform/chunk_submit.cpp']},
    'knob_units': {'SCENERY_CONE': ['native_static'],
                   'SCENERY_PIECE_STATE': ['native_static', 'native_ui'],
                   'FRONT_TEXOBJ': ['trans'],
                   'CHAR_CHUNK': ['native_actor_fast'],
                   'CHAR_CHUNK_BACKEND': ['native_actor_fast']},
    'knob_headers': {'FRONT_TEXOBJ': {'trans': 'records30.h'}},
    # Existing, unchanged provider TUs are compiled and linked only in ON arms.
    # They are not new production sources and not included in OFF identity counts.
    'on_only_units': ['native_ui', 'chunk_submit'],
    'off_profiles': {'release': ['NMR_POOL_LOD=0'], 'qa': QA},
    'on_profiles': {
        'cone-plus': QA + CONE,
        'cone-minus': QA + CONE + ['SCENERY_CONE_SIGN=-1'],
        'piece': QA + PIECE,
        'front': QA + FRONT,
        'combined-exact': COMBINED + ['ACTOR_LIGHT_FAST_ONLY=0', 'CHAR_CHUNK=2'],
        'combined-fast': COMBINED + ['ACTOR_LIGHT_FAST_ONLY=1'],
    },
    'existing_on_controls': {
        'cone-plus': ['native_static'], 'cone-minus': ['native_static'],
        'piece': ['native_static'], 'front': ['trans'],
        'combined-exact': ['native_actor_fast'], 'combined-fast': ['native_actor_fast'],
    },
    'watch_fields': ['QA_MENU', 'QA_LINK', 'SCENERY_CONE_SIGN', 'PS2_WORLD_HDR_CACHE',
                     'PS2_WORLD_ROOMS', 'SCENERY_CHUNK', 'SCENERY_STREAM',
                     'SCENERY_SUBMIT_BATCH', 'SCENERY_REPLAY_LEAN', 'PS2_PVS',
                     'PS2_PVS_BATCH_COMPOSE', 'WORLD_PORTAL29', 'FRONT_NATIVE',
                     'COARSE_ONE_SUBMIT', 'CHUNK_SUBMIT', 'ACTOR_LIGHT_FAST_ONLY'],
    'must_resolve': ['re4dc_ps2_piece_slot', 're4dc_chunk_'],
    'invalid_compositions': [
        *[{'reason': 'enabled scenery cone sign must be exactly 1 or -1',
           'options': QA + ['SCENERY_CONE=1', 'SCENERY_CONE_SIGN=' + value]}
          for value in ('', '0', '2', '1 -1')],
        {'reason': 'enabled actor chunk backend supports only 0 or 1',
         'options': QA + ['CHAR_CHUNK=1', 'CHAR_CHUNK_BACKEND=2']},
        {'reason': 'actor chunk backend requires the shared provider',
         'options': QA + ['CHAR_CHUNK=1', 'CHAR_CHUNK_BACKEND=1', 'CHUNK_SUBMIT=0']},
    ],
    'accepted_compositions': [
        {'reason': 'disabled scenery cone ignores its unused sign',
         'options': QA + ['SCENERY_CONE=0', 'SCENERY_CONE_SIGN=2']},
        {'reason': 'disabled scenery cone also ignores an empty unused sign',
         'options': QA + ['SCENERY_CONE=0', 'SCENERY_CONE_SIGN=']},
        {'reason': 'enabled scenery cone accepts the explicit positive sign',
         'options': QA + ['SCENERY_CONE=1', 'SCENERY_CONE_SIGN=+1']},
    ],
}
OBJECT_FIELDS = ('PLATFORM_OBJS', 'GAME_OBJS', 'GAME_LDFLAGS')


def compact_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def compact_state(row):
    result = dict(row)
    result['state'] = {key: value for key, value in row['state'].items() if key not in OBJECT_FIELDS}
    result['object_selection'] = {key: dict(sha256=compact_hash(row['state'][key]), words=len(row['state'][key].split()))
                                  for key in OBJECT_FIELDS if key in row['state']}
    return result


def validate_config(config):
    assert config['knobs'] and len(set(config['knobs'])) == len(config['knobs'])
    for name in config['knobs']:
        assert re.fullmatch(r'[A-Z][A-Z0-9_]*', name), name
    assert config['units'] and config['off_profiles'] and config['on_profiles']
    for name, (target, source) in config['units'].items():
        assert re.fullmatch(r'[a-zA-Z0-9_]+', name), name
        assert target.endswith('.o') and not Path(target).is_absolute(), target
        assert (DC / 'game' / source).resolve().is_relative_to(ROOT), source
    assert set(config.get('on_only_units', [])) <= set(config['units'])
    for matrix in ('off_profiles', 'on_profiles'):
        for name, options in config[matrix].items():
            assert re.fullmatch(r'[a-zA-Z0-9_-]+', name), name
            assert all(re.fullmatch(r'[A-Z][A-Z0-9_]*=[^\n]*', item) for item in options), options


def probe(out, tree, kos, sdk, options, knobs, watch):
    out.mkdir(parents=True, exist_ok=False)
    fields = tuple(dict.fromkeys([*knobs, *watch, *OBJECT_FIELDS]))
    query = out / 'query.mk'
    query.write_text('.PHONY: cloud-state\ncloud-state:\n\t@:\n' + '\n'.join(
        f'$(info CLOUD_STATE {name}=$({name}))' for name in fields) + '\n')
    command, _ = profile.make_command(out, tree, kos, sdk, options, 'cloud-state')
    command[3:3] = ['-f', 'Makefile', '-f', str(query)]
    result = subprocess.run(command, cwd=tree / 'port/dreamcast/game', capture_output=True, text=True)
    output = result.stdout + result.stderr
    (out / 'make.log').write_text(output)
    state = dict(line[len('CLOUD_STATE '):].split('=', 1) for line in output.splitlines()
                 if line.startswith('CLOUD_STATE '))
    return dict(returncode=result.returncode, state=state,
                command_sha256=compact_hash(command), log_sha256=profile.sha(out / 'make.log'),
                error=output[-2500:] if result.returncode else None)


def baseline_tree(output, cache, baseline):
    tree = (cache / baseline) if cache else (output / 'baseline-tree')
    if tree.exists():
        assert cache and (tree / '.cloud-baseline-sha').read_text().strip() == baseline
        return tree
    tree.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git', 'archive', baseline], cwd=ROOT))) as archive:
        archive.extractall(tree, filter='data')
    if cache:
        (tree / '.cloud-baseline-sha').write_text(baseline + '\n')
    return tree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'sh4-cxx', 'kos-root', 'sdk-root', 'toolchain-receipt'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--baseline', default=BASELINE)
    parser.add_argument('--baseline-cache', type=Path, help='Reuse an independently archived commit tree; used inputs are revalidated')
    parser.add_argument('--config', type=Path, help='Qualification matrix JSON; see --print-config')
    parser.add_argument('--print-config', action='store_true')
    parser.add_argument('--only', choices=('off', 'on'))
    parser.add_argument('--composition', help='Single named profile; omit for the complete matrix')
    args = parser.parse_args()
    config = json.loads(args.config.read_text()) if args.config else DEFAULT
    validate_config(config)
    if args.print_config:
        print(json.dumps(config, indent=2))
        return
    for name in ('output', 'sh4_cxx', 'kos_root', 'sdk_root', 'toolchain_receipt'):
        if getattr(args, name) is None:
            parser.error('--' + name.replace('_', '-') + ' is required')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    builder = profile.Build(out)
    toolchain = previous.verify_toolchain(builder, cxx, kos, sdk, args.toolchain_receipt.resolve())
    prefix = str(cxx).removesuffix('g++')
    baseline = subprocess.check_output(['git', 'rev-parse', args.baseline], cwd=ROOT, text=True).strip()
    tree = baseline_tree(out, args.baseline_cache.resolve() if args.baseline_cache else None, baseline) if args.only != 'on' or config.get('existing_on_controls') else None
    knobs, units = tuple(config['knobs']), tuple(config['units'])
    base_units = tuple(name for name in units if name not in config.get('on_only_units', []))
    assert base_units, 'At least one changed existing translation unit is required'
    profile.UNITS.update({name: tuple(value) for name, value in config['units'].items()})
    helper_paths = [Path(__file__), Path(previous.__file__), Path(shared.__file__), Path(profile.__file__),
                    Path(profile.profile.__file__), Path(profile.profile.helpers.__file__),
                    Path(profile.profile.helpers._helpers.__file__), Path(profile.profile.helpers.release_profile.__file__)]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in helper_paths}
    artifacts, states, recipes, dependencies, links = {}, {}, {}, {}, {}
    disabled, enabled, rejected, accepted = [], [], [], []
    header_definitions, fix_size_deltas = {}, {}
    cache_headers, baseline_verified = {}, set()

    def verify_archived(path):
        if path in baseline_verified:
            return
        expected = subprocess.check_output(['git', 'rev-parse', baseline + ':' + path], cwd=ROOT, text=True).strip()
        raw = (tree / path).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert actual == expected, (path, 'archived source differs from integration commit')
        baseline_verified.add(path)

    def track_input(path, digest):
        assert frozen.get(path, digest) == digest, (path, 'input changed during gate')
        frozen[path] = digest

    def compile_arm(name, source_tree, options, selected_units, zeros=()):
        flags, recipe, sources = profile.derive(out / name, cxx, kos, sdk, options, tree=source_tree, units=selected_units)
        recipes[name] = dict(options=options, profile_sha256=profile.sha(out / name / 'profile.json'),
                             flags_sha256=compact_hash(flags))
        for unit, row in recipe['profiles'].items():
            for path, digest in row['recipe_inputs']['source_sha256'].items():
                if source_tree == ROOT:
                    track_input(path, digest)
                else:
                    verify_archived(path)
            source = sources[unit].resolve()
            relative = str(source.relative_to(source_tree))
            if source_tree == ROOT:
                track_input(relative, profile.sha(source))
            else:
                verify_archived(relative)
            guards = [Path(value) for value in flags[unit] if value.endswith('/koscache-p2/require_p2.h')]
            if guards:
                assert len(guards) == 1
                key = 'base' if source_tree != ROOT else 'current'
                if key not in cache_headers:
                    prepared = out / ('kos-cache-' + key)
                    builder.run([sys.executable, source_tree / 'port/dreamcast/tools/d367/kos_cache_audit/prepare.py',
                                 '--kos-root', kos, '--output', prepared, '--patch',
                                 source_tree / 'port/dreamcast/patches/kos-804b319-cache-p2.patch'], label='prepare-cache-' + key)
                    cache_headers[key] = prepared
                if not guards[0].parent.exists():
                    shutil.copytree(cache_headers[key], guards[0].parent)
            common = [*flags[unit], *['-DRE4DC_' + knob + '=0' for knob in zeros], '-iquote', str(source.parent)]
            entry = {}
            for suffix, phase in (('ii', ['-E', '-P']), ('o', ['-c', '-fstack-usage', '-MMD', '-MF', out / f'{name}-{unit}.d'])):
                destination = out / f'{name}-{unit}.{suffix}'
                builder.run([*common, '-x', 'c++', '-', *phase, '-o', destination], cwd=source.parent,
                            source=source.read_bytes(), label=f'{name}-{unit}-{suffix}')
                entry[suffix] = dict(bytes=destination.stat().st_size, sha256=profile.sha(destination))
                if suffix == 'o':
                    stack = profile.stack_usage(destination.with_suffix('.su'))
                    entry[suffix].update(profile.sections(destination), stack=dict(
                        max_bytes=max((item['bytes'] for item in stack), default=0),
                        functions=len(stack), details_sha256=profile.sha(destination.with_suffix('.su'))))
                    closure = shared.dependencies(out / f'{name}-{unit}.d', source_tree, source.parent)
                    dependencies.setdefault(name, {})[unit] = compact_hash(closure)
                    for path, digest in closure.items():
                        if source_tree == ROOT:
                            track_input(path, digest)
                        else:
                            verify_archived(path)
            artifacts.setdefault(name, {})[unit] = entry
        states[name] = probe(out / (name + '-make'), source_tree, kos, sdk, options, knobs, config.get('watch_fields', []))
        assert states[name]['returncode'] == 0, states[name]
        return flags

    if args.only != 'on':
        for kind, options in config['off_profiles'].items():
            if args.composition and kind != args.composition:
                continue
            flags = {}
            for arm, zeros in (('baseline', ()), ('absent', ()), ('zero', knobs)):
                name = kind + '-' + arm
                source_tree = tree if arm == 'baseline' else ROOT
                flags[arm] = compile_arm(name, source_tree, options + [knob + '=0' for knob in zeros], base_units, zeros)
                if arm != 'baseline':
                    assert all(states[name]['state'][knob] == '0' for knob in knobs), (name, states[name])
                    for unit in base_units:
                        before = [shared.normalized(value, out / (kind + '-baseline'), tree) for value in flags['baseline'][unit]]
                        after = [shared.normalized(value, out / name, ROOT) for value in flags[arm][unit]]
                        assert before == after, (name, unit, 'disabled Make flags changed')
                        for suffix in ('ii', 'o'):
                            assert (out / f'{name}-{unit}.{suffix}').read_bytes() == (out / f'{kind}-baseline-{unit}.{suffix}').read_bytes(), (name, unit, suffix)
                            disabled.append(dict(profile=kind, arm=arm, unit=unit, artifact=suffix, identical=True))
                    for field in OBJECT_FIELDS:
                        before = shared.normalized(states[kind + '-baseline']['state'][field], out / (kind + '-baseline-make'), tree)
                        after = shared.normalized(states[name]['state'][field], out / (name + '-make'), ROOT)
                        assert before == after, (name, field, 'disabled object/link selection changed')
                print('PASS', name, flush=True)

    if args.only != 'off':
        for kind, options in config['on_profiles'].items():
            if args.composition and kind != args.composition:
                continue
            name = 'on-' + kind
            flags = compile_arm(name, ROOT, options, units)
            resolved_options = dict(value.split('=', 1) for value in options)
            for knob in knobs:
                assert states[name]['state'][knob] == resolved_options.get(knob, '0'), (name, knob, states[name])
                value = states[name]['state'][knob]
                if value != '0':
                    targets = config.get('knob_units', {}).get(knob)
                    expected = '-DRE4DC_' + knob + '=' + value
                    if targets:
                        for unit in targets:
                            header = config.get('knob_headers', {}).get(knob, {}).get(unit)
                            if header:
                                paths = [Path(flags[unit][i + 1]) for i, word in enumerate(flags[unit][:-1])
                                         if word == '-include' and Path(flags[unit][i + 1]).name == header]
                                assert len(paths) == 1, (name, knob, unit, 'generated definition header missing')
                                body = paths[0].read_text()
                                assert re.search(r'^#define\s+RE4DC_' + knob + r'\s+' + re.escape(value) + r'\s*$',
                                                 body, re.MULTILINE), (name, knob, body)
                                header_definitions.setdefault(name, {})[knob] = dict(
                                    unit=unit, generated_header=header, sha256=profile.sha(paths[0]), value=value)
                            else:
                                assert expected in flags[unit], (name, knob, unit, 'enabled compiler definition missing')
                    else:
                        assert any(expected in row for row in flags.values()), (name, knob, 'enabled compiler definition missing')
            # Existing switches already had ON implementations. Compare the
            # changed TUs against that exact same ON profile at integration,
            # so repair cost is not conflated with enabling the older feature.
            control_units = tuple(config.get('existing_on_controls', {}).get(kind, []))
            if control_units:
                control = 'control-' + name
                control_flags = compile_arm(control, tree, options, control_units)
                changes = {}
                for unit in control_units:
                    before_flags = [shared.normalized(value, out / control, tree) for value in control_flags[unit]]
                    after_flags = [shared.normalized(value, out / name, ROOT) for value in flags[unit]]
                    assert before_flags == after_flags, (name, unit, 'existing-ON flags differ')
                    before = artifacts[control][unit]['o']
                    after = artifacts[name][unit]['o']
                    delta = {key: after[key] - before[key] for key in
                             ('executable_bytes', 'allocated_bytes', 'zero_fill_bytes')}
                    frames = []
                    for arm in (control, name):
                        rows = profile.stack_usage(out / f'{arm}-{unit}.su')
                        frames.append({re.sub(r'^.*?:[0-9]+:[0-9]+:', '', row['function']): row['bytes'] for row in rows})
                    delta.update(max_stack_before=before['stack']['max_bytes'], max_stack_after=after['stack']['max_bytes'],
                                 changed_local_frames=[dict(function=fn, before=frames[0].get(fn), after=frames[1].get(fn))
                                                       for fn in sorted(set(frames[0]) | set(frames[1]))
                                                       if frames[0].get(fn) != frames[1].get(fn)],
                                 object_identical=before['sha256'] == after['sha256'])
                    changes[unit] = delta
                fix_size_deltas[kind] = dict(control=control, baseline=baseline, units=changes,
                                            scope='Same existing-ON Make options; changed TUs only; local stack frames, not call-chain peaks')
                print('PASS', control, flush=True)
            combined = out / (name + '-combined.o')
            builder.run([prefix + 'ld', '-m', 'shlelf', '-r', *[out / f'{name}-{unit}.o' for unit in units], '-o', combined], label=name + '-partial-link')
            undefined = builder.run([prefix + 'nm', '-u', '-C', combined], label=name + '-undefined').decode()
            unresolved_new = [line for line in undefined.splitlines() if any(text in line for text in config.get('must_resolve', []))]
            assert not unresolved_new, (name, unresolved_new)
            links[name] = dict(sha256=profile.sha(combined), checked_symbol_fragments=config.get('must_resolve', []),
                               new_hooks_resolved=True, ordinary_game_references_remain=True)
            enabled.append(dict(profile=kind, units=list(units), compiled=True))
            print('PASS', name, flush=True)

    for knob, values in config.get('invalid_values', {}).items():
        for value in values:
            row = probe(out / f'reject-{len(rejected)}', ROOT, kos, sdk, QA + [knob + '=' + value], knobs, [])
            assert row['returncode'] != 0, (knob, value, 'invalid assignment accepted')
            rejected.append(dict(knob=knob, value=value, **row))
    for item in config.get('invalid_compositions', []):
        row = probe(out / f'reject-{len(rejected)}', ROOT, kos, sdk, item['options'], knobs, [])
        assert row['returncode'] != 0, (item['reason'], 'invalid composition accepted')
        rejected.append(dict(reason=item['reason'], **row))
    for item in config.get('accepted_compositions', []):
        row = probe(out / f'accept-{len(accepted)}', ROOT, kos, sdk, item['options'], knobs, [])
        assert row['returncode'] == 0, (item['reason'], 'supported disabled composition rejected')
        accepted.append(dict(reason=item['reason'], **row))
    release = probe(out / 'release-defaults', ROOT, kos, sdk, ['NMR_POOL_LOD=0'], knobs, config.get('watch_fields', []))
    assert release['returncode'] == 0 and all(release['state'][knob] == '0' for knob in knobs), release
    assert frozen == {path: profile.sha(ROOT / path) for path in frozen}, 'source/build inputs changed during gate; rerun'
    assert disabled or enabled, 'No selected profiles ran'
    report = dict(status='PASS', scope=__doc__, baseline=baseline, gate_half=args.only or 'both', composition=args.composition,
                  config=config, config_sha256=compact_hash(config), source_sha256=frozen, **toolchain,
                  off_identity_comparisons=len(disabled), disabled_identity=disabled, enabled_compiles=enabled,
                  artifacts=artifacts, profiles=recipes, dependency_set_sha256=dependencies,
                  make_states={name: compact_state(row) for name, row in states.items()},
                  partial_links=links, make_rejections=[compact_state(row) for row in rejected],
                  make_acceptances=[compact_state(row) for row in accepted], generated_knob_definitions=header_definitions,
                  matched_existing_on_fix_deltas=fix_size_deltas,
                  release_state=compact_state(release),
                  raw_evidence=dict(build_commands='build-commands.json', complete_profiles='PROFILE/profile.json',
                                    stack_details='PROFILE-UNIT.su', complete_preprocessed='PROFILE-UNIT.ii', target_objects='PROFILE-UNIT.o'),
                  validation_only_overrides=dict(NMR_POOL_LOD=0, reason='Private selected LOD input unavailable; same public recipe override in control and candidate'))
    (out / 'target-controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', off_comparisons=len(disabled), enabled=len(enabled), receipt=str(out / 'target-controls.json'))))


if __name__ == '__main__':
    main()
