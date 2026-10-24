#!/usr/bin/env python3
"""Read-only exact water-selector inventory and provenance/coverage consistency checks.
No conversion, asset emission, gate admission or resident data writing.
"""
from __future__ import annotations
import argparse, ast, hashlib, json, math, pathlib, re, struct, sys

ROOT = pathlib.Path(__file__).resolve().parents[5]
U32 = 1 << 32
MAX_FRAMES = 4096
MAX_MODULUS = 1 << 20
CONTRACT_PATHS = ('src/game/espgen45.cpp', 'src/game/water_ps2_ext.inc', 'include/esp.h',
                  'port/dreamcast/tools/convert_tpl.py', 'port/dreamcast/tools/prepare_native_ui.py',
                  'port/dreamcast/tools/d367/test12fx/fx_ps2_pack.py',
                  'port/dreamcast/game/platform/native_ui.cpp')

def source_contract(root=ROOT):
    return {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in CONTRACT_PATHS}



def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def selector_source(root=ROOT):
    path = root / 'src/game/espgen45.cpp'
    text = path.read_text()
    start = text.index('static u32 WaterPs2Pattern(')
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def rows(root=ROOT):
    text = (root / 'src/game/water_ps2_ext.inc').read_text()
    result = []
    for line in text.splitlines():
        if not re.match(r'\s*\{0x', line):
            continue
        values = line.split('//')[0].replace('{', '').replace('}', '').rstrip(' ,').split(',')
        require(len(values) == 25, 'unsupported ext row field layout')
        result.append({'index': len(result), 'room': int(values[0], 0), 'area': int(values[1]),
                       'texture': int(values[18], 0), 'level': int(values[21]),
                       'rate': int(values[22]), 'ptn0': int(values[23]), 'display': int(values[24])})
    return result


def effective(animation, n, rate):
    require(0 <= n <= MAX_FRAMES and 0 <= rate <= 255, 'descriptor/rate limit')
    if n <= 1 or animation is None or rate == 0:
        return 1, [1]
    raw = animation['frames']
    require(0 <= raw <= 65535, 'invalid animation Frames')
    frames = raw if 0 < raw <= n else n
    table = animation['frame_cnt']
    if animation['data_num']:
        require(len(table) >= raw + frames, 'sparse/truncated duration table')
        times = table[raw:raw + frames]
        require(all(type(t) is int and 0 <= t <= 255 for t in times), 'duration not u8')
    else:
        times = [1] * frames
    require(sum(times) * 32 <= MAX_MODULUS, 'bounded inventory modulus exceeded')
    return frames, times


def select(animation, n, rate, ptn0, tick, flip):
    """Arithmetic oracle, independently checked against the extracted C++ source."""
    require(1 <= flip <= 65535 and 0 <= ptn0 <= 255 and 0 <= tick < U32, 'selector scalar domain')
    frames, times = effective(animation, n, rate)
    if n <= 1 or animation is None or rate == 0 or sum(times) == 0:
        return 0
    units = ((tick * rate) & (U32 - 1)) % (sum(times) * 32)
    pattern = 0
    for pattern, time in enumerate(times):
        if units < time * 32:
            break
        units -= time * 32
    pattern = (pattern + ptn0) % frames
    return pattern - pattern % flip if frames >= flip else pattern


