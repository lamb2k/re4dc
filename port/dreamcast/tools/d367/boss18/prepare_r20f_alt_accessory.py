#!/usr/bin/env python3
"""Append the original em14 BIN217/TPL219 role without rebuilding an accepted pool.

Private inputs are required. This reuses an existing source-derived color/mask
pair after proving the donor's raw source identity and exact masked UV mapping.
No geometry simplification, new texture bake, converter or runtime change.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
ROOT = TOOLS.parents[2]
sys.path[:0] = [str(TOOLS), str(TOOLS / 'd367'), str(TOOLS / 'd367/charbake'), str(ROOT / 'tools')]
import model_registry as mr
import ps2_bin
from motion import archive
from cb_blob import Blob

NAME = 'zealot-em14-08p'
REVISION = 'ps2-r20f-alt219-v1'
BASE_PACKAGE = 'd034c033b2e7796c5f260fdc51fdb31b77ec3e6dbccff4728b7f1fa8a218b3bc'
BASE_HEADER = 'a92cec63454d2bb85d9100b3abb37204fb0d90133915d316e784456b32a10f6a'
DONOR_HEADER = '3ee4075b82fbedbbc3690588e411f0e8abb0791216f8b07e21f1d9ce77076156'
PAIR_SHA = 'edc35f81c1e2958137856a3699ad0e0fa02b380c19bff75dc297d30ab92b0ac0'
RAW_SHA = {
    ('ps2', 0x217): '9f64d5e15e477d26f7918057c720647739eea90ee206553d77e6fb31d5f88be3',
    ('gc', 0x217): '51b10f043c65d39614eb21e83cfef5180663d9755f92fd98a08b83de98a76521',
    ('ps2', 0x218): 'c83fe37757c25654af3613204636218a2d6446593ddeeb2fec0c603c26ed8f9a',
    ('gc', 0x218): '6c3850c9ced2724dae2634f3c367c9289ba5caeb102ecad46eb9467e55aae0b3',
    ('ps2', 0x219): 'd306bfe30b7882c06cc471e6670db223b463708b3efbcc71277d6682d0486b54',
    ('gc', 0x219): 'c58e768d2ca1c235e97fd01d94bd791286f1a7a2c3ed8aa23961c2b9e1b88347',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def alias_chunk(text, source_info, new_info):
    """Keep every array and existing record literal; append one typed alias."""
    matches = list(mr.CHUNKS.finditer(text))
    require(len(matches) == 1, 'one chunk table required')
    table = matches[0]
    rows = list(mr.CROW.finditer(table.group(1)))
    require(rows, 'empty chunk table')
    ids = [int(row.group(1)) for row in rows]
    require(len(ids) == len(set(ids)), 'duplicate source info')
    require(new_info == max(ids) + 1 and new_info not in ids, 'append next source info only')
    selected = [row for row in rows if int(row.group(1)) == source_info]
    require(len(selected) == 1, 'source alias record missing')
    row = selected[0]
    require(len(set(row.groups()[6:])) == 1, 'mixed array prefixes')
    literal = re.sub(r'^\{\d+,', '{' + str(new_info) + ',', row.group(0))
    return text[:table.end(1)] + '\n' + literal + ',' + text[table.end(1):]


def masked_triangles(chunk, mask_dir):
    uv = (mask_dir / 'hair.uv').read_bytes()
    out = []
    for tri in Blob((mask_dir / 'hair.blob').read_bytes()).triangles():
        if tri is None:
            continue
        corners = []
        for vi, _ni, ui in tri:
            x, y, z, palette = struct.unpack_from('<3hH', chunk['positions'], vi * 8)
            ids, count, values = chunk['weights'][palette]
            corners.append(((x, y, z), tuple((ids[i], values[i]) for i in range(count)),
                            struct.unpack_from('<2H', uv, ui * 4)))
        out.append(tuple(corners))
    return out


def source_entries(inputs, name):
    ps2 = {i: (tag, data) for i, tag, data in ps2_bin.dat_entries((inputs / (name + '.dat')).read_bytes())}
    gc = archive.Archive(str(inputs / (name + '.drs')))
    out = {}
    for arc, tag in ((0x217, 'BIN'), (0x218, 'TPL'), (0x219, 'TPL')):
        ptag, data = ps2[arc - 4]
        require(ptag == tag, 'PS2 tag mismatch')
        g = gc.entry(arc - 4)
        require(g.tag == tag, 'GC tag mismatch')
        out['ps2', arc] = data
        out['gc', arc] = g.data
    return out


def prepare(base, inputs, donor_cast, donor_mask, out):
    require(not out.exists(), 'output already exists; preserve it')
    base_cast = base / 'cast'
    h0 = base_cast / NAME / 'ps2-v1/castmodel_runtime.h'
    h1 = donor_cast / 'zealot-em1c-09h/ps2-v1/castmodel_runtime.h'
    require(sha((base / 'r20f/package/r20f/registry.re4nmr').read_bytes()) == BASE_PACKAGE,
            'base package differs from current r20f')
    require(sha(h0.read_bytes()) == BASE_HEADER and sha(h1.read_bytes()) == DONOR_HEADER,
            'retained header changed')
    src = source_entries(inputs, 'em14')
    donor = source_entries(inputs, 'em1c')
    for key, expected in RAW_SHA.items():
        require(sha(src[key]) == expected and src[key] == donor[key], 'original BIN/TPL correspondence failed')
    chunks, bones = mr.parse_header(str(h0))
    donor_chunks, donor_bones = mr.parse_header(str(h1))
    require(bones == donor_bones == 37 and [c['source_info'] for c in chunks] == list(range(21)),
            'original complete pool owner/section set changed')
    c, dc = chunks[20], donor_chunks[22]
    base_spec = load(base / 'r20f.json')
    desc = next(d for d in base_spec['descriptors'] if d['name'] == NAME)
    masks = {int(k): Path(v) for k, v in desc['mask_runs'].items()}
    require(set(masks) == {13, 16, 20}, 'base mask selection changed')
    old_mask = masks[20]
    om, dm = load(old_mask / 'mask-runs.json'), load(donor_mask / 'mask-runs.json')
    require(dm['gc']['bin'] == '0x217' and dm['gc']['tpl'] == '0x219', 'wrong donor source role')
    require(om['header_sha256'] == BASE_HEADER and dm['header_sha256'] == DONOR_HEADER,
            'mask/header provenance mismatch')
    require((old_mask / 'hair.uv').read_bytes() == (donor_mask / 'hair.uv').read_bytes(), 'masked UV chart changed')
    require(masked_triangles(c, old_mask) == masked_triangles(dc, donor_mask),
            'oriented position/weight/masked-UV sequence changed')
    require(c['positions'] == dc['positions'] and c['normals'] == dc['normals'] and c['weights'] == dc['weights'],
            'donor source arrays differ')
    require(c['triangles'] == dc['triangles'] == 241 and om['mask_only'] and dm['mask_only'] and
            om['runs']['hair']['triangles'] == dm['runs']['hair']['triangles'] == 241 and
            om['runs']['opaque']['triangles'] == dm['runs']['opaque']['triangles'] == 0,
            'the complete mask-only source role changed')
    require((old_mask / 'hair.blob').read_bytes()[2] == c['stream'][2] == 12,
            'current lit normal/skin flags changed')
    pair = donor_mask / dm['pair_package']['file']
    require(sha(pair.read_bytes()) == dm['pair_package']['sha256'] == PAIR_SHA,
            'original alternate pair changed')

    # All refusals above happen before creating any output. No inherited input is edited.
    out.mkdir(parents=True)
    cast = out / 'cast'
    cast.mkdir()
    selected_names = [d['name'] for d in base_spec['descriptors']]
    require(len(selected_names) == 3 and len(set(selected_names)) == 3, 'unexpected room composition')
    for name in selected_names:
        shutil.copytree(base_cast / name, cast / name)
    shutil.copytree(base_cast / 'source', cast / 'source')
    audit = load(cast / 'source/archive-audit.json')
    (out / 'source').mkdir()
    for name in ('em14.dat', 'em14.drs'):
        shutil.copy2(inputs / name, out / 'source' / name)
    audit['em14']['source'] = str(out / 'source/em14.drs')
    dump(cast / 'source/archive-audit.json', audit)
    for (platform, arc), data in src.items():
        tag = 'bin' if arc == 0x217 else 'tpl'
        (out / 'source' / f'{platform}-{tag}{arc:x}.bin').write_bytes(data)

    catalog = load(base_cast / base_spec['revision_overlay'] / 'integration-bundle/catalog.json')
    catalog = [copy.deepcopy(e) for e in catalog if e['name'] in selected_names]
    require(len(catalog) == 3, 'missing selected catalog row')
    for entry in catalog:
        for texture in entry['texture_packages'].values():
            old = Path(texture['package'])
            target = cast / entry['name'] / entry['revision'] / 'texture' / old.name
            require(target.is_file() and sha(target.read_bytes()) == texture['package_sha256'],
                    'copied texture winner differs')
            texture['package'] = str(target)
        dump(cast / entry['name'] / entry['revision'] / 'revision-manifest.json', entry)
    entry = next(e for e in catalog if e['name'] == NAME)
    new_header_text = alias_chunk(h0.read_text(), 20, 21)
    revision = cast / NAME / REVISION
    revision.mkdir()
    header = revision / 'castmodel_runtime.h'
    header.write_text(new_header_text)
    header_sha = sha(header.read_bytes())
    added, added_bones = mr.parse_header(str(header))
    require(added_bones == bones and added[:-1] == chunks and
            {k: v for k, v in added[-1].items() if k != 'source_info'} ==
            {k: v for k, v in c.items() if k != 'source_info'}, 'alias changed source arrays/records')
    bindings_path = cast / NAME / 'source-bindings.json'
    bindings = load(bindings_path)
    require(len(bindings) == 21 and (bindings[20]['bin'], bindings[20]['tpl']) == (0x217, 0x218),
            'base source bindings changed')
    extra = copy.deepcopy(bindings[20])
    extra.update(tpl=0x219, role='acc38-b')
    bindings.append(extra)
    dump(bindings_path, bindings)
    source_path = cast / NAME / 'source.json'
    source = load(source_path)
    require(len(source['infos']) == 21 and source['source_model_id'] == 0x14 and source['types'] == [8],
            'base source identity changed')
    extra = copy.deepcopy(source['infos'][20])
    extra.update(id=21, source_tpl_arc=0x219, role='acc38-b')
    source['infos'].append(extra)
    dump(source_path, source)
    entry['previous_revision'] = entry['revision']
    entry['revision'] = REVISION
    entry['levels']['conservative'] = dict(runtime_header=f'{NAME}/{REVISION}/castmodel_runtime.h',
                                           header_sha256=header_sha)
    entry['texture_packages']['21'] = copy.deepcopy(entry['texture_packages']['20'])
    entry['status'] = 'Original em14 BIN217/TPL219 additive role; exact accepted lit geometry and retained source pair'
    dump(revision / 'revision-manifest.json', entry)
    ib = cast / base_spec['revision_overlay'] / 'integration-bundle'
    ib.mkdir(parents=True)
    dump(ib / 'catalog.json', catalog)

    for section, mask_dir in masks.items():
        dst = out / 'masks' / f's{section}'
        shutil.copytree(mask_dir, dst)
        meta = load(dst / 'mask-runs.json')
        meta['header_sha256'] = header_sha
        meta['rebind'] = dict(base_header_sha256=BASE_HEADER, section_arrays_and_runs_unchanged=True)
        dump(dst / 'mask-runs.json', meta)
        desc['mask_runs'][str(section)] = str(dst)
    alt = out / 'masks/s21'
    shutil.copytree(old_mask, alt)
    # Keep current lit stream, UVs, normals and skin flags. Only take the proven alternate images/pair.
    for name in ('colour.png', 'mask.png', 'pair.png', dm['pair_package']['file']):
        shutil.copy2(donor_mask / name, alt / name)
    meta = copy.deepcopy(om)
    meta.update(header_sha256=header_sha, section=21)
    for field in ('keys', 'pair_package', 'texture'):
        meta[field] = copy.deepcopy(dm[field])
    meta['gc']['tpl'] = '0x219'
    meta['retained_alternate'] = dict(donor_header_sha256=DONOR_HEADER, donor_section=22,
        raw_bin_tpl_byte_identity=True, masked_uv_and_oriented_geometry_equal=True,
        donor_stream_not_copied=True, current_lit_flags=12, new_color_bake=False)
    dump(alt / 'mask-runs.json', meta)
    desc['mask_runs']['21'] = str(alt)
    base_spec['cast_dir'] = str(cast)
    base_spec['registry'] = 'boss18-r20f-alt-material'
    base_spec['about'] = 'Original r20f types6/7/8 with one additive BIN217/TPL219 role; all existing data winners retained'
    dump(out / 'r20f.json', base_spec)
    proof = dict(base_package_sha256=BASE_PACKAGE, base_header_sha256=BASE_HEADER, new_header_sha256=header_sha,
        donor_header_sha256=DONOR_HEADER, raw_entry_sha256={f'{p}:{a:x}': s for (p, a), s in RAW_SHA.items()},
        raw_bin_tpl_byte_identity=True, bones=bones, old_sections=len(chunks), new_sections=len(added),
        all_old_chunk_records_and_arrays_exact=True, new_role=dict(bin=0x217, tpl=0x219, source_info=21,
        triangles=241, clone_of=20, source_material_flags=0, ps2_diffuse=0, ps2_opacity=255),
        mask_uv_sha256=sha((alt / 'hair.uv').read_bytes()), mask_stream_flags=12,
        pair=meta['keys'], pair_sha256=PAIR_SHA, no_new_bake=True, no_mesh_reduction=True,
        no_shared_converter_or_runtime_change=True,
        qualification='Offline data preparation only; existing source-derived GC pair mapping/ARGB4444 quantization retained. No PS2 pixel equality, runtime or look acceptance inferred.')
    dump(out / 'additive-proof.json', proof)
    return proof


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'inputs', 'donor-cast', 'donor-mask', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    try:
        proof = prepare(a.base.resolve(), a.inputs.resolve(), a.donor_cast.resolve(),
                        a.donor_mask.resolve(), a.out.resolve())
    except (ValueError, OSError, KeyError) as exc:
        p.exit(2, f'r20f alternate accessory refused: {exc}\n')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
