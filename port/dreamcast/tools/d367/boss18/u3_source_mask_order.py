#!/usr/bin/env python3
"""Restore original U3 PS2 alpha-triangle order in one pinned offline mask run.

Only index order and necessary padding change. The original full model, runtime
owner, skin/normal/UV records, encoded texture and source active blend stay intact.
This is not an implementation of the runtime texBlendTbl effect or a look gate.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import struct
import sys


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canon(triangle):
    return min(triangle, triangle[1:] + triangle[:1], triangle[2:] + triangle[:2])


def restore(data_root, contract_path):
    root = Path(data_root).resolve()
    contract = json.loads(Path(contract_path).read_text(encoding='utf-8'))
    if contract.get('schema') != 'boss18-u3-source-mask-order-1':
        raise ValueError('unsupported source mask contract')
    for rel, digest in contract['inputs'].items():
        path = (root / rel).resolve()
        if not path.is_relative_to(root) or sha(path.read_bytes()) != digest:
            raise ValueError('original source input pin changed: ' + rel)
    sys.path[:0] = [str(Path(__file__).resolve().parents[2]),
                   str(Path(__file__).resolve().parents[1]),
                   str(Path(__file__).resolve().parents[1] / 'charbake')]
    os.environ['PS2CAST_INPUTS'] = str(root / 'inputs')
    import ps2_cast as pc
    import model_registry as mr
    from cb_blob import Blob
    ps2, gc, _ = pc.inputs('em32', root / 'unused', pc.PS2_ISO, pc.GC_ISO)
    source = pc.pb.parse_bin(pc.ps2_entry(ps2, 7, 'BIN'))
    original = []
    for material, corners in pc.pb.triangles(source):
        if source.materials[material]['diffuse'] == 0:
            original.append(canon(tuple(tuple(int(round(x * 4)) for x in c['p']) for c in corners)))
    if len(original) != 6 or len(set(original)) != 6:
        raise ValueError('original six unique alpha triangles changed')
    header = root / contract['header']
    chunks, bones = mr.parse_header(str(header))
    if bones != 97:
        raise ValueError('original97part runtime owner changed')
    chunk = next(c for c in chunks if c['source_info'] == 2)
    positions = [struct.unpack_from('<3h', chunk['positions'], 8 * k)
                 for k in range(chunk['position_count'])]
    src = root / contract['mask']
    report = json.loads((src / 'mask-runs.json').read_text(encoding='utf-8'))
    if report['header_sha256'] != sha(header.read_bytes()) or report['triangles'] != dict(chunk=1168, opaque=1162, hair=6):
        raise ValueError('original full model/mask binding changed')
    if report.get('atlas_alpha_threshold') != 255 or not report['source'].startswith('atlas-rgba '):
        raise ValueError('original PS2 diffuse alpha candidate required')
    raw = (src / 'hair.blob').read_bytes()
    blob = Blob(raw)
    if blob.meshlets != 1 or blob.rs != 3 or blob.levels or blob.flags != 8:
        raise ValueError('unexpected pinned alpha run layout')
    triangles = [t for t in blob.triangles() if t is not None]
    lookup = {}
    for triangle in triangles:
        key = canon(tuple(positions[c[0]] for c in triangle))
        if key in lookup:
            raise ValueError('ambiguous alpha triangle correspondence')
        lookup[key] = triangle
    if set(lookup) != set(original):
        raise ValueError('original alpha geometry/winding differs')
    records = blob.table[0]['records']
    if len(records) != 12 or len(set(records)) != len(records):
        raise ValueError('original alpha corner records changed')
    rec_index = {rec: k for k, rec in enumerate(records)}
    # Six3corner strips keep the original triangle order without heuristic
    # restripification. All original position/normal/new-mask-UV records remain.
    indices = bytes(i | (0x80 if c == 2 else 0)
                    for key in original
                    for c, i in enumerate(rec_index[r] for r in lookup[key]))
    rec_at = blob.rec4 * 4
    record_bytes = b''.join(struct.pack('<3H', *r) for r in records)
    index_at = (rec_at + len(record_bytes) + 3) & ~3
    output = bytearray(index_at)
    output[:32] = raw[:32]
    struct.pack_into('<4B6H', output, 0, 0xfe, 3, blob.flags, 0, 1, blob.color_index,
                     rec_at // 4, index_at // 4, 0, 0)
    struct.pack_into('<IHH', output, 32, len(records) | (18 << 8) | (6 << 20), 0, 0)
    output[rec_at:rec_at + len(record_bytes)] = record_bytes
    output.extend(indices)
    output.extend(bytes((-len(output)) % 32))
    checked = Blob(bytes(output))
    actual = [canon(tuple(positions[c[0]] for c in t)) for t in checked.triangles()]
    if actual != original or checked.table[0]['records'] != records:
        raise ValueError('ordered alpha roundtrip changed source order or records')
    dest = (root / contract['output']).resolve()
    if not dest.is_relative_to(root) or dest.exists():
        raise ValueError('new private output directory required')
    shutil.copytree(src, dest)
    (dest / 'hair.blob').write_bytes(output)
    report['runs']['hair'].update(checked.stats(), sha256=sha(output), seed='original-PS2-six-triangle-order', w_dist=0.0)
    proof = dict(status='PASS', original_PS2_archive_sha256=contract['inputs']['inputs/em32.dat'],
                 source_BIN7_sha256=sha(pc.ps2_entry(ps2, 7, 'BIN')),
                 input_alpha_blob_sha256=sha(raw), output_alpha_blob_sha256=sha(output),
                 original_triangle_order_exact=True, original_full_runtime_header_unchanged=True,
                 original97part_skeleton_skin_and_all_corner_records_unchanged=True,
                 source_PS2_alpha_texture_and_UV_bytes_unchanged=True,
                 input_bytes=len(raw), output_bytes=len(output),
                 source_order=original, contract_sha256=sha(Path(contract_path).read_bytes()),
                 limitation='Source active texBlendTbl/ratio255/type2 still unsupported. No actual draw, animated look, fight, LOD or performance gate.')
    report['original_PS2_alpha_order_proof'] = proof
    (dest / 'mask-runs.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (dest / 'source-order-proof.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(proof, indent=2))
    return proof


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('data_root')
    ap.add_argument('--contract', default=str(Path(__file__).with_name('u3-source-mask-order.json')))
    args = ap.parse_args()
    restore(args.data_root, args.contract)