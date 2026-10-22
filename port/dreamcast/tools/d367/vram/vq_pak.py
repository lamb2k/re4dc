#!/usr/bin/env python3
"""vq_pak.py <in tex.pak> <out tex.pak> <work dir> <key>...  (lane vram12, 2026-10-14)
Re-encodes the named single-texture twiddled 16-bit packages of a tex.pak as full-codebook VQ with the pinned KOS
pvrtex (tools/vq_native_ui.py encode: same key, same native size and 16-bit format, 2048 + w*h/4 bytes), writes a
new tex.pak (tools/d367/texpack.py build + verify) and keeps per key the source / VQ preview PNGs and a JSON report
(PSNR over the whole image, alpha-weighted). Offline data only: nothing the game reads changes except these
packages' payloads. Private outputs: nothing produced here belongs in Git."""
import json, pathlib, struct, sys
T = str(pathlib.Path(__file__).resolve().parents[2])
sys.path.insert(0, T)
sys.path.insert(0, T + '/d367')
import vq_native_ui as vq   # noqa: E402
import texpack             # noqa: E402

PAK_MAGIC = b'RE4PAK1' + bytes(1)


def read_pak(blob):
    magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', blob, 0)
    assert magic == PAK_MAGIC, magic
    out = {}
    for i in range(count):
        c, f, o, n = struct.unpack_from('<4I', blob, ioff + 16 * i)
        out[(c, f)] = blob[o:o + n]
    return out


def restamp(src, new):
    """The VQ package with the source package's material name and flags (Package::find looks materials up by
    name) and the canonical runtime CRC over descriptors and payload."""
    import zlib
    tpl = vq.tpl
    sh, nh = list(tpl.HEADER.unpack_from(src)), list(tpl.HEADER.unpack_from(new))
    st, nt = list(tpl.TEXTURE.unpack_from(src, sh[5])), list(tpl.TEXTURE.unpack_from(new, nh[5]))
    if sh[8] == zlib.crc32(src[tpl.HEADER.size:]) & 0xffffffff:
        rule = 'header'
    elif sh[8] == zlib.crc32(src[sh[6]:]) & 0xffffffff:
        rule = 'data'
    else:
        raise SystemExit('source CRC rule unknown')
    nt[0], nt[6] = st[0], st[6]
    body = tpl.TEXTURE.pack(*nt) + new[nh[6]:]
    nh[8] = zlib.crc32(body) & 0xffffffff
    return tpl.HEADER.pack(*nh) + body, rule


def main():
    src, dst, work = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    keys = sys.argv[4:]
    pkgs = read_pak(src.read_bytes())
    loose = work / 'src-packages'
    outd = work / 'vq-packages'
    prev = work / 'previews'
    for d in (loose, outd, prev):
        d.mkdir(parents=True, exist_ok=True)
    report = []
    for name in keys:
        k = tuple(int(x, 16) for x in name.split('-'))
        blob = pkgs[k]
        (loose / (name + '.re4tex')).write_bytes(blob)
        w, h, fmt, flags, _ = vq.read_package(blob)
        entry = vq.encode(name, loose, outd, vq.PVRTEX, (w, h), prev)
        entry['source_flags'] = flags
        new, rule = restamp(blob, (outd / (name + '.re4tex')).read_bytes())
        (outd / (name + '.re4tex')).write_bytes(new)
        entry['source_crc_rule'] = rule
        entry['crc_rule'] = 'header'
        entry['package_sha256'] = __import__('hashlib').sha256(new).hexdigest()
        pkgs[k] = new
        report.append(entry)
        print('%s %4dx%-4d %-8s %7d -> %6d  psnr=%.1f dB  flags %#x' % (name, w, h, entry['format'], entry['before_vram'],
              entry['after_vram'], entry['psnr_db'], flags))
    out, _ = texpack.build(pkgs)
    texpack.verify(out)
    dst.write_bytes(out)
    tot = dict(images=len(report), before_vram=sum(e['before_vram'] for e in report),
               after_vram=sum(e['after_vram'] for e in report), source_pak=str(src), out_pak=str(dst))
    (work / 'vq-report.json').write_text(json.dumps(dict(summary=tot, images=report), indent=2) + '\n')
    print('total', tot)


if __name__ == '__main__':
    main()
