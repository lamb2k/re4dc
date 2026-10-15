#!/usr/bin/env python3
"""model_registry_pack_test.py <registry.re4nmr> <out dir> [--room 103]  (D367 generic native models, 2026-10-03)

Malformed-package test of the room registry package (NATIVE_MODEL_REGISTRY_PACK=1). Writes the generated package and
one variant per rule below into <out dir> (private: they hold converted meshes), builds model_registry_pack_test.cpp
(the target's own game/coarse_actor_registry_pack_check.inc on the host) and requires every variant to be refused
for the expected reason, and the original to pass. 'fixed' variants recompute every hash the change touches (the
geometry hash, the payload CRC32 / FNV-1a, the header CRC32), so the structural rule itself must refuse them.
Prints one line per case and exits 1 on any mismatch.

--slots (lane ps2cast 2026-10-14, PS2_ASHLEY): the package carries a draw-slot descriptor (model_registry.py --slots,
Ashley r117). The check is built as the PS2_ASHLEY image builds it (RE4DC_NMR_ASHLEY / SLOTS / MASK / DROP_BUMP /
BONES 64 / FACTS 72 / ACTOR_PL08) and runs the draw-slot cases (slot map order and range, source parents, the source
joint count, word 44, a source-only bind); a reader built without the knob must refuse the same package.
"""
import json, os, struct, subprocess, sys, zlib

HEADER, KINDS = 64, ('desc', 'ref', 'geom', 'blob', 'tex', 'parents', 'bind', 'fmodel', 'fpart', 'ftex', 'role', 'sblob')
HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(HERE, '..', '..', 'game')


def fnv(b):
    f = 2166136261
    for x in b:
        f = ((f ^ x) * 16777619) & 0xffffffff
    return f


class Pack:
    def __init__(self, data):
        self.b = bytearray(data)

    def u32(self, at):
        return struct.unpack_from('<I', self.b, at)[0]

    def put(self, at, v, fmt='<I'):
        struct.pack_into(fmt, self.b, at, v)

    def sec(self, kind):
        k = KINDS.index(kind); at = HEADER + 16 * k
        return dict(at=self.u32(at + 4), bytes=self.u32(at + 8), count=self.u32(at + 12), table=at)

    def rec(self, kind, i, size):
        return self.sec(kind)['at'] + i * size

    def regeom(self):
        """recompute every geometry record's hash over its five spans"""
        blob = self.sec('blob')['at']
        for g in range(self.sec('geom')['count']):
            r = self.rec('geom', g, 64)
            npos, nnrm, npal, _, sb, uvb = (self.u32(r + 4 * k) for k in range(6))
            spans = [(self.u32(r + 32), npos * 8), (self.u32(r + 36), nnrm * 8), (self.u32(r + 40), uvb), (self.u32(r + 44), sb),
                     (self.u32(r + 48), npal * 16)]
            data = b''.join(bytes(self.b[blob + a:blob + a + n]) for a, n in spans)
            self.put(r + 52, zlib.crc32(data) & 0xffffffff); self.put(r + 56, fnv(data))

    def fix(self):
        rest = bytes(self.b[HEADER:])
        self.put(36, zlib.crc32(rest) & 0xffffffff); self.put(40, fnv(rest))
        self.put(44, 0); self.put(44, zlib.crc32(bytes(self.b[:HEADER])) & 0xffffffff)
        return self


