#!/usr/bin/env python3
"""ps2_accessories.py: PS2 models and pictures for the Ganado accessories (cObj12) in a prepared enemy archive
(test 12 item, lane ps2cast, 2026-10-15).

em10SetAccesory (src/em10/em10.cpp) hangs a cObj12 on a Ganado's head joint (SetObj12 + setParent(em, 4, 1)): the
caps (Cap_type 1 / 2: BIN 0x25F with TPL 0x260 / 0x261), kinds 3 / 4 (BIN 0x262, TPL 0x263 / 0x264), the hats
(kinds 5 / 6: BIN 0x265, TPL 0x266 / 0x267) and the glasses (pGlasses: BIN 0x268, TPL 0x269). The archive entries
are GameCube data on every disc so far (the crowd12 census: 2,786 of 7,943 actor-path triangles in the village at 12
alive). The PS2 archive (BIO4DAT emXX.dat) has the same entries at the same ARC numbers.

This tool keeps the GC attachment logic and every source identity and swaps only data, in the prepared (le_mirror +
prepare_enemy_motions) archive the release stages:
  geometry  ps2_objects.rebuild(GC BIN, PS2 BIN): a GameCube-format ModelData (GC header, joints, weight palette, part
            headers kept) with the PS2 positions, normals, UVs and triangles, then le_mirror's BIN conversion (to_le);
  pictures  each TPL image the BIN samples: the PS2 TPL image of the same index (GS-decoded, transposed when the PS2
            rotate flag is set, as ps2_objects_tex.py), encoded as a dc/tex package (opaque -> VQ when smaller, else
            twiddled RGB565 / ARGB1555 / ARGB4444); the R4NREF record's crc / fnv words then name that package.
The entries 0x25F..0x268 are re-laid out inside their own span (each 32-byte aligned, in source order); the span
keeps its size (the rebuilt BINs are 2,688 + 2,944 + 2,656 + 3,040 B against 2,656 + 2,976 + 2,656 + 3,072 B), so the
payload size, every other entry and the static REL descriptor stay byte-identical. The NTR texture-identity rows of
the moved TPL records are rebased by their entry's move (table crc refreshed); an ESQ / MTC row inside the span is
refused. Disc data only: the executable is unchanged.

  py ps2_accessories.py build --release <prepared emXX.drs> --gc <GC emXX.drs (big-endian, GC disc)>
                              --ps2 <PS2 emXX.dat> --out <new emXX.drs> --texdir <dir> [--json report.json]
  py ps2_accessories.py census <staged emXX.drs> --release <knob-off prepared emXX.drs> --gc <GC emXX.drs>
                              --ps2 <PS2 emXX.dat>
     every accessory BIN / TPL image of the staged archive: GC (the knob-off release's bytes / keys) or PS2 (this
     tool's output); exit 1 when any is GC (the cObj12 GC-fallback count).
Runs on Windows Python (numpy + PIL: ps2_room_r4im's encoder and PS2 TPL decoder).
"""
import argparse, hashlib, json, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
sys.path[:0] = [str(TOOLS), str(TOOLS.parents[2] / 'tools')]
import le_mirror as mirror  # noqa: E402
import ps2_objects as po  # noqa: E402
import ps2_bin as pb  # noqa: E402
import drs  # noqa: E402

# BIN arc -> the TPL arcs it is drawn with (em10SetAccesory; em15_set / em10_set mot[52..62])
ACCESSORIES = {0x25F: (0x260, 0x261), 0x262: (0x263, 0x264), 0x265: (0x266, 0x267), 0x268: (0x269,)}
SPAN = (0x25F, 0x268)
NTR_MAGIC = b'R4NTEX\0\0'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def al(n):
    return (n + 31) & ~31


