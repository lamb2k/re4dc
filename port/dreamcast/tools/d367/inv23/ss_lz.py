#!/usr/bin/env python3
"""ss_lz.py: the SS_DATA_LZ data set (lane inv23, 2026-10-22).

Compresses the sub screen's own data files (SS/<lang>/ss_cmmn.dat, ss_pzzl.dat) offline into SS/<lang>/ss_cmmn.lz,
ss_pzzl.lz, which an SS_DATA_LZ=1 program reads at each sub screen open instead of the .dat files
(subscreen_backing.cpp re4dc_ssb_lz_read). Without the .lz files, or with SS_DATA_LZ=0, the .dat files are read as before.

File format (little endian): 'SSLZ', u32 raw size, u32 packed size, u32 crc32 of the raw bytes, then one standard
LZ4 block (offsets <= 65535, the last sequence literals only). The encoder is deterministic (greedy, hash chains of
fixed depth, lazy step of one byte), so the same input gives the same bytes.

  ss_lz.py pack <in.dat> <out.lz>      write one file (prints sizes)
  ss_lz.py verify <in.dat> <file.lz>   decode and compare
  ss_lz.py set <disc tree> <out dir>   pack SS/*/ss_cmmn.dat and ss_pzzl.dat of an extracted disc tree into
                                       <out dir>/ss/<lang>/*.lz + SHA256SUMS
"""
import hashlib, os, struct, sys, zlib

MAGIC = b'SSLZ'
MINMATCH = 4
WINDOW = 65535
DEPTH = 32


def lz4_compress(src):
    n = len(src)
    out = bytearray()
    head = {}
    prev = [0] * n
    anchor = 0
    i = 0
    limit = n - 12  # LZ4: the last match starts at least 12 bytes before the end

    def insert(p):
        k = src[p:p + 4]
        prev[p] = head.get(k, -1)
        head[k] = p

    def best(p):
        k = src[p:p + 4]
        c = head.get(k, -1)
        bl, bo, d = 0, 0, 0
        maxl = n - 5 - p  # the last 5 bytes are literals
        while c >= 0 and p - c <= WINDOW and d < DEPTH:
            if src[c:c + 4] == k:
                l = 4
                while l < maxl and src[c + l] == src[p + l]:
                    l += 1
                if l > bl:
                    bl, bo = l, p - c
                    if l >= maxl:
                        break
            c = prev[c]
            d += 1
        return bl, bo

    def emit(lit_from, lit_to, ml, off):
        ln = lit_to - lit_from
        tok_l = 15 if ln >= 15 else ln
        tok_m = 0
        if ml:
            m = ml - MINMATCH
            tok_m = 15 if m >= 15 else m
        out.append(tok_l << 4 | tok_m)
        if ln >= 15:
            v = ln - 15
            while v >= 255:
                out.append(255); v -= 255
            out.append(v)
        out.extend(src[lit_from:lit_to])
        if ml:
            out.extend(struct.pack('<H', off))
            m = ml - MINMATCH
            if m >= 15:
                v = m - 15
                while v >= 255:
                    out.append(255); v -= 255
                out.append(v)

    while i < limit:
        bl, bo = best(i)
        if bl >= MINMATCH and i + 1 < limit:
            insert(i)
            bl2, bo2 = best(i + 1)
            if bl2 > bl + 1:
                i += 1
                bl, bo = bl2, bo2
            else:
                prev_i = i
                emit(anchor, i, bl, bo)
                for p in range(prev_i + 1, min(i + bl, limit)):
                    insert(p)
                i += bl
                anchor = i
                continue
        if bl >= MINMATCH:
            emit(anchor, i, bl, bo)
            for p in range(i, min(i + bl, limit)):
                insert(p)
            i += bl
            anchor = i
            continue
        insert(i)
        i += 1
    emit(anchor, n, 0, 0)
    return bytes(out)


def lz4_decompress(blk, raw_size):
    out = bytearray()
    i = 0
    while i < len(blk):
        t = blk[i]; i += 1
        ln = t >> 4
        if ln == 15:
            while True:
                b = blk[i]; i += 1; ln += b
                if b != 255:
                    break
        out += blk[i:i + ln]; i += ln
        if i >= len(blk):
            break
        off = blk[i] | blk[i + 1] << 8; i += 2
        ml = t & 15
        if ml == 15:
            while True:
                b = blk[i]; i += 1; ml += b
                if b != 255:
                    break
        ml += MINMATCH
        assert 0 < off <= len(out)
        for _ in range(ml):
            out.append(out[-off])
    assert len(out) == raw_size, (len(out), raw_size)
    return bytes(out)


def pack(raw):
    blk = lz4_compress(raw)
    assert lz4_decompress(blk, len(raw)) == raw
    return MAGIC + struct.pack('<III', len(raw), len(blk), zlib.crc32(raw) & 0xffffffff) + blk


def unpack(data):
    assert data[:4] == MAGIC
    raw_size, blk_size, crc = struct.unpack('<III', data[4:16])
    raw = lz4_decompress(data[16:16 + blk_size], raw_size)
    assert zlib.crc32(raw) & 0xffffffff == crc
    return raw


def main(a):
    if a[0] == 'pack':
        raw = open(a[1], 'rb').read()
        d = pack(raw)
        open(a[2], 'wb').write(d)
        print('%s %d -> %d B (%.1f%%)' % (a[2], len(raw), len(d), 100.0 * len(d) / len(raw)))
    elif a[0] == 'verify':
        ok = unpack(open(a[2], 'rb').read()) == open(a[1], 'rb').read()
        print('VERIFY', 'OK' if ok else 'FAIL', a[2])
        return 0 if ok else 1
    elif a[0] == 'set':
        tree, out = a[1], a[2]
        sums = []
        ss = os.path.join(tree, 'ss')
        if not os.path.isdir(ss):
            ss = os.path.join(tree, 'SS')
        for lang in sorted(os.listdir(ss)):
            for base in ('ss_cmmn', 'ss_pzzl'):
                src = None
                for nm in (base + '.dat', base.upper() + '.DAT'):
                    p = os.path.join(ss, lang, nm)
                    if os.path.isfile(p):
                        src = p
                if not src:
                    continue
                raw = open(src, 'rb').read()
                d = pack(raw)
                rel = 'ss/%s/%s.lz' % (lang.lower(), base)
                os.makedirs(os.path.dirname(os.path.join(out, rel)), exist_ok=True)
                open(os.path.join(out, rel), 'wb').write(d)
                sums.append('%s  %s' % (hashlib.sha256(d).hexdigest(), rel))
                print('%s %d -> %d B (%.1f%%) src sha256 %s' % (rel, len(raw), len(d), 100.0 * len(d) / len(raw),
                                                               hashlib.sha256(raw).hexdigest()[:16]))
        open(os.path.join(out, 'SHA256SUMS'), 'w').write('\n'.join(sums) + '\n')
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
