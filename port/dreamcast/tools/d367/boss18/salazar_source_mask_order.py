#!/usr/bin/env python3
"""Restore source-GX order for two pinned Salazar mask candidates, offline only.

The existing mask membership, UV remap and encoded texture are retained. This
proves an oriented corner sequence, not source alpha classification, original GS
blending, native material admission, animated appearance or recovered gameplay.
"""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import struct
import sys


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ordered_blob(data, triangles):
    from cb_blob import Blob, canon
    old = Blob(data)
    if old.rs != 3 or old.levels or old.flags & 0x83:
        raise ValueError('unsupported original mask record layout')
    groups, records, lookup, indices = [], [], {}, []
    count = 0

    def flush():
        nonlocal records, lookup, indices, count
        if records:
            groups.append((records, bytes(indices), count))
        records, lookup, indices, count = [], {}, [], 0

    for triangle in triangles:
        if len(triangle) != 3 or len(set(triangle)) != 3:
            raise ValueError('original nondegenerate triangle required')
        if len(set(records) | set(triangle)) > 64 or len(indices) + 3 > 1024:
            flush()
        for corner, record in enumerate(triangle):
            if record not in lookup:
                lookup[record] = len(records)
                records.append(record)
            indices.append(lookup[record] | (0x80 if corner == 2 else 0))
        count += 1
    flush()
    if not groups:
        raise ValueError('empty alpha source sequence')
    rec_at = (32 + 8 * len(groups) + 3) & ~3
    record_bytes = b''.join(struct.pack('<3H', *r) for rs, _, _ in groups for r in rs)
    idx_at = (rec_at + len(record_bytes) + 3) & ~3
    if max(rec_at, idx_at) // 4 > 65535 or len(groups) > 65535:
        raise ValueError('original FE/v3 offset range exceeded')
    output = bytearray(idx_at)
    output[:32] = data[:32]
    struct.pack_into('<4B6H', output, 0, 0xfe, 3, old.flags, 0, len(groups),
                     old.color_index, rec_at // 4, idx_at // 4, 0, 0)
    nr = ni = 0
    for i, (rs, ix, nt) in enumerate(groups):
        if not 0 < len(rs) <= 64 or not 0 < len(ix) <= 1024 or max(nr, ni) > 65535:
            raise ValueError('original meshlet/index limit exceeded')
        struct.pack_into('<IHH', output, 32 + 8 * i,
                         len(rs) | len(ix) << 8 | nt << 20, nr, ni)
        nr += len(rs)
        ni += len(ix)
    output[rec_at:rec_at + len(record_bytes)] = record_bytes
    output.extend(b''.join(ix for _, ix, _ in groups))
    output.extend(bytes((-len(output)) % 32))
    checked = Blob(bytes(output))
    if [canon(t) for t in checked.triangles()] != [canon(t) for t in triangles]:
        raise ValueError('source oriented corner sequence changed')
    if Counter(map(canon, checked.triangles())) != Counter(map(canon, old.triangles())):
        raise ValueError('original corner records or duplicate multiplicity changed')
    return bytes(output), checked.stats()


def prepare(source_root, output, contract_path):
    root, dest = Path(source_root).resolve(), Path(output).resolve()
    contract = json.loads(Path(contract_path).read_text(encoding='utf-8'))
    if contract.get('schema') != 'boss18-salazar-mask-order-1':
        raise ValueError('unsupported source contract')
    if dest.exists() or dest == root or dest.is_relative_to(root):
        raise ValueError('new output outside the immutable source set required')
    for rel, digest in contract['inputs'].items():
        path = (root / rel).resolve()
        if not path.is_relative_to(root) or sha(path.read_bytes()) != digest:
            raise ValueError('original source input pin changed: ' + rel)
    here = Path(__file__).resolve()
    sys.path[:0] = [str(here.parents[2]), str(here.parents[1]),
                   str(here.parents[1] / 'charbake')]
    import numpy as np
    from PIL import Image
    import model_registry as mr
    import ps2_gctex_bake as bk
    from cb_blob import Blob, canon
    samples = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [.5, .5, 0],
                        [0, .5, .5], [.5, 0, .5], [1/3, 1/3, 1/3]])
    pending = []
    names = [row['name'] for row in contract['models']]
    if not names or len(set(names)) != len(names):
        raise ValueError('distinct nonempty model names required')
    for row in contract['models']:
        model = (root / row['model']).resolve()
        mask = (root / row['mask']).resolve()
        result = (dest / row['name']).resolve()
        if (not model.is_relative_to(root) or not mask.is_relative_to(root) or
                result == dest or not result.is_relative_to(dest)):
            raise ValueError('source or output path leaves its owned root')
        header = model / 'runtime/castmodel_runtime.h'
        chunks, bones = mr.parse_header(str(header))
        chunk = next(c for c in chunks if c['source_info'] == 0)
        if bones != row['bones']:
            raise ValueError('original source owner changed')
        for key, ext in [('positions', 'pos'), ('normals', 'nrm'), ('uv', 'uv')]:
            if (model / ('native/info0.' + ext)).read_bytes() != chunk[key]:
                raise ValueError('native source arrays are not byte-identical')
        raw = (model / 'native/info0.gx').read_bytes()
        n = struct.unpack_from('>H', raw, 1)[0]
        if raw[0] != 0x90 or n % 3 or any(raw[3 + n*6:]):
            raise ValueError('pinned original source triangle list required')
        corners = [struct.unpack_from('>3H', raw, 3 + i*6) for i in range(n)]
        source = [tuple(corners[i:i+3]) for i in range(0, n, 3)]
        full = [tuple(t) for t in Blob(chunk['stream']).triangles() if t is not None]
        if Counter(map(canon, source)) != Counter(map(canon, full)):
            raise ValueError('full original oriented corner multiset changed')
        uv = np.array(list(struct.iter_unpack('<2H', chunk['uv'])), float) / 32768
        atlas = np.array(Image.open(model / 'atlas-rgba.png').convert('RGBA'), float)
        # Reconstruct the OLD pinned membership and its first-seen UV bijection.
        # Reclassifying cyclically rotated source faces is deliberately avoided:
        # that legacy float threshold is not a source-material correctness proof.
        alpha = [t for t in full if bk.sample(atlas, samples @ uv[[c[2] for c in t]])[:, 3].min() < 255]
        nmap = {}
        for triangle in alpha:
            for _, _, u in triangle:
                if u not in nmap:
                    nmap[u] = len(nmap)
        remap = lambda t: tuple((p, n, nmap[u]) for p, n, u in t)
        old_raw = (mask / 'hair.blob').read_bytes()
        old = [canon(t) for t in Blob(old_raw).triangles() if t is not None]
        if len(alpha) != row['alpha_triangles'] or len(nmap)*4 != (mask / 'hair.uv').stat().st_size:
            raise ValueError('original alpha membership or UV bijection changed')
        if Counter(canon(remap(t)) for t in alpha) != Counter(old):
            raise ValueError('full position/normal/mapped-UV correspondence changed')
        remaining = Counter(map(canon, alpha))
        selected = []
        for triangle in source:
            key = canon(triangle)
            if remaining[key]:
                selected.append(canon(remap(triangle)))
                remaining[key] -= 1
        if +remaining:
            raise ValueError('original alpha source projection incomplete')
        new_raw, stats = ordered_blob(old_raw, selected)
        cc = dict(chunk, stream=new_raw, stream_bytes=len(new_raw), triangles=len(selected),
                  uv=(mask / 'hair.uv').read_bytes())
        if mr.preflight_chunk(cc, bones):
            raise ValueError('unchanged preflight mirror refuses the ordered chunk')
        proof = dict(source_header_sha256=sha(header.read_bytes()), alpha_triangles=len(selected),
                     UV_bijection_entries=len(nmap), original_oriented_corner_order_exact=True,
                     original_full_corner_multiset_exact=True, input_bytes=len(old_raw),
                     output_bytes=len(new_raw), output_sha256=sha(new_raw), stats=stats,
                     scope='Index order only. Existing alpha membership, UV resampling and textures retained; '
                           'not source alpha/GS blending, native material, animated look or fight acceptance.')
        pending.append((row, mask, new_raw, proof))
    dest.mkdir(parents=True)
    proofs = []
    for row, mask, new_raw, proof in pending:
        d = dest / row['name']
        shutil.copytree(mask, d)
        (d / 'hair.blob').write_bytes(new_raw)
        report = json.loads((d / 'mask-runs.json').read_text(encoding='utf-8'))
        report['runs']['hair'].update(proof['stats'], sha256=sha(new_raw),
                                      seed='retained-source-GX-alpha-subsequence', w_dist=0.0)
        report['source_order_proof'] = proof
        (d / 'mask-runs.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        (d / 'source-order-proof.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
        proofs.append(proof)
    return proofs


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source_root')
    ap.add_argument('output')
    ap.add_argument('--contract', default=str(Path(__file__).with_name('salazar-source-mask-order.json')))
    args = ap.parse_args()
    print(json.dumps(prepare(args.source_root, args.output, args.contract), indent=2))
