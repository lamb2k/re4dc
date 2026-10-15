import sys, hashlib, struct
sys.path[:0] = ['/root/probe/lanes-20261014/ps2cast/tree/tools']
import drs
R = '/root/probe/lanes-20261014/fullplay/work/rel-36cb116398e91c40/tree/em/'
I = '/root/probe/lanes/ps2cast/inputs/'
def le_entries(b):
    # DVD container: 32-byte magic then 32-byte headers (type,size,dest,ofs,...) LE; find the tagged archive
    for end in ('<', '>'):
        try:
            g = drs.Drs(b) if end == '>' else None
            if g: return [(drs.tag_name(t), x) for t, x in g.entries]
        except Exception:
            pass
    # LE: walk DvdHeaders
    out = None
    for k in range(32, 32 * 64, 32):
        typ, size, dest, ofs = struct.unpack_from('<4I', b, k)
        if typ == 0xFFFFFFFF: break
        arc = b[ofs:ofs + size]
        if len(arc) < 16: continue
        n = struct.unpack_from('<I', arc, 0)[0]
        if not 0 < n < 4096: continue
        offs = struct.unpack_from('<%dI' % n, arc, 16)
        tags = [arc[16 + 4 * n + 4 * i:16 + 4 * n + 4 * i + 4] for i in range(n)]
        ends = list(offs[1:]) + [len(arc)]
        cand = [(t.rstrip(b'\0').decode('latin1'), arc[o:e]) for t, o, e in zip(tags, offs, ends)]
        if out is None or len(cand) > len(out): out = cand
    return out
sel = {'em2a': [4, 5, 8, 9], 'em29': [4, 5], 'em2e': [4, 5, 6], 'em27': [4, 5], 'em24': [5, 6], 'pl0f': [5, 6],
       'em11': [0x1fc, 0x1fd, 0x1fe, 0x201, 0x204, 0x208], 'em13': [0x1e7, 0x1e8, 0x1f0, 0x1f1, 0x1ee, 0x1ed, 0x1ef, 0x1e9, 0x1ea, 0x1f4, 0x1f8]}
for a, arcs in sel.items():
    gb, rb = open(I + a + '.drs', 'rb').read(), open(R + a + '.drs', 'rb').read()
    g, r = le_entries(gb), le_entries(rb)
    rows = []
    for arc in arcs:
        tg, bg = g[arc - 4]; tr, br = r[arc - 4]
        rows.append('%x:%s/%s:%s' % (arc, tg, tr, 'same' if bg[:len(br)] == br and len(bg) >= len(br) - 32 else 'DIFF(%d/%d)' % (len(bg), len(br))))
    print(a, 'in', hashlib.sha256(gb).hexdigest()[:12], 'rel', hashlib.sha256(rb).hexdigest()[:12], ' '.join(rows))
