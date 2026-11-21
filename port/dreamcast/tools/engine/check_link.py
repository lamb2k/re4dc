#!/usr/bin/env python3
"""check_link.py: the engine image may link only the original functions on the allowed list (lane eng-svc4).

    check_link.py <image.map> [--allowed port/dreamcast/engine/game/allowed_original.txt] [--waive FILE]
                  [--json out.json] [--list] [--quiet]

Owner rule 2026-11-19 ("Split it"): no original service code in the engine image. Only behaviour (decisions,
scripts, player, partner and enemy logic) may be original. This reads the GNU ld map of the image (-Wl,-Map=,
written by engine/game/Makefile) and lists every code section the link KEPT from an original object: the hosted
units compiled from src/ (<OUT>/h/...), the SDK library (<OUT>/sdk/...) and the game's fdlibm (<OUT>/fd/...).
Each one must match a line of the allowed list; any other one is an original service function and fails the check.

A code section is `.text.<name>` (-ffunction-sections: one function a section; static functions included) or the
presentation section `e1_present` (several functions: the map's symbol lines name them). Data, read-only data and
discarded sections are not checked.

Allowed list format (one entry a line; '#' starts a comment):
    ## <group>: <reason>                       starts a group; every entry below it belongs to it
    <unit> <pattern> [<pattern> ...]           unit = the object's path under <OUT> without .o (game/player,
                                               wep02/wep02, sdk/mtx, fd/ef_acos); pattern = an fnmatch glob on
                                               the demangled name ("cPlayer::*", "*") or on the mangled name
    !<unit> <pattern> ...                      an exception inside an allowed unit: a matching function is NOT
                                               allowed even if another line allows it (service functions that
                                               live in a behaviour unit: view frustum, camera evaluation, ...)
    ?<unit> <pattern> ...                      a service-name guard (lane eng-e1f): a function of a matching unit
                                               whose name matches is NOT allowed, whatever allows it (a wildcard
                                               or its own name), unless a "+" line marks it reviewed. It catches
                                               a service function allowed by mistake when its name says what it is
                                               (sound, effect, pose, camera, drawing, collision, memory, tables)
    +<unit> <pattern> ...                      reviewed: a decision whose name matches a guard (the guard skips it)
    =<unit> <pattern> <bytes>                  a size ceiling (lane eng-e1n): a matching function larger than <bytes>
                                               is NOT allowed (an allowed body that grew; 0: it may not be linked)
    -<unit> <symbol> ...                       a reference ban (lane eng-e1n): the unit's object may not reference
                                               the symbols (fnmatch on the name, with or without the leading
                                               underscore), read from the map's cross reference table (-Wl,--cref);
                                               a map without the table fails the line

A pattern matches the demangled name, the mangled name, or the base name (the demangled name without its argument
list and clone suffix: "em10NeckMove" matches "em10NeckMove(cEm10*) [clone .part.0]").

--waive FILE: a second list in the same format whose entries pass but are reported as waived (today's known
remaining service functions, for the control: with them waived the check passes, and one more linked service
function must fail it).

--write-waive FILE: write today's SERVICE functions as such a list (mangled names).

--list: print every original function the image keeps, by unit, with its size, the group that allows it or
"SERVICE" (not allowed). Exit status: 0 PASS, 1 FAIL (an original function outside the list), 2 usage error.
"""
import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict, defaultdict

ORIG_DIRS = ('h', 'sdk', 'fd')   # <OUT>/h (hosted src/), <OUT>/sdk (SDK library), <OUT>/fd (fdlibm)
ORIG_DEFAULT = r'/(h|sdk|fd)/(.+)\.o$'
ORIG_RE = ORIG_DEFAULT


