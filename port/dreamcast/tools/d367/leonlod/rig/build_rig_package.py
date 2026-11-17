#!/usr/bin/env python3
"""LEON_LOD rig package (lane leonlod, 2026-11-16): the four Leon rungs reduced from the PS2 RIG arm (LEON_PS2_RIG=1) and
packed into dc/native/pl00/leon_lod.re4lp.

  build_rig_package.py <rig arm dir> <work dir>

<rig arm dir>: the private rig arm the recipe's PS2_LEON_DIR names (mesh.json from build_arm_a.py --rig, ps2leon_runtime.h,
ps2leon_hair_runs.h, leon_pl08_runtime.h, report.json). <work dir> receives arms/ (reduced mesh.json + report), pk/<rung>/
(pack_arm.py output) and leon_lod.re4lp. Host Python (numpy, Pillow), the private character-prototype tools as pack_arm.py
needs them (PS2LEON_TREE, PS2LEON_WORK, RE4_PRIVATE as leon_sources.py).

Rungs (package order; the reduction is lod_mesh.py's half-edge collapse: every surviving vertex is an original PS2 vertex with
its own weights, normal and UV, so no new bone combination appears; locked seams / borders / role junctions stay watertight):
  0 A     the full PS2 rig Leon (the arm itself)
  1 lg65  legs 924 -> ~600 triangles, the head attachment's never-seen triangles (vis-a.json) removed. Torso, jacket, arms,
          face, hair, hands, knife untouched.
  2 bd70  lg65 plus the body's arms / sleeves, the jacket and the knife at ~63 % (error cap 20 mm, large flat parts first).
          Face, hair, head attachment (apart from the never-seen part) and hands untouched.
  3 u70   every role at ~65 %, face (562 -> 351) and hair (682 -> 426) included. The 2026-10-15 pick; not for close-ups
          (the radio-call portrait draws the loaded rung's hair).
vis-a.json: per-triangle "seen" counts of the PS2 Leon from the 2026-10-15 look study (same triangle order as the rig arm).
"""
import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEONLOD = HERE.parent
PS2LEON = LEONLOD.parent / 'ps2leon'
VIS = HERE / 'vis-a.json'

SPECS = {
    'lg65': {"targets": {"0": {"legs": 600, "head": 40, "arms": 0, "torso": 0}, "1": {"torso": 0, "arms": 0}, "4": {"hidden": 30}},
             "max_error_mm": {"0": {"arms": 1.0, "torso": 1.0}, "1": {"torso": 1.0, "arms": 1.0}},
             "keep_roles": [2, 3, 5, 6, 7], "allow_border": True, "w_bone": 1.0,
             "lock_components_below": {"0": 50, "1": 40}, "hard_cap_mm": 20.0},
    'bd70': {"targets": {"0": {"*": 1124}, "1": {"*": 566}, "2": {"*": 64}, "4": {"hidden": 20}},
             "max_error_mm": {"7": {"head": 3.0}},
             "keep_roles": [3, 5, 6, 7], "allow_border": True, "w_bone": 1.0,
             "lock_components_below": {"0": 13, "1": 13}, "hard_cap_mm": 20},
    'u70': {"targets": {"0": {"*": 1124}, "1": {"*": 566}, "2": {"*": 64}, "3": {"*": 351}, "4": {"*": 291}, "7": {"*": 426}},
            "keep_roles": [5, 6], "allow_border": True, "hard_cap_mm": 20, "w_bone": 1.0,
            "lock_components_below": {"0": 13, "1": 13}},
}


def run(*a):
    print('+', ' '.join(str(x) for x in a), flush=True)
    r = subprocess.run([sys.executable, *map(str, a)], text=True, capture_output=True)
    sys.stdout.write(r.stdout[-1500:])
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(r.returncode)


def main():
    arm, work = Path(sys.argv[1]), Path(sys.argv[2])
    (work / 'arms').mkdir(parents=True, exist_ok=True)
    for name, spec in SPECS.items():
        spec = dict(spec, vis=str(VIS).replace('\\', '/'))
        sp = work / ('spec-%s.json' % name)
        sp.write_text(json.dumps(spec, indent=1))
        run(LEONLOD / 'lod_mesh.py', arm / 'mesh.json', work / 'arms' / (name + '.json'), '--spec', sp,
            '--report', work / 'arms' / (name + '-report.json'))
        run(PS2LEON / 'pack_arm.py', work / 'arms' / (name + '.json'), work / 'pk' / name, '--pl08', arm / 'leon_pl08_runtime.h')
    run(LEONLOD / 'lod_pack.py', 'pack', work / 'leon_lod.re4lp', 'A=%s' % arm,
        *['%s=%s' % (n, work / 'pk' / n) for n in SPECS])
    run(LEONLOD / 'lod_pack.py', 'show', work / 'leon_lod.re4lp')


if __name__ == '__main__':
    main()
