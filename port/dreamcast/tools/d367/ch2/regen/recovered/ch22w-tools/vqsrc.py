#!/usr/bin/env python3
"""vqsrc.py OUT DIR...: symlink into OUT every package vq_native_ui can read (single twiddled 16-bit, no mips)."""
import sys, os, collections
from pathlib import Path
sys.path.insert(0, '/root/probe/lanes-20261013/ch22/port/dreamcast/tools')
import vq_native_ui as vq
out = Path(sys.argv[1]); out.mkdir(exist_ok=True)
why = collections.Counter()
for d in map(Path, sys.argv[2:]):
    if not d.is_dir():
        continue
    for t in sorted(d.glob('*.re4tex')):
        if (out / t.name).exists():
            continue
        try:
            vq.read_package(t.read_bytes())
        except ValueError as e:
            why[(d.name, str(e))] += 1
            continue
        os.symlink(t.resolve(), out / t.name)
        why[(d.name, 'ok')] += 1
for k, v in sorted(why.items()):
    print(k, v)
