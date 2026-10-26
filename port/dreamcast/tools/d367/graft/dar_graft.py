#!/usr/bin/env python3
"""dar_graft.py: member-level graft of ETM sub-files into a composed native room archive (lane fix-r100-props26 10-26).

  dar_graft.py <composed .dar> <member source .dar> <name,name,...> <out .dar> [--json OUT]

Names: ETM sub-files ("et0000.bin") and/or whole tagged entries in member_census naming ("0x37 EFF"); a graft of a whole
entry that a native table row points into is refused unless the bytes there are unchanged (remap_native_tables).

A data set that changes a few members of a room archive (windows26: the window panes) must not replace the whole
archive: whole-file replacement at its place in DATA throws away every later set's work on the same archive (pmrest25's
motions) and anything the rebuild touched (prebuilt sound banks, models). A graft runs at staging time on the archive
ALL sets composed (t11-fix.py applies DATA[...]['graft'] after the last set), and copies in only the named ETM sub-files,
each byte for byte from the source archive (its 0x40 record header + body). Every other member stays byte-identical; the
NTR / ESQ native tables are rebased by ps2_objects.remap_native_tables when the ETM entry changes size (each row is
checked to still name the same bytes). verify() proves it member by member (member_census.dar_members).
"""
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent), str(HERE.parent), str(HERE.parent / 'rr')]
import room_smd as rs  # noqa: E402
import ps2_objects as po  # noqa: E402
from member_census import dar_members  # noqa: E402


def _payload(dar):
    kind, size, dest, off = struct.unpack_from('<4I', dar, 0x20)
    if kind != 0 or off + size > len(dar):
        raise ValueError('not a native room archive')
    return off, dar[off:off + size]


def _etm(pay):
    ents = rs.tagged_entries(pay, '<')
    hits = [i for i, (t, s, e) in enumerate(ents) if t.rstrip(b'\0') == b'ETM']
    if len(hits) != 1:
        raise ValueError('archive has %d ETM entries' % len(hits))
    i = hits[0]
    return i, pay[ents[i][1]:ents[i][2]]


def graft(composed, source, names):
    """-> (out .dar bytes, report). names: ETM sub-file names copied from source, and/or whole tagged entries named as
    member_census does ("0x37 EFF": entry index 0x37-4 with that tag in both archives), copied whole."""
    off, pay = _payload(composed)
    _, spay = _payload(source)
    whole = [n for n in names if n.startswith('0x')]
    names = [n for n in names if not n.startswith('0x')]
    rep_entries, report = {}, []
    if whole:
        pe, se = rs.tagged_entries(pay, '<'), rs.tagged_entries(spay, '<')
        for w in whole:
            idx, tag = w.split(' ', 1)
            i = int(idx, 16) - 4
            if pe[i][0].rstrip(b'\0').decode('latin1') != tag or se[i][0].rstrip(b'\0').decode('latin1') != tag:
                raise ValueError('graft %s: entry tag differs' % w)
            rep_entries[i] = spay[se[i][1]:se[i][2]]
            report.append(dict(name=w, bytes_before=pe[i][2] - pe[i][1], bytes_after=len(rep_entries[i]),
                               same=rep_entries[i] == pay[pe[i][1]:pe[i][2]]))
    if not names:
        newpay = po.rebuild_tagged(pay, '<', rep_entries)
        newpay, tables = po.remap_native_tables(pay, newpay, {})
        out = bytearray(composed[:off]) + newpay
        out += bytes(po.al(len(out), 2048) - len(out))
        struct.pack_into('<4I', out, 0x20, 0, len(newpay), 0, off)
        return bytes(out), dict(grafted=report, native_tables=tables, payload_before=len(pay), payload_after=len(newpay))
    ei, etm = _etm(pay)
    _, setm = _etm(spay)
    src = {n: setm[a:z] for n, a, z in po.etm_entries(setm, '<')}
    ents = po.etm_entries(etm, '<')
    if ents[0][1] != 0x20 or ents[-1][2] != len(etm):
        raise ValueError('ETM sub-files do not tile the entry')
    want = set(names)
    have = {n for n, a, z in ents}
    if want - have or want - set(src):
        raise ValueError('graft names missing: composed %s source %s' % (sorted(want - have), sorted(want - set(src))))
    new = bytearray(etm[:0x20])
    moves = [(0, 0x20, 0, False)]
    for n, a, z in ents:
        body = etm[a:z]
        if n in want:
            nb = bytearray(src[n])
            last = struct.unpack_from('<I', body, 0)[0] == 0
            nb += bytes(po.al(len(nb)) - len(nb))
            struct.pack_into('<I', nb, 0, 0 if last else len(nb))
            report.append(dict(name=n, bytes_before=len(body), bytes_after=len(nb), same=bytes(nb) == body))
            body = bytes(nb)
        moves.append((a, z, len(new), n in want))
        new += body
    new += bytes(po.al(len(new)) - len(new))
    rep_entries[ei] = bytes(new)
    newpay = po.rebuild_tagged(pay, '<', rep_entries)
    newpay, tables = po.remap_native_tables(pay, newpay, {ei: moves})
    out = bytearray(composed[:off]) + newpay
    out += bytes(po.al(len(out), 2048) - len(out))
    struct.pack_into('<4I', out, 0x20, 0, len(newpay), 0, off)
    return bytes(out), dict(grafted=report, native_tables=tables, payload_before=len(pay), payload_after=len(newpay))


def verify(composed, out, names, source=None):
    """Member identity: every member except ETM/<names> (and NTR / ESQ, rebased) byte-identical to the composed archive;
    the grafted members equal the source's. -> list of problems (empty = proven)."""
    a, b = dar_members(composed), dar_members(out)
    allowed = {n if n.startswith('0x') else 'ETM/' + n for n in names}
    bad = []
    for m in sorted(set(a) | set(b)):
        if a.get(m) == b.get(m) or m in allowed:
            continue
        if m.split(' ', 1)[-1] in ('NTR', 'ESQ') and m in a and m in b:
            continue  # rebased offsets only (remap_native_tables checked every row)
        bad.append('%s %s' % (m, 'added' if m not in a else 'removed' if m not in b else 'changed'))
    if source is not None:
        s = dar_members(source)
        key = lambda n: n if n.startswith('0x') else 'ETM/' + n
        bad += ['%s differs from the source' % key(n) for n in names if b.get(key(n)) != s.get(key(n))]
    return bad


def main():
    a = sys.argv[1:]
    js = None
    if '--json' in a:
        i = a.index('--json'); js = a[i + 1]; del a[i:i + 2]
    comp, srcp, names, outp = Path(a[0]).read_bytes(), Path(a[1]).read_bytes(), a[2].split(','), a[3]
    out, rep = graft(comp, srcp, names)
    bad = verify(comp, out, names, srcp)
    rep['verify'] = bad
    Path(outp).write_bytes(out)
    if js:
        Path(js).write_text(json.dumps(rep, indent=1))
    print('GRAFT %s %s: %s; members %s' % ('OK' if not bad else 'FAIL', outp, ', '.join(
        '%s %d->%d' % (g['name'], g['bytes_before'], g['bytes_after']) for g in rep['grafted']), 'identical' if not bad else bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