class Payload:
    """The prepared archive's native payload (DVD container slot) as a mutable body."""

    def __init__(self, data):
        self.file = bytearray(data)
        slot = mirror.native_payload_slot(self.file)
        self.size, self.base = struct.unpack_from('<I4xI', self.file, slot + 4)
        self.body = bytearray(self.file[self.base:self.base + self.size])
        self.count, self.rel = struct.unpack_from('<2I', self.body)
        self.offs = list(struct.unpack_from('<%dI' % self.count, self.body, 16))
        self.tags = [bytes(self.body[16 + 4 * self.count + 4 * i:20 + 4 * self.count + 4 * i]).rstrip(b'\0').decode('latin-1')
                     for i in range(self.count)]

    def end(self, i):
        o = self.offs[i]
        return min([v for v in self.offs if v > o] + [self.rel or self.size])

    def entry(self, arc):
        i = arc - 4
        return bytes(self.body[self.offs[i]:self.end(i)])

    def table(self, tag):
        i = self.tags.index(tag) if tag in self.tags else None
        if i is None:
            return None
        o = self.offs[i]
        magic, ver, cnt, row, crc = struct.unpack_from('<8s4I', self.body, o)
        return i, o, magic, ver, cnt, row, crc

    def bytes(self):
        out = bytearray(self.file)
        assert len(self.body) == self.size
        out[self.base:self.base + self.size] = self.body
        return bytes(out)


def tpl_records(body, tpl):
    """{image index: (record offset, record 8 bytes, width, height, format)} of a little-endian TPL at body[tpl:]."""
    num, desc = struct.unpack_from('<II', body, tpl + 4)
    out = {}
    for k in range(num):
        tex, clut = struct.unpack_from('<II', body, tpl + desc + 8 * k)
        if not tex:
            continue
        h, w = struct.unpack_from('<HH', body, tpl + tex)
        fmt, data = struct.unpack_from('<II', body, tpl + tex + 4)
        out[k] = (tpl + data, bytes(body[tpl + data:tpl + data + 8]), w, h, fmt)
    return out


def gc_entries(path):
    d = drs.Drs(Path(path).read_bytes())
    return {k + 4: (drs.tag_name(t), b) for k, (t, b) in enumerate(d.entries)}


def ps2_entries(path):
    return {i + 4: (t, b) for i, t, b in pb.dat_entries(Path(path).read_bytes())}


def converted_bins(gc, ps2):
    """{BIN arc: (little-endian rebuilt BIN, stats, little-endian GC BIN)}."""
    out = {}
    for a in ACCESSORIES:
        gt, g = gc.get(a, ('', b''))
        if not gt and not g:
            continue  # the family is absent from this archive (em17: no ARC 0x262..0x264)
        pt, p = ps2[a]
        if gt != 'BIN' or pt != 'BIN':
            raise ValueError('ARC %#x: GC %s / PS2 %s, not a BIN pair' % (a, gt, pt))
        new, st = po.rebuild(g, p)
        out[a] = (po.to_le(new, 'acc%x' % a), st, po.to_le(g, 'gc%x' % a))
    return out


def encode_images(gc, ps2, label, families):
    """{TPL arc: {image: (re4tex bytes, key, meta)}} from the PS2 TPL of the same arc (image k -> PS2 image k)."""
    import numpy as np  # noqa
    import ps2_room_r4im as wr
    sys.path.insert(0, str(TOOLS))
    out = {}
    for a in families:
        for t in ACCESSORIES[a]:
            gt, gtpl = gc[t]
            pt, ptpl = ps2[t]
            if gt != 'TPL' or pt != 'TPL':
                raise ValueError('ARC %#x: GC %s / PS2 %s, not a TPL pair' % (t, gt, pt))
            pim = ps2_images(wr, ptpl)
            out[t] = {}
            for k, (w, h, rgba, il) in pim.items():
                img, how, err = orient(rgba, gc_image(gtpl, k), il & 1)
                data, key, meta = encode(wr, img, 'PS2 Ganado accessory TPL %#x image %d' % (t, k))
                meta.update(orient=how, mean_abs_diff_vs_gc=err, ps2_size='%dx%d' % (w, h))
                out[t][k] = (data, key, meta)
    return out


