#!/usr/bin/env python3
"""src_blob_patch.py: registry packages that name PS2-derived source BINs (lane srcgeo, 2026-11-17, no-GameCube-assets rule).

Problem: the native cast (actor_lifetime.inc re4dc_actor_archive_adopt) adopts a source model only when the archive entry's
whole little-endian BIN digests to a registry SBlob row (digest of the first `normalized.bytes` bytes), and then proves each
source part (coarse_actor_material.inc info(): the ten header words, then per part the 13 material bytes, display-list
bytes and polygon count). ps2_ganado_bins.py therefore had to keep every BIN a package names as GameCube bytes
("native cast source BIN: kept"). The cast DRAWS its own PS2 geometry from the package; the source BIN is identity,
skeleton and material facts only.

This tool carries the same facts for the PS2-derived BIN instead. For every source model of a room package
(fmodel / fpart / sblob rows) it
  1. finds the archive BIN the SBlob row digests (searching the GameCube-form prepared archives given with --arc);
  2. takes the PS2-derived GC-format ModelData that ps2_objects.rebuild() makes from (GC BIN, PS2 BIN of the same ARC), the
     same bytes ps2_ganado_bins.py writes into the archive (checked against the converted archive);
  3. recomputes the rows with model_registry.bin_facts (the generator's own rules) and rewrites fmodel / fpart / sblob in
     place. Counts and sizes do not change (part headers are kept by rebuild), so the layout, geometry, textures, roles and
     skeleton stay byte-identical; only the payload crc / fnv and the header crc are refreshed.
A BIN the converted archive still carries as GameCube bytes keeps its row. Self-check: the GC BIN's facts must reproduce the
package's existing row exactly before it is replaced.

  src_blob_patch.py --tree <checkout> --pkg in.re4nmr --out out.re4nmr
        --arc name=<prepared GC-form em.drs>:<converted em.drs>:<GC em.drs>:<PS2 em.dat> [--arc ...] [--json report.json]
"""
import argparse, hashlib, json, os, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
D367 = HERE.parent
sys.path[:0] = [str(HERE), str(D367)]
import model_registry as mr  # noqa: E402
import ps2_accessories as pa  # noqa: E402

po = pa.po
K = ['desc', 'ref', 'geom', 'blob', 'tex', 'parents', 'bind', 'fmodel', 'fpart', 'ftex', 'role', 'sblob']


class _Ent:
    def __init__(self, tag, data):
        self.tag, self.data = tag, data


class _Arc:
    """model_registry.bin_facts' archive shim over one big-endian BIN."""

    def __init__(self, no, data):
        self.no, self.data = no, data

    def entry(self, idx):
        assert idx == self.no - 4
        return _Ent('BIN', self.data)


def load_arc(spec, tree):
    name, rest = spec.split('=', 1)
    old, new, gcp, ps2p = rest.split(':')
    return dict(name=name, old=pa.Payload(Path(old).read_bytes()), new=pa.Payload(Path(new).read_bytes()),
                gc=pa.gc_entries(gcp), ps2=pa.ps2_entries(ps2p))


def facts_of(be_bin, no, le_mirror):
    return mr.bin_facts(_Arc(no, be_bin), le_mirror, 'src', no)


