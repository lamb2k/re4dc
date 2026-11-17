#!/usr/bin/env python3
"""srcgeo_store.py: build the srcgeo data set (lane srcgeo, 2026-11-17): the enemy archives of a disc with every GameCube BIN
member rebuilt as PS2 geometry (ps2_ganado_bins.py, NO cast keep), and every room registry package re-rowed so the native
cast adopts the PS2-derived source BIN (src_blob_patch.py). Disc data only; default off (recipe D3_SRCGEO / D2_SRCGEO).

  srcgeo_store.py --out <store dir> --tree <checkout> --gc-iso <GC iso> --ps2-afs <afs.json> --ps2-iso <PS2 iso>
      --arch name=<release em.drs>  ...          the disc's FINAL archive for each enemy archive to convert
      --pkg room=<final registry package>  ...   the disc's FINAL package of each room (partner.re4nmr: --pkg r205/partner=...)
Writes <store>/em/<name>.drs, <store>/dc/native/<room>/registry.re4nmr, manifest.tsv (disc paths), report/*.json, RECIPE.txt.
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parents[1])]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def base_rows(tree):
    """{(arc): [(bytes, crc, fnv), ...]} of the ELF's compiled family-2 source blob rows (actor_material_records.inc)."""
    import re
    text = (Path(tree) / 'port/dreamcast/game/actor_material_records.inc').read_text()
    out = {}
    for _m, bn, n, c, f in re.findall(r'\{&m_(\w+),2u,(\d+)u,\{(\d+)u,(\d+)u,(\d+)u\}\}', text):
        out.setdefault(int(bn), []).append((int(n), int(c), int(f)))
    return out


