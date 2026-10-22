#!/usr/bin/env python3
"""Source/host qualification only; no assets or R4TC output is generated."""
import argparse
import ast
import collections
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import types
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tr_classify as candidate

H = struct.Struct('<8s10I')
D = struct.Struct('<64s8I')
PARENT = '0425534d848973c1dae3ab960d0006ac9afcf363'
checks = []

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def fixture(side, fmt, layout, mip, height=None, legacy_crc=False):
    """Authored lower levels all zero; base has varied alpha and hidden RGB."""
    height = height or side
    pixels = side * height
    if layout == 2:
        book = []
        for entry in range(256):
            for corner in range(4):
                alpha = (entry * 3 + corner * 5) % (2 if fmt == 1 else 16)
                book.append((alpha << (15 if fmt == 1 else 12)) | ((entry * 7 + corner) & 0xfff))
        base = bytes((i * 17 + 11) % 256 for i in range(pixels // 4))
        lower = bytearray()
        if mip:
            lower.append(0)
            n = 2
            while n < side:
                lower.extend(bytes(n * n // 4))
                n *= 2
        payload = struct.pack('<1024H', *book) + lower + base
    else:
        words = [(((i * 7 + 3) % (2 if fmt == 1 else 16)) << (15 if fmt == 1 else 12)) |
                 ((i * 17 + 1) & 0xfff) for i in range(pixels)]
        lower = bytearray(6) if mip else bytearray()
        if mip:
            n = 1
            while n < side:
                lower.extend(bytes(n * n * 2))
                n *= 2
        payload = lower + struct.pack('<%dH' % len(words), *words)
    desc = D.pack(b'authored synthetic alpha contract', side, height, fmt, 144, len(payload),
                  (3 if fmt == 1 else 1) | (4 if mip else 0), layout, 0)
    body = desc + payload
    crc = zlib.crc32(payload if legacy_crc else body) & 0xffffffff
    return H.pack(b'RE4DCTX\0', 2, 48, 96, 1, 48, 144, len(payload), crc, 7, 29) + body


def patch(blob, offset, value, restamp=True):
    result = bytearray(blob)
    struct.pack_into('<I', result, offset, value)
    if restamp:
        struct.pack_into('<I', result, 36, zlib.crc32(result[48:]) & 0xffffffff)
    return bytes(result)


def read(blob, mode=None):
    t = candidate.Textures([], [], **({} if mode is None else {'mip_aware_alpha': mode}))
    t.blob = lambda key: blob
    result = t.alpha('synthetic')
    check('cache-%d' % len(checks), t.alpha('synthetic') == result)
    return result


def reference(lib, blob):
    """Actual already-built pinned KOS pvrtex decoder, independent of new reader."""
    desc = D.unpack_from(blob, 48)
    _, side, height, fmt, off, size, flags, layout, _ = desc
    assert side == height
    fn = lib.mipmap_oracle_decode if layout == 2 else lib.mipmap_oracle_decode_twiddled
    fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_uint,
                   ctypes.c_int, ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t]
    fn.restype = ctypes.c_int
    out = ctypes.create_string_buffer(side * side * 4)
    count = fn(blob[off:], size, fmt, side, bool(flags & 4), side.bit_length() - 1,
               out, len(out))
    check('actual-pvrtex-decode-%d' % len(checks), count == len(out))
    divisor = 255 if fmt == 1 else 17
    hist = dict(collections.Counter(v // divisor for v in out.raw[3::4]))
    return hist, 1 if fmt == 1 else 15


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--oracle', type=Path, required=True, help='existing pvrtex oracle with VQ and TWID symbols')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    lib = ctypes.CDLL(str(args.oracle))
    path = ROOT / 'tr_classify.py'
    parent_source = subprocess.check_output(['git', 'show', PARENT + ':port/dreamcast/tools/d367/tr_classify.py'], text=True, cwd=ROOT)
    old = types.ModuleType('legacy_classifier')
    old.__file__ = str(path)
    exec(compile(parent_source, str(path), 'exec'), old.__dict__)
    old_ast, new_ast = ast.parse(parent_source), ast.parse(path.read_text())
    for name in ('stats', 'tex_class', 'part_class', 'classify_room'):
        def body(tree):
            return ast.dump(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name))
        check(name + '-AST-unchanged', body(old_ast) == body(new_ast))
    def method(tree):
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Textures')
        return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'alpha')
    new_alpha = method(new_ast)
    new_alpha.body = [n for n in new_alpha.body if not
                     (isinstance(n, ast.If) and isinstance(n.test, ast.Attribute) and
                      n.test.attr == 'mip_aware_alpha')]
    check('legacy-alpha-body-AST-unchanged-except-opt-in-dispatch',
          ast.dump(method(old_ast)) == ast.dump(new_alpha))
    cases = []
    for fmt in (1, 2):
        for layout in (1, 2):
            for side in (8, 16, 64, 128):
                for mip in (False, True):
                    for legacy_crc in (False, True):
                        blob = fixture(side, fmt, layout, mip, legacy_crc=legacy_crc)
                        exact = reference(lib, blob)
                        check('base-hist-%d' % len(checks), read(blob, True) == exact)
                        check('base-texel-count-%d' % len(checks), sum(exact[0].values()) == side * side)
                        legacy = old.Textures([], [])
                        legacy.blob = lambda key: blob
                        prior = legacy.alpha('synthetic')
                        check('default-legacy-exact-%d' % len(checks), read(blob) == prior)
                        check('explicit-off-legacy-exact-%d' % len(checks), read(blob, False) == prior)
                        if not mip:
                            check('nonmip-exact-%d' % len(checks), exact == prior)
                        cases.append(dict(format=fmt, layout=layout, side=side, mip=mip,
                                          crc='legacy-payload' if legacy_crc else 'descriptor-payload',
                                          histogram=exact[0], old_histogram=prior[0],
                                          old_wrong=prior != exact, package_sha256=hashlib.sha256(blob).hexdigest()))
    for fmt in (0, 1, 2):
        for layout in (0, 1, 2):
            blob = fixture(8, fmt, layout, False, height=16)
            legacy = old.Textures([], [])
            legacy.blob = lambda key: blob
            check('rect-nonmip-%d' % len(checks), read(blob, True) == legacy.alpha('synthetic'))
    # Missing, malformed headers/extents, unknown payloads/formats/flags and incomplete chains.
    base = fixture(16, 2, 2, True)
    negative = {'missing': None, 'empty': b'', 'short-header': base[:47], 'short-desc': base[:143],
                'truncated': base[:-1], 'trailing': base + b'\0', 'magic': b'X' + base[1:]}
    for name, offset, value in [('version', 8, 3), ('header-size',12,49), ('stride',16,95),
             ('count0',20,0), ('count2',20,2), ('descriptor-offset',24,49), ('data-offset',28,145),
             ('header-data-size',32,len(base)-145), ('bad-crc',36,0), ('width0',112,0),
             ('width4',112,4), ('width-nonpower',112,17), ('width-large',112,2048),
             ('height0',116,0), ('mip-nonsquare',116,8), ('format3',120,3), ('pal4',120,4),
             ('pal8',120,5), ('format-unknown',120,6), ('payload-offset',124,145),
             ('payload-short',128,len(base)-145), ('payload-big',128,len(base)-143),
             ('topdrop',132,1<<30), ('unknown-flags',132,8), ('linear-mip',136,0),
             ('payload-unknown',136,3), ('reserved',140,1)]:
        negative[name] = patch(base, offset, value, offset != 36)
    twid = fixture(16, 1, 1, True)
    negative['twid-truncated'] = twid[:-2]
    negative['twid-nonmip-size'] = patch(twid,132,3)
    for name, blob in (('vq-short-chain', base[:-1]), ('twid-short-chain', twid[:-2])):
        declared = patch(blob,32,len(blob)-144)
        negative[name] = patch(declared,128,len(blob)-144)
    for name, blob in negative.items():
        check('refuse-' + name, read(blob, True) is None)
    # Demonstrate both historic bugs, rather than only exercising equal histograms.
    for layout in (1, 2):
        check('historic-mip-bug-reproduced-%d' % layout,
              any(c['layout'] == layout and c['mip'] and c['old_wrong'] for c in cases))
    # Default legacy PAL reader remains available and exact. Opt-in PAL stays unsupported.
    pal = fixture(8,2,1,False)
    pal = patch(pal,120,4)
    legacy = old.Textures([],[])
    legacy.blob = lambda key: pal
    check('default-pal-unchanged', read(pal) == legacy.alpha('synthetic'))
    check('opt-in-pal-unsupported', read(pal,True) is None)
    help_text = subprocess.check_output([sys.executable,str(path),'--help'], text=True)
    check('cli-opt-in-visible', '--mip-aware-alpha' in help_text)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    summary = dict(status='PASS', scope='source/host only; no generated R4TC, assets, programme or guest',
        checks=len(checks), names=checks, base_cases=cases, negative_cases=len(negative),
        parent=PARENT, source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        oracle=dict(path=str(args.oracle),bytes=args.oracle.stat().st_size,
                    sha256=hashlib.sha256(args.oracle.read_bytes()).hexdigest()),
        limitations=['PAL/unknown formats unsupported in opt-in mode',
                     'legacy payload-only CRC input accepted; not runtime admission',
                     'existing R4TC class-byte compatibility requires a separate per-material gate',
                     'no programme, guest, rendering, LOD, performance or physical Dreamcast claim'])
    args.out.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(status='PASS',checks=len(checks),base_cases=len(cases),negatives=len(negative))))

if __name__ == '__main__':
    main()