def patch(pkg, arcs, le_mirror):
    b = bytearray(pkg)
    if bytes(b[:8]) != mr.PACK_MAGIC:
        raise SystemExit('not a registry package')
    sec = {}
    for k in range(12):
        _kind, off, n, cnt = struct.unpack_from('<4I', b, 64 + 16 * k)
        sec[K[k]] = (off, n, cnt)
    fm_off, _, fm_cnt = sec['fmodel']
    fp_off, _, fp_cnt = sec['fpart']
    sb_off, _, sb_cnt = sec['sblob']
    rep = dict(models=[], kept_gc=[], selfcheck_fail=[])
    for u in range(sb_cnt):
        fm, fam, bn, nbytes, crc, fnv, _, _ = struct.unpack_from('<8I', b, sb_off + 32 * u)
        want = [nbytes, crc, fnv]
        hit = None
        for a in arcs:
            if bn - 4 < a['old'].count and a['old'].tags[bn - 4] == 'BIN':
                e = a['old'].entry(bn)
                if len(e) >= nbytes and mr.digest(e[:nbytes]) == want:
                    hit = a
                    break
        if hit is None:
            rep['kept_gc'].append(dict(bin=bn, why='no listed archive carries this digest'))
            continue
        gt, g = hit['gc'].get(bn, ('', b''))
        pt, p = hit['ps2'].get(bn, ('', b''))
        if gt != 'BIN' or pt != 'BIN':
            rep['kept_gc'].append(dict(bin=bn, archive=hit['name'], why='no PS2 BIN at this ARC'))
            continue
        # self-check: the GC BIN's facts are the package's current row
        gf = facts_of(g, bn, le_mirror)
        mrow = fm_off + 96 * fm
        cur = struct.unpack_from('<24I', b, mrow)
        want_row = [*gf['header'], *gf['positions'], *gf['normals'], *gf['weights'], *gf['uv']]
        if list(cur[:22]) != want_row[:22] or list(cur[22:24]) != [cur[22], gf['header'][8]] or gf['normalized'] != want:
            rep['selfcheck_fail'].append(dict(bin=bn, archive=hit['name']))
            continue
        try:
            new_be, st = po.rebuild(g, p)
        except Exception as e:  # noqa: same refusals ps2_ganado_bins reports as "rebuild refused"
            rep['kept_gc'].append(dict(bin=bn, archive=hit['name'], why='rebuild refused: %s' % e))
            continue
        new_le = po.to_le(new_be, 'ps2%x' % bn)
        have = hit['new'].entry(bn)
        if have[:len(new_le)] != new_le or have[len(new_le):].strip(b'\0'):
            rep['kept_gc'].append(dict(bin=bn, archive=hit['name'], why='converted archive does not carry the rebuilt BIN'))
            continue
        nf = facts_of(new_be, bn, le_mirror)
        if len(nf['parts']) != gf['header'][8] or len(nf['parts']) != len(gf['parts']) or \
                nf['header'][8] != gf['header'][8]:
            raise SystemExit('bin %#x: part count changed' % bn)
        # the 13 material bytes of every part are kept by rebuild; the proof compares them
        if [x[0] for x in nf['parts']] != [x[0] for x in gf['parts']]:
            raise SystemExit('bin %#x: part material bytes changed' % bn)
        # The row names one digest for every archive that carries these GameCube bytes: another listed archive with the same
        # old BIN (em1d / em1e / em1f share some) must rebuild to the same new BIN, or the cast would adopt one and not the other.
        clash = None
        for other in arcs:
            if other is hit or bn - 4 >= other['old'].count or other['old'].tags[bn - 4] != 'BIN':
                continue
            oe = other['old'].entry(bn)
            if len(oe) < nbytes or mr.digest(oe[:nbytes]) != want:
                continue
            ot, op = other['ps2'].get(bn, ('', b''))
            try:
                if ot != 'BIN':
                    raise ValueError('no PS2 BIN')
                onb, _ost = po.rebuild(g, op)
                same = po.to_le(onb, 'ps2%x' % bn) == new_le
            except Exception as e:  # noqa
                same, clash = False, 'archive %s: %s' % (other['name'], e)
            if not same:
                clash = clash or 'archive %s rebuilds differently' % other['name']
                break
        if clash:
            rep['kept_gc'].append(dict(bin=bn, archive=hit['name'], why='shared GameCube BIN, ' + clash))
            continue
        first = cur[22]
        row = [*nf['header'], *nf['positions'], *nf['normals'], *nf['weights'], *nf['uv']]
        struct.pack_into('<24I', b, mrow, *row, first, len(nf['parts']))
        for k, (material, size, poly, pcrc, pfnv) in enumerate(nf['parts']):
            struct.pack_into('<16sIIII', b, fp_off + 32 * (first + k), bytes.fromhex(material).ljust(16, b'\0'), size, poly, pcrc, pfnv)
        struct.pack_into('<III', b, sb_off + 32 * u + 12, *nf['normalized'])
        rep['models'].append(dict(bin=bn, archive=hit['name'], gc_bytes=nbytes, out_bytes=nf['normalized'][0],
                                  gc_tris=st['gc_tris'], out_tris=st['out_tris']))
    # payload crc / fnv (header words 9, 10) and the header crc (word 11, over the header with that word zero)
    rest = bytes(b[64:])
    pcrc, pfnv = mr.pack_crc_fnv(rest)
    struct.pack_into('<II', b, 36, pcrc, pfnv)
    head = bytearray(b[:64])
    struct.pack_into('<I', head, 44, 0)
    struct.pack_into('<I', b, 44, zlib.crc32(bytes(head)) & 0xffffffff)
    return bytes(b), rep


