#!/usr/bin/env python3
"""mot_refs.py: static MOTION-KEYS gate (lane cast-ps2-25, 2026-10-26; Test 25 r100 house-siege "RE4DC MISSING: motion key
read" for dc/mot/18f9ad45-ba6230e7.fcv: a stale em/em1X.drs with GC Ganado motion staged after pmgan24, whose remove list
had dropped those GC keys).

  mot_refs.py <disc tree> [--fixture <t11 fixture .json>] [--json <out>]

Every MTC table (R4MOTBL v2 / v3) in every file of the tree (em/*.drs, st*/r*.dar / .arc, etc/*, ...) names its clips'
key files /cd/dc/mot/<crc>-<fnv>.fcv (native_motion.cpp reads them; a missing one halts the game). The gate fails when
  - a referenced key has no dc/mot/<key>.fcv in the tree, or
  - (--fixture) the fixture's "remove" list holds a referenced key (a data set dropped a key some staged archive uses).
Prints one line per failure and a summary; exit 1 on any failure."""
import argparse, json, os, struct, sys

MAGIC = b'R4MOTBL\x00'


def live(b, p, size):
    """True when the table at p is the MTC member of a body the game binds: the body of <size> bytes either ends the
    file (prepared .drs: native_motion.cpp binds the container's last member) or is the payload the container record at
    0x20 points at; its header (u32 count, ..., offsets, tags) lists MTC as its last member at offset p. A rewritten
    archive can keep an older body in front of the live one; that table is never read and is skipped."""
    bases = {len(b) - size}
    if len(b) >= 0x30:
        kind, psize, dest, off = struct.unpack_from('<4I', b, 0x20)
        if psize == size:
            bases.add(off)
    for base in bases:
        if not 0 <= base <= p < base + size <= len(b):
            continue
        n = struct.unpack_from('<I', b, base)[0]
        if not 0 < n < 4096 or base + 16 + 8 * n > len(b):
            continue
        last = base + 16 + 4 * n + 4 * (n - 1)
        if b[last:last + 3] == b'MTC' and base + struct.unpack_from('<I', b, base + 16 + 4 * (n - 1))[0] == p:
            return True
    return False


def tables(b, dead=None):
    p = b.find(MAGIC)
    while p >= 0:
        ver, cnt = struct.unpack_from('<II', b, p + 8)
        size = struct.unpack_from('<I', b, p + 24)[0]
        if ver in (2, 3) and 0 < cnt < 4096 and p + 32 + 20 * cnt <= len(b):
            if live(b, p, size):
                yield p, ['%08x-%08x' % struct.unpack_from('<II', b, p + 32 + 20 * k + 8) for k in range(cnt)]
            elif dead is not None:
                dead.append(p)
        p = b.find(MAGIC, p + 8)


def scan(tree):
    refs = {}
    for r, ds, fs in os.walk(tree):
        ds.sort()
        for f in sorted(fs):
            path = os.path.join(r, f)
            rel = os.path.relpath(path, tree).replace(os.sep, '/')
            if rel.startswith('dc/mot/') or rel == 'dc/tex.pak' or rel.startswith('dc/tex/') or rel.startswith('dc/movie/'):
                continue
            with open(path, 'rb') as fh:
                b = fh.read()
            if MAGIC not in b:
                continue
            dead = []
            for p, keys in tables(b, dead):
                for k in keys:
                    refs.setdefault(k, set()).add(rel)
            for p in dead:
                print('MOTION-KEYS note: %s MTC table at %#x is not in the bound body (skipped)' % (rel, p))
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tree'); ap.add_argument('--fixture'); ap.add_argument('--json')
    a = ap.parse_args()
    refs = scan(a.tree)
    mot = os.path.join(a.tree, 'dc', 'mot')
    have = {f[:-4].lower() for f in os.listdir(mot) if f.endswith('.fcv')} if os.path.isdir(mot) else set()
    missing = sorted(k for k in refs if k not in have)
    removed = []
    if a.fixture:
        fx = json.load(open(a.fixture))
        rm = {os.path.basename(x)[:-4].lower() for x in fx.get('remove', []) if x.lower().startswith('dc/mot/') and x.endswith('.fcv')}
        removed = sorted(k for k in refs if k in rm)
    for k in missing:
        print('MOTION-KEYS missing dc/mot/%s.fcv referenced by %s' % (k, ' '.join(sorted(refs[k]))))
    for k in removed:
        print('MOTION-KEYS removed-but-referenced dc/mot/%s.fcv (fixture remove) referenced by %s' % (k, ' '.join(sorted(refs[k]))))
    archives = sorted(set().union(*refs.values())) if refs else []
    ok = not missing and not removed
    print('MOTION-KEYS %s: %d keys referenced by %d archives, %d dc/mot files, %d missing, %d removed-but-referenced'
          % ('PASS' if ok else 'FAIL', len(refs), len(archives), len(have), len(missing), len(removed)))
    if a.json:
        json.dump(dict(pass_=ok, keys=len(refs), archives=archives, missing={k: sorted(refs[k]) for k in missing},
                       removed={k: sorted(refs[k]) for k in removed}), open(a.json, 'w'), indent=1)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