# --- PS2 picture helpers (the encoder / decoder / orientation of tools/ps2_objects_tex.py, lane objs 2026-10-14)

def ps2_images(wr, body):
    t = wr.tpl
    out = {}
    for i, h in enumerate(t.parse_tpl(body)['entries']):
        w, hh, rgba = t.decode(body, h, 'gs')[:3]
        import numpy as np
        out[i] = (w, hh, np.frombuffer(bytes(rgba), np.uint8).reshape(hh, w, 4), h['interlace'])
    return out


def gc_image(gc_tpl_bytes, k):
    import numpy as np
    import convert_tpl as ct
    try:
        im = ct.parse_tpl(gc_tpl_bytes)[k]
        return np.array(ct.decode_image(im), np.uint8).reshape(im.height, im.width, 4)
    except Exception:  # noqa
        return None


def orient(ps2, gc, rotate):
    import numpy as np
    c = np.ascontiguousarray(ps2.transpose(1, 0, 2)) if rotate else ps2
    how = 'transpose(rotate flag)' if rotate else 'as stored'
    if gc is None:
        return c, how + ', no GC image', None
    gh, gw = gc.shape[:2]
    ch, cw = c.shape[:2]
    ys = np.arange(gh) * ch // gh
    xs = np.arange(gw) * cw // gw
    err = float(np.mean(np.abs(c[ys][:, xs].astype(np.int32)[..., :3] - gc[..., :3].astype(np.int32))))
    if ch * gw != cw * gh:
        how += ', aspect %dx%d vs GC %dx%d' % (cw, ch, gw, gh)
    return c, how, err


def encode(wr, image, label):
    import numpy as np
    h, w = image.shape[:2]
    alpha = np.unique(image[..., 3])
    mode = 'opaque' if alpha.min() == 255 else ('cutout' if np.all(np.isin(alpha, [0, 255])) else 'graded')
    fmt = {'opaque': 0, 'cutout': 1, 'graded': 2}[mode]
    target = image.astype(np.float64)
    use_vq = fmt == 0 and 2048 + w * h // 4 < w * h * 2
    if use_vq:
        payload = wr.vq_encode(target, fmt); ptype = 2
    else:
        q = wr.pack16(target, fmt)
        raw = np.empty(w * h, dtype='<u2'); raw[wr.codec.untwiddle_index(w, h).ravel()] = q.ravel()
        payload = raw.tobytes(); ptype = 1
    data, key = wr.re4dctx_bytes(label, w, h, fmt, ptype, payload)
    return data, key, dict(width=w, height=h, alpha_mode=mode, format=fmt, payload='vq' if use_vq else 'native16',
                           vram_bytes=len(payload))


# --- build

