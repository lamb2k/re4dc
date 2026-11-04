#!/usr/bin/env python3
"""Event-file lint (CH-FIXES-CARRY rows 21 / 23; world-ch5 11-04): a disc tree ships no event file that its room already
plays as a route movie, and every shipped event file is little-endian with its .evq.

  evd_movie_lint.py <disc tree> <repo>

An event evd/rRRRsEE.evd is movie-owned when the room script src/st*/rRRR.cpp calls re4dc_movie_available(0xRRREE)
(directly or through a macro such as R206_MOVIES_OWN) and dc/movie/rRRRsEE.seq is on the same tree: the room then reads
the evd only when the movie is missing, so the file is dead weight (and its GameCube models a CAST-GC risk). Exit 1 lists
each offending file."""
import pathlib, re, struct, sys

tree, repo = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
bad = []
for f in sorted((tree / 'evd').glob('*.evd')):
    m = re.fullmatch(r'r([0-9a-f]{3})s([0-9a-f]{2})', f.stem.lower())
    b = f.read_bytes()
    n, at = struct.unpack_from('<2I', b, 0x48) if len(b) >= 0x50 else (0, 0)
    if not (b.startswith(b'event/') and 0 < n <= 4096 and 0x50 <= at and at + n * 0x40 <= len(b)):
        bad.append('%s: not a little-endian event file' % f.name)
    if not (f.parent / (f.name + '.evq')).is_file():
        bad.append('%s: no .evq' % f.name)
    if not m:
        continue
    room, ev = m.groups()
    src = list(repo.glob('src/st*/r%s.cpp' % room))
    owned = any(re.search(r're4dc_movie_available\(0x%s%s\)' % (room, ev), s.read_text(errors='replace'), re.I) for s in src)
    if owned and (tree / 'dc/movie' / (f.stem + '.seq')).is_file():
        bad.append('%s: r%s plays %s as a route movie (dc/movie/%s.seq ships); drop the evd' % (f.name, room, f.stem, f.stem))
for line in bad:
    print('evd_movie_lint:', line)
print('evd_movie_lint: %s (%d event files)' % ('FAIL' if bad else 'PASS', len(list((tree / 'evd').glob('*.evd')))))
sys.exit(1 if bad else 0)
