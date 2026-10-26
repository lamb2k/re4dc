#!/usr/bin/env python3
"""ps2_ganado_bins.py: PS2 geometry for the GameCube model members (BIN entries) left in a prepared Ganado archive
(emNN.drs; lane gcleft26 2026-10-26, no-GameCube-assets rule).

PROVENANCE_FOLLOW_BYTES=1 (gc_port23/provenance.py) showed the release's em11..em17 archives still carry the GameCube
BINs of the Ganado bodies, heads, hands, weapons and props: the sets that touched those archives (acc12d: the cObj12
accessories; pmgan24: motion) changed other members only. This tool does for every remaining BIN what
ps2_accessories.py does for ARC 0x25F..0x268:

  geometry  ps2_objects.rebuild(GC BIN, PS2 BIN of the same ARC in BIO4DAT emNN.dat): a GameCube-format ModelData (GC
            header, joints, weight palette and part headers kept, so every source info the game and the native cast
            bind stays where it was) with the PS2 positions, normals, UVs and triangles (the PS2 models are the reduced
            ones: e.g. em12 ARC 0x1bc 1,460 -> 610 triangles), then le_mirror's BIN conversion (to_le).

A member is converted only when the prepared archive's bytes are exactly the le_mirror form of the GC BIN (anything
another set already changed is left alone) and the rebuilt BIN fits the member's own slot: it is written in place and
the slot's tail is zero filled, so no entry moves and every NTR / ESQ / MTC row and the payload size stay unchanged.
A member whose rebuilt BIN is larger than its slot gets the smallest window of neighbouring entries (up to 9; the
converted ones trimmed to their rebuilt size) re-laid out in place by ps2_accessories.relayout (source order, window size
kept, NTR rows rebased; refused when an ESQ / MTC row points into it); with no such window it is reported, not converted. Pictures are untouched: the BINs keep
their TPL references (the archive TPLs / tex.pak keys are handled by the picture sets). Disc data only.

  ps2_ganado_bins.py build --release <prepared emNN.drs> --gc <GC emNN.drs> --ps2 <PS2 emNN.dat> --out <new .drs>
                           [--json report.json] [--only 0x1bc,...]
Report: per member GC / PS2 / output triangles and vertices (positions), bytes, and the members left GC with the reason.
"""
import argparse, hashlib, json, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ps2_accessories as pa  # noqa: E402

po = pa.po


def sha(b):
    return hashlib.sha256(b).hexdigest()


