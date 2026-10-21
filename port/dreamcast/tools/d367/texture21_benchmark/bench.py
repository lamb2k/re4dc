#!/usr/bin/env python3
"""Prepare immutable texture benchmark receipts; never builds, launches, or estimates FPS."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
SCENES = {
    'farm-wide': ('actorplan/farm-warp.txt', '0x103'),
    'farm-midfight': ('rigid20/hwfarm-warp.txt', '0x103'),
    'woods-bridge': ('enc/fixtures/tour-r100-bridge-warp.txt', '0x100'),
}
# Resolved values are captured, never inferred from an arm label. ANIMALS_OFF=1
# deliberately matches retained current QA; animals-on must be another experiment.
MATCH_KNOBS = ['ALIVE_CAP', 'ALIVE_CAP_N', 'ALIVE_CAP_PARK', 'ANIMALS_OFF',
               'ACTOR_PLAN', 'SKIN_SH4ZAM', 'GAME_SH4ZAM', 'GAME_SH4ZAM_LOGIC',
               'GAME_SH4ZAM_RENDER_ONLY', 'SH4ZAM_ON', 'CAST_MIPMAP',
               'GANADO_ATLAS_DROP', 'NATIVE_ACTOR_LOD', 'LEON_LOD',
               'SS_WINDOW_HOLD_RESTORE', 'PAUSE_NATIVE_PRESENTATION',
               'FOG_FAR', 'FOG_FIT', 'ENEMY_VIS_CULL', 'SCENERY_CHUNK_STREAM']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def receipt(path):
    p = Path(path)
    return {'size': p.stat().st_size, 'sha256': sha(p)}


def write_new(path, value):
    with Path(path).open('x') as out:
        json.dump(value, out, indent=2, sort_keys=True)
        out.write('\n')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def knobs(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            if k in result:
                raise ValueError('duplicate resolved knob: ' + k)
            result[k] = v
    return result


def scene(name, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    relative, room = SCENES[name]
    source = TOOLS / relative
    # Keep all original source fixture commands. Rename only the diagnostic name.
    lines = [s for s in source.read_text().splitlines() if not s.startswith(('name ', '#'))]
    if not any(s == 'god' for s in lines):
        lines.append('god')
    if not any(s.startswith('alivelog ') for s in lines):
        lines.append('alivelog 30')
    warp = 'name texture21-' + name + '\n' + '\n'.join(lines) + '\n'
    (out / 'warp.txt').write_text(warp)
    # Source room frame window, independent of capture wall time or screenshot time.
    # Short window fits the <=50 second guest budget; completeness must be observed.
    plan = {'schema': 1, 'scene': name, 'room': room, 'fixture_source': relative,
            'fixture_source_identity': receipt(source), 'warp': receipt(out / 'warp.txt'),
            'window': {'clock': 'source room frame', 'first': 300, 'last': 419,
                       'settle_last': 299, 'inclusive_frames': 120},
            'input': 'no pad input after fixture entry', 'guest_limit_seconds': 50,
            'required_actual_knobs': {'ALIVE_CAP': '4', 'ALIVE_CAP_N': '4',
                                      'SS_WINDOW_HOLD_RESTORE': '0'},
            'controls': {'animals': 'pin actual ANIMALS_OFF, never infer from fixture comment',
                         'corpse_pile': 'unchanged; separate render-only investigation',
                         'offscreen': 'unchanged; pause is a different experiment'},
            'gate': 'PREPARED_ONLY; no target run or timing result',
            'measurements_required': ['actual source frames and room/camera', 'drawn pictures and logic ticks',
                                      'CPU/PVR cost with evidence type', 'disc request/byte deltas',
                                      'VRAM pinned/dynamic/free/largest and heap peaks',
                                      'screenshots with frame receipts', 'gameplay/error counters']}
    write_new(out / 'scene.json', plan)
    return plan


def seal(repo, build, scene_path, out, macros=()):
    repo, build = Path(repo), Path(build)
    required = ['re4dc-game.elf', 'program.bin', 'resolved-knobs.txt']
    if not all((build / n).is_file() for n in required):
        raise ValueError('missing ELF/program/resolved knobs')
    objects = {str(p.relative_to(build)): receipt(p) for p in sorted((build / 'obj').rglob('*.o'))}
    if not objects:
        raise ValueError('no target objects to bind')
    values = knobs(build / 'resolved-knobs.txt')
    plan = json.loads(Path(scene_path).read_text())
    violations = [f'{k} requires {v}, got {values.get(k)!r}'
                  for k, v in plan['required_actual_knobs'].items() if values.get(k) != v]
    paths = required + sorted(p.name for p in build.glob('*.ovl'))
    preprocessing = {str(Path(p)): receipt(p) for p in macros}
    result = {'schema': 1, 'source': {'head': git(repo, 'rev-parse', 'HEAD'),
               'branch': git(repo, 'branch', '--show-current'),
               'dirty': git(repo, 'status', '--porcelain'),
               'diff_sha256': hashlib.sha256(git(repo, 'diff', 'HEAD').encode()).hexdigest()},
              'build': {n: receipt(build / n) for n in paths}, 'objects': objects,
              'knobs': {k: values.get(k) for k in MATCH_KNOBS},
              'preprocessing': preprocessing, 'scene': plan,
              'input_paths': {'repo': str(repo), 'build': str(build)},
              'admission_errors': violations,
              'unresolved': ([] if preprocessing else ['actual preprocessing not supplied']) +
                            ['ELF-to-program/staged binding and target scene not yet qualified'],
              'evidence': 'source/artifact receipt only; no Flycast or physical console acceptance'}
    write_new(out, result)
    return result


def image(track, out):
    # Reuse the established reader; no extracting or copying full discs.
    spec = importlib.util.spec_from_file_location('fp_iso', TOOLS / 'fullplay/fp_iso.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tr = mod.Track(track, 45000)
    try:
        rows = {p.lstrip('/'): {'size': size, 'sha256': hashlib.sha256(tr.read_bytes(ext, size)).hexdigest()}
                for p, ext, size in mod.files(tr)}
    finally:
        tr.f.close()
    write_new(out, {'track': receipt(track), 'files': rows,
                    'scope': 'in-place staged-file identities; not a release acceptance'})
    return rows


def compare(a, b, ia, ib, allowed):
    errors = []
    if a['scene'] != b['scene']:
        errors.append('scene/control/window differs')
    if a['knobs'] != b['knobs']:
        errors.append('resolved gameplay/render knobs differ')
    if a['source'] != b['source']:
        errors.append('source head/dirty identity differs')
    if sorted(a['preprocessing'].values(), key=lambda x: x['sha256']) != sorted(b['preprocessing'].values(), key=lambda x: x['sha256']):
        errors.append('actual preprocessing differs')
    for key in ['build', 'objects']:
        if a[key] != b[key]:
            errors.append(key + ' differs in asset-only comparison')
    for label, arm in [('baseline', a), ('candidate', b)]:
        errors += [label + ': ' + x for x in arm['admission_errors']]
        if arm['source'].get('dirty'):
            errors.append(label + ': dirty source requires separate reviewed snapshot')
        if not arm['preprocessing']:
            errors.append(label + ': actual preprocessing missing')
    changed = sorted(k for k in set(ia['files']) | set(ib['files']) if ia['files'].get(k) != ib['files'].get(k))
    extra = sorted(set(changed) - set(allowed))
    if extra:
        errors.append('unapproved staged differences: ' + ', '.join(extra))
    # Program + overlays in each image must bind actual sealed build output.
    for label, arm, disc in [('baseline', a, ia), ('candidate', b, ib)]:
        pairs = [('1ST_READ.BIN', 'program.bin')] + [('dc/' + n, n) for n in arm['build'] if n.endswith('.ovl')]
        for staged, built in pairs:
            if disc['files'].get(staged) != arm['build'][built]:
                errors.append(label + ': staged binding mismatch ' + staged)
    return {'asset_pair_admissible': not errors, 'errors': errors, 'changed_files': changed,
            'scope': 'asset-only artifact matching; target frames/gameplay/look/timing remain separate',
            'performance_improvement_claimed': False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scene'); s.add_argument('name', choices=SCENES); s.add_argument('out')
    s = sub.add_parser('seal'); s.add_argument('--repo', required=True); s.add_argument('--build', required=True)
    s.add_argument('--scene', required=True); s.add_argument('--out', required=True)
    s.add_argument('--preprocessed', action='append', default=[])
    s = sub.add_parser('image'); s.add_argument('track'); s.add_argument('out')
    s = sub.add_parser('compare'); s.add_argument('baseline'); s.add_argument('candidate')
    s.add_argument('baseline_image'); s.add_argument('candidate_image'); s.add_argument('--allow-file', action='append', default=[])
    s.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.cmd == 'scene': result = scene(a.name, a.out)
    elif a.cmd == 'seal': result = seal(a.repo, a.build, a.scene, a.out, a.preprocessed)
    elif a.cmd == 'image': result = image(a.track, a.out)
    else:
        read = lambda p: json.loads(Path(p).read_text())
        result = compare(read(a.baseline), read(a.candidate), read(a.baseline_image), read(a.candidate_image), a.allow_file)
        write_new(a.out, result)
    print(json.dumps({'command': a.cmd, 'ok': result.get('asset_pair_admissible', True) if isinstance(result, dict) else True}))
    if a.cmd == 'compare' and not result['asset_pair_admissible']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
