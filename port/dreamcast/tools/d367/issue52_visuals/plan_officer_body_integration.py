#!/usr/bin/env python3
"""Metadata-only integration plan for frozen47d officer BODY assets.

Reads exact originals/candidate; hashes hypothetical outputs without writing any
archive, package, pack, image, stage or guest. Explicit plan flag and new JSON.
"""
from __future__ import annotations
import argparse, bisect, hashlib, json, struct, sys, zlib
from pathlib import Path
TOOLS = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(TOOLS), str(TOOLS / 'd367')]
import room_smd
DAR_SHA = '4abfcc88bb61989fadc4759d885879da07b9e670d8c38206620d57912482c37d'
PACK_SHA = '18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef'
PLAN_SHA = '630dd8ea65cef68de30102cd7a109017848a4cf4035fefa2fe60650c0d2215ce'
EMITTER_SHA = 'b91a6d0498aff01be49ebe3d9e7b672b52313afe552f55496fb8abd4cbfd6167'
SOURCE47 = '47d98481d50b38d07d27bf114d28fdb02f4d7d6f'
FLAGS = ['TEX_PACK', 'TEX_PACK_WINDOW', 'TEX_REF_SELFKEY', 'TEX_RESIDENT',
         'TEX_PAYLOAD_CRC', 'UI_VRAM', 'VRAM_PAGES', 'VRAM_PAGES_VQ_ONLY',
         'CAST_MIPMAP', 'TEX_PAL4_ALPHA', 'QUALITY_ASSETS', 'PVR_PIPELINE',
         'SS_HOLD_RESTORE', 'SS_WINDOW_HOLD_RESTORE', 'MESH_TEXTURES']
BUDGET = 4 * 1024**2


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_id(path):
    with path.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def require(value, why):
    if not value:
        raise ValueError(why)