def relayout(P, bins):
    """Re-lay out ARC SPAN[0]..SPAN[1] inside their span with the converted BINs; returns {old offset: new offset}."""
    # an empty slot (no tag) carries the next entry's offset (em17 ARC 0x262..0x264 = ARC 0x265's); it follows that entry
    arcs = [a for a in range(SPAN[0], SPAN[1] + 1) if P.offs[a - 4] and P.tags[a - 4]]
    idx = [a - 4 for a in arcs]
    o = [P.offs[i] for i in idx]
    if any(not x for x in o) or o != sorted(o) or len(set(o)) != len(o):
        raise ValueError('span entries are not in source order')
    start, stop = o[0], P.end(idx[-1])
    starts = {P.offs[i]: i for i in idx}
    aliases = [i for i, v in enumerate(P.offs) if start <= v < stop and i not in idx and not P.tags[i] and v in starts]
    inside = [i for i, v in enumerate(P.offs) if start <= v < stop and i not in idx and i not in aliases]
    if inside:
        raise ValueError('other entries alias the span: %s' % [hex(i + 4) for i in inside])
    new = bytearray()
    moved = {}
    for a, i in zip(arcs, idx):
        data = bins[a][0] if a in bins else bytes(P.body[P.offs[i]:P.end(i)])
        new += bytes(al(len(new)) - len(new))
        moved[i] = (P.offs[i], P.end(i), start + len(new), a in bins)
        new += data
    new += bytes(al(len(new)) - len(new))
    if len(new) > stop - start:
        raise ValueError('converted span %d B does not fit the source span %d B' % (len(new), stop - start))
    new += bytes(stop - start - len(new))
    old_body = bytes(P.body)
    P.body[start:stop] = new
    for i in aliases:
        s2 = moved[starts[P.offs[i]]][2]
        P.offs[i] = s2
        struct.pack_into('<I', P.body, 16 + 4 * i, s2)
    for i, (s, e, s2, repl) in moved.items():
        P.offs[i] = s2
        struct.pack_into('<I', P.body, 16 + 4 * i, s2)

    def mapped(x):
        for i, (s, e, s2, repl) in moved.items():
            if s <= x < e:
                if repl:
                    raise ValueError('table offset %#x inside a replaced BIN' % x)
                return x - s + s2
        if start <= x < stop:
            raise ValueError('table offset %#x in the span padding' % x)
        return x
    # NTR rows: (record, image header, TPL) payload offsets
    t = P.table('NTR')
    rebased = 0
    if t:
        ti, to, magic, ver, cnt, row, crc = t
        if row != 12 or ver != 1 or zlib.crc32(P.body[to + 32:to + 32 + 12 * cnt]) & 0xffffffff != crc:
            raise ValueError('NTR table header not understood')
        for r in range(cnt):
            ro = to + 32 + 12 * r
            vals = struct.unpack_from('<3I', P.body, ro)
            nv = tuple(mapped(v) for v in vals)
            for v, n_, ln in zip(vals, nv, (32, 36, 12)):
                if old_body[v:v + ln] != P.body[n_:n_ + ln]:
                    raise ValueError('NTR row %d: data at %#x did not move intact' % (r, v))
            if nv != vals:
                struct.pack_into('<3I', P.body, ro, *nv)
                rebased += 1
        struct.pack_into('<I', P.body, to + 20, zlib.crc32(P.body[to + 32:to + 32 + 12 * cnt]) & 0xffffffff)
    # ESQ (effect sequences) and MTC (motion cache) rows must not point into the span
    for tag, stride in (('ESQ', 12), ('MTC', 20)):
        t = P.table(tag)
        if not t:
            continue
        ti, to, magic, ver, cnt, row, crc = t
        for r in range(cnt):
            v = struct.unpack_from('<I', P.body, to + 32 + row * r)[0]
            if start <= v < stop:
                raise ValueError('%s row %d points into the span' % (tag, r))
    # every non-replaced entry moved intact; everything outside the span unchanged
    for i, (s, e, s2, repl) in moved.items():
        if not repl and old_body[s:e] != P.body[s2:s2 + e - s]:
            raise ValueError('entry %#x did not move intact' % (i + 4))
    return dict(span=[start, stop], used=len(new.rstrip(b'\0')), ntr_rows_rebased=rebased,
                moves={'%#x' % (i + 4): [s, s2] for i, (s, e, s2, r) in moved.items()})


