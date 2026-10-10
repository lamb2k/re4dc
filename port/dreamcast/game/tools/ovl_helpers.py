#!/usr/bin/env python3
"""Room-overlay helpers (tools/link.sh, LINK_OVL_HELPERS=1): code that only a room overlay reaches moves into it.

usage: ovl_helpers.py <work dir> <overlay section>... < objects (one per line)

For each overlay section <s> (e.g. .ovl_em2b), <work dir>/base.gc and <work dir>/<s>.gc are the linker's
--print-gc-sections reports of the full link and of the same link with <s> discarded. A .text.* input section that
the second link removes and the first keeps is reached from <s> and from nothing else in the image (every other
overlay stays kept): its only callers are that overlay's code, so it can live in the overlay. Such sections are
renamed <s>.h<n> in a copy of their object (<work dir>/o<k>_<name>.o; the overlay's output section keeps <s>.h*),
and the object list comes back on stdout with the copies in place of the originals. <work dir>/moves.tsv lists
overlay, object, section, bytes. Only code moves: data, read-only data and bss stay in the image (no module
state changes, and moved code still reaches them by absolute address).
"""
import re
import subprocess
import sys
from pathlib import Path

GC = re.compile(r"removing unused section '([^']+)' in file '([^']+)'")


def removed(path):
    return {(m.group(2), m.group(1)) for m in map(GC.search, Path(path).read_text().splitlines()) if m}


def section_sizes(obj):
    out = subprocess.run(['sh-elf-objdump', '-h', obj], capture_output=True, text=True, check=True).stdout
    sizes = {}
    for line in out.splitlines():
        f = line.split()
        if len(f) >= 3 and f[0].isdigit():
            sizes[f[1]] = int(f[2], 16)
    return sizes


def group_members(obj):
    """Sections in a COMDAT group (inline functions, templates): the linker keeps one object's copy, so renaming
    one copy could keep another; they stay where they are."""
    out = subprocess.run(['sh-elf-readelf', '-g', '-W', obj], capture_output=True, text=True, check=True).stdout
    return {m.group(1) for m in re.finditer(r'^\s+\[\s*\d+\]\s+(\S+)', out, re.M)}


def main():
    work = Path(sys.argv[1])
    overlays = sys.argv[2:]
    objects = [l.strip() for l in sys.stdin if l.strip()]
    present = set(objects)
    base = removed(work / 'base.gc')
    moves = {}  # object -> [(section, overlay)]
    rows = []
    for s in overlays:
        only = sorted(removed(work / ('%s.gc' % s)) - base)
        for obj, sec in only:
            if not sec.startswith('.text.') or obj not in present:
                continue  # code only; library members ("lib.a(x.o)") stay where the libraries put them
            moves.setdefault(obj, []).append((sec, s))
    renamed = {}
    n = 0
    for obj in list(moves):
        grouped = group_members(obj)
        moves[obj] = [(sec, s) for sec, s in moves[obj] if sec not in grouped]
        if not moves[obj]:
            del moves[obj]
    for k, obj in enumerate(sorted(moves)):
        sizes = section_sizes(obj)
        copy = work / ('o%d_%s' % (k, Path(obj).name))
        args = ['sh-elf-objcopy']
        for sec, s in moves[obj]:
            n += 1
            args += ['--rename-section', '%s=%s.h%d' % (sec, s, n)]
            rows.append('%s\t%s\t%s\t%d' % (s, obj, sec, sizes.get(sec, 0)))
        subprocess.run(args + [obj, str(copy)], check=True)
        renamed[obj] = str(copy)
    (work / 'moves.tsv').write_text(''.join(r + '\n' for r in rows))
    total = sum(int(r.rsplit('\t', 1)[1]) for r in rows)
    print('ovl_helpers: %d sections, %d bytes into %s' % (len(rows), total, ' '.join(overlays)), file=sys.stderr)
    print(' '.join(renamed.get(o, o) for o in objects))


if __name__ == '__main__':
    main()