def cases(good):
    def m(fn, fixed=True, geom=False):
        return (fn, fixed, geom)

    def build(spec):
        if isinstance(spec, Pack):
            return spec
        fn, fixed, geom = spec
        p = Pack(good); r = fn(p)
        if r is not None:
            p = r
        if geom:
            p.regeom()
        return p.fix() if fixed else p
    blob_at = Pack(good).sec('blob')['at']
    have = {k: Pack(good).sec(k)['count'] for k in KINDS}
    # Records each case touches (a smaller room package lacks some: that case is skipped and reported, not faked).
    NEED = {'descriptor-sections': dict(ref=3), 'ref-bones': dict(ref=3, geom=2), 'geometry-hash': dict(geom=2),
            'geometry-overlap': dict(geom=2), 'geometry-duplicate': dict(geom=2), 'weight-bone': dict(geom=2),
            'weight-nan': dict(geom=3), 'texture-duplicate': dict(tex=2), 'role-duplicate': dict(role=2),
            'identity-ambiguous': dict(role=2, fmodel=1)}
    skipped = []

    class Cases(list):
        def append(self, c):
            need = NEED.get(c[0], {})
            if any(have[k] < n for k, n in need.items()):
                skipped.append(c[0]); return
            list.append(self, c)
    C = Cases()
    C.append(('good', 'none', Pack(good)))
    C.append(('truncated', 'header', Pack(good[:-32])))
    C.append(('magic', 'header', m(lambda p: p.put(0, 0x58585858), fixed=False)))
    C.append(('version-2', 'header', m(lambda p: p.put(8, 2))))
    C.append(('header-crc', 'hash', m(lambda p: p.put(44, p.u32(44) ^ 1), fixed=False)))
    C.append(('payload-bit', 'hash', m(lambda p: p.put(blob_at + 100, p.b[blob_at + 100] ^ 0x10, '<B'), fixed=False)))
    C.append(('wrong-room', 'room', m(lambda p: p.put(32, 0x106))))
    C.append(('oversize-skin', 'size', m(lambda p: p.put(28, 200000))))
    C.append(('skin-sum', 'size', m(lambda p: p.put(28, p.u32(28) + 8))))
    C.append(('section-misaligned', 'table', m(lambda p: p.put(p.sec('desc')['table'] + 4, p.sec('desc')['at'] + 4))))
    C.append(('section-kind', 'table', m(lambda p: p.put(p.sec('tex')['table'], 9))))
    C.append(('role-capacity', 'table', m(lambda p: (p.put(p.sec('role')['table'] + 12, 13), p.put(p.sec('role')['table'] + 8, 13 * 32)) and None)))
    C.append(('descriptor-appearance', 'descriptor', m(lambda p: p.put(p.rec('desc', 0, 48) + 16, 0x201))))
    C.append(('descriptor-name', 'descriptor', m(lambda p: p.b.__setitem__(slice(p.rec('desc', 0, 48), p.rec('desc', 0, 48) + 16), b'x' * 16))))
    C.append(('descriptor-sections', 'ref',  # its 2nd section's ref is cow-01's (source_info 0 != 1)
              m(lambda p: p.put(p.rec('desc', 0, 48) + 28, 2))))
    C.append(('ref-geometry', 'ref', m(lambda p: p.put(p.rec('ref', 0, 16), 31))))
    C.append(('ref-bones', 'ref', m(lambda p: p.put(p.rec('ref', 2, 16), 0))))  # chicken section -> cow geometry (27 bones)
    C.append(('geometry-span', 'geometry', m(lambda p: p.put(p.rec('geom', 0, 64) + 32, p.sec('blob')['bytes']))))
    C.append(('geometry-unaligned', 'geometry', m(lambda p: p.put(p.rec('geom', 0, 64) + 40, p.u32(p.rec('geom', 0, 64) + 40) + 4), geom=True)))
    C.append(('geometry-hash', 'hash', m(lambda p: p.put(p.rec('geom', 1, 64) + 52, p.u32(p.rec('geom', 1, 64) + 52) ^ 1))))
    C.append(('geometry-overlap', 'overlap', m(lambda p: p.put(p.rec('geom', 1, 64) + 40, p.u32(p.rec('geom', 0, 64) + 32)), geom=True)))
    C.append(('geometry-duplicate', 'duplicate', m(lambda p: p.b.__setitem__(slice(p.rec('geom', 1, 64), p.rec('geom', 1, 64) + 64),
                                                                              bytes(p.b[p.rec('geom', 0, 64):p.rec('geom', 0, 64) + 64])))))
    def weight_bone(p):
        r = p.rec('geom', 1, 64); w = p.sec('blob')['at'] + p.u32(r + 48)
        p.put(w, p.u32(r + 28), '<B')  # first weight's bone = the geometry's bone count
    C.append(('weight-bone', 'geometry', m(weight_bone, geom=True)))
    def weight_nan(p):
        r = p.rec('geom', 2, 64); w = p.sec('blob')['at'] + p.u32(r + 48)
        p.put(w + 4, 0x7fc00000)
    C.append(('weight-nan', 'geometry', m(weight_nan, geom=True)))
    C.append(('bind-nan', 'skeleton', m(lambda p: p.put(p.sec('bind')['at'] + 5 * 4, 0x7f800000))))
    C.append(('parents-order', 'skeleton', m(lambda p: p.put(p.sec('parents')['at'] + 1, 5, '<b'))))
    C.append(('parents-root', 'skeleton', m(lambda p: p.put(p.sec('parents')['at'], 0, '<b'))))
    C.append(('texture-duplicate', 'duplicate', m(lambda p: p.b.__setitem__(slice(p.rec('tex', 1, 16), p.rec('tex', 1, 16) + 8),
                                                                             bytes(p.b[p.rec('tex', 0, 16):p.rec('tex', 0, 16) + 8])))))
    C.append(('texture-size', 'texture', m(lambda p: p.put(p.rec('tex', 0, 16) + 8, 300))))
    C.append(('fact-part-pad', 'facts', m(lambda p: p.put(p.rec('fpart', 0, 32) + 13, 1, '<B'))))
    C.append(('fact-part-count', 'facts', m(lambda p: p.put(p.rec('fmodel', 0, 96) + 92, 2))))
    C.append(('role-duplicate', 'duplicate', m(lambda p: p.b.__setitem__(slice(p.rec('role', 1, 32), p.rec('role', 1, 32) + 32),
                                                                          bytes(p.b[p.rec('role', 0, 32):p.rec('role', 0, 32) + 32])))))
    C.append(('role-range', 'role', m(lambda p: p.put(p.rec('role', 0, 32) + 4, 1))))
    C.append(('role-binding', 'binding', m(lambda p: p.put(p.rec('role', 0, 32) + 8, 99))))
    # the first two role rows on the same source BIN model fact (r103: cow-00 / cow-01; r101: chicken-00 / chicken-01)
    g = Pack(good); fm = [g.u32(g.rec('role', i, 32) + 16) for i in range(have['role'])]
    pair = next(((i, j) for i in range(len(fm)) for j in range(i + 1, len(fm)) if fm[i] == fm[j]), None)

    def ambiguous(p):  # the second row proves the first row's TPL and texture facts: two descriptors, one source identity
        a, b = p.rec('role', pair[0], 32), p.rec('role', pair[1], 32)
        for off in (12, 20, 24):
            p.put(b + off, p.u32(a + off))
    if pair is None:
        skipped.append('identity-ambiguous')
    else:
        C.append(('identity-ambiguous', 'duplicate', m(ambiguous)))
    C.append(('blob-family', 'blob', m(lambda p: p.put(p.rec('sblob', 0, 32) + 4, 1))))
    C.append(('blob-bin', 'binding', m(lambda p: p.put(p.rec('sblob', 0, 32) + 8, 77))))
    return [(n, w, build(x)) for n, w, x in C], skipped


