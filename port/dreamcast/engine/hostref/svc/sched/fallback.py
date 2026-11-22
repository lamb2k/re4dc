#!/usr/bin/env python3
"""fallback.py STUBS.cpp ERRORS.txt FALLBACK (lane eng-sched1): the link names of the generated stubs (gen_stubs.py)
the compiler could not type from the headers (their class or function is not declared in gen_stubs.py's headers),
added to the comma list FALLBACK; printed. Each stub is a comment, its extern line naming asm("NAME"), its body."""
import re
import sys

src, err, fb = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(src).read().split('\n')
names = set(x for x in fb.split(',') if x)
base = re.escape(src.rsplit('/', 1)[-1])
for m in re.finditer(base + r':(\d+):\d+: error', open(err, errors='replace').read()):
    i = int(m.group(1)) - 1
    while i >= 0:
        a = re.search(r'asm\("([^"]+)"\)', lines[i])
        if a:
            names.add(a.group(1))
            break
        i -= 1
print(','.join(sorted(names)))