def verify_rows(pkg, arcs):
    """What re4dc_actor_archive_adopt will see: every SBlob row of the (patched) package against the converted archives.
    ok-new = an output archive carries the digested bytes (the PS2-derived BIN); ok-gc = the row digests GameCube bytes the output
    archive still carries; CLASH = the row digests GameCube bytes whose archive BIN was converted (the cast would decline it: a
    CAST-GC regression); external = no listed archive has that BIN (an archive this set does not carry)."""
    b = bytes(pkg)
    sb_off, _, sb_cnt = struct.unpack_from('<4I', b, 64 + 16 * 11)[1:4]
    out = dict(ok_new=0, ok_gc=0, clash=[], external=[])
    for u in range(sb_cnt):
        _fm, _fam, bn, n, c, f, _, _ = struct.unpack_from('<8I', b, sb_off + 32 * u)
        want, verdict = [n, c, f], None
        for a in arcs:
            if bn - 4 >= a['new'].count or a['new'].tags[bn - 4] != 'BIN':
                continue
            ne = a['new'].entry(bn)
            if len(ne) >= n and mr.digest(ne[:n]) == want:
                verdict = 'ok_gc' if bn - 4 < a['old'].count and a['old'].entry(bn)[:n] == ne[:n] else 'ok_new'
                break
            oe = a['old'].entry(bn) if bn - 4 < a['old'].count and a['old'].tags[bn - 4] == 'BIN' else b''
            if len(oe) >= n and mr.digest(oe[:n]) == want:
                verdict = 'clash'
        if verdict in ('ok_new', 'ok_gc'):
            out[verdict] += 1
        elif verdict == 'clash':
            out['clash'].append(bn)
        else:
            out['external'].append(bn)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', required=True, help='checkout (le_mirror lives under <tree>/tools)')
    ap.add_argument('--pkg', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--arc', action='append', required=True)
    ap.add_argument('--json')
    a = ap.parse_args()
    _archive, _parse_tpl, le_mirror = mr.archive_facts(a.tree)
    arcs = [load_arc(s, a.tree) for s in a.arc]
    out, rep = patch(Path(a.pkg).read_bytes(), arcs, le_mirror)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(out)
    rep.update(pkg=a.pkg, out=a.out, in_sha256=hashlib.sha256(Path(a.pkg).read_bytes()).hexdigest(),
               out_sha256=hashlib.sha256(out).hexdigest())
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + '\n')
    print('%s: %d models re-rowed, %d kept GC, %d self-check failures' % (os.path.basename(os.path.dirname(a.pkg)) or a.pkg,
          len(rep['models']), len(rep['kept_gc']), len(rep['selfcheck_fail'])))


if __name__ == '__main__':
    main()