def alias_cases(good):
    """Narrow r11f v2 contract; every structural mutation has repaired hashes."""
    def case(name, why, edit=lambda p: None, geom=False):
        p=Pack(good); edit(p)
        if geom: p.regeom()
        return name,why,p.fix()
    def g(p,n,w): return p.rec('geom',n,64)+w
    rows=[case('good','none'),
          case('version-3','header',lambda p:p.put(8,3)),
          case('v2-zero-flag','header',lambda p:p.put(56,0)),
          case('v2-unknown-flag','header',lambda p:p.put(56,3)),
          case('v1-flag1','header',lambda p:p.put(8,1)),
          case('v1-aliases','overlap',lambda p:(p.put(8,1),p.put(56,0))),
          case('reserved-word','header',lambda p:p.put(60,1)),
          case('other-room','header',lambda p:p.put(32,0x11e)),
          case('immutable-hash','hash',lambda p:p.put(p.sec('blob')['at']+100,p.b[p.sec('blob')['at']+100]^1,'<B')),
          case('partial-alias','overlap',lambda p:p.put(g(p,1,32),p.u32(g(p,0,32))+32),True),
          case('cross-kind','overlap',lambda p:p.put(g(p,1,36),p.u32(g(p,0,32))),True),
          case('count-mismatch','overlap',lambda p:p.put(g(p,1,0),p.u32(g(p,1,0))-4),True),
          case('palette-context','overlap',lambda p:p.put(g(p,1,8),p.u32(g(p,1,8))-2),True),
          case('bone-context','overlap',lambda p:p.put(g(p,1,28),p.u32(g(p,1,28))-1),True),
          case('stream-alias','overlap',lambda p:p.put(g(p,1,44),p.u32(g(p,0,44))),True),
          case('stream-nested','overlap',lambda p:p.put(g(p,1,44),p.u32(g(p,0,44))+32),True),
          case('section-overlap','table',lambda p:p.put(p.sec('tex')['table']+4,p.sec('blob')['at'])),
          case('geometry-duplicate','duplicate',lambda p:p.b.__setitem__(slice(g(p,1,0),g(p,1,0)+64),bytes(p.b[g(p,0,0):g(p,0,0)+64]))),
          case('skin-sum','size',lambda p:p.put(28,p.u32(28)+8)),
          case('mask-reference','ref',lambda p:p.put(p.rec('ref',0,16)+12,0xffffffff)),
          case('parents-root','skeleton',lambda p:p.put(p.sec('parents')['at'],0,'<b')),
          case('fact-part-pad','facts',lambda p:p.put(p.rec('fpart',0,32)+13,1,'<B')),
          case('role-binding','binding',lambda p:p.put(p.rec('role',0,32)+8,99)),
          case('blob-bin','binding',lambda p:p.put(p.rec('sblob',0,32)+8,77))]
    return rows, []