def build(a):
    rel = Path(a.release).read_bytes()
    P = pa.Payload(rel)
    gc, ps2 = pa.gc_entries(a.gc), pa.ps2_entries(a.ps2)
    only = {int(x, 16) for x in a.only.split(',')} if a.only else None
    rep = dict(release=a.release, release_sha256=sha(rel), gc=a.gc, ps2=a.ps2, converted={}, left={})
    big, done = {}, {}
    for arc, (t, g) in sorted(gc.items()):
        if t != 'BIN' or arc - 4 >= P.count or not P.tags[arc - 4] or (only and arc not in only):
            continue
        i = arc - 4
        start, end = P.offs[i], P.end(i)
        have = bytes(P.body[start:end])
        gle = po.to_le(g, 'gc%x' % arc)
        if have[:len(gle)] != gle or have[len(gle):].strip(b'\0'):
            continue  # not the GC bytes (another set's member, or already PS2)
        pt, p = ps2.get(arc, ('', b''))
        if pt != 'BIN':
            rep['left']['%#x' % arc] = 'no PS2 BIN at this ARC (%s)' % (pt or 'absent')
            continue
        try:
            new, st = po.rebuild(g, p)
        except Exception as e:  # noqa
            rep['left']['%#x' % arc] = 'rebuild refused: %s' % e
            continue
        le = po.to_le(new, 'ps2%x' % arc)
        row = dict(gc_tris=st['gc_tris'], ps2_tris=st['ps2_tris'], out_tris=st['out_tris'],
                   gc_verts=st['gc_vertices'], out_verts=st['out_vertices'],
                   gc_bytes=len(gle), out_bytes=len(le), slot=end - start,
                   flipped=st['flipped'], weight_mismatch=st['weight_mismatch'],
                   degenerate=st['degenerate'], gc_sha256=sha(gle), out_sha256=sha(le))
        if len(le) > end - start:
            big[arc] = (le, row)
            continue
        P.body[start:end] = le + bytes(end - start - len(le))
        done[arc] = le
        rep['converted']['%#x' % arc] = row
    # a rebuilt BIN larger than its slot: re-lay out the smallest window of neighbouring entries (the converted ones
    # trimmed to their rebuilt size) that holds it (ps2_accessories.relayout: entries keep source order, the window keeps
    # its size, NTR rows rebased, ESQ / MTC rows may not point into it)
    for arc, (le, row) in sorted(big.items()):
        ok = False
        allt = [x for x in range(4, P.count + 4) if P.tags[x - 4]]
        k = allt.index(arc)
        for width in range(1, 9):
            for s in range(max(0, k - width), k + 1):
                tagged = allt[s:s + width + 1]
                if arc not in tagged or len(tagged) != width + 1:
                    continue
                lo, hi = tagged[0], tagged[-1]
                bins = {x: (done[x],) for x in tagged if x in done}
                bins[arc] = (le,)
                save = (bytes(P.body), list(P.offs), pa.SPAN)
                try:
                    pa.SPAN = (lo, hi)
                    lay = pa.relayout(P, bins)
                    ok = True
                except ValueError:
                    P.body[:] = save[0]
                    P.offs[:] = save[1]
                finally:
                    pa.SPAN = save[2]
                if ok:
                    row['relayout'] = dict(window=['%#x' % lo, '%#x' % hi], ntr_rows_rebased=lay['ntr_rows_rebased'])
                    done[arc] = le
                    rep['converted']['%#x' % arc] = row
                    break
            if ok:
                break
        if not ok:
            rep['left']['%#x' % arc] = 'rebuilt BIN %d B > slot %d B and no window of <= 9 entries holds it' % (len(le), row['slot'])
    why = pa.adopt_check(bytes(P.body))
    if why:
        raise ValueError('output payload fails the runtime NTR check: %s' % why)
    out = P.bytes()
    if len(out) != len(rel):
        raise ValueError('archive size changed')
    Path(a.out).write_bytes(out)
    c = rep['converted']
    rep.update(out=a.out, out_sha256=sha(out), tool_sha256=sha(Path(__file__).read_bytes()),
               totals=dict(members=len(c), gc_tris=sum(m['gc_tris'] for m in c.values()),
                           out_tris=sum(m['out_tris'] for m in c.values()),
                           gc_verts=sum(m['gc_verts'] or 0 for m in c.values()),
                           out_verts=sum(m['out_verts'] or 0 for m in c.values()), left=len(rep['left'])))
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1))
    for arc, m in c.items():
        print('BIN %s tris %d -> %d verts %s -> %s bytes %d -> %d' % (arc, m['gc_tris'], m['out_tris'], m['gc_verts'],
                                                                    m['out_verts'], m['gc_bytes'], m['out_bytes']))
    for arc, w in rep['left'].items():
        print('LEFT %s %s' % (arc, w))
    print('TOTAL', json.dumps(rep['totals']))
    print(a.out, rep['out_sha256'])


def main():
    ap = argparse.ArgumentParser()
    s = ap.add_subparsers(dest='cmd', required=True)
    b = s.add_parser('build')
    for k in ('--release', '--gc', '--ps2', '--out'):
        b.add_argument(k, required=True)
    b.add_argument('--json')
    b.add_argument('--only')
    a = ap.parse_args()
    build(a)


if __name__ == '__main__':
    main()
