#!/usr/bin/env python3
"""Qualify and emit the pinned private r109 metadata-only experiment."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

from metadata import build, crc, headers, meshlets, require
from host_runtime import compile_probe

BASE = '64a28a7bdc44312924b14414501b7d4ff1d2d032'
PINNED = {
    'mesh': ('/root/re4payload/t164-20261018/tree/dc/native/r109/ps2-world.re4mesh', 'be2460555f63cd49d8c0be0a9cbbe36af91094dc119db106d587b9c50db85704'),
    'source_policy': ('/root/re4payload/t164-20261018/tree/dc/native/r109/ps2-world.r4pw', '62810bd1d47ff8ccee794565c1d0dfc1cd76eddd9c5b62c5ef9eb2f934da36a0'),
    'scoped_policy': ('/root/re4data/private/mip22b-20261022/dc/native/r109/ps2-world.r4pw', '6c6c268cb4dc5a9903fe496a723600c497e016912ef56b14d017f80c10599a73'),
    'room_data': ('/root/re4data/private/rc19s-20261019/r109/room.r4rc', 'a12796befffbeb638dfcc6e04148a8d1b245a63c5f666f5c285d9808c64ffb5a'),
    'conversion_report': ('/mnt/c/Game Dev/Emulators/re4-assets-private/t11-20261014/blackps2/r109/ps2-world.json', '24658f765a175cb20363510e7321da1e7b8092dcb33ed57f3b7d7b13ead18736'),
    'original_smd': ('/mnt/c/Game Dev/Emulators/re4-assets-private/ps2rooms-20260930/inputs/r109/r109_004.SMD', '4ab5982faace27eda46d771725c39bea228559821f1e20d172e19a9706331e87'),
    'original_smx': ('/mnt/c/Game Dev/Emulators/re4-assets-private/ps2rooms-20260930/inputs/r109/r109_005.SMX', '8434bc1124bc34dd716539d6da493b3d49ba42c7763242acb61096ca98680caa'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(command, **kw):
    return subprocess.check_output(list(map(str, command)), **kw).decode().strip()


def verify_records(mesh, source, result):
    h, _ = headers(mesh, source)
    ng = struct.unpack_from('<I', result, 12)[0]
    checked = 0
    for li, _, positions, strips in meshlets(mesh, h):
        boundaries, end = {}, 0
        for raw in strips:
            end += len(raw)
            boundaries[end] = raw
        prev, consumed = 0, []
        for group in range(ng):
            r = struct.unpack_from('<6HHBB', result, 32+16*(li*ng+group))
            end = r[6]
            if end == prev:
                require(r[:6] == (0,)*6 and r[7:] == (1, 0), 'noncanonical empty group')
                continue
            require(end > prev and end in boundaries, 'group end not original strip boundary')
            part, cursor = [], 0
            for raw in strips:
                if prev <= cursor < end:
                    part.append(raw)
                cursor += len(raw)
            require(sum(map(len, part)) == end-prev, 'strip overlap or short group')
            ks = [k for raw in part for k in raw[1:]]
            require(r[7:] == (min(ks), max(ks)), 'corner range mismatch')
            for k in ks:
                require(all(r[a] <= positions[k][a] <= r[a+3] for a in range(3)), 'nonconservative bounds')
            consumed.extend(part)
            prev = end
            checked += 1
        require(consumed == strips, 'original ordered strip stream not covered exactly once')
    return checked


def selector_tests(exe, scratch):
    # Four spatial groups with overlapping original corner intervals. Interior
    # rejection leaves holes inside one transformed enclosing range.
    records = [(0, 0, 0, 2, 2, 2, 4, 0, 2), (10, 0, 0, 12, 2, 2, 8, 2, 4),
               (20, 0, 0, 22, 2, 2, 12, 4, 6), (30, 0, 0, 32, 2, 2, 16, 6, 8)]
    path = scratch/'selection.bin'

    cases = []

    def select(rs, planes, mask=1):
        path.write_bytes(b''.join(struct.pack('<6HHBB', *r) for r in rs))
        coef = [0.0]*40
        for i, plane in enumerate(planes):
            coef[8*i:8*i+len(plane)] = plane
        values = run([exe, 'select', path], input=(' '.join(map(str, [len(rs), mask, *coef]))).encode())
        observed = list(map(int, values.split()))
        nr, lo, hi, cut = observed[:4]
        cases.append(dict(selected_groups=nr, lo=lo, hi=hi, culled_groups=cut,
                          transformed_count=hi-lo+1 if nr else 0,
                          strip_ranges=[observed[i:i+2] for i in range(4,len(observed),2)]))
        return observed

    require(select(records, [], 0)[:4] == [4, 0, 8, 0], 'all kept span')
    require(select(records, [(1, 0, 0, 0, 0, 0, -15)])[:4] == [2, 4, 8, 2], 'leading cut span')
    require(select(records, [(0, 0, 0, -1, 0, 0, 15)])[:4] == [2, 0, 4, 2], 'trailing cut span')
    require(select(records, [(0, 0, 0, 0, 0, 0, -2)])[:4] == [0, 255, 0, 4], 'all cut')
    # Spatially outside interior ranges remain within transformed lo..hi.
    reordered_boxes = [records[0], (*records[3][:6], *records[1][6:]),
                       (*records[2][:6], *records[2][6:]), (*records[0][:6], *records[3][6:])]
    require(select(reordered_boxes, [(0, 0, 0, -1, 0, 0, 5)])[:4] == [2, 0, 8, 2], 'interior hole enclosing span')
    empty = (0, 0, 0, 0, 0, 0, 4, 1, 0)
    require(select([records[0], empty], [], 0)[:4] == [1, 0, 2, 0], 'empty padding')
    near = (0, 0, 0, 2, 2, 20, 4, 0, 2)
    behind = (0, 0, 0, 2, 2, 8, 8, 2, 4)
    planes = [(0,)*8]*4 + [(0, 0, 1, 0, 0, 0, -10)]
    require(select([near, behind], planes, 16)[:4] == [1, 0, 2, 1], 'near-plane straddler retained')
    boundary = (0, 0, 0, 2, 2, 9, 4, 0, 2)
    require(select([boundary], planes, 16)[:4] == [1, 0, 2, 0], 'minus-one conservative slack')
    require([c['transformed_count'] for c in cases] == [9, 5, 5, 0, 9, 3, 3, 3], 'transformed enclosing counts')
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runtime-tree', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--mirror', required=True)
    args = ap.parse_args()
    output, mirror = Path(args.output), Path(args.mirror)
    require(not output.exists() and not mirror.exists(), 'use fresh output and mirror directories')
    inputs, data = {}, {}
    for key, (path, digest) in PINNED.items():
        data[key] = Path(path).read_bytes()
        require(sha(data[key]) == digest, 'pinned input mismatch: '+key)
        inputs[key] = dict(path=path, sha256=digest, bytes=len(data[key]))
    mesh, source, scoped = data['mesh'], data['source_policy'], data['scoped_policy']
    conversion = json.loads(data['conversion_report'])
    require(conversion['room'] == 'r109' and conversion['re4mesh_sha256'] == sha(mesh)
            and conversion['r4pw_sha256'] == sha(source), 'conversion report lineage mismatch')
    h, p = headers(mesh, source)
    headers(mesh, scoped)
    require(source[32+16*p[3]:] == scoped[32+16*p[3]:], 'placements changed')
    for i in range(p[3]):
        require(source[40+16*i:48+16*i] == scoped[40+16*i:48+16*i], 'non-key part policy changed')
    result, stats = build(mesh, source)
    require(verify_records(mesh, source, result) == 4396, 'group inventory drift')
    tree = Path(__file__).resolve().parents[5]
    converter = tree/'port/dreamcast/tools/ps2_strip_groups.py'
    with tempfile.TemporaryDirectory(prefix='visibility23-') as td:
        scratch = Path(td)
        exe, runtime = compile_probe(args.runtime_tree, scratch)
        group = scratch/'new.r4sg'
        group.write_bytes(result)
        acceptance = run([exe, PINNED['mesh'][0], PINNED['scoped_policy'][0], group])
        require(acceptance == '5d07de5b ok', 'real runtime did not accept exact source-policy binding: '+acceptance)
        require(run([exe, PINNED['mesh'][0], PINNED['source_policy'][0], group]) == acceptance, 'original policy acceptance')
        rejections = 0
        for offset in range(0, 32, 4):
            bad = bytearray(result);bad[offset] ^= 1
            group.write_bytes(bad)
            require(run([exe, PINNED['mesh'][0], PINNED['scoped_policy'][0], group]).endswith('header'), 'header mismatch accepted')
            rejections += 1
        for bad in (result[:16], result[:-16], result+b'\0'*16, result[:50]+b'X'+result[51:]):
            group.write_bytes(bad)
            require(not run([exe, PINNED['mesh'][0], PINNED['scoped_policy'][0], group]).endswith('ok'), 'size/record mismatch accepted')
            rejections += 1
        group.write_bytes(result)
        bad_scoped = bytearray(scoped);bad_scoped[32] ^= 1
        struct.pack_into('<I', bad_scoped, 20, crc(bad_scoped[32:]))
        bad_policy = scratch/'mutated.r4pw';bad_policy.write_bytes(bad_scoped)
        require(run([exe, PINNED['mesh'][0], bad_policy, group]).endswith('header'), 'uncertified policy accepted')
        rejections += 1
        stale_original = bytearray(source);stale_original[32] ^= 1
        bad_policy.write_bytes(stale_original)
        require(run([exe, PINNED['mesh'][0], bad_policy, group]).startswith('sidecar-reject'), 'stale source-policy CRC accepted')
        rejections += 1
        # Recompute CRC so record checks, rather than checksum, reject each case.
        for offset, value in ((44, 3), (45, 3), (40, 0)):
            bad = bytearray(source)
            if offset == 40:
                struct.pack_into('<H', bad, offset, value)
            else:
                bad[offset] = value
            struct.pack_into('<I', bad, 20, crc(bad[32:]))
            bad_policy.write_bytes(bad)
            require(run([exe, PINNED['mesh'][0], bad_policy, group]).startswith('sidecar-reject'), 'invalid source-policy record accepted')
            rejections += 1
        bad_mesh = bytearray(mesh);bad_mesh[12] ^= 1
        bad_mesh_path = scratch/'mutated.re4mesh';bad_mesh_path.write_bytes(bad_mesh)
        require(not run([exe, bad_mesh_path, PINNED['scoped_policy'][0], group]).endswith('ok'), 'wrong mesh accepted')
        rejections += 1
        selection_cases = selector_tests(exe, scratch)
        # Execute the pre-change converter and new default path on the exact
        # real baseline, comparing mesh, metadata, report and stdout bytes.
        legacy = scratch/'legacy.py'
        legacy.write_bytes(subprocess.check_output(['git', '-C', str(tree), 'show', BASE+':port/dreamcast/tools/ps2_strip_groups.py']))
        stdout = []
        for name, tool in (('legacy', legacy), ('current', converter)):
            stdout.append(subprocess.check_output(['python3', str(tool), PINNED['mesh'][0], PINNED['source_policy'][0],
                         str(scratch/(name+'.mesh')), str(scratch/(name+'.sg')), '--report', str(scratch/(name+'.json'))]))
        require(stdout[0] == stdout[1], 'default stdout changed')
        for suffix in ('.mesh', '.sg', '.json'):
            require((scratch/('legacy'+suffix)).read_bytes() == (scratch/('current'+suffix)).read_bytes(), 'default output changed: '+suffix)
        cli = scratch/'cli.r4sg'
        run(['python3', converter, PINNED['mesh'][0], PINNED['source_policy'][0], '-', cli, '--preserve-order'])
        require(cli.read_bytes() == result, 'CLI metadata differs')
    # Re-read every source asset after conversion; no rewritten output is staged.
    for key, item in inputs.items():
        require(sha(Path(item['path']).read_bytes()) == item['sha256'], 'input changed during qualification: '+key)
    receipt = dict(source_base=BASE, source_head=run(['git','-C',tree,'rev-parse','HEAD']), inputs=inputs,
                   converter_sources={str(path.relative_to(tree)): sha(path.read_bytes()) for path in
                       [converter, *sorted(Path(__file__).resolve().parent.glob('*.py'))]},
                   stats=stats, host_runtime_sources=runtime, real_loader_acceptance=acceptance,
                   mismatch_rejections=rejections, real_selector_cases=selection_cases,
                   default_converter='mesh, R4SG, JSON report and stdout byte-identical on pinned r109',
                   ordered_coverage='all 1189 meshlets, every original strip exactly once and in order',
                   source_assets_rehashed_unchanged=True,
                   evidence_scope='Host only. No guest, program build, memory fit, pixels, FPS or console acceptance.')
    (output/'r109').mkdir(parents=True)
    (output/'r109/ps2-world.r4sg').write_bytes(result)
    (output/'QUALIFICATION.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    (output/'README.txt').write_text('Private r109 metadata-only G4 experiment. Stage only r109/ps2-world.r4sg beside the exact baseline assets in QUALIFICATION.json.\nRequires the authenticated WORLD_RECT21 policy mapping present in the recorded runtime tree; raw origin/t15/int at this base lacks it and rejects scoped-policy metadata.\nKeep Full view, CPU backface OFF, cones/piece state/dedup OFF. Adds 76128 bytes of optional sidecar storage (heap allocation rounds to the same size). Runtime/camera/pixels/performance/memory and console gates remain open.\n')
    members = sorted(p for p in output.rglob('*') if p.is_file())
    sums = ''.join(sha(p.read_bytes())+'  '+p.relative_to(output).as_posix()+'\n' for p in members)
    (output/'SHA256SUMS').write_text(sums)
    shutil.copytree(output, mirror)
    for file in output.rglob('*'):
        if file.is_file():
            require(file.read_bytes() == (mirror/file.relative_to(output)).read_bytes(), 'mirror mismatch')
    print(json.dumps(dict(output=str(output), mirror=str(mirror), stats=stats, mismatch_rejections=rejections,
                          real_selector_cases=len(selection_cases)), sort_keys=True))


if __name__ == '__main__':
    main()
