#!/usr/bin/env python3
"""Build and exercise the production ACTOR_FORMAT32 UV certificate helper."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='actor-uv32-') as directory:
        binary = Path(directory) / 'uv16-host'
        command = ['c++', '-std=c++17', '-O2', '-Wall', '-Wextra']
        if args.sanitize:
            command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        command += [str(Path(__file__).with_name('uv16_host.cpp')), '-o', str(binary)]
        subprocess.run(command, check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    main()