def unit_of(path):
    """'.../<OUT>/h/game/atari.o' -> 'game/atari'; '.../<OUT>/sdk/mtx.o' -> 'sdk/mtx'; None if not original.
    With --orig-pattern (another build's layout, e.g. re4ref's), group 2 of the pattern names the unit."""
    p = path.replace('\\', '/')
    m = re.search(ORIG_RE, p)
    if not m:
        return None
    if m.group(1) == 'h' or ORIG_RE != ORIG_DEFAULT:
        return m.group(2)
    return m.group(1) + '/' + m.group(2)


def parse_map(path):
    """-> list of (unit, section, size, [symbol names]) for every kept code input section from an original object."""
    with open(path, errors='replace') as f:
        lines = f.read().splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith('Linker script and memory map'):
            start = i + 1
            break
    if start is None:
        sys.exit(f'check_link: {path}: not a GNU ld map (no "Linker script and memory map")')
    out = []
    cur = None
    pend = None   # a section name alone on its line; its address, size and object are on the next
    sec_re = re.compile(r'^ (\S+)\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)\s+(\S.*)$')
    cont_re = re.compile(r'^\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)\s+(\S.*)$')
    sym_re = re.compile(r'^\s+0x([0-9a-fA-F]+)\s{8,}(\S.*)$')
    for ln in lines[start:]:
        if ln.startswith('Cross Reference Table'):
            break
        m = sec_re.match(ln)
        if m:
            cur = (m.group(1), int(m.group(3), 16), m.group(4).strip())
            pend = None
            out.append([cur[0], cur[1], cur[2], []])
            continue
        if pend is not None:
            m = cont_re.match(ln)
            if m:
                out.append([pend, int(m.group(2), 16), m.group(3).strip(), []])
                pend = None
                continue
        m = re.match(r'^ (\S+)\s*$', ln)
        if m and not ln.startswith('  '):
            pend = m.group(1)
            continue
        m = sym_re.match(ln)
        if m and out:
            name = m.group(2).strip()
            if not name.startswith(('.', '*', 'PROVIDE', 'ASSERT')) and '=' not in name:
                out[-1][3].append(name)
            continue
        pend = None
    res = []
    for sec, size, obj, syms in out:
        u = unit_of(obj)
        if u is None or size == 0:
            continue
        if not (sec.startswith('.text') or sec == 'e1_present'):
            continue
        res.append((u, sec, size, syms))
    return res


def parse_cref(path):
    """-> {unit: set(symbols it references)} from the map's cross reference table (-Wl,--cref), or None when the map
    has none. A table entry is the symbol and its defining file, then the referencing files (indented)."""
    with open(path, errors='replace') as f:
        lines = f.read().splitlines()
    try:
        i = next(k for k, ln in enumerate(lines) if ln.startswith('Cross Reference Table'))
    except StopIteration:
        return None
    refs = defaultdict(set)
    sym = None
    first = False   # the next file named is the definer
    for ln in lines[i + 1:]:
        if not ln.strip() or ln.startswith('Symbol') and 'File' in ln:
            continue
        if not ln[0].isspace():
            parts = ln.split()
            sym = parts[0]
            first = True
            if len(parts) > 1:
                first = False   # the definer is on this line
            continue
        if sym is None:
            continue
        if first:
            first = False
            continue
        u = unit_of(ln.strip())
        if u:
            refs[u].add(sym)
    return refs


def demangle_all(names):
    """mangled -> demangled (c++filt when available; the names unchanged otherwise)."""
    tool = shutil.which('c++filt') or shutil.which('sh-elf-c++filt')
    names = list(names)
    if not tool or not names:
        return {n: n for n in names}
    r = subprocess.run([tool], input='\n'.join(names) + '\n', capture_output=True, text=True)
    dem = r.stdout.splitlines()
    if len(dem) != len(names):
        return {n: n for n in names}
    return dict(zip(names, dem))


