#!/usr/bin/env python3
"""Read back a reviewed mipmap23 candidate and report static preload costs.

This is package/host qualification. It neither measures runtime memory fit nor
proves a material is drawn or usefully minified. Private assets stay local.
"""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent

def sha(b):
    return hashlib.sha256(b).hexdigest()

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def pixel_digest(px):
    return sha(bytes(c for p in px for c in p))

def alpha_hist(px):
    return {str(a): n for a,n in sorted(collections.Counter(p[3] for p in px).items())}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--report-name', default='qualification.json')
    args = p.parse_args()
    ds = args.dataset
    assert Path(args.report_name).name == args.report_name
    target = ds/args.report_name
    assert not target.exists()
    cv = load(TOOLS/'texsrc22/convert.py', 'mipmap23_qualification_converter')
    pre = json.loads((ds/'input-preflight.json').read_bytes())
    conversion = json.loads((ds/'conversion-report.json').read_bytes())
    source_path = Path(pre['source_pack'])
    before = source_path.read_bytes()
    assert sha(before) == pre['source_pack_sha256'] == conversion['source_pack_sha256']
    assert source_path.stat().st_size == pre['source_pack_bytes']
    assert source_path.stat().st_mtime_ns == pre['source_pack_mtime_ns']
    after = (ds/'dc/tex.pak').read_bytes()
    assert sha(after) == conversion['output_pack_sha256']
    cv.texpack.verify(before)
    cv.texpack.verify(after)
    bp, ap = cv.read_pak(before), cv.read_pak(after)
    assert bp.keys() == ap.keys() and len(bp) == pre['source_members']
    off, off_receipt = cv.build_candidate(before)
    assert off == before and off_receipt['changed'] == 0
    selected = {r['key']: r for r in pre['selected']}
    report_rows = {r['key']: r for r in conversion['rows']}
    changed = {'%08x-%08x' % k for k in bp if bp[k] != ap[k]}
    assert changed == set(conversion['changed_keys']) and changed <= selected.keys()
    shared = json.loads((TOOLS/'texsrc22/resume-review.json').read_bytes())['shared_ganado']
    shared_keys = {r['key'] for r in shared['rows']}
    assert len(shared_keys) == 41 and shared['consumer_unresolved_count'] == 39
    assert not shared_keys.intersection(selected)
    assert all(bp[cv.key_tuple(k)] == ap[cv.key_tuple(k)] for k in shared_keys)
    assert all(bp[k] == ap[k] for k in bp if '%08x-%08x' % k not in selected)
    gate_path = Path(pre['quality_gate'])
    assert sha(gate_path.read_bytes()) == pre['quality_gate_sha256']
    gate = cv.load_gate(gate_path, pre['quality_gate_sha256'])
    holds_path = Path(pre['room_hold_manifest'])
    hold_blob = holds_path.read_bytes()
    assert sha(hold_blob) == pre['room_hold_manifest_sha256']
    gate.HOLD_KEYS.clear()
    gate.HOLD_KEYS.update(cv.hold_keys(hold_blob))
    rows = []
    room = collections.defaultdict(lambda: dict(keys=[], extra_payload_bytes=0, extra_alloc32_bytes=0))
    for key, prior in sorted(selected.items()):
        b, a = bp[cv.key_tuple(key)], ap[cv.key_tuple(key)]
        kind, bn, decode, generate, base = cv.identify(b)
        akind, an, adecode, _, abase = cv.identify(a)
        assert kind == akind
        report = report_rows[key]
        assert sha(b) == prior['source_package_sha256'] == report['source_package_sha256']
        assert sha(a) == report['output_package_sha256']
        bpx, apx = decode(bn,bn.size), adecode(an,an.size)
        assert base(bn) == abase(an) and bpx == apx
        levels = []
        if key in changed:
            cv.unchanged_base(bn, an, decode, base)
            audit_key, audit, held = gate.audit((cv.key_tuple(key), a))
            assert audit_key == cv.key_tuple(key) and audit['verdict'] == 'pass' and held is None
            assert audit == report['quality']
            for side in [bn.size >> i for i in range(1,bn.size.bit_length())]:
                px = adecode(an,side)
                assert len(px) == side*side
                levels.append(dict(side=side, decoded_rgba_sha256=pixel_digest(px),
                    alpha_histogram=alpha_hist(px), opaque_at_128=sum(p[3]>=128 for p in px)))
            assert levels[-1]['side'] == 1
        else:
            assert report['verdict'] == 'held' and b == a and not an.mipmapped
            # The rejected generated levels were already decoded by the converter's gate;
            # they are not falsely represented as present in this selected pack.
            assert report['quality']['verdict'] == 'held'
        row = dict(key=key, verdict=report['verdict'], reasons=report['reasons'],
            source_package_sha256=sha(b), output_package_sha256=sha(a),
            base_payload_exact=True, base_decoded_exact=True,
            base_rgba_sha256=pixel_digest(bpx), base_alpha_histogram=alpha_hist(bpx),
            levels=levels, extra_payload_bytes=len(an.payload)-len(bn.payload),
            extra_alloc32_bytes=((len(an.payload)+31)//32-(len(bn.payload)+31)//32)*32)
        rows.append(row)
        for record in prior['preload_records']:
            rr = room[record['room']]
            assert key not in rr['keys']
            rr['keys'].append(key)
            rr['extra_payload_bytes'] += row['extra_payload_bytes']
            rr['extra_alloc32_bytes'] += row['extra_alloc32_bytes']
    rr_blob = Path(pre['rr_package']).read_bytes()
    assert sha(rr_blob) == pre['rr_package_sha256']
    resident_blob = Path(pre['resident']).read_bytes()
    assert sha(resident_blob) == pre['resident_sha256']
    # Final read protects the frozen input after all qualification work.
    assert sha(source_path.read_bytes()) == pre['source_pack_sha256']
    result = dict(schema='re4dc-mipmap23-qualification-1', scope='source/host/package only',
        source_pack_sha256=sha(before), output_pack_sha256=sha(after),
        source_pack_bytes=len(before), output_pack_bytes=len(after), pack_delta_bytes=len(after)-len(before),
        same_member_keys=True, members=len(bp), selected=len(selected), changed=len(changed),
        unchanged=len(bp)-len(changed), unselected_exact=len(bp)-len(selected),
        all_41_shared_ganado_exact=True, unresolved_39_not_converted=True,
        actual_pack_default_off_exact=True, current_input_pack_before_after_exact=True,
        resident_input_unchanged=True, output_resident_file='none; retain current RR resident.bin at ' + pre['resident'],
        quality_gate_sha256=pre['quality_gate_sha256'], room_hold_manifest_sha256=pre['room_hold_manifest_sha256'],
        lower_levels_in_output=sum(len(r['levels']) for r in rows),
        generated_lower_levels_audited=sum(len(r['quality']['levels']) for r in conversion['rows']),
        extra_payload_bytes=sum(r['extra_payload_bytes'] for r in rows),
        extra_alloc32_bytes=sum(r['extra_alloc32_bytes'] for r in rows),
        room_preload_delta=dict(sorted(room.items())), rows=rows,
        limits=['Static preload allocation delta; not a measured room peak or fit.',
                'Non-preloaded/event/object consumers may load a key elsewhere.',
                'No new material sampling/minification, Flycast, full release or physical-console evidence.',
                'No performance improvement claimed.'],
        preflight_sha256=sha((ds/'input-preflight.json').read_bytes()),
        conversion_report_sha256=sha((ds/'conversion-report.json').read_bytes()))
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('members','selected','changed','unselected_exact',
        'pack_delta_bytes','extra_payload_bytes','extra_alloc32_bytes','lower_levels_in_output',
        'generated_lower_levels_audited','output_pack_sha256','room_preload_delta')},indent=2))

if __name__ == '__main__':
    main()