def slot_cases(good):
    """Draw-slot descriptor rules (descriptor 0 is the slot descriptor); every mutation has repaired hashes."""
    g = Pack(good); d0 = g.rec('desc', 0, 48)
    S = (g.u32(d0 + 44) >> 8) & 255; bones = g.u32(d0 + 24)
    pat = g.sec('parents')['at'] + g.u32(d0 + 36); bat = g.sec('bind')['at'] + 48 * g.u32(d0 + 40)
    if not S:
        sys.exit('--slots: descriptor 0 is not a draw-slot descriptor')
    hidden = next(j for j in range(S) if j not in set(g.b[pat + S:pat + S + bones]))  # a source joint no slot draws

    def case(name, why, edit=lambda p: None):
        q = Pack(good); edit(q); return name, why, q.fix()
    rows = [case('good', 'none'),
            case('slot-order', 'skeleton', lambda p: (p.put(pat + S + 1, p.b[pat + S], '<B'))),
            case('slot-range', 'skeleton', lambda p: p.put(pat + S + bones - 1, S, '<B')),
            case('source-root', 'skeleton', lambda p: p.put(pat, 0, '<B')),
            case('source-forward', 'skeleton', lambda p: p.put(pat + 5, 5, '<B')),
            case('source-count', 'descriptor', lambda p: p.put(d0 + 44, (p.u32(d0 + 44) & 0xff) | (bones << 8))),
            case('word44-high', 'descriptor', lambda p: p.put(d0 + 44, p.u32(d0 + 44) | (1 << 16))),
            case('source-bind-nan', 'skeleton', lambda p: p.put(bat + 48 * hidden + 4, 0x7fc00000)),
            case('parents-short', 'descriptor', lambda p: p.put(d0 + 44, (p.u32(d0 + 44) & 0xff) | ((S + 1) << 8)))]
    return rows, []


