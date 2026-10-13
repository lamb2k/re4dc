#!/usr/bin/env python3
"""Read-only first-pass evidence gate; never starts a build, emulator or trace.

Native actor submission does not establish PS2 asset provenance. That independent
pack/fixture audit remains required even when the source-fallback census passes.
Missing coverage is UNPROVEN, not PASS. This is not a STRICT or hardware gate.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re

import texchk


def fields(line):
    return dict(re.findall(r'([A-Za-z_]+)=([^ ]+)', line))


def assess(text, room):
    room = int(room.removeprefix('r'), 16) if isinstance(room, str) else room
    lines = text.splitlines()
    result = {}

    def gate(name, evidence, failures=(), reason='missing positive coverage'):
        result[name] = dict(status='FAIL' if failures else 'PASS' if evidence else 'UNPROVEN',
                            evidence=list(evidence), failures=list(failures))
        if not evidence and not failures:
            result[name]['reason'] = reason

    entries = [l for l in lines if re.search(r'warp: room enter 0*%x\b' % room, l)]
    fatal = [l for l in lines if re.search(r'\b(?:HALT|FAULT|MISALIGN)\b', l)]
    gate('entry', entries)
    gate('no_fatal', entries, fatal)
    unknown = [l for l in lines if 'warp: unknown line' in l or 'warp: area ' in l and 'not found' in l]
    gate('warp_directives', entries, unknown)

    # A motion command and horizontal displacement are both needed. Vertical
    # settling and a few units of idle animation are not a short-walk proof.
    active_room = None
    motions, points = [], []
    for line in lines:
        match = re.search(r'warp: room enter ([0-9a-fA-F]+)', line)
        if match:
            active_room = int(match[1], 16)
        if active_room == room and re.search(r'warp: act \d+ .*stick=-?[1-9]\d* hold=[1-9]', line):
            motions.append(line)
        match = re.search(r'warp: (?:placed|frame \d+) room=([0-9a-fA-F]+) pl=(-?\d+),(-?\d+),(-?\d+)', line)
        if match and int(match[1], 16) == room:
            points.append((int(match[2]), int(match[4])))
    displacement = max(((x-points[0][0])**2 + (z-points[0][1])**2 for x, z in points), default=0)**0.5
    gate('short_walk', motions if motions and displacement >= 32 else [],
         reason='requires a fired movement action and >=32 source units horizontal displacement')
    result['short_walk'].update(horizontal_displacement=displacement, positions_xz=points)

    opened = [l for l in lines if re.search(r'PS2MESH room=0*%x open\b' % room, l)]
    no_std = [l for l in lines if re.search(r'no-std room=0*%x: scenery package not opened' % room, l)]
    draw, world_bad = [], []
    world_room = None
    for line in lines:
        match = re.search(r'PS2MESH room=([0-9a-fA-F]+) open', line)
        if match:
            world_room = int(match[1], 16)
        if 'PS2MESH frame=' in line and ' pass=' in line and world_room == room:
            f = fields(line)
            if int(f.get('native', 0)) > 0:
                draw.append(line)
            if int(f.get('fallback', 0)) or int(f.get('aborts', 0)):
                world_bad.append(line)
        if world_room == room and ('PS2MESH open failed:' in line or 'PS2WORLD fallback ' in line):
            world_bad.append(line)
    gate('ps2_world_draw', opened + no_std + draw[-3:] if opened and no_std and draw else [], world_bad,
         reason='requires matching PS2MESH room/open, no-std and positive native draws')

    census, model_bad, incomplete = [], [], []
    for line in lines:
        if line.startswith('NMRS ') and ' room=' in line:
            f = fields(line)
            if int(f['room'], 16) != room:
                continue
            census.append(line)
            if any(int(f.get(k, 0)) for k in ('declined', 'registry_declined', 'absent', 'would')):
                model_bad.append(line)
        if line.startswith('NMRS ') and 'overflow=' in line and int(fields(line)['overflow']):
            incomplete.append(line)
        if line.startswith('NMRM decline ') or line.startswith('NMRPACK refuse '):
            model_bad.append(line)
    gate('model_source_fallback', census if not incomplete else [], model_bad,
         reason='requires complete matching-room NMRS census; native counts need a separate PS2 asset audit')
    result['model_source_fallback']['coverage_gaps'] = incomplete
    result['model_ps2_asset_provenance'] = dict(status='UNPROVEN', reason='separate selected actor-pack/fixture provenance audit required')
    result['memory_observations'] = [l for l in lines if 'PS2MESH open bytes=' in l or
                                    'native UI VRAM:' in l or 'native stream:' in l][-12:]
    result['scope'] = 'one captured run only; no STRICT, combined-image or hardware acceptance'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--room', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    raw = args.log.read_bytes()
    result = assess(raw.decode('latin1'), args.room)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        passed = texchk.check(args.log)
    result['tex_check'] = dict(status='PASS' if passed else 'FAIL', report=output.getvalue())
    result['log'] = str(args.log.resolve())
    result['log_sha256'] = hashlib.sha256(raw).hexdigest()
    checks = [x['status'] for x in result.values() if isinstance(x, dict) and 'status' in x]
    result['overall'] = 'FAIL' if 'FAIL' in checks else 'UNPROVEN' if 'UNPROVEN' in checks else 'PASS'
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end='')
    return 1 if result['overall'] == 'FAIL' else 2 if result['overall'] == 'UNPROVEN' else 0


if __name__ == '__main__':
    raise SystemExit(main())
