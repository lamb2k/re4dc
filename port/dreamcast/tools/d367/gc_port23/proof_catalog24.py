#!/usr/bin/env python3
"""Offline selected-payload catalog with explicit reviewed-origin trust boundary.
No directory scan, guest log learning, conversion, runtime pin or allowance growth.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

import catalog_index as idx
import build_reviewed_seed as seed
import judge

MAX_METADATA = 16 * 1024 * 1024
MAX_PROOF_FILE = 4 * 1024 * 1024
MAX_PROOF_BYTES = 32 * 1024 * 1024
SHA = re.compile(r'[0-9a-f]{64}\Z')
KEY = re.compile(r'[0-9a-f]{8}-[0-9a-f]{8}\Z')
DIGEST_KINDS = {'model', 'motion', 'geometry', 'layout', 'font', 'ui', 'movie'}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def encode(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True)+'\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def metadata(path, expected):
    need(isinstance(expected, str) and SHA.fullmatch(expected), 'invalid metadata pin')
    p = Path(path)
    need(p.is_file() and p.stat().st_size <= MAX_METADATA, 'metadata bounds')
    raw = p.read_bytes()
    need(digest(raw) == expected, 'metadata pin mismatch')
    return raw


def exact_fields(row, fields, label):
    need(isinstance(row, dict) and set(row) == set(fields), label+' fields')


def source_name(value):
    need(isinstance(value, str), 'asset name type')
    p = PurePosixPath(value)
    need(not p.is_absolute() and '..' not in p.parts and str(p) == value and '\\' not in value,
         'unsafe selected asset name')
    return value


def read_manifest(raw):
    obj = seed.decode_json(raw)
    need(isinstance(obj, dict) and 0 < len(obj) <= 20000, 'manifest bounds')
    for name, row in obj.items():
        source_name(name)
        exact_fields(row, ['sha256', 'size'], 'manifest row')
        need(SHA.fullmatch(row['sha256']) and type(row['size']) is int and 0 < row['size'] <= 0xffffffff,
             'manifest digest/size')
    return obj


def fingerprint(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def file_hash(fp):
    fp.seek(0)
    h = hashlib.sha256()
    for block in iter(lambda: fp.read(1024*1024), b''):
        h.update(block)
    return h.hexdigest()


@contextmanager
def immutable(path, roots, pin, size):
    p = seed.contained(path, roots)
    before = fingerprint(p.stat())
    need(before[2] == size, 'selected file size mismatch')
    with p.open('rb') as fp:
        need(before == fingerprint(os.fstat(fp.fileno())), 'selected file replaced at open')
        need(file_hash(fp) == pin, 'selected file digest mismatch')
        yield fp, p
        need(file_hash(fp) == pin, 'selected file mutated during read')
        need(before == fingerprint(os.fstat(fp.fileno())) == fingerprint(p.stat()),
             'selected file replaced during read')


def span_hash(fp, offset, size):
    fp.seek(offset)
    h = hashlib.sha256()
    remaining = size
    while remaining:
        block = fp.read(min(remaining, 1024*1024))
        need(bool(block), 'short selected payload')
        h.update(block)
        remaining -= len(block)
    return h.hexdigest()


def checked_identity(kind, identity, sha):
    idx.text(kind, 16)
    idx.text(identity, 48)
    need(SHA.fullmatch(sha), 'invalid payload digest')
    if kind == 'texture':
        need(KEY.fullmatch(identity), 'texture identity format')
    elif kind in DIGEST_KINDS:
        need(identity == sha[:40], 'original span digest-prefix identity mismatch')
    elif kind == 'sound-stream':
        need(identity == 'aica-str-dat', 'unsupported stream identity')
    else:
        raise ValueError('unreviewed identity kind')
    return kind, identity, sha


def proof_file(ref, roots, budget):
    exact_fields(ref, ['path', 'sha256'], 'proof receipt')
    need(SHA.fullmatch(ref['sha256']), 'proof receipt pin')
    p = seed.contained(ref['path'], roots)
    size = p.stat().st_size
    need(0 < size <= MAX_PROOF_FILE, 'proof receipt bounds')
    budget[0] += size
    need(budget[0] <= MAX_PROOF_BYTES, 'proof chain total bounds')
    with immutable(p, roots, ref['sha256'], size) as (fp, resolved):
        return {'path': str(resolved), 'sha256': ref['sha256'], 'bytes': size}


def reviewed_origins(raw, selection_sha, roots):
    if raw is None:
        return {}
    obj = seed.decode_json(raw)
    exact_fields(obj, ['schema', 'selection_sha256', 'entries'], 'reviewed origin envelope')
    need(type(obj['schema']) is int and obj['schema'] == 1 and obj['selection_sha256'] == selection_sha,
         'reviewed origins selection mismatch')
    need(isinstance(obj['entries'], list) and len(obj['entries']) <= idx.MAX_RECORDS, 'reviewed origins capacity')
    rows = {}
    budget = [0]
    for row in obj['entries']:
        exact_fields(row, ['kind', 'id', 'sha256', 'provenance', 'owner', 'reason', 'reviewed', 'chain'], 'reviewed origin')
        key = checked_identity(row['kind'], row['id'], row['sha256'])
        need(key not in rows, 'duplicate reviewed origin')
        need(row['provenance'] in ('gc', 'ps2', 'authored') and row['reviewed'] is True,
             'origin is not independently reviewed')
        need(all(isinstance(row[x], str) and row[x].strip() == row[x] and row[x] for x in ('owner', 'reason')),
             'reviewed origin reason/owner')
        need(isinstance(row['chain'], list) and 0 < len(row['chain']) <= 32, 'missing reviewed proof chain')
        receipts = [proof_file(ref, roots, budget) for ref in row['chain']]
        need(len({x['path'] for x in receipts}) == len(receipts), 'duplicate proof receipt')
        rows[key] = dict(row, chain=receipts)
    return rows


def allowance_rows(raw):
    obj = seed.decode_json(raw)
    exact_fields(obj, ['schema', 'entries'], 'allowance envelope')
    need(type(obj['schema']) is int and obj['schema'] == 1 and isinstance(obj['entries'], list), 'allowance schema')
    need(len(obj['entries']) <= 200000, 'allowance capacity')
    rows = {}
    for row in obj['entries']:
        scope = judge.scope_name(row)
        fields = {'phase'} if scope.startswith('@') else {'room'}
        if scope == '@transition':
            fields |= judge.transition_location(row).keys()
        exact_fields(row, fields | {'kind', 'id', 'sha256', 'provenance', 'reason', 'owner', 'evidence'}, 'allowance row')
        # An accepted ceiling may contain classes not covered by this selection.
        # Validate exact protocol identity, then prune absent rows; never rewrite them.
        idx.text(row['kind'], 16);idx.text(row['id'], 48)
        need(isinstance(row['sha256'], str) and SHA.fullmatch(row['sha256']), 'allowance payload digest')
        need(row['provenance'] in ('gc', 'unknown'), 'allowance origin')
        need(all(isinstance(row[x], str) and row[x].strip() for x in ('reason', 'owner', 'evidence')), 'allowance metadata')
        identity = judge.identity(row)
        need(identity not in rows, 'duplicate allowance')
        rows[identity] = row
    return rows


def shrink_allowance(baseline_raw, requested_raw, catalog):
    baseline = allowance_rows(baseline_raw) if baseline_raw is not None else {}
    requested = allowance_rows(requested_raw) if requested_raw is not None else baseline
    for identity, row in requested.items():
        need(identity in baseline and baseline[identity] == row, 'allowance growth or reviewed row change')
    current = {(r['kind'], r['id'], r['sha256'], r['provenance']) for r in catalog}
    result = [row for row in requested.values() if (row['kind'], row['id'], row['sha256'], row['provenance']) in current]
    return sorted(result, key=judge.identity)


def generate(selection_raw, manifest_raw, roots, proofs_raw=None, baseline_raw=None, requested_raw=None, proposals_raw=None):
    selection = seed.decode_json(selection_raw)
    exact_fields(selection, ['schema', 'manifest_sha256', 'providers'], 'selection')
    need(type(selection['schema']) is int and selection['schema'] == 1 and selection['manifest_sha256'] == digest(manifest_raw),
         'selection manifest mismatch')
    need(isinstance(selection['providers'], list) and 0 < len(selection['providers']) <= idx.MAX_RECORDS, 'provider count')
    roots = [Path(x).resolve(strict=True) for x in roots]
    need(roots and all(p.is_dir() for p in roots), 'readonly roots required')
    manifest = read_manifest(manifest_raw)
    origins = reviewed_origins(proofs_raw, digest(selection_raw), roots)
    found = {}
    providers = []
    boundary_budget = [0]
    seen_provider = set()
    def add(kind, identity, sha, source):
        key = checked_identity(kind, identity, sha)
        need(len(found) < idx.MAX_RECORDS or key in found, 'catalog capacity')
        found.setdefault(key, []).append(source)
    for row in selection['providers']:
        need(isinstance(row, dict), 'provider type')
        mode = row.get('provider')
        common = {'provider', 'asset', 'path'}
        if mode == 'texpak': fields = common
        elif mode == 'file': fields = common | {'kind', 'id'}
        elif mode == 'span': fields = common | {'kind', 'id', 'offset', 'bytes', 'sha256', 'boundary'}
        else: raise ValueError('unsupported provider')
        exact_fields(row, fields, 'provider')
        asset = source_name(row['asset'])
        need(asset in manifest and asset not in ('1ST_READ.BIN',) and not asset.endswith('.ovl'), 'provider outside selected assets')
        unique = encode(row)
        need(unique not in seen_provider, 'duplicate provider recipe')
        seen_provider.add(unique)
        pin = manifest[asset]
        sources = []
        with immutable(row['path'], roots, pin['sha256'], pin['size']) as (fp, path):
            info = {'asset': asset, 'path': str(path), **pin}
            if mode == 'texpak':
                need(asset == 'dc/tex.pak', 'texpak asset identity')
                entries = seed.pak_index(fp, pin['size'])
                need(len(entries) <= idx.MAX_RECORDS, 'texpak catalog capacity')
                for identity, (offset, size) in sorted(entries.items()):
                    fp.seek(offset);need(fp.read(8) == b'RE4DCTX\0', 'texture header')
                    payload = span_hash(fp, offset, size)
                    add('texture', identity, payload, dict(info, offset=offset, bytes=size))
            elif mode == 'file':
                if row['kind'] == 'texture':
                    need(asset == 'dc/tex/'+row['id']+'.re4tex', 'loose texture asset/key mismatch')
                    fp.seek(0);need(fp.read(8) == b'RE4DCTX\0', 'texture header')
                elif row['kind'] == 'sound-stream':
                    need(asset == 'bgm/aica_str.dat', 'stream asset identity')
                add(row['kind'], row['id'], pin['sha256'], dict(info, offset=0, bytes=pin['size']))
            else:
                need(row['kind'] in ('model', 'motion'), 'span kind unsupported')
                need(type(row['offset']) is int and type(row['bytes']) is int and row['offset'] >= 0 and
                     row['bytes'] > 0 and row['offset'] <= pin['size']-row['bytes'], 'span bounds')
                need(SHA.fullmatch(row['sha256']), 'span digest pin')
                receipt = proof_file(row['boundary'], roots, boundary_budget)
                payload = span_hash(fp, row['offset'], row['bytes'])
                need(payload == row['sha256'], 'original span mismatch')
                add(row['kind'], row['id'], payload, dict(info, offset=row['offset'], bytes=row['bytes'], boundary=receipt))
            providers.append(dict(info, provider=mode))
    need(set(origins) <= set(found), 'reviewed proof outside selected immutable identities')
    rows = []
    for key, sources in sorted(found.items()):
        proof = origins.get(key)
        rows.append({'kind':key[0], 'id':key[1], 'sha256':key[2], 'provenance':proof['provenance'] if proof else 'unknown',
                     'evidence':'selection_sha256='+digest(selection_raw)+'; '+('reviewed_proofs_sha256='+digest(proofs_raw) if proof else 'unproved original identity; no origin inferred'),
                     'sources':sources, 'reviewed_proof':proof})
    allowed = shrink_allowance(baseline_raw, requested_raw, rows)
    proposals = allowance_rows(proposals_raw) if proposals_raw is not None else {}
    identities = {(x['kind'],x['id'],x['sha256'],x['provenance']) for x in rows}
    unapproved = [x for x in proposals.values() if (x['kind'],x['id'],x['sha256'],x['provenance']) in identities and judge.identity(x) not in {judge.identity(v) for v in allowed}]
    data, pin = idx.build(rows)
    reader = idx.Reader(lambda o,n:data[o:o+n], len(data), pin)
    need(reader.count == len(rows), 'index readback count')
    return {'catalog.json':{'schema':1,'entries':rows}, 'allowlist.json':{'schema':1,'entries':allowed},
            'unapproved-proposals.json':{'schema':1,'entries':sorted(unapproved,key=judge.identity)},
            'gc-assets.idx':data,
            'report.json':{'schema':1,'selection_sha256':digest(selection_raw),'manifest_sha256':digest(manifest_raw),
                'proofs_sha256':digest(proofs_raw) if proofs_raw is not None else None,
                'accepted_baseline_sha256':digest(baseline_raw) if baseline_raw is not None else None,
                'requested_allowance_sha256':digest(requested_raw) if requested_raw is not None else None,
                'historical_proposals_sha256':digest(proposals_raw) if proposals_raw is not None else None,
                'manifest_asset_rows':len(manifest),'provider_files':providers,'records':len(rows),
                'origins':{p:sum(x['provenance']==p for x in rows) for p in idx.ORIGINS},
                'index_sha256':pin.hex(),'index_bytes':len(data),'index_capacity':idx.MAX_RECORDS,
                'retained_accepted_allowances':len(allowed),'unapproved_proposals':len(unapproved),
                'production_pin_unchanged':0,'emission_or_coverage_or_gate_pass':False,
                'runtime_contract':{'read_only_catalog_FDs':1,'header_bytes':idx.HEADER.size,'record_bytes':idx.RECORD.size,
                    'install_hash_scratch_bytes':512,'Seen_capacity_bytes':2048,'unknown_quarantine_entries':8,
                    'max_record_reads_per_lookup':len(rows).bit_length()+1,'extra_runtime_allocations_from_tool':0},
                'scope':'Selected immutable payloads only; neither load/read nor a reviewed origin proves accepted consumer coverage.'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('selection','manifest'):
        parser.add_argument('--'+name, type=Path, required=True);parser.add_argument('--'+name+'-sha256', required=True)
    for name in ('reviewed-proofs','accepted-allowlist','requested-allowlist','historical-proposals'):
        parser.add_argument('--'+name, type=Path);parser.add_argument('--'+name+'-sha256')
    parser.add_argument('--store-root', type=Path, action='append', required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    need(not args.out_dir.exists(), 'new output directory required')
    roots = [p.resolve(strict=True) for p in args.store_root]
    need(not any(args.out_dir.resolve().is_relative_to(p) for p in roots), 'output inside readonly store')
    optional = []
    for name in ('reviewed_proofs','accepted_allowlist','requested_allowlist','historical_proposals'):
        path, pin = getattr(args,name),getattr(args,name+'_sha256')
        need(bool(path)==bool(pin), 'optional metadata and pin required together')
        optional.append(metadata(path,pin) if path else None)
    docs = generate(metadata(args.selection,args.selection_sha256),metadata(args.manifest,args.manifest_sha256),roots,*optional)
    docs['data-option.json'] = {'replace': {'dc/gc-assets.idx': str(args.out_dir.resolve()/'gc-assets.idx')},
        'remove': [], 'provenance': ['Private candidate index only; production pin remains0; no gate/coverage acceptance.']}
    # No output allocated until all source/proof/allowance checks pass.
    args.out_dir.mkdir(parents=True,exist_ok=False)
    for name,obj in docs.items():
        (args.out_dir/name).write_bytes(obj if isinstance(obj,bytes) else encode(obj))
    print(json.dumps({k:docs['report.json'][k] for k in ('records','origins','index_sha256','index_bytes','retained_accepted_allowances','unapproved_proposals')},sort_keys=True))

if __name__=='__main__':main()