def pack_rows(path):
    with path.open('rb') as f:
        head = f.read(2048)
        magic, version, count, index_at, data_at, crc = struct.unpack_from('<8s5I', head)
        require(magic == b'RE4PAK1\0' and version == 1 and 1 <= count <= 8192, 'pack header')
        require(index_at == 2048 and data_at == 2048 + ((count * 16 + 2047) // 2048) * 2048, 'pack index extent')
        index = f.read(data_at - index_at)
        require(zlib.crc32(index) & 0xffffffff == crc, 'pack index CRC')
        rows = list(struct.iter_unpack('<4I', index[:16 * count]))
        require(rows == sorted(rows) and len({r[:2] for r in rows}) == count, 'pack key order')
        off = data_at
        for a, b, start, size in rows:
            require(start == off and size > 0, 'canonical baseline pack layout')
            off += (size + 2047) // 2048 * 2048
            f.seek(start)
            require(f.read(8) == b'RE4DCTX\0', 'member package magic')
        require(off == path.stat().st_size, 'pack total size')
    return head, index, rows


def expected_pack(path, additions):
    """Return only metadata. Two hash methods consume a virtual canonical pack."""
    head, index, original = pack_rows(path)
    old = {r[:2]: r[2:] for r in original}
    require(not set(additions) & set(old), 'new key collides with baseline')
    keys = sorted(set(old) | set(additions))
    count = len(keys)
    require(count <= 8192, 'pack capacity')
    data_at = 2048 + ((count * 16 + 2047) // 2048) * 2048
    new_index, offset, new_rows = bytearray(), data_at, []
    # Segments describe virtual bytes; no transformed pack is materialized.
    segments = []
    for key in keys:
        size = len(additions[key]) if key in additions else old[key][1]
        new_index += struct.pack('<4I', *key, offset, size)
        new_rows.append((*key, offset, size))
        segments.append((offset, size, additions.get(key), None if key in additions else old[key][0]))
        offset += (size + 2047) // 2048 * 2048
    new_index += bytes(data_at - 2048 - len(new_index))
    new_head = b'RE4PAK1\0' + struct.pack('<5I', 1, count, 2048, data_at, zlib.crc32(new_index) & 0xffffffff)
    new_head += bytes(2048 - len(new_head))
    # Sequential canonical writer-equivalent SHA, read only.
    h = hashlib.sha256(new_head + new_index)
    member_inventory = hashlib.sha256()
    with path.open('rb') as f:
        for start, size, blob, origin in segments:
            if blob is None:
                f.seek(origin)
                blob = f.read(size)
                require(len(blob) == size, 'short source package')
                member_inventory.update(struct.pack('<II', origin, size) + bytes.fromhex(sha(blob)))
            h.update(blob)
            h.update(bytes((-size) % 2048))
    sequential_sha = h.hexdigest()
    # Independent reader: parse recomputed index and random-read output extents
    # at 65521-byte boundaries, crossing package/index/padding boundaries.
    parsed = [struct.unpack_from('<4I', new_index, i * 16) for i in range(count)]
    starts = [row[2] for row in parsed]
    def virtual_read(f, at, size):
        result = bytearray()
        while size:
            if at < data_at:
                prefix = new_head + new_index
                n = min(size, data_at - at)
                result.extend(prefix[at:at + n])
            else:
                i = bisect.bisect_right(starts, at) - 1
                k0, k1, start, length = parsed[i]
                limit = parsed[i + 1][2] if i + 1 < len(parsed) else offset
                n = min(size, limit - at)
                available = max(0, min(n, start + length - at))
                if available:
                    key = (k0, k1)
                    if key in additions:
                        result.extend(additions[key][at - start:at - start + available])
                    else:
                        old_at, old_size = old[key]
                        require(length == old_size, 'independent preserved size')
                        f.seek(old_at + at - start)
                        piece = f.read(available)
                        require(len(piece) == available, 'independent short read')
                        result.extend(piece)
                result.extend(bytes(n - available))
            at += n
            size -= n
        return bytes(result)
    ref = hashlib.sha256()
    with path.open('rb') as f:
        for at in range(0, offset, 65521):
            ref.update(virtual_read(f, at, min(65521, offset - at)))
    require(ref.hexdigest() == sequential_sha, 'independent virtual pack SHA mismatch')
    return dict(expected_bytes=offset, expected_sha256=sequential_sha,
                independent_virtual_reader_sha256=ref.hexdigest(),
                expected_index_sha256=sha(new_index), expected_index_crc32=zlib.crc32(new_index) & 0xffffffff,
                expected_count=count, original_count=len(original), index_bytes=len(new_index),
                baseline_index_sha256=sha(index), preserved_member_count=len(original),
                preserved_member_inventory_sha256=member_inventory.hexdigest(),
                preserved_member_inventory_encoding='Baseline key-sorted SHA stream: LE u32 original_offset,size +32byte SHA(package); baseline index binds keys.',
                added_rows=[dict(key='%08x-%08x' % r[:2], offset=r[2], bytes=r[3]) for r in new_rows if r[:2] in additions],
                growth_bytes=offset - path.stat().st_size,
                policy='Add three keys; retain all6501 baseline members byte-exact, including old body keys. No unrelated garbage collection.')


def plan(dar_path, pack_path, bundle, source_plan, flags_path, binding_path):
    baseline = dar_path.read_bytes()
    require(sha(baseline) == DAR_SHA, 'baseline DAR identity')
    pack_identity = file_id(pack_path)
    require(pack_identity['sha256'] == PACK_SHA, 'baseline pack identity')
    frozen = source_plan.read_bytes()
    require(sha(frozen) == PLAN_SHA, 'frozen605 plan identity')
    body = json.loads(frozen)
    emission = json.loads((bundle / 'emission.json').read_bytes())
    require(emission['emitter_sha256'] == EMITTER_SHA and emission['frozen_plan_sha256'] == PLAN_SHA, 'frozen47 emission identity')
    expected_assets = {r['path']: r for r in emission['files']}
    wanted_assets = {'r100-body-25.tpl': dict(sha256=body['transformed_TPL_sha256'], bytes=256)}
    wanted_assets.update({'tex/' + row['new_key'] + '.re4tex': dict(sha256=row['package_sha256'], bytes=row['package_bytes']) for row in body['pictures']})
    require(set(expected_assets) == set(wanted_assets), 'frozen47 asset set')
    require(emission['source_inputs'] == body['inputs'], 'frozen605 source inputs')
    for name, row in expected_assets.items():
        require(all(row[field] == wanted_assets[name][field] for field in ('sha256', 'bytes')), 'candidate asset differs from frozen605: ' + name)
    assets = {}
    for name, row in expected_assets.items():
        data = (bundle / name).read_bytes()
        require(len(data) == row['bytes'] and sha(data) == row['sha256'], 'emitted asset changed: ' + name)
        assets[name] = data
    tpl = assets['r100-body-25.tpl']
    require(len(tpl) == 256 and sha(tpl) == body['transformed_TPL_sha256'], 'body TPL identity')
    kind, size, dest, archive_at = struct.unpack_from('<4I', baseline, 32)
    require((kind, dest) == (0, 0) and archive_at + size <= len(baseline), 'active DAR extent')
    archive = baseline[archive_at:archive_at + size]
    entries = room_smd.tagged_entries(archive, '<')
    # Independent table interpretation, without room_smd end calculations.
    count = int.from_bytes(archive[:4], 'little')
    offsets = [int.from_bytes(archive[16 + 4 * i:20 + 4 * i], 'little') for i in range(count)]
    for i, (tag, a, b) in enumerate(entries):
        end = min([n for n in offsets if n > offsets[i]] + [len(archive)])
        require((a, b) == (offsets[i], end), 'independent archive member interpretation')
    tag, start, end = entries[0x25 - 4]
    original_tpl = archive[start:end]
    require(tag == b'TPL\0' and len(original_tpl) == 256 and sha(original_tpl) == body['original_TPL_sha256'], 'selected body TPL')
    for slot in (0x24, 0x26):
        a, b = entries[slot - 4][1:]
        require(sha(archive[a:b]) == body['inputs']['r100-active-%02x.bin' % slot], 'unchanged body BIN identity')
    changed = [i for i, (a, b) in enumerate(zip(original_tpl, tpl)) if a != b]
    allowed = body['allowed_TPL_ranges']
    require(len(changed) == 32 and all(any(a <= i < b for a, b in allowed) for i in changed), 'TPL patch scope')
    at = archive_at + start
    # Expected-only hashes; no archive output object leaves memory or is written.
    expected_dar = sha(baseline[:at] + tpl + baseline[at + len(tpl):])
    reference = bytearray(baseline)
    for i in changed:
        reference[at + i] = tpl[i]
    require(sha(reference) == expected_dar, 'independent sparse DAR hash')
    patched_archive = bytes(reference[archive_at:archive_at + size])
    members = []
    for slot, (tag, a, b) in enumerate(entries, 4):
        before, after = archive[a:b], patched_archive[a:b]
        require(slot == 0x25 or before == after, 'unrelated archive member changed')
        members.append(dict(slot=slot, tag=tag.rstrip(b'\0').decode('ascii'), archive_offset=a,
                            DAR_offset=archive_at + a, bytes=b - a, baseline_sha256=sha(before),
                            expected_sha256=sha(after), unchanged=before == after))
    ntr_rows = []
    for tag, a, b in entries:
        if tag != b'NTR\0':
            continue
        ntr = archive[a:b]
        magic, version, n, stride, crc, old_size, active_size = struct.unpack_from('<8s6I', ntr)
        require(magic == b'R4NTBL\0\0' and version == 1 and stride == 12 and active_size == size and old_size > size, 'NTR header')
        require(zlib.crc32(ntr[32:32 + n * 12]) & 0xffffffff == crc, 'NTR CRC')
        for i in range(n):
            rec, hdr, tbase = struct.unpack_from('<3I', ntr, 32 + i * 12)
            if start <= rec < end:
                require(start <= hdr < end and tbase == start, 'body NTR binding')
                p = patched_archive[rec:rec + 32]
                h = patched_archive[hdr:hdr + 36]
                require(p[:8] == b'R4NREF\0\0' and (rec & 31) == 0, 'native reference record')
                w, height, fmt = struct.unpack_from('<3I', p, 16)
                require((height, w, fmt) == struct.unpack_from('<HHI', h), 'native descriptor dimensions')
                require(tbase + struct.unpack_from('<I', h, 8)[0] == rec and fmt == 14 and not any(h[33:36]), 'NTR record/header contract')
                ntr_rows.append(dict(row=i, archive_record=rec, archive_header=hdr, archive_TPL=tbase,
                                     key='%08x-%08x' % struct.unpack_from('<2I', p, 8), shape=[w, height], source_format=fmt))
    require(len(ntr_rows) == 3, 'all body native references registered')
    additions = {tuple(int(n, 16) for n in Path(name).stem.split('-')): data for name, data in assets.items() if name.startswith('tex/')}
    require(len(additions) == 3, 'body package count')
    pack = expected_pack(pack_path, additions)
    prior_rows = []
    for folder in ('chandelier-atlas-candidate01', 'officer-head-candidate01', 'lake-candidate01'):
        tex = bundle.parent / folder / 'tex'
        for path in sorted(tex.glob('*.re4tex')):
            key = tuple(int(n, 16) for n in path.stem.split('-'))
            require(key not in additions or path.read_bytes() == additions[key], 'collision with preserved lane candidate')
            prior_rows.append(dict(candidate=folder, key=path.stem, sha256=sha(path.read_bytes()),
                                   collision_with_body=key in additions))
    pack['prior_lane_candidate_collisions'] = prior_rows
    pack['final_combined_pack_collision_gate'] = 'NOT RUN: main must repeat against selected whole-pack/mipmap/atlas/rectangle composition; original public pack and retained own candidates only qualified here.'
    knob_text = flags_path.read_text()
    knobs = dict(line.split('=', 1) for line in knob_text.splitlines() if '=' in line and line.split('=', 1)[0] in FLAGS)
    require(knobs.get('TEX_PACK') == '1' and knobs.get('TEX_REF_SELFKEY') == '1', 'baseline runtime flags')
    binding = json.loads(binding_path.read_bytes())
    require(binding['source'] == 'fe0efcddc736c49861b51988593629ca04ced336' and len(binding['files']) == 15 and all(r['exact'] for r in binding['files']), 'release program/14 overlay binding')
    sources = [Path(__file__), TOOLS / 'room_smd.py', TOOLS / 'd367/texpack.py',
               TOOLS.parent.parent.parent / 'src/st1/r100.cpp',
               TOOLS.parent / 'game/platform/native_ui.cpp', TOOLS.parent / 'room/texture_package.cpp']
    return dict(schema='issue52-officer-body-metadata-integration-plan-1', source_candidate_commit=SOURCE47,
        frozen605_commit=emission['frozen_source_commit'], frozen_plan_sha256=PLAN_SHA,
        candidate_bundle=str(bundle), candidate_assets=list(expected_assets.values()),
        baseline_DAR=file_id(dar_path), baseline_pack=pack_identity,
        active_archive=dict(DAR_offset=archive_at, bytes=size, baseline_sha256=sha(archive),
                            expected_sha256=sha(patched_archive), member_count=len(entries), suffix_bytes=len(baseline) - archive_at - size,
                            outside_active_archive_sha256=sha(baseline[:archive_at] + baseline[archive_at + size:])),
        TPL=dict(slot=0x25, archive_offset=start, DAR_offset=at, bytes=256,
                 baseline_sha256=sha(original_tpl), expected_sha256=sha(tpl), changed_bytes=32,
                 changed_offsets_in_TPL=changed, changed_offsets_in_DAR=[at + i for i in changed],
                 allowed_ranges_in_TPL=allowed,
                 fields=[dict(image=i, header=36 + i * 36, native_record=160 + i * 32,
                              permitted='header height/width + record key,width,height only; sourceformat14/wrap/pointers retained') for i in range(3)]),
        expected_DAR=dict(bytes=len(baseline), sha256=expected_dar, independent_sparse_patch_sha256=sha(reference),
                          no_archive_repack=True, changes_outside_TPL=0),
        members=members, NTR=dict(unchanged=True, CRC_unchanged=True, body_rows=ntr_rows),
        global_pack=pack, model_contracts=body['models'],
        unchanged_slots=dict(body_BIN=[0x24, 0x26], head_BIN=[0x27, 0x29], head_TPL=[0x28, 0x2a], motion=[0x2b, 0x2c],
                             guarantee='Every archive member except TPL25 SHA-exact; includes body geometry, normals, UVs, weights, materials, heads, motion and all remaining bytes.'),
        runtime=dict(resolved_knobs=knobs, resolved_knobs_file=file_id(flags_path),
                     format_contract='Source TPL format14 names external native picture; package format0 RGB565/payload1 twiddled/no mipmaps. Rectangular power-of-two uncompressed16 accepted without a new format knob.',
                     identity_contract='Existing NTR3 rows remain valid after coherent header/record shape update; TEX_REF_SELFKEY1 is retained baseline fallback, not a substitute for failed NTR.',
                     pack_contract='TEX_PACK1 uses sorted RE4PAK1 global index; new keys absent from6501-entry original. TEX_PACK_WINDOW0 retained.',
                     allocation_contract='UI_VRAM1 / VRAM_PAGES_VQ_ONLY1 non-VQ >2KiB path accepts raw payload size. Actual free/largest block, pins, eviction and allocator overhead require target measurement.',
                     program_binding=file_id(binding_path), baseline_programs=binding,
                     future_program='Main must freeze actual control/candidate program+ELF+14overlays/resolved flags; public release identities above are reference only. No claim currentQA or future integration equals Test21.',
                     required_candidate_overrides=dict(SS_WINDOW_HOLD_RESTORE=0),
                     restoration_override_reason='User requires menu-window restoration candidate disabled after +102 requests/+168032B inventory cycle; SS_WINDOW_HOLD_RESTORE0 is the separate experimental guard. Historical SS_HOLD_RESTORE1 is a different existing feature and is not changed here; no performance improvement claim.',
                     recipe_changes='None; do not copy historical resolved knobs blindly. Main freezes actual control/candidate; no new format feature needed and restoration candidate stays disabled.'),
        residency=dict(previous_three_unique_payload_bytes=73728, new_three_unique_payload_bytes=212992,
                       delta_unique_payload_bytes=139264, per_texture_payload_bytes=[65536,16384,131072],
                       largest_required_texture_block=131072, new_package_metadata_bytes=432,
                       shared='Both officers share TPL25/three keys; do not double-count payload for two actors.',
                       caution='Source payload cost only, not measured VRAM/traffic. Old keys retained globally may also remain resident through other owners. Determine actual coexistence and allocator overhead on target.'),
        independent_checks=['old archive table independently parsed', 'full expectedDAR SHA equals sparse32byte-patch SHA',
                            'virtual canonical sorted pack SHA equals independent65521byte reader SHA',
                            'all6501 baseline package bytes retained and inventory-hashed', 'NTR3 descriptor/record bindings valid and table unchanged'],
        target_plan=dict(state='QUEUED_NO_ALLOCATION',
          preflight=['Main allocates disk/start/runtime floors and evidence cap; do not reuse earlier guest allowance.',
                     'Freeze final combined asset/program/ELF/14overlay identities and effective flags; all other lane candidates independently recorded.',
                     'Recheck global key collisions against final merged pack, quality/Standard aliases and loose paths; never silently replace a key.',
                     'Apply only256B TPL at manifestDAR offset; preserve DAR/ISO extents. Repack tex.pak deterministically in separate output after allocation; larger pack needs ISO file-table update, not in-place sector overwrite.',
                     'Independent output parse/SHA vs expected manifest; all old package bytes and all nonTPL archive members exact; no head/lake/chandelier candidate silently folded in.'],
          target_look=['Use same frozen program and normal source-defined r100 opening/car camera route for control and body-only candidate. Record save/flags/seed/source-frame/camera/input timeline.',
                       'Capture full scene and body crops for each officer, uniform, sleeves, trousers, shoes and shoulder seams under matching views/lighting; compare against actual pairedPS2 source pictures.',
                       'Heads retain baseline appearance in body-only test; head repair is separate. Check idle/movement/joints/attachment silhouettes for regression without claiming historical weights repaired.'],
          residency=['Record load/first drawn three keys, package/header/dimensions/format, cache bind/upload success, VRAM free/largest block/minima, pinned bytes, uploadfail/eviction/retry/missing counters at room entry, idle and repeat camera pass.',
                     'Prove allthree newkeys actually draw. Watch131072B contiguous allocation, metadata/heap, coexistence of old/newkeys and repeated loads. Stop/reject missing officers/materials, allocation failures or new thrash.',
                     'If timing is allocated, report scene/program/assets/framewindow/resolvedknobs and hardware vs Flycast separately; no performance improvement inferred from source sampling.'],
          acceptance=['Source/host plan PASS only. DAR/pack emission NOT RUN. ISO/release checks NOT RUN. Candidate Flycast NOT RUN. Physical Dreamcast appearance/capacity/performance acceptance NOT RUN.']),
        source_files=[file_id(p) for p in sources],
        limits=['JSON metadata only; no DAR/package/pack/image writes or guest.', 'Main retains integration decision and Claude production merge/release ownership.',
                'Previous47d bundle and lake/head/chandelier candidates preserved; no shared runtime/converter/recipe edits.'])


def output_guard(report, bundle):
    require(report.suffix == '.json', 'metadata output must be JSON')
    require(not report.exists(), 'refusing existing metadata output')
    require(not report.resolve().is_relative_to(bundle.resolve()), 'preserve frozen47 bundle directory')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ['dar', 'pack', 'bundle', 'source-plan', 'flags', 'binding', 'report']:
        ap.add_argument('--' + name, required=True, type=Path)
    ap.add_argument('--enable-integration-plan', action='store_true')
    args = ap.parse_args()
    require(args.enable_integration_plan, 'plan disabled; explicit flag required')
    output_guard(args.report, args.bundle)
    result = plan(args.dar, args.pack, args.bundle, args.source_plan, args.flags, args.binding)
    data = (json.dumps(result, indent=2) + '\n').encode()
    require(len(data) * 3 + 1024**2 <= BUDGET, 'metadata/three copies+tool allowance exceed4MiB')
    with args.report.open('xb') as f:
        f.write(data)
    require(args.report.read_bytes() == data, 'metadata readback')
    print(json.dumps(dict(report=str(args.report), bytes=len(data), expected_DAR=result['expected_DAR'],
                          global_pack=result['global_pack']), indent=2))


if __name__ == '__main__':
    main()
