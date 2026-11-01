#!/usr/bin/env python3
"""Compile the actual WP29 loader/runtime plus pc geometric core on synthetic data."""
import argparse
import pathlib
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[5]
    platform = root / 'port/dreamcast/game/platform'
    text = (platform / 'native_static.cpp').read_text()
    start = text.index('inline void setup_state(State& st,')
    end = text.index('State& trans_state();', start)
    # Literal production core, including WORLD_PORTAL29 actor guard, portal
    # frustum construction, world/grid AABB tests. No source transformations.
    core = text[start:end]
    with tempfile.TemporaryDirectory(prefix='wp29-host-') as temp:
        target = pathlib.Path(temp)
        (target / 'portal29_pc_core.inc').write_text(core)
        exe = target / 'portal29-host'
        command = ['c++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Wno-misleading-indentation',
                   '-I', str(platform / 'include'), '-I', str(target),
                   str(pathlib.Path(__file__).with_name('portal_runtime_fixture.cpp')), '-o', str(exe)]
        if args.sanitize:
            command[2:2] = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        subprocess.run(command, check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
