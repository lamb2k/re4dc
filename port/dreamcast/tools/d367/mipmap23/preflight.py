#!/usr/bin/env python3
"""Pin the seven authorized room-object candidates to a current local RR pack.

Metadata only. No classification rerun, asset output, fixture or runtime change.
"""
from pathlib import Path
import argparse, csv, hashlib, importlib.util, json, struct, subprocess

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
EXPECTED = {
    '09b9d35d-9a1a2fc2', '4f784887-fc80dbee', '5926862b-e61d4941',
    'c8d0db2f-3126bc5d', 'daa3d452-b10799f3', 'de020f0a-cc184ee1',
    'f56596f9-c3b192f2',
}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rr-package', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    assert not args.out.exists(), 'Use a fresh private output namespace'
    cv = load(TOOLS / 'texsrc22/convert.py', 'mipmap23_converter')
    classify = load(TOOLS / 'texsrc22/classify.py', 'mipmap23_classifier')
    table = TOOLS / 'texsrc22/resume-review.tsv'
    rows = [r for r in csv.DictReader(table.open(), delimiter='\t')
            if r['review_group'] == 'ps2-world-object']
    assert {r['key'] for r in rows} == EXPECTED and len(rows) == 7
    rr_blob = args.rr_package.read_bytes()
    rr = json.loads(rr_blob)
    files = rr['replace']
    pack, resident = Path(files['dc/tex.pak']), Path(files['dc/resident.bin'])
    assert pack == Path('/root/re4data/private/mip22b-20261022/dc/tex.pak')
    stat0 = pack.stat()
    source = pack.read_bytes()
    pack_sha = sha(source)
    assert (pack.stat().st_size, pack.stat().st_mtime_ns) == (stat0.st_size, stat0.st_mtime_ns)
    assert pack_sha == '5bba464a1175d8ebe153d5aecb629ea9637807c2bf4fc438a32c17148d0729da'
    cv.texpack.verify(source)
    packages = cv.read_pak(source)
    rb = resident.read_bytes()
    assert len(rb) % 512 == 0
    preload = {}
    for room, w, h, f, c, fn in struct.iter_unpack('<4H2I', rb):
        key = '%08x-%08x' % (c, fn)
        if key in EXPECTED:
            assert room and w and h
            preload.setdefault(key, []).append(dict(room='r%03x' % room,
                width=w, height=h, flags=f))
    assert set(preload) == EXPECTED, ('A selected key lacks actual preload evidence', preload.keys())
    native_bindings = {k: [] for k in EXPECTED}
    native_inputs = {}
    for logical, path in files.items():
        if logical.startswith('dc/native/') and logical.endswith('/ps2-world.r4pw'):
            blob = Path(path).read_bytes()
            bound = classify.world_material_keys(blob)
            matched = EXPECTED.intersection(bound)
            if matched:
                native_inputs[logical] = dict(source=path, sha256=sha(blob))
                for k in matched:
                    native_bindings[k].append(logical)
    for row in rows:
        key = row['key']
        blob = packages[cv.key_tuple(key)]
        kind, native, decode, generate, base = cv.identify(blob)
        assert not native.mipmapped, ('Selected member already mipped', key)
        row.update(preload_records=preload[key], actual_material_bindings=native_bindings[key],
            source_package_sha256=sha(blob), source_package_bytes=len(blob),
            actual_generator=kind, actual_side=native.size, actual_format=native.texture[3],
            actual_flags=native.texture[6], actual_label=native.texture[0].split(b'\0')[0].decode('latin1'))
    gate = TOOLS / 'mipmap21/mip_quality.py'
    holds = TOOLS / 'mipmap22/room-select.tsv'
    selection = dict(schema=cv.SCHEMA, base_pack_sha256=pack_sha,
        quality_gate_sha256=sha(gate.read_bytes()), hold_keys_sha256=sha(holds.read_bytes()),
        approved_keys=sorted(EXPECTED))
    cv.validate_selection(selection, source, gate.read_bytes(), holds.read_bytes())
    assert not EXPECTED.intersection(cv.hold_keys(holds.read_bytes()))
    args.out.mkdir(parents=True, exist_ok=False)
    repo = HERE.parents[4]
    head = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    report = dict(schema='re4dc-mipmap23-preflight-1', source_commit=head,
        rr_package=str(args.rr_package), rr_package_sha256=sha(rr_blob),
        source_pack=str(pack), source_pack_bytes=len(source), source_pack_sha256=pack_sha,
        source_pack_mtime_ns=stat0.st_mtime_ns, source_members=len(packages),
        resident=str(resident), resident_sha256=sha(rb), selected=rows,
        quality_gate=str(gate), quality_gate_sha256=selection['quality_gate_sha256'],
        room_hold_manifest=str(holds), room_hold_manifest_sha256=selection['hold_keys_sha256'],
        native_material_inputs=native_inputs, selection_table_sha256=sha(table.read_bytes()),
        private_generation_only=True, minification='unmeasured',
        shared_ganado_action='retain all 41; hold 39 unresolved consumers; no selected shared keys',
        prune_action='none')
    (args.out/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    (args.out/'input-preflight.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