def functions(sections):
    """-> list of dicts {unit, name (mangled or the map's), dem, size, section} (one a function)."""
    fns = []
    mangled = []
    for u, sec, size, syms in sections:
        if sec.startswith('.text.'):
            nm = sec[len('.text.'):]
            fns.append({'unit': u, 'name': nm, 'size': size, 'section': sec})
            mangled.append(nm)
        elif sec == '.text':
            fns.append({'unit': u, 'name': '(.text of %s)' % u, 'size': size, 'section': sec})
        else:   # e1_present: one entry a symbol (the map lists them demangled); the size is shared
            names = sorted(set(syms)) or ['(%s of %s)' % (sec, u)]
            for nm in names:
                fns.append({'unit': u, 'name': nm, 'size': size // len(names), 'section': sec, 'dem': nm})
    dm = demangle_all(sorted(set(mangled)))
    for f in fns:
        f.setdefault('dem', dm.get(f['name'], f['name']))
    return fns


def load_list(path):
    """-> (rules, groups): rules = [(kind, unit_glob, [patterns], group)], kind '' allow, '!' exception, '?' guard,
    '+' reviewed; groups = {group: reason}."""
    rules = []
    groups = OrderedDict()
    group = '(no group)'
    with open(path) as f:
        for n, ln in enumerate(f, 1):
            s = ln.strip()
            if s.startswith('##'):
                g = s[2:].strip()
                name, _, reason = g.partition(':')
                group = name.strip()
                groups[group] = reason.strip()
                continue
            s = s.split('#', 1)[0].strip()
            if not s:
                continue
            kind = s[0] if s[0] in '!?+=-' else ''
            if kind:
                s = s[1:].strip()
            parts = s.split()
            if len(parts) < 2:
                sys.exit(f'check_link: {path}:{n}: want "<unit> <pattern>..."')
            rules.append((kind, parts[0], parts[1:], group))
    return rules, groups


def base_name(dem):
    """'em10NeckMove(cEm10*) [clone .part.0]' -> 'em10NeckMove'; 'cEm10::move()' -> 'cEm10::move'."""
    b = re.sub(r' \[clone [^]]*\]$', '', dem)
    i = b.find('(')
    return b[:i] if i > 0 else b


def match(rules, f):
    """-> the group of the first allowing rule, unless an exception (!) matches, or a guard (?) matches a function no
    reviewed line (+) names; None if not allowed (f['why'] says 'guard' when a guard refused it)."""
    names = (f['dem'], f['name'], base_name(f['dem']))
    def hit(r):
        _, ug, pats, _ = r
        if not fnmatch.fnmatchcase(f['unit'], ug):
            return False
        return any(fnmatch.fnmatchcase(n, p) for n in names for p in pats)
    for r in rules:
        if r[0] == '!' and hit(r):
            return None
    for r in rules:   # size ceilings: "=<unit> <pattern> <bytes>"
        if r[0] == '=' and fnmatch.fnmatchcase(f['unit'], r[1]) and \
                any(fnmatch.fnmatchcase(n, r[2][0]) for n in names) and f['size'] > int(r[2][-1]):
            f['why'] = 'ceiling %s B' % r[2][-1]
            return None
    for r in rules:
        if r[0] == '' and hit(r):
            if any(g[0] == '?' and hit(g) for g in rules) and not any(v[0] == '+' and hit(v) for v in rules):
                f['why'] = 'guard'
                return None
            return r[3]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map')
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--allowed', default=os.path.join(here, '..', '..', 'engine', 'game', 'allowed_original.txt'))
    ap.add_argument('--waive')
    ap.add_argument('--json')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--write-waive', help='write the SERVICE functions found as a waive list (mangled names)')
    ap.add_argument('--orig-pattern', help='regex on object paths that marks an original object; group 2 = its unit')
    a = ap.parse_args()
    if a.orig_pattern:
        global ORIG_RE
        ORIG_RE = a.orig_pattern
    rules, groups = load_list(a.allowed)
    wrules, _ = load_list(a.waive) if a.waive else ([], {})
    fns = functions(parse_map(a.map))
    if not fns:
        print(f'check_link: {a.map}: no original code section kept (wrong map?)')
        sys.exit(2)
    allowed, waived, bad = [], [], []
    for f in fns:
        g = match(rules, f)
        if g is not None:
            f['group'] = g
            allowed.append(f)
            continue
        if wrules and match(wrules, f) is not None:
            f['group'] = 'WAIVED'
            waived.append(f)
            continue
        why = f.get('why', '')
        f['group'] = 'SERVICE(guard)' if why == 'guard' else 'SERVICE(%s)' % why if why else 'SERVICE'
        bad.append(f)
    # reference bans ("-<unit> <symbol>..."): the cross reference table
    bans = [r for r in rules if r[0] == '-']
    if bans:
        cref = parse_cref(a.map)
        for r in bans:
            if cref is None:
                bad.append({'unit': r[1], 'name': '(no cross reference table in the map: -Wl,--cref)', 'size': 0,
                            'dem': '(no cross reference table in the map: -Wl,--cref)', 'group': 'SERVICE(ref)'})
                continue
            for u, syms in sorted(cref.items()):
                if not fnmatch.fnmatchcase(u, r[1]):
                    continue
                for s in sorted(syms):
                    if any(fnmatch.fnmatchcase(s, p) or fnmatch.fnmatchcase(s.lstrip('_'), p) for p in r[2]):
                        bad.append({'unit': u, 'name': 'references ' + s, 'dem': 'references ' + s, 'size': 0,
                                    'group': 'SERVICE(ref)', 'why': 'ref'})
    by_unit = defaultdict(list)
    for f in bad:
        by_unit[f['unit']].append(f)
    verdict = 'FAIL' if bad else 'PASS'
    if a.list:
        for f in sorted(fns, key=lambda f: (f['unit'], f['dem'])):
            print(f"{f['unit']:22s} {f['size']:6d}  {f['group']:22s} {f['dem']}")
    if not a.quiet:
        print(f'check_link: {a.map}: {len(fns)} original functions kept; allowed {len(allowed)} '
              f'({sum(f["size"] for f in allowed)} B), waived {len(waived)} ({sum(f["size"] for f in waived)} B), '
              f'SERVICE {len(bad)} ({sum(f["size"] for f in bad)} B'
              + (f', {sum(1 for f in bad if f.get("why") == "guard")} by the name guard' if any(f.get('why') == 'guard' for f in bad) else '')
              + f'): {verdict}')
        for u in sorted(by_unit, key=lambda u: -sum(f['size'] for f in by_unit[u])):
            fl = by_unit[u]
            print(f'  {u}: {len(fl)} functions, {sum(f["size"] for f in fl)} B: '
                  + ', '.join(f['dem'] for f in sorted(fl, key=lambda f: -f['size'])[:12])
                  + (' ...' if len(fl) > 12 else ''))
    if a.write_waive:
        with open(a.write_waive, 'w') as f:
            f.write('## waived: original service functions linked in %s (written by check_link.py)\n' % a.map)
            for u in sorted(by_unit):
                f.write(u + ' ' + ' '.join(sorted(set(x['name'] for x in by_unit[u]))) + '\n')
    if a.json:
        rep = {'map': a.map, 'allowed_list': a.allowed, 'waive': a.waive, 'verdict': verdict,
               'functions': len(fns), 'allowed': len(allowed), 'waived': len(waived), 'service': len(bad),
               'service_bytes': sum(f['size'] for f in bad),
               'service_by_guard': sorted(f['dem'] for f in bad if f.get('why') == 'guard'),
               'by_unit': {u: {'functions': len(fl), 'bytes': sum(f['size'] for f in fl),
                               'names': sorted(f['dem'] for f in fl), 'mangled': sorted(f['name'] for f in fl)}
                           for u, fl in sorted(by_unit.items())},
               'groups': {g: {'reason': groups[g], 'functions': sum(1 for f in allowed if f['group'] == g)}
                          for g in groups}}
        with open(a.json, 'w') as f:
            json.dump(rep, f, indent=1)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