def legal_patterns(animation, n, rate, ptn0, flip):
    """All u32 ticks, not a sampled clock window; returns one tick witness/output.

    rate*tick modulo2^32 ranges over multiples of gcd(rate,2^32).
    For each nonzero duration interval, CRT yields its first reachable unit.
    The explicit modulus bound keeps the first CRT product below2^32.
    """
    select(animation, n, rate, ptn0, 0, flip)  # shared strict scalar validation
    frames, times = effective(animation, n, rate)
    if n <= 1 or animation is None or rate == 0 or not sum(times):
        return {0: 0}
    modulus = sum(times) * 32
    g = math.gcd(rate, U32)
    d = math.gcd(g, modulus)
    require(modulus * g < U32, 'CRT bound unavailable')
    out, start = {}, 0
    for i, time in enumerate(times):
        end = start + 32 * time
        unit = ((start + d - 1) // d) * d
        if unit < end:
            q = g // d
            k = 0 if q == 1 else (-unit // d * pow(modulus // d, -1, q)) % q
            product = unit + modulus * k
            require(product < U32 and product % g == 0, 'CRT witness bound')
            tick = (product // g * pow(rate // g, -1, U32 // g)) % (U32 // g)
            pattern = (i + ptn0) % frames
            if frames >= flip:
                pattern -= pattern % flip
            require(select(animation, n, rate, ptn0, tick, flip) == pattern, 'witness mismatch')
            out.setdefault(pattern, tick)
        start = end
    return out


class Reader:
    """One immutable read per referenced file; exact full-file and borrowed-span pins."""
    def __init__(self, base):
        self.base, self.cache, self.pins = pathlib.Path(base), {}, []

    def read(self, ref):
        path = (self.base / ref['file']).resolve()
        if path not in self.cache:
            self.cache[path] = path.read_bytes()
        full = self.cache[path]
        require(digest(full) == ref['sha256'], 'full file digest mismatch: ' + str(path))
        offset, size = ref.get('offset', 0), ref.get('length', len(full))
        require(type(offset) is int and type(size) is int and 0 <= offset <= len(full) and 0 < size <= len(full)-offset,
                'borrowed span outside file')
        data = full[offset:offset+size]
        require(digest(data) == ref['span_sha256'], 'span digest mismatch')
        self.pins.append({'file': str(path), 'sha256': digest(full), 'offset': offset,
                          'length': size, 'span_sha256': digest(data)})
        return data


def eff_texture(data, tex, ps2=False):
    """Original big-endian GC EFF or little-endian PS2 EFF; bounds every table."""
    endian = '<' if ps2 else '>'
    def read(fmt, off):
        length = struct.calcsize(endian + fmt)
        require(0 <= off <= len(data)-length, 'EFF field outside original span')
        return struct.unpack_from(endian + fmt, data, off)
    hdr = read('12I', 0)
    require(hdr[0] == 11 and all(x < len(data) for x in hdr[1:] if x), 'unsupported EFF header')
    def offsets(off, n):
        require(off != 0 and read('I', off)[0] == n, 'EFF table count mismatch')
        result = [off + read('I', off+4+4*i)[0] for i in range(n)]
        require(all(off+4+4*n <= x < len(data) for x in result), 'EFF target overlaps table/outside span')
        return result
    ids_off = hdr[1]
    require(ids_off >= 48, 'invalid texture ID table')
    n = read('I', ids_off)[0]
    require(0 < n <= MAX_FRAMES, 'texture ID count limit')
    ids = [read('H', ids_off+4+8*i)[0] for i in range(n)]
    require(len(set(ids)) == len(ids) and tex in ids, 'duplicate/missing texture ID')
    tpls, anms = offsets(hdr[6], n), offsets(hdr[7], n)
    index = ids.index(tex)
    t, a = tpls[index], anms[index]
    frame_count = read('I', t+4)[0]
    require(0 < frame_count <= MAX_FRAMES, 'TPL descriptor count limit')
    raw_frames = read('H', a+8)[0]
    data_num = read('B', a+12)[0]
    needed = raw_frames + (raw_frames if 0 < raw_frames <= frame_count else frame_count) if data_num else raw_frames
    animation_end = min(x for x in (*tpls, *anms, *hdr[1:], len(data)) if x > a)
    require(a+16+needed <= animation_end, 'animation bytes outside its component')
    animation = {'frames': raw_frames, 'data_num': data_num, 'frame_cnt': list(data[a+16:a+16+needed])}
    if ps2:
        require(read('I', t)[0] == 0x1000, 'PS2 TPL magic')
        start = read('I', t+8)[0]
        limit = min(x for x in (*tpls, *anms, *hdr[1:], len(data)) if x > t)
        require(start >= 12 and t+start+48*frame_count <= limit, 'PS2 descriptors outside TPL component')
        pictures = []
        for i in range(frame_count):
            off = t+start+48*i
            w, h, depth, inter = read('4H', off)
            require(w > 0 and h > 0 and depth in (8, 9) and inter & ~3 == 0, 'unsupported PS2 descriptor')
            io, po = read('2I', off+32)
            bits = 4 if depth == 8 else 8
            pixel_bytes, palette_bytes = (w*h*bits+7)//8, (96 if bits == 4 else 1024)
            require(min(io, po) >= start+48*frame_count and t+io+pixel_bytes <= limit and t+po+palette_bytes <= limit, 'PS2 payload outside TPL component')
            pictures.append({'descriptor_sha256': digest(data[off:off+48]),
                             'pixels_sha256': digest(data[t+io:t+io+pixel_bytes]),
                             'palette_sha256': digest(data[t+po:t+po+palette_bytes]),
                             'width': w, 'height': h, 'depth': depth, 'interlace': inter})
    else:
        # Reuse the established source TPL parser and image-key function; no converter is run.
        tools = ROOT / 'port/dreamcast/tools'
        sys.path.insert(0, str(tools))
        from convert_tpl import parse_tpl
        module = ast.parse((tools / 'prepare_native_ui.py').read_text())
        function = next(x for x in module.body if isinstance(x, ast.FunctionDef) and x.name == 'image_identity')
        import zlib
        namespace = {'struct': struct, 'zlib': zlib}
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'actual image_identity', 'exec'), namespace)
        # End at the next known EFF component start, preventing a TPL reading a later component.
        ends = [x for x in (*tpls, *anms, *hdr[1:], len(data)) if x > t]
        tpl = data[t:min(ends)]
        images = parse_tpl(tpl)
        require(len(images) == frame_count, 'source TPL count mismatch')
        pictures = []
        for im in images:
            key, payload = namespace['image_identity'](im)
            pictures.append({'key': key, 'width': im.width, 'height': im.height, 'format': im.format,
                             'source_image_sha256': digest(payload)})
    return {'texture': tex, 'tpl_offset': t, 'animation_offset': a, 'animation': animation,
            'animation_span_sha256': digest(data[a:a+16+needed]), 'pictures': pictures}


def resident_records(data):
    require(len(data) % 512 == 0, 'resident pack is not512-byte padded')
    result, padding, keys = [], False, set()
    for row in struct.iter_unpack('<4H2I', data):
        if not any(row):
            padding = True
            continue
        require(not padding, 'nonzero resident row after padding')
        room, w, h, fmt, crc, fnv = row
        # Room0 with nonzero metadata/key is CORE_PIN, not padding (native_ui4041).
        require(w and h and w <= 1024 and h <= 1024 and (crc or fnv), 'invalid resident record')
        identity = room, crc, fnv
        require(identity not in keys, 'duplicate/conflicting resident key')
        keys.add(identity)
        result.append(row)
    require(result == sorted(result, key=lambda x: (x[0], x[4], x[5])), 'resident records unsorted')
    return result


def preserve_resident(before, after, requirements, remap_before=b'', remap_after=b''):
    """Check a separately produced private candidate; never emit one."""
    old, new = resident_records(before), resident_records(after)
    require(remap_before == remap_after, 'resident remap changed')
    old_by_key = {(x[0], x[4], x[5]): x for x in old}
    new_by_key = {(x[0], x[4], x[5]): x for x in new}
    require(all(new_by_key.get(k) == v for k, v in old_by_key.items()), 'old room record lost/changed')
    required = set(requirements)
    require(all(x in new for x in required), 'required water key missing or metadata differs')
    permitted = set(old) | required
    require(set(new) <= permitted, 'unrequested resident key addition')
    return {'old_records': len(old), 'candidate_records': len(new), 'required_records': len(required)}


def audit(manifest, base, root=ROOT):
    require(manifest['schema'] == 1 and manifest['option'] == 'waterres24-private-off', 'unsupported private option')
    require(manifest['selector_sha256'] == digest(selector_source(root).encode()), 'selector source changed')
    require(manifest['source_contract'] == source_contract(root), 'source contract changed')
    reader, result = Reader(base), []
    required_records, image_keys = {}, {}
    actual_rows = rows(root)
    rooms = manifest['rooms']
    level = manifest['renderer_level']
    require(rooms and len(set(rooms)) == len(rooms) and set(rooms) <= {0x10c, 0x10d, 0x10e}, 'room scope unsupported')
    require(type(level) is int and 0 <= level <= 2, 'renderer level unsupported/unproven')
    expected_scope = {r['index'] for r in actual_rows if r['room'] in rooms and r['texture'] != 0xf7 and r['level'] >= level}
    require(set(manifest['row_scope']) == expected_scope and len(manifest['row_scope']) == len(expected_scope), 'room/quality rows omitted or duplicated')
    seen_rows = set()
    for entry in manifest['entries']:
        index = entry['row_index']
        require(type(index) is int and 0 <= index < len(actual_rows) and index not in seen_rows, 'missing/duplicate row identity')
        seen_rows.add(index)
        row = actual_rows[index]
        require(row['texture'] != 0xf7, 'untextured base has no package requirement')
        source_bytes, ps2_bytes = reader.read(entry['source_eff']), reader.read(entry['ps2_eff'])
        source, ps2 = eff_texture(source_bytes, row['texture']), eff_texture(ps2_bytes, row['texture'], True)
        legal = legal_patterns(source['animation'], len(source['pictures']), row['rate'], row['ptn0'], manifest['flip'])
        receipt_bytes = reader.read(entry['conversion_receipt'])
        receipt = json.loads(receipt_bytes)
        require(receipt['schema'] == 1 and receipt['profile'] == 'fx_ps2_pack.py:frame-mod-v1', 'conversion profile unproven')
        converter = reader.read(entry['converter'])
        require(digest(converter) == digest((root/'port/dreamcast/tools/d367/test12fx/fx_ps2_pack.py').read_bytes()), 'converter source differs')
        require(receipt['source_eff_sha256'] == digest(source_bytes) and receipt['ps2_eff_sha256'] == digest(ps2_bytes)
                and receipt['converter_sha256'] == digest(converter), 'conversion receipt input mismatch')
        bindings = receipt['bindings']
        require(len({b['source_key'] for b in bindings}) == len(bindings), 'duplicate conversion binding')
        used = []
        for frame, tick in sorted(legal.items()):
            im = source['pictures'][frame]
            require(im['key'] not in image_keys or image_keys[im['key']] == im['source_image_sha256'], 'source image identity collision')
            image_keys[im['key']] = im['source_image_sha256']
            crc, fnv = (int(x, 16) for x in im['key'].split('-'))
            record = (row['room'], im['width'], im['height'], im['format'], crc, fnv)
            identity = row['room'], crc, fnv
            require(identity not in required_records or required_records[identity] == record, 'required key metadata conflict')
            required_records[identity] = record
            binding = next((x for x in bindings if x['source_key'] == im['key']), None)
            require(binding is not None, 'selected source key lacks ancestry binding')
            target_frame = frame % len(ps2['pictures'])
            require(binding['texture'] == row['texture'] and binding['ps2_frame'] == target_frame
                    and binding['ps2_picture'] == ps2['pictures'][target_frame], 'PS2 descriptor/payload ancestry mismatch')
            payload = reader.read(entry['packages'][im['key']])
            require(digest(payload) == binding['package_sha256'], 'converted package digest mismatch')
            # Existing package reader bounds/CRC contract; normalization stays in RAM and is never written.
            sys.path.insert(0, str(ROOT/'port/dreamcast/tools'))
            from convert_tpl import canonical_native_crc
            canonical_native_crc(payload)
            used.append({'pattern': frame, 'tick_witness': tick, **im, 'ps2_frame': target_frame,
                         'package_sha256': digest(payload)})
        result.append({'row': row, 'source': source, 'ps2': ps2, 'selected': used})
    require(seen_rows == set(manifest['row_scope']), 'declared scope/entries differ')
    coverage = {'status': 'NOT_RUN', 'reason': 'no separately prepared candidate supplied; no residency/memory claim'}
    if 'resident' in manifest:
        resident = manifest['resident']
        coverage = preserve_resident(reader.read(resident['before']), reader.read(resident['candidate']),
                                     required_records.values(), reader.read(resident['remap_before']), reader.read(resident['remap_candidate']))
        coverage['status'] = 'RECORD_COVERAGE_ONLY'
    return {'schema': 1, 'claim': 'read-only ancestry consistency and complete u32 selector inventory within declared rows; no asset-origin/admission/residency or memory PASS',
            'source_pin': digest(selector_source(root).encode()), 'rows': result, 'input_pins': reader.pins,
            'required_resident_records': sorted(required_records.values()), 'resident_record_coverage': coverage,
            'source_owner_binding': 'UNPROVEN', 'conversion_replayed': False, 'origin_admitted': False,
            'current_loaded_payload_binding': False, 'resident_memory_qualified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=pathlib.Path)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        output = audit(json.loads(args.manifest.read_text()), args.manifest.parent)
    except (ValueError, KeyError, TypeError, struct.error, OSError, StopIteration) as exc:
        parser.exit(2, 'REFUSED: '+str(exc)+'\n')
    require(args.output.suffix == '.json', 'report output must be a new JSON file')
    with args.output.open('x') as report:
        report.write(json.dumps(output, indent=2)+'\n')


if __name__ == '__main__':
    main()
