#!/usr/bin/env python3
"""Explicit private emission of the frozen605 officer BODY fragment and textures.

No room/archive/image/staging action. Never writes an existing directory. C:
must remain above18GiB+64MiB; three bundle copies plus tooling fit below4MiB.
"""
from __future__ import annotations
import argparse, hashlib, importlib, json, shutil, sys
from pathlib import Path
TOOLS = Path(__file__).resolve().parents[2]
FROZEN_COMMIT = '605d76beddff0a1e132b8be362937e143f325730'
PLAN_SHA = '630dd8ea65cef68de30102cd7a109017848a4cf4035fefa2fe60650c0d2215ce'
FLOOR = 18 * 1024**3 + 64 * 1024**2
TOTAL_BUDGET = 4 * 1024**2
TOOL_ALLOWANCE = 1024**2
PINS = {
 'd367/issue52_visuals/transform_officer_body.py': '29c13f039fc49bbf5862e24f855a7ae8f89003a93c6318302a2cc6dcdf73592c',
 'ps2_objects.py': 'c2d9f2bd10dbfbd16b07d9ddbb198e59c05c0ee0730796a93cdf116c9117b06c',
 'ps2_bin.py': 'a9aef9f92f8c7c89c7539ef171d51be92e132090397a4405d0ea3e2a09c7d9a1',
 'convert_character.py': '78e6bdd1a5464f4f1fcc13c8143662abffd9c39ae2270b9bca10b9eceb507470',
 'convert_room_bins.py': 'ae36a661041e39078f51f18401ed3c7c840b792e147460967238b0abd838280b',
 'room_smd.py': '5487ea552c5f836c8244b8cd280bc2d3225f7a7f3d29287b0a0b4d63582c8d44',
 'le_mirror.py': 'dce98783d944ced311d238277c13fa793693d501477cdd7e411c29c98ccaadcb',
 'convert_tpl.py': 'e306b31fb8a46d2fc993c75be22ee0064454fd0d91d32135b5c5bb08b4d232c2',
 'd367/test12fx/ps2_tpl_decode.py': '19592a896163d12a3ba321be1a57a8dc46edd15bdcecd0fb9ce17fd63ecf80f7',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def c_free():
    volume = Path('/mnt/c') if Path('/mnt/c').is_dir() else Path('C:/')
    return shutil.disk_usage(volume).free


def check_capacity(planned, free):
    if planned < 0 or 3 * planned + TOOL_ALLOWANCE > TOTAL_BUDGET:
        raise ValueError('three copies exceed4MiB combined budget')
    if free < FLOOR + planned:
        raise ValueError('C: floor18GiB+64MiB would be crossed')


def output_guard(out, sources):
    if out.exists():
        raise ValueError('refusing to overwrite output directory')
    if out.resolve().is_relative_to(sources.resolve()):
        raise ValueError('output must stay outside original source directory')


def frozen_transform(plan_path, sources):
    raw = plan_path.read_bytes()
    if sha(raw) != PLAN_SHA:
        raise ValueError('unreviewed605 source plan identity')
    for name, expected in PINS.items():
        if sha((TOOLS / name).read_bytes()) != expected:
            raise ValueError('frozen605 dependency changed: ' + name)
    sys.path.insert(0, str(Path(__file__).parent))
    body = importlib.import_module('transform_officer_body')
    inputs = {n: (sources / n).read_bytes() for n in body.INPUTS}
    tpl, packages, report = body.transform(inputs)
    plan = json.loads(raw)
    if sha(tpl) != plan['transformed_TPL_sha256']:
        raise ValueError('computed TPL differs from frozen plan')
    expected = {p['new_key']: p['package_sha256'] for p in plan['pictures']}
    if {k: sha(v) for k, v in packages.items()} != expected:
        raise ValueError('computed textures differ from frozen plan')
    return tpl, packages, report


def emit(plan_path, sources, out):
    output_guard(out, sources)
    check_capacity(0, c_free())
    tpl, packages, report = frozen_transform(plan_path, sources)
    files = {'r100-body-25.tpl': tpl}
    files.update({'tex/' + k + '.re4tex': v for k, v in packages.items()})
    rows = [dict(path=p, bytes=len(b), sha256=sha(b)) for p, b in sorted(files.items())]
    manifest = dict(schema='issue52-officer-body-private-assets-1', frozen_source_commit=FROZEN_COMMIT,
        frozen_plan_sha256=PLAN_SHA, frozen_dependencies=PINS, source_inputs=report['inputs'],
        emitter_sha256=sha(Path(__file__).read_bytes()), files=rows,
        TPL_archive_slot=0x25, TPL_patch_scope='Only dimensions/native reference identities;256B extent,32changedbytes.',
        geometry_UV_motion_material_head_bytes_changed=0,
        body_source_payload_bytes=212992, previous_payload_bytes=73728, source_residency_delta_bytes=139264,
        limits=['Private TPL fragment and3texture assets only; no room/archive/image/stage/guest.',
                'No runtime/converter/recipe enablement. Main retains integration decision.',
                'No target appearance/capacity/performance/release/physicalDreamcast acceptance.'])
    metadata = (json.dumps(manifest, indent=2) + '\n').encode()
    planned = sum(len(v) for v in files.values()) + len(metadata)
    free_before = c_free()
    check_capacity(planned, free_before)
    out.mkdir(parents=True, exist_ok=False)
    for name, blob in list(files.items()) + [('emission.json', metadata)]:
        check_capacity(len(blob), c_free())
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f:
            f.write(blob)
        if path.read_bytes() != blob:
            raise ValueError('private output readback differs: ' + name)
    return dict(out=str(out), source_commit=FROZEN_COMMIT, asset_bytes=sum(len(v) for v in files.values()),
                bundle_bytes=planned, floor_bytes=FLOOR, disk_free_before=free_before,
                disk_free_after=c_free(), files=rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ['sources', 'plan', 'out']:
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--enable-body-assets', action='store_true')
    args = ap.parse_args()
    if not args.enable_body_assets:
        raise ValueError('asset emission disabled; explicit --enable-body-assets required')
    print(json.dumps(emit(args.plan, args.sources, args.out), indent=2))


if __name__ == '__main__':
    main()