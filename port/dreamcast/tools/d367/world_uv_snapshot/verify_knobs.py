#!/usr/bin/env python3
"""Check the actual Test22 Make recipes for UV and all S/B/R combinations."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True, help='build-controls.json or submit-profile.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text())
    profile = profile.get('profile', profile)
    args.output.mkdir(parents=True, exist_ok=False)
    cases = [('absent', [], True, (0, 0, 0, 0))]
    for select, batch, replay, snapshot in itertools.product((0, 1), repeat=4):
        cases.append((f's{select}-b{batch}-r{replay}-u{snapshot}',
            [f'SCENERY_SELECT_ONLY={select}', f'SCENERY_SUBMIT_BATCH={batch}',
             f'SCENERY_REPLAY_LEAN={replay}', f'SCENERY_UV_SNAPSHOT={snapshot}'],
            True, (select, batch, replay, snapshot)))
    cases += [('invalid', ['SCENERY_UV_SNAPSHOT=2'], False, None),
              ('negative', ['SCENERY_UV_SNAPSHOT=-1'], False, None),
              ('no_chunk', ['SCENERY_UV_SNAPSHOT=1', 'SCENERY_CHUNK=0'], False, None)]
    for transition, r11f in itertools.product((0, 1), repeat=2):
        cases.append((f'owner-t{transition}-r{r11f}', ['SCENERY_UV_SNAPSHOT=1',
            f'PS2_WORLD_TRANSITION_OWNER={transition}', f'PS2_WORLD_R11F_OWNER={r11f}'], True, (0, 0, 0, 1)))
    rows = []
    for name, extra, accepted, modes in cases:
        row = dict(name=name, options=extra, accepted=accepted)
        for tu in ('native_static', 'native_ui'):
            command = profile[tu]['command'] + extra
            run = subprocess.run(command, cwd=DC / 'game', text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (args.output / (name + '-' + tu + '.log')).write_text(run.stdout)
            assert (run.returncode == 0) == accepted, (name, tu, run.stdout)
            if accepted:
                commands = [shlex.split(line) for line in run.stdout.replace('\\\n', ' ').splitlines()
                            if line.startswith('kos-c++ ')]
                assert len(commands) == 1, (name, tu)
                select, batch, replay, snapshot = modes
                expected = dict(SCENERY_SELECT_ONLY=select if tu == 'native_static' else 0,
                    SCENERY_SUBMIT_BATCH=batch, SCENERY_REPLAY_LEAN=replay if tu == 'native_static' else 0,
                    SCENERY_UV_SNAPSHOT=snapshot if tu == 'native_static' else 0)
                for knob, mode in expected.items():
                    assert ('-DRE4DC_' + knob + '=1' in commands[0]) == bool(mode), (name, tu, knob)
            row[tu] = dict(exit=run.returncode,
                diagnostics=[line for line in run.stdout.splitlines() if '***' in line])
        rows.append(row)
    report = dict(status='PASS', configurations=len(rows), translation_units=2, cases=rows,
        source_sha256=hashlib.sha256((DC / 'game/scenery19.mk').read_bytes()).hexdigest(),
        scope='Actual Make dry runs; no compile/link recipes executed. All four switches, owner independence, value and dependency guards.')
    (args.output / 'knob-controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'configurations', 'translation_units')}))


if __name__ == '__main__':
    main()
