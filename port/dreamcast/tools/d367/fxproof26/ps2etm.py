"""PS2 ETM members (room .dat ETM entry): header 0x20 (u32 size incl. name, u32 type), name 0x20, data. Lane fxproof26."""
import struct, sys
sys.path.insert(0, '/root/work/lanes/fxproof26')
sys.path.insert(0, '/root/work/lanes/fxproof26/wt/port/dreamcast/tools/d367/test12fx')
import ps2afs
import fx_ps2_pack as F


def members(m):
    n = struct.unpack_from('<I', m, 0)[0]
    off, out = 0x20, []
    for _ in range(n):
        if off + 0x40 > len(m):
            break
        size, typ = struct.unpack_from('<II', m, off)
        name = m[off + 0x20:off + 0x40].split(b'\0')[0].decode('latin1')
        out.append((name, typ, off + 0x40, off + size))
        if size == 0:
            break
        off += size
    return out


def eff_ids(e):
    hdr = struct.unpack_from('<12I', e, 0)
    o = hdr[1]
    n = struct.unpack_from('<I', e, o)[0]
    return [struct.unpack_from('<H', e, o + 4 + 8 * i)[0] for i in range(n)]


if __name__ == '__main__':
    ents = ps2afs.entries()
    for k in sorted(ents):
        if not (k.startswith('BIO4DAT.AFS:r') and k.endswith('.dat')):
            continue
        b = ps2afs.read(k)
        try:
            de = F.dat_entries(b)
        except Exception:
            continue
        for i, (t, o, e) in enumerate(de):
            if t != 'ETM':
                continue
            for name, typ, a, z in members(b[o:e]):
                if name.endswith('.eff'):
                    eb = b[o + a:o + z]
                    try:
                        ids = eff_ids(eb)
                    except Exception as ex:
                        ids = 'ERR %s' % ex
                    print(k.split(':')[1], i, name, hex(a), z - a, [hex(x) for x in ids] if isinstance(ids, list) else ids)
