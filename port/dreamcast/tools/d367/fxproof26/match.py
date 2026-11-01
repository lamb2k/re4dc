"""match.py <gc prefix> <ps2 prefix> <keys file|-> <out.tsv> [--top N]: nearest PS2 pictures for each GameCube picture.

Distance d = 100 * (1 - NCC) of the 16x16 premultiplied-luminance signatures (mean removed, unit length), min over the 8
rotations/flips of the PS2 picture. NCC ignores overall brightness and blend mode (a GameCube additive picture on
opaque black and the PS2 alpha picture of the same shape score as the same). Lane fxproof26.
"""
import sys, math, operator
from PIL import Image
S = 16
DIH = [None, Image.FLIP_LEFT_RIGHT, Image.FLIP_TOP_BOTTOM, Image.ROTATE_90, Image.ROTATE_180, Image.ROTATE_270,
       Image.TRANSPOSE, Image.TRANSVERSE]


def vec(s):
    p = s
    v = [(p[i] * 299 + p[i + 1] * 587 + p[i + 2] * 114) / 1000.0 for i in range(0, len(p), 4)]
    m = sum(v) / len(v)
    v = [x - m for x in v]
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n > 1e-6 else None


def variants(s):
    im = Image.frombytes('RGBA', (S, S), s)
    return [vec((im if t is None else im.transpose(t)).tobytes()) for t in DIH]


def load(prefix):
    raw = open(prefix + '.sig', 'rb').read()
    rows = [l.rstrip('\n').split('\t') for l in open(prefix + '.tsv')]
    return [(rows[i], raw[1024 * i:1024 * (i + 1)]) for i in range(len(rows))]


def main(a):
    top = int(a[a.index('--top') + 1]) if '--top' in a else 3
    gc, ps2 = load(a[0]), load(a[1])
    want = None if a[2] == '-' else set(l.strip() for l in open(a[2]) if l.strip())
    uniq = {}
    for row, s in ps2:
        uniq.setdefault(s, []).append(row)
    cand = []
    for s, rows in uniq.items():
        vs = variants(s)
        if vs[0] is not None:
            cand.append((vs, rows))
    print('ps2 unique', len(cand), file=sys.stderr)
    done = set()
    out = open(a[3], 'w')
    for row, s in gc:
        key = row[0]
        if (want is not None and key not in want) or key in done:
            continue
        done.add(key)
        q = vec(s)
        if q is None:
            out.write('%s\t%s\t%sx%s\tFLAT\n' % (key, row[1], row[2], row[3])); continue
        res = []
        for vs, rows in cand:
            best = max(sum(map(operator.mul, q, v)) for v in vs if v is not None)
            res.append((100 * (1 - best), rows))
        res.sort(key=lambda x: x[0])
        cols = []
        for d, rows in res[:top]:
            r = rows[0]
            cols.append('%.1f %s:%s@%s/%s %s id=%s (+%d same)' % (d, r[0], r[1], r[2], r[3], r[4], r[6], len(rows) - 1))
        out.write('%s\t%s\t%sx%s\t%s\n' % (key, row[1], row[2], row[3], '\t'.join(cols)))
        out.flush()


if __name__ == '__main__':
    main(sys.argv[1:])
