#!/usr/bin/env python3
"""snd28_store.py TREE OVERLAY MAP.json BASE_PROOFS.json STORE PS2DIR  (lane snd28, 2026-10-28)

Writes data set snd28's store from a `ps2_audio.py banks --dsp` run on a final disc tree:
  STORE/<path>          every overlay file that differs from TREE (same size required)
  STORE/provenance.tsv  one row per catalog member of those files (gc_port23/build_catalog.member_rows):
                          sound-mram / sound-aram of a block with at least one PS2 sample -> ps2 (ps2_sha256 = the
                          PS2 .snd files the samples came from), a block with none -> gc;
                          any other member -> gc only if BASE_PROOFS (the release candidate's provenance proofs)
                          already says gc; other members get no row
  STORE/README-snd28.txt  the recipe. Deliberately NOT named RECIPE*: provenance.py would then credit every member
                          without a row (models in the same archives) to PS2. Without a RECIPE the set's level stays
                          unknown, so only the rows above change attribution.
  STORE/_map/           the banks map + banks.txt;  STORE/SHA256SUMS
"""
import hashlib, json, os, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'gc_port23'))
import build_catalog  # noqa: E402

sha = lambda b: hashlib.sha256(b).hexdigest()


def main(tree, ov, mapf, proofs, store, ps2dir):
    tree, ov, store = Path(tree), Path(ov), Path(store)
    if store.exists():
        raise SystemExit('store exists: %s' % store)
    mp = json.load(open(mapf))
    base = {(r['kind'], r['sha256']): r['provenance'] for r in json.load(open(proofs))['entries']}
    rows, files = [], []
    for f in mp['files']:
        rel = f['spec'].split('#')[0]
        new, old = (ov / rel).read_bytes(), (tree / rel).read_bytes()
        if len(new) != len(old):
            raise SystemExit('size differs: ' + rel)
        if new == old:
            continue
        files.append(rel)
        (store / rel).parent.mkdir(parents=True, exist_ok=True)
        (store / rel).write_bytes(new)
        mapped = sum(b['mapped'] for b in f['blocks'])
        src = ' '.join(sorted({r['ps2'].split(':')[0] for b in f['blocks'] for r in b['rows'] if r.get('ps2')}))
        for kind, ident, data, where in build_catalog.member_rows(rel, new):
            o = sha(data)
            if kind in ('sound-mram', 'sound-aram'):
                # the PS2 source members' bytes (concatenated in the map's order)
                ps2 = sha(b''.join((Path(ps2dir) / n).read_bytes() for n in f['ps2'])) if mapped else ''
                rows.append((kind, ident, o, ps2, ('PS2 USA BIO4DAT.AFS ' + ','.join(f['ps2'])) if mapped else '',
                             '%s: %d of %d samples PS2 (%s); tools/ps2_audio.py banks --dsp' % (
                                 rel, mapped, sum(b['samples'] for b in f['blocks']), src[:200])))
            elif kind != 'motion' and base.get((kind, o)) == 'gc':
                rows.append((kind, ident, o, '', '', '%s: unchanged member, gc in the base proofs' % rel))
    with open(store / 'provenance.tsv', 'w') as w:
        w.write('kind\tid\toutput_sha256\tps2_sha256\tps2_source\tevidence\n')
        for r in rows:
            w.write('\t'.join(r) + '\n')
    (store / '_map').mkdir()
    shutil.copy(mapf, store / '_map' / 'banks-map.json')
    print('snd28 store: %d files, %d provenance rows' % (len(files), len(rows)))
    return files


if __name__ == '__main__':
    main(*sys.argv[1:7])