def adopt_check(data):
    """The runtime's SourceIdentityTable::adopt (room/texture_package.cpp; src/game/read.cpp halts with "invalid prepared
    enemy texture identities" when it fails) over a payload body: '' when it accepts, else the first failed check."""
    u32 = lambda o: struct.unpack_from('<I', data, o)[0]
    u16 = lambda o: struct.unpack_from('<H', data, o)[0]
    n, size = u32(0), len(data)
    native = None
    for i in range(n):
        if data[16 + 4 * n + 4 * i:20 + 4 * n + 4 * i] != b'NTR\0':
            continue
        off = u32(16 + 4 * i)
        if native is not None or off > size or size - off < 32:
            return 'NTR slot'
        native = off
    if native is None:
        return ''
    if data[native:native + 8] != b'R4NTBL\0\0' or u32(native + 8) != 1 or u32(native + 16) != 12:
        return 'NTR header'
    if u32(native + 28) != size or u32(native + 24) <= size:
        return 'NTR size words'
    cnt = u32(native + 12)
    if not cnt or cnt > (size - native - 32) // 12 or cnt > 1024:
        return 'NTR count'
    if zlib.crc32(data[native + 32:native + 32 + 12 * cnt]) & 0xffffffff != u32(native + 20):
        return 'NTR crc'
    for i in range(cnt):
        rec, hdr, tpl = struct.unpack_from('<3I', data, native + 32 + 12 * i)
        if rec > size - 32 or hdr > size - 36 or tpl > size - 12 or rec & 31 or hdr & 3 or tpl & 3:
            return 'row %d offsets' % i
        w, ht, fmt = u32(rec + 16), u32(rec + 20), u32(rec + 24)
        indexed = data[rec:rec + 8] == b'R4PREF\0\0'
        if indexed:
            if rec > size - 64 or fmt not in (8, 9) or u32(rec + 32) > 2 or not u32(rec + 36) or u32(rec + 36) & 1 or \
                    u32(rec + 36) > (32 if fmt == 8 else 512) or u32(rec + 28) < 64 or any(u32(rec + k) for k in (48, 52, 56, 60)):
                return 'row %d palette record' % i
        if (not indexed and (data[rec:rec + 8] != b'R4NREF\0\0' or (fmt > 6 and fmt != 14))) or not w or not ht or \
                w > 1024 or ht > 1024 or data[hdr + 33] or (data[hdr + 34] and indexed) or data[hdr + 35] or \
                w != u16(hdr + 2) or ht != u16(hdr) or fmt != u32(hdr + 4) or tpl + u32(hdr + 8) != rec:
            return 'row %d record / image header' % i
    return ''


def build(a):
    rel = Path(a.release).read_bytes()
    P = Payload(rel)
    gc, ps2 = gc_entries(a.gc), ps2_entries(a.ps2)
    # the prepared archive's BINs must be the GC BINs (le_mirror form) before conversion
    bins = converted_bins(gc, ps2)
    for arc, (le, st, gle) in bins.items():
        have = P.entry(arc)
        if have[:len(gle)] != gle or have[len(gle):].strip(b'\0'):
            raise ValueError('release ARC %#x is not the le_mirror GC BIN' % arc)
    report = dict(release=a.release, release_sha256=sha(rel), gc=a.gc, ps2=a.ps2, models={}, images=[])
    for arc, (le, st, gle) in bins.items():
        report['models']['%#x' % arc] = dict(gc_tris=st['gc_tris'], ps2_tris=st['ps2_tris'], out_tris=st['out_tris'],
                                             gc_bytes=len(gle), out_bytes=len(le), flipped=st['flipped'],
                                             weight_mismatch=st['weight_mismatch'], degenerate=st['degenerate'])
    report['layout'] = relayout(P, {k: v for k, v in bins.items()})
    imgs = encode_images(gc, ps2, Path(a.release).stem, sorted(bins))
    texdir = Path(a.texdir); texdir.mkdir(parents=True, exist_ok=True)
    for t, per in imgs.items():
        recs = tpl_records(P.body, P.offs[t - 4])
        for k, (rec, magic, gw, gh, gfmt) in recs.items():
            if magic not in (b'R4NREF\0\0', b'R4PREF\0\0'):
                raise ValueError('TPL %#x image %d: not a prepared record (%r)' % (t, k, magic))
            if k not in per:
                raise ValueError('TPL %#x image %d: no PS2 image' % (t, k))
            data, key, meta = per[k]
            (texdir / (key + '.re4tex')).write_bytes(data)
            crc, fnv = (int(x, 16) for x in key.split('-'))
            old = struct.unpack_from('<II', P.body, rec + 8)
            struct.pack_into('<II', P.body, rec + 8, crc, fnv)
            report['images'].append(dict(tpl='%#x' % t, image=k, record=rec, old_key='%08x-%08x' % old, key=key,
                                         gc=dict(width=gw, height=gh, format=gfmt), ps2=meta, bytes=len(data), sha256=sha(data)))
    for label, body in (('release', Payload(rel).body), ('output', P.body)):
        why = adopt_check(bytes(body))
        if why:
            raise ValueError('%s payload fails the runtime NTR check: %s' % (label, why))
    out = P.bytes()
    if len(out) != len(rel):
        raise ValueError('archive size changed')
    Path(a.out).write_bytes(out)
    report.update(out=a.out, out_sha256=sha(out), tool_sha256=sha(Path(__file__).read_bytes()))
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1))
    for arc, m in report['models'].items():
        print('BIN %s tris GC %d PS2 %d (out %d) bytes %d -> %d' % (arc, m['gc_tris'], m['ps2_tris'], m['out_tris'], m['gc_bytes'], m['out_bytes']))
    for i in report['images']:
        print('TPL %s image %d %s -> %s  GC %dx%d fmt %d  PS2 %s %s %s diff %s' % (
            i['tpl'], i['image'], i['old_key'], i['key'], i['gc']['width'], i['gc']['height'], i['gc']['format'],
            i['ps2']['ps2_size'], i['ps2']['payload'], i['ps2']['orient'],
            '%.1f' % i['ps2']['mean_abs_diff_vs_gc'] if i['ps2']['mean_abs_diff_vs_gc'] is not None else '-'))
    print('layout', json.dumps(report['layout']))
    print(a.out, report['out_sha256'])


