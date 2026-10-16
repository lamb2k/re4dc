#!/usr/bin/env python3
"""Reject a supposed switch comparison that actually built the same configuration.

verify_pair.py CONTROL_OUT CANDIDATE_OUT [--switch NAME ...] [--output JSON]
Uses resolved make values, compiler command lines, affected object code and the
loadable image. ELF debug paths are deliberately excluded from code identity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile

SWITCHES = ('ACTOR_PROOF_LEAN', 'ACTOR_MATERIAL_RECORD', 'ACTOR_BIND_REUSE')
SOURCES = {'coarse_actor': 'coarse_actor.cpp', 'coarse_ganado': 'coarse_ganado_cast.cpp'}
TOOLS = Path('/opt/toolchains/dc/sh-elf/bin')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect(path, switches):
    knobs = dict(line.split('=', 1) for line in (path / 'resolved-knobs.txt').read_text().splitlines() if '=' in line)
    lines = (path / 'build.log').read_text().splitlines()
    result = {'path': str(path), 'resolved': {k: knobs.get(k) for k in switches}, 'objects': {}}
    for name, source in SOURCES.items():
        command = next(line for line in lines if line.startswith('kos-c++ ') and ' -c ' + source + ' ' in line)
        argv = shlex.split(command)
        definitions = {k: next((a.split('=', 1)[1] for a in reversed(argv)
                                      if a.startswith('-DRE4DC_' + k + '=')), '0') for k in switches}
        code = subprocess.check_output([str(TOOLS / 'sh-elf-objdump'), '-d', str(path / 'obj' / (name + '.o'))])
        # Only the first header line names the object path. The rest is code,
        # local labels and relocatable addresses, so path-only ELF changes pass.
        code = b'\n'.join(code.splitlines()[2:])
        result['objects'][name] = {'definitions': definitions, 'code_sha256': digest(code)}
    with tempfile.TemporaryDirectory(prefix='actor-switch-') as tmp:
        image = Path(tmp) / 'image.bin'
        subprocess.run([str(TOOLS / 'sh-elf-objcopy'), '-R', '.stack', '-O', 'binary',
                        str(path / 're4dc-game.elf'), str(image)], check=True)
        result['image_sha256'] = digest(image.read_bytes())
    result['elf_sha256'] = digest((path / 're4dc-game.elf').read_bytes())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--switch', action='append')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    switches = args.switch or SWITCHES
    control, candidate = (inspect(p, switches) for p in (args.control, args.candidate))
    changed = [k for k in switches if control['resolved'][k] != candidate['resolved'][k]]
    errors = []
    if not changed:
        errors.append('No selected resolved knob differs; this is not an off/on experiment.')
    for arm in (control, candidate):
        for k in switches:
            # All three affect coarse_actor; BIND_REUSE also affects coarse_ganado.
            for obj in ('coarse_actor', 'coarse_ganado') if k == 'ACTOR_BIND_REUSE' else ('coarse_actor',):
                if arm['resolved'][k] != arm['objects'][obj]['definitions'][k]:
                    errors.append('%s: %s disagrees with %s compiler definition' % (arm['path'], k, obj))
    if control['image_sha256'] == candidate['image_sha256']:
        errors.append('Loadable images are identical; do not attribute a timing difference to these switches.')
    report = {'status': 'INVALID_PAIR' if errors else 'DISTINCT_PAIR', 'changed_switches': changed,
              'control': control, 'candidate': candidate, 'errors': errors}
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
