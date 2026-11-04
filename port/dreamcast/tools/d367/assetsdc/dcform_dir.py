#!/usr/bin/env python3
"""dcform_dir.py <tree> <out dir> [--jobs N]   (lane assets-dc, 2026-11-02; Disc 3 island loose textures)

dcform_pak.py's per-package conversion over the loose dc/tex*/.../<key>.re4tex files of a content tree (the island tree
discsets/d3-content.sh writes). Changed packages only are written to <out>/<same relative path>; report.json lists each
(how, w, h, bytes before/after) and the totals; manifest.tsv (path, sha256) for the store.
Same rules as dcform_pak.py: raw 16-bit >= 64x64 -> VQ (+ mips when square); smaller square 16-bit / square VQ / PAL4
without mips -> + mips (base kept); non-square small raw 16-bit left.
"""
import hashlib, json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dcform_pak as dp  # noqa: E402


def work(args):
    rel, path = args
    key, out, row = dp.convert((rel, open(path, 'rb').read()))
    row['path'] = rel
    return rel, out, row


def main():
    tree, out = Path(sys.argv[1]), Path(sys.argv[2])
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2
    out.mkdir(parents=True, exist_ok=False)
    todo = []
    for d, _, fs in os.walk(tree):
        for f in fs:
            if f.endswith('.re4tex'):
                p = Path(d) / f
                todo.append((p.relative_to(tree).as_posix(), str(p)))
    todo.sort()
    rows, man, before, after = [], [], 0, 0
    with ProcessPoolExecutor(jobs) as ex:
        for rel, blob, row in ex.map(work, todo, chunksize=16):
            rows.append(row)
            if blob is not None:
                q = out / rel; q.parent.mkdir(parents=True, exist_ok=True); q.write_bytes(blob)
                man.append((rel, hashlib.sha256(blob).hexdigest()))
                before += row['before']; after += row['after']
    (out / 'manifest.tsv').write_text(''.join('%s\t%s\n' % m for m in man))
    import collections
    summ = dict(files=len(todo), changed=len(man), bytes_before=before, bytes_after=after,
                how=collections.Counter(r.get('how', r.get('note')) for r in rows))
    (out / 'report.json').write_text(json.dumps(dict(tree=str(tree), summary=summ, rows=rows), indent=1) + '\n')
    print(json.dumps(summ))


if __name__ == '__main__':
    main()