def main():
    args = sys.argv[1:]
    room = '103'
    alias = '--immutable-arrays' in args
    if alias: args.remove('--immutable-arrays')
    slots = '--slots' in args
    if slots: args.remove('--slots')
    if '--room' in args:
        i = args.index('--room'); room = args[i + 1]; del args[i:i + 2]
    if len(args) != 2:
        sys.exit(__doc__)
    src, out = args
    if os.path.exists(out):
        sys.exit(f'{out} exists')
    os.makedirs(out)
    good = open(src, 'rb').read()
    # the target's record types, extracted (not restated)
    mat = open(os.path.join(GAME, 'coarse_actor_material.inc')).read()
    reg = open(os.path.join(GAME, 'coarse_actor_owner_registry.inc')).read()
    a, b = mat.index('struct Digest'), mat.index('struct SourceBlob'); b = mat.index('\n', b) + 1
    c = reg.index('namespace nmr {'); d = reg.index('constexpr unsigned kRegDescriptors=16'); d = reg.index('\n', d) + 1
    types = ('#pragma once\n#include <cstdint>\nnamespace re4dc_material {\n' + mat[a:b] + '#include "actor_material_records.inc"\n}\n'
             + reg[c:d])
    if alias or slots:  # MASK builds validate mask runs through registry_geom_view
        start=reg.index('nmr::Chunk registry_geom_view('); end=reg.index('\n}',start)+2
        types+='\n'+reg[start:end]+'\n'
    open(os.path.join(out, 'pack_test_types.h'), 'w').write(types)
    exe = os.path.join(out, 'model_registry_pack_test')
    # platform/include: actor_material_records.inc includes actor_ganado_ps2_stump.h (since 32619278)
    cc = ['g++', '-std=c++17', '-O1', '-Wall', '-Wno-unused-function', '-Wno-unused-variable', '-I', out, '-I', GAME,
          '-I', os.path.join(GAME, 'platform', 'include'),
          os.path.join(HERE, 'model_registry_pack_test.cpp'), '-o', exe]
    if alias:
        cc[1:1]=['-DRE4DC_NMR_IMMUTABLE_ALIAS=1','-DRE4DC_ROUTE_CH23=1','-DRE4DC_NMR_MASK=1',
                 '-DRE4DC_NMR_DROP_BUMP=1','-DRE4DC_NMR_BONES=96','-DRE4DC_NMR_SHIFT=1','-DRE4DC_ACTOR_PL08=1']
    if slots:
        cc[1:1] = ['-DRE4DC_NMR_ASHLEY=2', '-DRE4DC_NMR_SLOTS=1', '-DRE4DC_NMR_MASK=1', '-DRE4DC_NMR_DROP_BUMP=1',
                   '-DRE4DC_NMR_BONES=64', '-DRE4DC_NMR_FACTS=72', '-DRE4DC_ACTOR_PL08=1']
    r = subprocess.run(cc, capture_output=True, text=True)
    if r.returncode:
        sys.exit('build failed:\n' + r.stderr[-4000:])
    files, want = [], {}
    built, skipped = alias_cases(good) if alias else slot_cases(good) if slots else cases(good)
    if skipped:
        print('skipped (records absent in this package): ' + ' '.join(skipped))
    for name, why, p in built:
        f = os.path.join(out, name + '.re4nmr'); open(f, 'wb').write(bytes(p.b)); files.append(f); want[f] = (name, why)
    r = subprocess.run([exe, room] + files, capture_output=True, text=True)
    bad, rows = 0, []
    for line in r.stdout.splitlines():
        f, why, detail = line.rsplit(' ', 2)
        name, exp = want[f]
        ok = why == exp
        bad += not ok
        rows.append(dict(case=name, expected=exp, got=why, detail=int(detail), ok=ok))
        print(f'{"PASS" if ok else "FAIL"} {name:24s} expected={exp:10s} got={why} detail={detail}')
    if len(rows) != len(files):
        bad += 1; print(f'FAIL {len(files)} cases, {len(rows)} results')
    if alias:
        # The same v1 reader with the new option disabled must refuse v2.
        legacy=exe+'-legacy'; legacy_cc=[a for a in cc if a!='-DRE4DC_NMR_IMMUTABLE_ALIAS=1']
        legacy_cc[legacy_cc.index('-o')+1]=legacy
        subprocess.run(legacy_cc,check=True,capture_output=True)
        rejected=subprocess.check_output([legacy,room,src],text=True).split()[-2]=='header'
        print(('PASS' if rejected else 'FAIL')+' legacy-rejects-v2');bad+=not rejected
        # Mutation of each stream must leave immutable arrays and all other streams intact.
        p=Pack(good); blob=p.sec('blob')['at']; immutable=[]; streams=[]
        for i in range(p.sec('geom')['count']):
            r=p.rec('geom',i,64)
            for off,n in ((32,p.u32(r)*8),(36,p.u32(r+4)*8),(40,p.u32(r+20)),(48,p.u32(r+8)*16)):
                at=blob+p.u32(r+off);immutable.append((at,bytes(p.b[at:at+n])))
            at=blob+p.u32(r+44); streams.append((at,bytes(p.b[at:at+p.u32(r+16)])))
        for i,(at,data) in enumerate(streams):
            mutated=bytearray(good);mutated[at:at+len(data)]=bytes(x^255 for x in data)
            assert all(mutated[a:a+len(b)]==b for a,b in immutable)
            assert all(mutated[a:a+len(b)]==b for j,(a,b) in enumerate(streams) if j!=i)
        print('PASS independent-stream-mutation-canaries')
    if slots:
        # A reader without the draw-slot rules must refuse the package: PS2_ASHLEY off (refused by the 192 KiB ceiling
        # before anything else) and, to reach the descriptor rule, the PS2_ASHLEY capacities without RE4DC_NMR_SLOTS.
        for tag, drop, want in (('knob-off', ('-DRE4DC_NMR_SLOTS=1', '-DRE4DC_NMR_ASHLEY=2'), 'size'),
                                ('no-slot-rules', ('-DRE4DC_NMR_SLOTS=1',), 'descriptor')):
            legacy = exe + '-' + tag; legacy_cc = [a for a in cc if a not in drop]
            legacy_cc[legacy_cc.index('-o') + 1] = legacy
            subprocess.run(legacy_cc, check=True, capture_output=True)
            got = subprocess.check_output([legacy, room, src], text=True).split()[-2]
            print(('PASS' if got == want else 'FAIL') + f' {tag}-rejects-slots expected={want} got={got}'); bad += got != want
    json.dump(dict(package=src, room=room, cases=rows, failures=bad), open(os.path.join(out, 'results.json'), 'w'), indent=1)
    print(f'{len(rows) - bad}/{len(files)} as expected')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
