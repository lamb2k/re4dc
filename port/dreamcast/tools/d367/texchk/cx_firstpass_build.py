#!/usr/bin/env python3
"""Build one private, untraced test9 dW arm for per-room first-pass checks.

The authoritative test9 script is read and snapshotted, never executed. Its
F/LOOK/PS2/P2/T9K/ON/WP assignments supply the unchanged gameplay recipe. Only
TEX_CHECK=2 and explicit disabled logic/decision traces are appended to dW.
All output, programs, registry and logs live under --output-root. The standard
build-slot lock is the only shared write. Run in an isolated checkout.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess


NAMES = ('F', 'LOOK', 'PS2', 'P2', 'T9K', 'ON', 'WP')
REQUIRED = {'TEX_CHECK': '2', 'NATIVE_MODEL_REGISTRY_CENSUS': '1',
            'LOGIC_TRACE': '0', 'GAME_DECISION_TRACE': '0',
            'DBG_WARP': '1', 'PC_SAMPLER': '1'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recipe_groups(source):
    """Accept test9's audited assignment grammar; never run its build function."""
    assignments = {}
    for line in source.splitlines():
        name, _, value = line.partition('=')
        if name not in NAMES:
            continue
        if name in assignments:
            raise ValueError('duplicate recipe assignment: ' + name)
        if name == 'T9K':
            match = re.fullmatch(r'\$\{T9K:-(.*)\}', value)
        else:
            match = re.fullmatch(r'"(.*)"', value)
        if not match:
            raise ValueError('unsupported recipe assignment: ' + line)
        value = match[1]
        if name == 'ON':
            value = value.replace('${XON:-}', '')
            for dependency in ('T9K', 'PS2', 'P2'):
                value = value.replace('$' + dependency, assignments[dependency])
        if not re.fullmatch(r'[A-Za-z0-9_=/ .+:-]*', value):
            raise ValueError('recipe needs review: ' + line)
        assignments[name] = value
    if set(assignments) != set(NAMES):
        raise ValueError('missing test9 groups: ' + str(set(NAMES) - set(assignments)))
    return {name: shlex.split(assignments[name]) for name in NAMES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', type=Path,
                        default=Path('/root/probe/lanes-20261012/test9/t9-build.sh'))
    parser.add_argument('--tree', type=Path, default=Path(__file__).resolve().parents[5])
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--label', default='cxfirstpassW')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'cx[A-Za-z0-9_-]+', args.label):
        parser.error('label must start with cx and contain only letters, digits, _ or -')
    tree, root = args.tree.resolve(), args.output_root.resolve()
    # A fresh root prevents route-build's legacy cleanup from replacing evidence.
    root.mkdir(parents=True, exist_ok=False)
    groups = recipe_groups(args.recipe.read_text())
    knobs = (groups['F'] + groups['LOOK'] + groups['ON'] + ['IMAGE_PAD_BYTES=0',
             'NATIVE_MODEL_REGISTRY_CENSUS=1'] + groups['WP'] +
             ['TEX_CHECK=2', 'LOGIC_TRACE=0', 'GAME_DECISION_TRACE=0'])
    build = root / ('out-' + args.label)
    program = root / 'programs' / ('candidate-route' + args.label)
    snapshot = root / 'cx-test9-recipe.sh'
    snapshot.write_bytes(args.recipe.read_bytes())
    env = dict(os.environ)
    # Build knobs supplied by ambient GNU make environment are not part of test9.
    for name in ('MAKEFLAGS', 'MFLAGS', 'MAKEOVERRIDES', 'GNUMAKEFLAGS'):
        env.pop(name, None)
    private_env = {'TREE': str(tree), 'ROUTE_OUT_ROOT': str(root),
                   'ROUTE_PROGRAMS_DIR': str(root / 'programs'),
                   'ROUTE_PROGRAMS_JSON': str(root / 'programs-route.json'),
                   'ROUTE_REGISTRY_LOCK': str(root / 'programs-route.lock'),
                   'SOURCE_DATE_EPOCH': '1760000000', 'JOBS': '4'}
    env.update(private_env)
    route = tree / 'port/dreamcast/tools/d367/route/route-build.sh'
    command = ['bash', '/root/probe/d367-buildslot.sh', 'bash', str(route), args.label] + knobs
    report = {'label': args.label, 'tree': str(tree), 'output': str(build),
              'candidate_dir': str(program), 'recipe': str(args.recipe),
              'recipe_snapshot': str(snapshot), 'recipe_sha256': sha(snapshot),
              'tree_head': subprocess.check_output(['git', '-C', str(tree), 'rev-parse', 'HEAD'], text=True).strip(),
              'recipe_groups': groups, 'command': command, 'environment': private_env,
              'route_sha256': sha(route), 'driver_sha256': sha(Path(__file__)),
              'diagnostic_additions_to_test9_dW': ['TEX_CHECK=2', 'LOGIC_TRACE=0', 'GAME_DECISION_TRACE=0'],
              'required_resolved': REQUIRED, 'status': 'prepared'}
    report_path = root / 'cx-build-provenance.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'provenance': str(report_path), 'candidate_dir': str(program)}), flush=True)
    if args.prepare_only:
        return 0
    with (root / 'cx-build.log').open('w') as log:
        run = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT)
    report['returncode'] = run.returncode
    report['status'] = 'build-failed'
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    if run.returncode:
        return run.returncode
    resolved = dict(line.split('=', 1) for line in (build / 'resolved-knobs.txt').read_text().splitlines() if '=' in line)
    mismatches = {key: {'expected': value, 'actual': resolved.get(key)}
                  for key, value in REQUIRED.items() if resolved.get(key) != value}
    missing = build / 'missing.txt'
    report.update(resolved_checks=mismatches, missing_bytes=missing.stat().st_size if missing.exists() else None,
                  elf_sha256=sha(build / 're4dc-game.elf'),
                  resolved_knobs=str(build / 'resolved-knobs.txt'), syms=str(build / 'syms.txt'))
    report['status'] = 'passed' if not mismatches and report['missing_bytes'] == 0 else 'verification-failed'
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
