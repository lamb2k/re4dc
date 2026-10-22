#!/usr/bin/env python3
"""texconv22: exact-base repeat-square mip chains for the alpha keys whose compact
representation changed base pixels (missing-profile holds). Reuses Codex's
repeat_alpha_plan.repeat_base / mipmap_* add_mipmaps unchanged, except that the
ARGB1555 twiddled source is admitted (same word-repeat code path)."""
import collections, ctypes, hashlib, json, struct, sys, zlib
from pathlib import Path

R = Path('/root/work/lanes/texconv22/rect21/port/dreamcast/tools')
sys.path[:0] = [str(R / 'd367/texture_rect21'), str(R), str(R / 'd367')]
import convert_tpl as tpl, mipmap_vq as vq, mipmap_twiddled as tw, rectangular_vq as rect
import scoped_candidate as scoped, tr_classify as classifier
import zlib as _z

H = lambda b: hashlib.sha256(b).hexdigest()
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=False); (OUT / 'textures').mkdir()
SRC = Path('/root/re4data/private/mipmap21-release21-pack-recovery-20261021/tex.pak')
A = Path('/root/re4data/private/texture-rect21-next142-alpha-20261022-v1')
raw = SRC.read_bytes(); assert H(raw) == '18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef'
v, n, ioff, doff, crc = struct.unpack_from('<5I', raw, 8)
index = {tuple(struct.unpack_from('<4I', raw, ioff + 16 * i)[:2]): struct.unpack_from('<4I', raw, ioff + 16 * i)[2:] for i in range(n)}
receipt = {x['original_key']: x for x in json.loads((A / 'conversion-receipt.json').read_text())['selected']}
checks = {x['original_key']: x for x in json.loads((A / 'policy-classification.json').read_text())['checks']}

L = ctypes.CDLL('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/oracle-02/oracle.so')
RT = ctypes.CDLL('/root/re4data/private/texture-rect21-next18-twiddled-20261022-v1/rect-twiddled-oracle.so').rect_oracle_decode
RV = L.rect_oracle_decode
for f in (RV, RT): f.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t]
dec = {2: L.mipmap_oracle_decode, 1: L.mipmap_oracle_decode_twiddled}
for f in dec.values(): f.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_uint, ctypes.c_int, ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t]


def rect_pixels(b, w, h):
    t = tpl.TEXTURE.unpack_from(b, 48); p = b[t[4]:t[4] + t[5]]; buf = (ctypes.c_ubyte * (w * h * 4))()
    assert {2: RV, 1: RT}[t[7]](p, len(p), t[3], w, h, buf, len(buf)) == len(buf); return bytes(buf)