def census(a):
    S, R = Payload(Path(a.staged).read_bytes()), Payload(Path(a.release).read_bytes())
    why = adopt_check(bytes(S.body))
    print('runtime NTR check (SourceIdentityTable::adopt): %s' % (why or 'pass'))
    if why:
        return 2
    gc = gc_entries(a.gc)
    ps2 = ps2_entries(a.ps2)
    bins = converted_bins(gc, ps2)
    gcn = 0
    for arc, (le, st, gle) in bins.items():
        have = S.entry(arc)
        kind = 'PS2' if have[:len(le)] == le and not have[len(le):].strip(b'\0') else (
            'GC' if have[:len(gle)] == gle and not have[len(gle):].strip(b'\0') else 'OTHER')
        gcn += kind != 'PS2'
        print('BIN %#x %s (%d tris)' % (arc, kind, st['out_tris'] if kind == 'PS2' else st['gc_tris']))
        for t in ACCESSORIES[arc]:
            sr, rr = tpl_records(S.body, S.offs[t - 4]), tpl_records(R.body, R.offs[t - 4])
            for k in sorted(sr):
                ks, kr = sr[k][0], rr[k][0]
                key_s = struct.unpack_from('<II', S.body, ks + 8)
                key_r = struct.unpack_from('<II', R.body, kr + 8)
                kind = 'GC' if key_s == key_r else 'PS2'
                gcn += kind == 'GC'
                print('  TPL %#x image %d %s key %08x-%08x' % (t, k, kind, *key_s))
    print('cObj12 accessory GC data: %d' % gcn)
    return 1 if gcn else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    b = sp.add_parser('build')
    for k in ('release', 'gc', 'ps2', 'out', 'texdir'):
        b.add_argument('--' + k, required=True)
    b.add_argument('--json')
    c = sp.add_parser('census')
    c.add_argument('staged')
    for k in ('release', 'gc', 'ps2'):
        c.add_argument('--' + k, required=True)
    a = ap.parse_args()
    if a.cmd == 'build':
        build(a)
        return 0
    return census(a)


if __name__ == '__main__':
    sys.exit(main())