def convertible(release, gc_path, tree):
    """ps2_ganado_bins --only list: every GC BIN of the release archive except those a compiled base row digests, or None
    (no restriction) when no BIN of the archive is bound by a base row."""
    import model_registry as mr
    import ps2_accessories as pa
    rows = base_rows(tree)
    P = pa.Payload(Path(release).read_bytes())
    gc = pa.gc_entries(str(gc_path))
    keep, allarcs = set(), []
    for arc, (t, _g) in sorted(gc.items()):
        if t != 'BIN' or arc - 4 >= P.count or not P.tags[arc - 4]:
            continue
        allarcs.append(arc)
        e = P.entry(arc)
        if any(len(e) >= n and mr.digest(e[:n]) == [n, c, f] for n, c, f in rows.get(arc, [])):
            keep.add(arc)
    return None if not keep else (','.join('%x' % a for a in allarcs if a not in keep) or '0')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--tree', required=True)
    ap.add_argument('--gc-iso', default='/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso')
    ap.add_argument('--ps2-afs', required=True, help='json {name: [[offset, size], ...]} of BIO4DAT.AFS (first entry with size > 0 is the file)')
    ap.add_argument('--ps2-iso', default='/mnt/c/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso')
    ap.add_argument('--arch', action='append', default=[])
    ap.add_argument('--pkg', action='append', default=[])
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        raise SystemExit('%s exists' % out)
    (out / 'em').mkdir(parents=True)
    (out / 'report').mkdir()
    sys.path.insert(0, str(Path(a.tree) / 'port/dreamcast/tools'))
    from assetpipe.rooms import GcIso  # noqa: E402
    gc = GcIso(a.gc_iso)
    afs = json.load(open(a.ps2_afs))
    iso = open(a.ps2_iso, 'rb')
    work = Path(tempfile.mkdtemp(prefix='srcgeo-'))
    arcspec, procs = [], []
    for spec in a.arch:
        name, rel = spec.split('=', 1)
        ents = [e for e in afs.get(name + '.dat', []) if e[1] > 0]
        gp = gc.find('em/%s.drs' % name) or gc.find('em/%s.das' % name)
        if not ents or not gp:
            raise SystemExit('%s: no PS2 dat or GC archive' % name)
        iso.seek(ents[0][0])
        (work / (name + '.dat')).write_bytes(iso.read(ents[0][1]))
        (work / (name + '.gc.drs')).write_bytes(gc.read(gp))
        # BINs the ELF's own base rows bind (actor_material_records.inc source_blobs, family 2: em11..em17) keep their GameCube
        # bytes wherever the archive still holds the bytes those rows digest: code constants, not package rows.
        only = convertible(rel, work / (name + '.gc.drs'), a.tree)
        cmd = [sys.executable, str(HERE / 'ps2_ganado_bins.py'), 'build', '--release', rel, '--gc', str(work / (name + '.gc.drs')),
               *(['--only', only] if only is not None else []),
               '--ps2', str(work / (name + '.dat')), '--out', str(out / 'em' / (name + '.drs')),
               '--json', str(out / 'report' / (name + '.json'))]
        procs.append((name, subprocess.Popen(cmd, stdout=open(out / 'report' / (name + '.log'), 'w'), stderr=subprocess.STDOUT)))
        arcspec.append((name, rel, str(out / 'em' / (name + '.drs')), str(work / (name + '.gc.drs')), str(work / (name + '.dat'))))
    for name, p in procs:
        rc = p.wait()
        if rc:
            tail = (out / 'report' / (name + '.log')).read_text()[-600:]
            raise SystemExit('ps2_ganado_bins failed for %s (rc=%s):\n%s' % (name, rc, tail))
    import model_registry as mr  # noqa: E402
    import src_blob_patch as sp  # noqa: E402
    _a, _t, le_mirror = mr.archive_facts(a.tree)
    arcs = [sp.load_arc('%s=%s:%s:%s:%s' % s, a.tree) for s in arcspec]
    manifest = ['em/%s.drs' % s[0] for s in arcspec]
    summary = {}
    for spec in a.pkg:
        room, p = spec.split('=', 1)
        name = room if '/' in room else room + '/registry'
        data, rep = sp.patch(Path(p).read_bytes(), arcs, le_mirror)
        dest = out / 'dc/native' / (name.split('/')[0]) / (name.split('/')[1] + '.re4nmr')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        rep.update(pkg=p, in_sha256=sha(Path(p).read_bytes()), out_sha256=sha(data))
        (out / 'report' / ('pkg-' + name.replace('/', '-') + '.json')).write_text(json.dumps(rep, indent=1) + '\n')
        manifest.append('dc/native/%s.re4nmr' % name)
        summary[name] = (len(rep['models']), len(rep['kept_gc']), len(rep['selfcheck_fail']))
        print('%s: %d re-rowed, %d kept GC, %d self-check failures' % ((name,) + summary[name]))
    # provenance.tsv (gc_port23/provenance.py Store.tsv, decided by output sha256) + the FOLLOW_BYTES marker: this set rewrites
    # whole files other sets own, so rows it did not change keep the previous owner's verdict (follow_bytes), the model rows
    # whose bytes this set changed are PS2 (ps2_ganado_bins rebuilds from the PS2 BIN of the same ARC), and each patched
    # package (PS2 cast geometry, source rows re-derived) is PS2.
    sys.path.insert(0, str(HERE.parent / 'gc_port23'))
    import build_catalog as bc  # noqa: E402
    rows = ['kind\tid\toutput_sha256\tps2_sha256\tps2_source\tevidence']
    for name, rel, outp, _gcp, ps2p in arcspec:
        before = {sha(d) for k, _i, d, _s in bc.member_rows('em/%s.drs' % name, Path(rel).read_bytes()) if k == 'model'}
        seen = set()
        for k, ident, d, _s in bc.member_rows('em/%s.drs' % name, Path(outp).read_bytes()):
            h = sha(d)
            if k == 'model' and h not in before and h not in seen:
                seen.add(h)
                rows.append('model\t%s\t%s\t%s\tPS2 USA BIO4DAT.AFS %s.dat\tem/%s.drs: GameCube BIN rebuilt as PS2 geometry '
                            '(ps2_ganado_bins.py, ps2_objects.rebuild)' % (ident, h, sha(Path(ps2p).read_bytes()), name, name))
    for spec in a.pkg:
        room, p = spec.split('=', 1)
        name = room if '/' in room else room + '/registry'
        dest = out / 'dc/native' / name.split('/')[0] / (name.split('/')[1] + '.re4nmr')
        h = sha(dest.read_bytes())
        rows.append('geometry\t%s\t%s\t%s\tPS2 USA cast package\t%s: PS2 cast geometry unchanged; source rows re-derived '
                    '(src_blob_patch.py)' % (h[:40], h, sha(Path(p).read_bytes()), name))
    (out / 'provenance.tsv').write_text('\n'.join(rows) + '\n')
    (out / 'FOLLOW_BYTES').write_text('rows this set did not change keep the previous owner\'s provenance (gc_port23/provenance.py)\n')
    (out / 'manifest.tsv').write_text('\n'.join(manifest) + '\n')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    subprocess.run('cd %s && find em dc -type f | sort | xargs sha256sum > SHA256SUMS.txt' % out, shell=True, check=True)


if __name__ == '__main__':
    main()
