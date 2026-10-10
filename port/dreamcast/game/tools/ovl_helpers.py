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
import os
import re
import subprocess
import sys
from pathlib import Path

GC = re.compile(r"removing unused section '([^']+)' in file '([^']+)'")


def removed(path):
    # A COMDAT member is reported as '<section>[<group signature>]': keep the section name (what objcopy renames).
    return {(m.group(2), re.sub(r'\[[^\]]*\]$', '', m.group(1)))
            for m in map(GC.search, Path(path).read_text().splitlines()) if m}


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


def groups(obj):
    """COMDAT group signature -> member sections of one object."""
    out = subprocess.run(['sh-elf-readelf', '-g', '-W', obj], capture_output=True, text=True, check=True).stdout
    res, cur = {}, None
    for line in out.splitlines():
        m = re.match(r"COMDAT group section \[\s*\d+\] `\.group' \[(.+)\] contains", line)
        if m:
            cur = res.setdefault(m.group(1), [])
            continue
        m = re.match(r'^\s+\[\s*\d+\]\s+(\S+)', line)
        if m and cur is not None:
            cur.append(m.group(1))
    return res


def private_groups(objects, ro):
    """object -> COMDAT member sections whose group no other image object defines (only overlay module objects of
    the RO overlays may hold another copy; whichever copy the linker keeps then lands in the overlay)."""
    mods = {'%s.o' % s[len('.ovl_'):] for s in ro}
    owners = {}
    per = {}
    for o in objects:
        if Path(o).name in mods or not o.endswith('.o'):
            continue
        per[o] = groups(o)
        for sig in per[o]:
            owners.setdefault(sig, set()).add(o)
    return {o: {sec for sig, secs in g.items() if owners[sig] == {o} for sec in secs} for o, g in per.items()}


SYM = re.compile(r'^[0-9a-f]+\s(.{7})\s(\S+)\s+[0-9a-f]+\s+(.*)$')


def symbols(obj):
    """(local, global): symbol name -> defining section of one object."""
    out = subprocess.run(['sh-elf-objdump', '-t', obj], capture_output=True, text=True, check=True).stdout
    local, glob = {}, {}
    for line in out.splitlines():
        m = SYM.match(line)
        if not m or m.group(2) in ('*UND*', '*ABS*', '*COM*'):
            continue
        flags = m.group(1)
        (glob if ('g' in flags or 'w' in flags or 'u' in flags) else local)[m.group(3).strip()] = m.group(2)
    return local, glob


def relocations(obj):
    """section -> names (symbols or section names) its relocations reference."""
    out = subprocess.run(['sh-elf-objdump', '-r', obj], capture_output=True, text=True, check=True).stdout
    refs, cur = {}, None
    for line in out.splitlines():
        m = re.match(r'RELOCATION RECORDS FOR \[(.+)\]:', line)
        if m:
            cur = refs.setdefault(m.group(1), set())
            continue
        f = line.split()
        if cur is not None and len(f) >= 3 and re.match(r'^[0-9a-f]+$', f[0]):
            cur.add(re.split(r'[+-]0x', f[2])[0])
    return refs


def image_referenced(work, overlays, base, present, moves):
    """Sections of `moves` that must stay in the image for the RO overlays. Everything an overlay reaches is kept by
    the final link; what reaches it only from that overlay but does not move (COMDAT members such as a class's weak
    vtable, writable data) is image memory, so a moved section it references would be an image word pointing into
    the overlay. Closure: a section kept this way blocks what it references in turn."""
    cand = {(o, sec) for o, l in moves.items() for sec, _ in l}
    blocked = set()
    why = []
    info = {}

    def load(obj):
        if obj not in info:
            info[obj] = symbols(obj) + (relocations(obj),)
        return info[obj]

    for s in overlays:
        only = removed(work / ('%s.gc' % s)) - base
        glob = {}
        for o in sorted({o for o, _ in only if o in present}):
            for name, sec in load(o)[1].items():
                if (o, sec) in only:
                    glob.setdefault(name, (o, sec))
        stay = [(o, sec) for o, sec in only if o in present and (o, sec) not in cand and not sec.startswith('.ovl_')]
        seen = set(stay)
        while stay:
            o, sec = stay.pop()
            local, _, refs = load(o)
            for name in refs.get(sec, ()):
                t = (o, local[name]) if name in local else (o, name) if name.startswith('.') else glob.get(name)
                if t is None or t in seen or t not in only or t[1].startswith('.ovl_'):
                    continue
                seen.add(t)
                if t in cand:
                    blocked.add(t)
                    why.append('%s\t%s\t%s\t%s\n' % (o, sec, t[0], t[1]))
                stay.append(t)
    (work / 'blocked.tsv').write_text(''.join(why))
    return blocked


def main():
    work = Path(sys.argv[1])
    overlays = sys.argv[2:]
    objects = [l.strip() for l in sys.stdin if l.strip()]
    present = set(objects)
    base = removed(work / 'base.gc')
    moves = {}  # object -> [(section, overlay)]
    rows = []
    # RE4DC_OVL_HELPERS_RO: overlays that also take the read-only data only they reach (.rodata.*: vtables, type
    # info, string and constant pools). pl11 (Ashley) reaches the DOL partner class cSubChar, whose methods are
    # referenced from its vtable: the code can move only with the vtable. Read-only data has no state to keep; an
    # object whose vtable is in the overlay never outlives it (Ashley's cEm is gone before the room reset releases it).
    ro = set(os.environ.get('RE4DC_OVL_HELPERS_RO', '').split())
    for s in overlays:
        only = sorted(removed(work / ('%s.gc' % s)) - base)
        for obj, sec in only:
            if not (sec.startswith('.text.') or (s in ro and sec.startswith('.rodata.'))) or obj not in present:
                continue  # code only; library members ("lib.a(x.o)") stay where the libraries put them
            moves.setdefault(obj, []).append((sec, s))
    renamed = {}
    n = 0
    private = private_groups(objects, ro) if ro else {}
    for obj in list(moves):
        grouped = group_members(obj)
        moves[obj] = [(sec, s) for sec, s in moves[obj] if sec not in grouped or (s in ro and sec in private.get(obj, ()))]
        if not moves[obj]:
            del moves[obj]
    if ro:
        blocked = image_referenced(work, [s for s in overlays if s in ro], base, present, moves)
        for obj in list(moves):
            moves[obj] = [(sec, s) for sec, s in moves[obj] if (obj, sec) not in blocked]
            if not moves[obj]:
                del moves[obj]
        print('ovl_helpers: %d sections stay in the image (referenced from data that stays: COMDAT, writable)'
              % len(blocked), file=sys.stderr)
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
