"""Offline proof of original addModel tables on an unchanged modelInit owner.

No runtime exception: source BIN/material facts, skeleton checks and capacities
are emitted as before. The optional descriptor contract pins the source/header
and both original archives; original partial/duplicate metadata stays intact.
"""
import hashlib
import json
import math
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def _index(value):
    return type(value) is int


def _xyz(value):
    return isinstance(value, (list, tuple)) and len(value) == 3 and all(
        type(x) in (int, float) and math.isfinite(x) for x in value)


def _gc_parts(model):
    return [dict(id=p.no, parent=p.parent, attach=p.attach, translation=list(p.pos)) for p in model.parts]


def prove_tables(source, bindings, chunks, contract, ps2_models, gc_models, ps2_bins, gc_bins):
    """Re-derive every original section table and weighted owner reference."""
    if len(bindings) < 2 or len(chunks) != len(bindings):
        raise ValueError('owner contract needs all original source sections/chunks')
    if contract['owner_bin'] != bindings[0]['bin']:
        raise ValueError('owner contract must name the first modelInit body')
    owner = _gc_parts(gc_models[0]); ps2_owner = ps2_models[0].bones; n = len(owner)
    if not 1 <= n <= 255 or len(ps2_owner) != n or len(source.get('bones', [])) != n:
        raise ValueError('owner contract needs the complete original body skeleton')
    world = []
    for i, (g, p, s) in enumerate(zip(owner, ps2_owner, source['bones'])):
        if (any(not _index(x) for x in (g['id'], g['attach'], g['parent'], p['id'], p['parent'])) or
            (g['id'], g['attach'], p['id']) != (i, i, i) or
            p['parent'] != g['parent'] or
            not -1 <= g['parent'] < i or
            not _xyz(g['translation']) or
            not _xyz(p['pos'])):
            raise ValueError('original body owner ids/parents/translations changed')
        parent = g['parent']; t = g['translation']
        w = list(t) if parent < 0 else [world[parent][k] + t[k] for k in range(3)]
        world.append(w)
        rest = [[float(r == c) for c in range(4)] for r in range(4)]
        for k in range(3):
            rest[k][3] = w[k]
        if (s.get('id'), s.get('parent'), s.get('rest')) != (i, parent, rest):
            raise ValueError('source skeleton is not the unchanged original GC owner')
    if bindings[0]['part_bindings'] != owner:
        raise ValueError('body bindings differ from original GC BIN')
    body_hash = dict(kind='same-id-parent-gc-inverse-bind', ps2_sha256=sha(ps2_bins[0]), gc_sha256=sha(gc_bins[0]))
    if source.get('source_bind_offsets', {}).get('0', {}).get('contract') != body_hash:
        raise ValueError('original body inverse-bind source contract changed')
    proofs = source.get('attachment_owner_skeletons', {})
    if set(proofs) != {str(i) for i in range(1, len(bindings))}:
        raise ValueError('owner contract needs each original attachment proof exactly once')
    rows = []
    for i, (b, c, pmodel, gmodel) in enumerate(zip(bindings, chunks, ps2_models, gc_models)):
        actual = _gc_parts(gmodel)
        if b['part_bindings'] != actual or b['parts'] != len(actual) or c['source_info'] != i:
            raise ValueError('section bindings/order differ from original GC BIN')
        weighted = {bone for _, corners in pmodel.triangles for corner in corners
                    for bone, weight in corner['w'] if weight > 0}
        native = {bones[k] for bones, count, values in c['weights'] for k in range(count) if values[k] > 0}
        if not weighted or any(not _index(k) or not 0 <= k < n for k in weighted) or not native <= weighted:
            raise ValueError('native/source weights escape original body owner')
        if i == 0:
            continue
        proof = proofs[str(i)]
        hashes = dict(ps2_sha256=sha(ps2_bins[i]), gc_sha256=sha(gc_bins[i]),
                      owner_ps2_sha256=body_hash['ps2_sha256'], owner_gc_sha256=body_hash['gc_sha256'])
        if (proof.get('kind') != 'source-pinned-retarget-owner-attachment' or
            proof.get('source_BIN_sha256') != hashes or
            proof.get('owner_parts') != n or
            proof.get('weighted_ids') != sorted(weighted) or
            proof.get('owner_bind_offsets', {}).get('contract') != body_hash):
            raise ValueError('attachment source/owner/weighted identity contract changed')
        if (canonical(proof.get('original_PS2_rest_records')) != canonical(pmodel.bones) or
            proof.get('original_PS2_rest_record_count') != len(pmodel.bones)):
            raise ValueError('original PS2 partial/duplicate metadata changed')
        original = {}; seen = set()
        for q in pmodel.bones:
            k, parent = q['id'], q['parent']
            if (not _index(k) or
                not 0 <= k < n or
                not _index(parent) or
                not -1 <= parent < n or
                not _xyz(q['pos']) or
                (parent >= 0 and parent not in seen)):
                raise ValueError('invalid original PS2 attachment table')
            value = (parent, tuple(q['pos']))
            if k in original and original[k] != value:
                raise ValueError('conflicting original duplicate PS2 metadata')
            original[k] = value; seen.add(k)
        recorded = proof.get('original_GC_rest_records', [])
        if len(recorded) != len(actual) or proof.get('original_GC_rest_record_count') != len(actual):
            raise ValueError('original GC partial metadata count changed')
        attached = set()
        for g, r in zip(actual, recorded):
            k, parent = g['attach'], g['parent']
            if ({key:r.get(key) for key in g} != g or
                not _index(k) or
                not 0 <= k < n or
                k in attached or
                not _index(parent) or
                not -1 <= parent < n or
                not _xyz(g['translation'])):
                raise ValueError('original GC attachment metadata/reference changed')
            rest = r.get('rest')
            if not isinstance(rest, list) or len(rest) != 4 or any(not isinstance(row, list) or len(row) != 4 or
                    any(type(x) not in (int, float) or not math.isfinite(x) for x in row) for row in rest):
                raise ValueError('nonfinite original GC attachment rest metadata')
            if k in weighted and parent not in (-1, owner[k]['parent']):
                raise ValueError('weighted original GC attachment parent differs from owner')
            attached.add(k)
        if not weighted <= (set(original) & attached):
            raise ValueError('weighted id missing from an original attachment table')
        rows.append(dict(section=i, bin=b['bin'], original_PS2_records=len(pmodel.bones),
                         original_GC_records=len(actual), weighted_ids=sorted(weighted), source_BIN_sha256=hashes))
    return dict(schema='re4dc-source-body-owner-1', owner_bin=contract['owner_bin'], owner_parts=n,
                sections=rows, policy='Original modelInit owner unchanged; original addModel metadata/facts retained; weighted references independently re-derived')