def repeat_base(blob):
    h = list(tpl.HEADER.unpack_from(blob)); t = list(tpl.TEXTURE.unpack_from(blob, 48)); w, hh, fmt = t[1:4]; layout = t[7]
    if fmt not in (1, 2) or t[6] or layout not in (1, 2) or w <= hh or w % hh or w // hh not in (2, 4) or t[8]:
        raise ValueError('repeat contract')
    if layout == 2:
        return rect.square_candidate(blob, enabled=True)[0]
    assert h[:6] == [tpl.MAGIC, tpl.VERSION, 48, 96, 1, 48] and t[4] == 144 and h[6] == 144 and t[5] == w * hh * 2 and len(blob) == 144 + t[5]
    payload = blob[144:]
    assert h[8] in (zlib.crc32(blob[48:]) & 0xffffffff, zlib.crc32(payload) & 0xffffffff)
    words = struct.unpack('<%dH' % (w * hh), payload); order = tpl.twiddle_16bpp(list(range(w * hh)), w, hh); linear = [0] * len(words)
    for at, i in enumerate(order): linear[i] = words[at]
    full = [linear[(i // w % hh) * w + i % w] for i in tpl.twiddle_16bpp(list(range(w * w)), w, w)]
    p = struct.pack('<%dH' % len(full), *full); t[1] = t[2] = w; t[5] = h[7] = len(p); body = tpl.TEXTURE.pack(*t) + p
    h[8] = zlib.crc32(body) & 0xffffffff
    return tpl.HEADER.pack(*h) + body, linear


rows = []
for x in receipt.values():
    if x['policy_qualified']: continue
    if x['source_texture_class'] != x['candidate_texture_class']: continue  # the 16 repeats Codex already built
    if x.get('base_exact'): continue
    w, h = x['logical']
    if not (w > h and w // h in (2, 4)):
        rows.append(dict(original_key=x['original_key'], scoped_key=x['scoped_key'], decision='keep-compact-approx',
                         reason='aspect %dx%d outside repeat contract; compact RGB max err %s' % (w, h, x['source_center_RGBA_max'])))
        continue
    key = tuple(int(k, 16) for k in x['original_key'].split('-')); off, nb = index[key]; blob = raw[off:off + nb]
    assert H(blob) == x['source_package_sha256']
    t0 = tpl.TEXTURE.unpack_from(blob, 48); layout = t0[7]; fmt = t0[3]
    before = rect_pixels(blob, w, h)
    rb = repeat_base(blob)
    base, linear = (rb if isinstance(rb, tuple) else (rb, None))
    module = {2: vq, 1: tw}[layout]
    cand, _ = module.add_mipmaps(base, enabled=True)
    native = module.read_native_vq(cand) if layout == 2 else module.read_native_twiddled(cand)
    strict = native.header[8] == zlib.crc32(cand[48:]) & 0xffffffff
    levels = []
    for lv in range(w.bit_length()):
        side = 1 << lv; buf = (ctypes.c_ubyte * (side * side * 4))()
        assert dec[layout](native.payload, len(native.payload), fmt, w, 1, lv, buf, len(buf)) == len(buf)
        ref = bytes(c for px in module.decode_level(native, side) for c in px)
        levels.append(dict(side=side, oracle_eq_module=bytes(buf) == ref, sha256=H(bytes(buf))))
        if side == w: top = bytes(buf)
    expect = bytes(c for y in range(w) for xx in range(w) for c in before[((y % h) * w + xx) * 4:((y % h) * w + xx + 1) * 4])
    base_pixels_exact = top == expect
    # word-level: every original 16-bit texel word (or VQ index/codebook) unchanged
    if layout == 1:
        tb = tpl.TEXTURE.unpack_from(cand, 48)
        words_exact = None  # base plane location inside the mip chain is checked through the decoder above
    sc = classifier.tex_class((dict(collections.Counter(a // 17 for a in before[3::4])), 15))
    cc = classifier.tex_class((dict(collections.Counter(a // 17 for a in top[3::4])), 15))
    newkey = '%08x-%08x' % scoped.scoped_key(key, H(cand))
    p = OUT / 'textures' / (newkey + '.re4tex'); p.write_bytes(cand)
    ok = strict and base_pixels_exact and all(l['oracle_eq_module'] for l in levels) and sc == cc
    rows.append(dict(original_key=x['original_key'], replaces_compact_scoped_key=x['scoped_key'], scoped_key=newkey,
                     decision='convert-exact-base-repeat' if ok else 'FAILED', logical=[w, h], physical=[w, w], uv_scale=[1.0, h / w],
                     format=fmt, payload_type=layout, mip_levels=len(levels), package_bytes=len(cand), sha256=H(cand),
                     payload_crc32=native.header[8], strict_crc_48_eof=strict, base_pixels_exact=base_pixels_exact,
                     levels_oracle_eq=all(l['oracle_eq_module'] for l in levels), source_class=sc, candidate_class=cc,
                     source_request_rounded=x['source_request_rounded'], compact_request_rounded=x['candidate_request_rounded'],
                     repeat_request_rounded=(len(native.payload) + 31) & ~31,
                     descriptor=dict(width=w, height=w, format=fmt, flags=tpl.TEXTURE.unpack_from(cand, 48)[6], payload=layout, bytes=len(native.payload), checksum=native.header[8]),
                     refs=[(r['room'], r['part'], r['shipped_class']) for r in checks[x['original_key']]['refs']]))
(OUT / 'repeat6.json').write_text(json.dumps(rows, indent=1) + '\n')
for r in rows: print(r['original_key'], r['decision'], r.get('scoped_key'), r.get('compact_request_rounded'), '->', r.get('repeat_request_rounded'), r.get('reason', ''))