def prove(inputs, descriptor, source, bindings, arc, gc_archive_sha256, header_path, chunks):
    """Opt-in loader; all contracts and original input bytes are hash-pinned."""
    selection = descriptor['source_owner_contract']
    if not isinstance(selection, dict) or set(selection) != {'path', 'sha256'}:
        raise ValueError('source owner selection needs exactly path and sha256')
    path = inputs.take(selection['path'], 'owner-contract/' + descriptor['name'] + '.json')
    raw = Path(path).read_bytes()
    if sha(raw) != selection['sha256']:
        raise ValueError('source owner manifest hash changed')
    contract = json.loads(raw)
    keys = {'schema', 'source_sha256', 'bindings_sha256', 'header_sha256', 'ps2_archive',
            'ps2_archive_sha256', 'gc_archive_sha256', 'owner_bin'}
    if set(contract) != keys or contract['schema'] != 're4dc-source-body-owner-1':
        raise ValueError('unknown source owner manifest schema/fields')
    if (contract['source_sha256'] != canonical(source) or
        contract['bindings_sha256'] != canonical(bindings) or
        contract['header_sha256'] != sha(Path(header_path).read_bytes()) or
        contract['gc_archive_sha256'] != gc_archive_sha256 or
        source.get('source_archive_sha256') != gc_archive_sha256):
        raise ValueError('source owner source/bindings/header/GC archive identity changed')
    data_path = inputs.take(contract['ps2_archive'], 'owner-contract/' + source['source_archive'] + '.dat')
    data = Path(data_path).read_bytes()
    if sha(data) != contract['ps2_archive_sha256'] or sha(data) != source.get('ps2_archive_sha256'):
        raise ValueError('source owner original PS2 archive identity changed')
    import ps2_bin
    from motion import modelbin
    entries = {i:(tag, payload) for i, tag, payload in ps2_bin.dat_entries(data)}
    ps2_bins = []; gc_bins = []; ps2_models = []; gc_models = []
    for b in bindings:
        tag, payload = entries[b['bin'] - 4]
        gc = arc.entry(b['bin'] - 4)
        if tag != 'BIN' or gc.tag != 'BIN':
            raise ValueError('source owner selection is not an original BIN')
        pmodel = ps2_bin.parse_bin(payload)
        pmodel.triangles = list(ps2_bin.triangles(pmodel))
        ps2_bins.append(payload); gc_bins.append(gc.data)
        ps2_models.append(pmodel); gc_models.append(modelbin.parse(gc.data))
    result = prove_tables(source, bindings, chunks, contract, ps2_models, gc_models, ps2_bins, gc_bins)
    result['manifest_sha256'] = selection['sha256']
    return result
