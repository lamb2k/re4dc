#!/usr/bin/env python3
"""split_check.py (lane eng-e2d): no copy of a service function hidden inside a hosted unit's linked code.

    split_check.py --map <e1.map> [--allowed <allowed_original.txt>] [--json out.json] [--quiet]
    split_check.py --obj <unit.o> --unit <unit> [--allowed ...] [--weak <symbol>...]

The link check (check_link.py) reads the image's map: it sees a function only as its own code section. A hosted unit
compiled from src/ can still carry a service function's code where the map does not show it:
  - inlined (wholly or in part) into a decision function of the same unit;
  - as a clone the callers call instead (".part", ".constprop", ".isra", ".cold": GCC's partial inlining and
    interprocedural clones), which weakening the global symbol cannot redirect;
  - and, for a function the engine REPLACES (the unit's copy made weak so the engine's strong body is linked), in what
    a caller of the same unit assumed about the body it saw: the registers it clobbers (-fipa-ra), its purity
    (-fipa-pure-const), the memory it touches (-fipa-modref, -fipa-reference), its return value's range (-fipa-vrp,
    -fipa-bit-cp), constants propagated into it (-fipa-cp) and its arguments' layout (-fipa-sra), or a merge with an
    identical body (-fipa-icf). The engine's body differs, so those assumptions are wrong.

For every hosted object (a unit under <OUT>/h/ that the map loads) this checks, per unit:
  1. the compiler's own inlining report (<object>.inl.txt, -fopt-info-inline-optimized, written by game/Makefile's
     SPLIT_REPORT) exists; a unit without it is refused (it was not built by the image rule);
  2. no function the link check refuses for that unit (allowed_original.txt: the "!" exceptions, the "?" name guards
     not marked reviewed, "=" ceilings, and default deny) and no replaced function is inlined into another function,
     unless that caller is itself refused or replaced (a service body inside a service body: the link check sees the
     caller);
  3. no clone of such a function exists in the object;
  4. a unit with a replaced function was compiled without the interprocedural optimisations (game/Makefile
     SPLIT_NOIPA, read from the object's .GCC.command.line, -frecord-gcc-switches): the copies of points 2 and 3 cannot
     occur and no caller trusts the body it saw.
A function is REPLACED when this object defines it and the image takes another, non-original object's definition (the
map's cross reference table names the definer).

check_link.py runs this on every image it checks and counts each problem as a service function (group
SERVICE(split)), so the link check's count includes what inlining hid. Exit status: 0 PASS, 1 FAIL, 2 usage error.
The per-object form (--obj) checks points 1 to 3 and, with --weak, point 4 for the listed symbols; the image rule of a
unit may call it so that a bad object stops the build.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_link as cl  # noqa: E402  (the allowed list's reader and matcher: one meaning of "refused")

# game/Makefile SPLIT_NOIPA: the flags a unit with a replaced function must have (the last of -fX / -fno-X wins)
NOIPA = ('inline-functions', 'inline-small-functions', 'partial-inlining', 'ipa-cp', 'ipa-sra', 'ipa-icf', 'ipa-ra',
         'ipa-pure-const', 'ipa-modref', 'ipa-reference', 'ipa-vrp', 'ipa-bit-cp')
CLONE_RE = re.compile(r'\[clone [^]]*\]|\.(part|constprop|isra|cold|localalias)\.\d')
REPORT_RE = re.compile(r'Inlin(?:ing|ed) (.*?)/\d+ into (.*?)/\d+')


def tool(name):
    for t in ('sh-elf-' + name, name):
        if shutil.which(t):
            return t
    return 'sh-elf-' + name


def qualname(sig):
    """'virtual void cEm10::move()' -> 'cEm10::move'; 'T* cManager<T>::createBack() [with T = cEm]' ->
    'cManager<cEm>::createBack'; 'static void cUnit::operator delete(void*, unsigned int)' -> 'cUnit::operator delete'"""
    s = sig.strip()
    with_t = re.search(r'\[with (.*)\]$', s)
    s = re.sub(r'\s*\[with .*\]$', '', s)
    # the argument list: the first '(' at template depth 0 that does not belong to 'operator()'
    depth, cut = 0, len(s)
    i = 0
    while i < len(s):
        c = s[i]
        if c == '<':
            depth += 1
        elif c == '>':
            depth = max(0, depth - 1)
        elif c == '(' and depth == 0:
            if s[max(0, i - 8):i].endswith('operator') and s[i:i + 2] == '()':
                i += 2
                continue
            cut = i
            break
        i += 1
    head = s[:cut].strip()
    # the name is the last word at depth 0, except an operator's ("operator delete", "operator new")
    k = head.rfind('operator')
    if k >= 0 and re.match(r'operator\b', head[k:]):
        j = head.rfind(' ', 0, k)   # the qualified name holding the operator starts after the last space before it
        name = head[j + 1:]
    else:
        depth, start = 0, 0
        for j, c in enumerate(head):
            if c == '<':
                depth += 1
            elif c == '>':
                depth = max(0, depth - 1)
            elif c == ' ' and depth == 0:
                start = j + 1
        name = head[start:]
    name = re.sub(r'\.(part|constprop|isra|cold|localalias)\.\d+$', '', name.lstrip('*&'))
    if with_t:   # put the template arguments in: T = cEm, U = ...
        for a in with_t.group(1).split(';'):
            if '=' in a:
                p, v = a.split('=', 1)
                name = re.sub(r'\b%s\b' % re.escape(p.strip()), v.strip(), name)
    return name


def is_refused(rules, unit, name, dem=None):
    f = {'unit': unit, 'name': name, 'dem': dem or name, 'size': 0}
    return cl.match(rules, f) is None


def flags_of(obj):
    """-> {option: bool} for the -f options recorded in the object (.GCC.command.line), None when not recorded"""
    r = subprocess.run([tool('readelf'), '-p', '.GCC.command.line', obj], capture_output=True, text=True)
    if r.returncode != 0 or '.GCC.command.line' not in r.stdout or 'GNU' not in r.stdout:
        return None
    opts = {}
    for t in ' '.join(r.stdout.splitlines()).split():
        m = re.match(r'-f(no-)?([a-z0-9-]+)$', t)
        if m:
            opts[m.group(2)] = m.group(1) is None
    return opts


def symbols(obj):
    """-> (defined: {demangled: kind}, clones: [demangled]) of the object's code symbols"""
    r = subprocess.run([tool('nm'), '-C', obj], capture_output=True, text=True, check=True)
    defined, clones = {}, []
    for ln in r.stdout.splitlines():
        p = ln.split(None, 2)
        if len(p) < 3 or p[1] not in 'TtWw':
            continue
        defined[p[2]] = p[1]
        if CLONE_RE.search(p[2]):
            clones.append(p[2])
    return defined, clones


def check_unit(obj, unit, rules, replaced, kept=None):
    """-> list of problems (strings) of one hosted object; replaced = the base names of its replaced functions; kept =
    the base names of its functions the image keeps (None: every function counts, the per-object form)"""
    bad = []
    rep = obj + '.inl.txt'
    if not os.path.exists(rep):
        # GCC writes no report when it inlined nothing: the object's recorded command line must then name the report
        r = subprocess.run([tool('readelf'), '-p', '.GCC.command.line', obj], capture_output=True, text=True)
        if '-fopt-info-inline-optimized=' + os.path.basename(rep) not in r.stdout.replace(os.path.dirname(rep) + '/', ''):
            return ['no inlining report %s (the unit was not built by the image rule: SPLIT_REPORT)' % rep]
        rep = os.devnull
    try:
        defined, clones = symbols(obj)
    except (OSError, subprocess.CalledProcessError) as e:
        return ['cannot read %s: %s' % (obj, e)]

    def service(n):
        return n in replaced or is_refused(rules, unit, n)
    with open(rep, errors='replace') as f:
        for ln in f:
            m = REPORT_RE.search(ln)
            if not m:
                continue
            what, into = qualname(m.group(1)), qualname(m.group(2))
            if what == into or not service(what):
                continue   # a function's own split part put back, or a decision's helper
            if service(into):
                continue   # inside a body the link check refuses (or the engine replaces) anyway
            if kept is not None and into not in kept:
                continue   # inside a function the image does not keep (--gc-sections dropped it)
            bad.append('inlined %s into %s (%s)' % (what, into, 'replaced' if what in replaced else 'refused'))
    for c in clones:
        b = cl.base_name(c)
        b = re.sub(r'\.(part|constprop|isra|cold|localalias)\.\d.*$', '', b)
        if not service(b):
            continue
        if kept is None:
            bad.append('clone %s' % c)
        elif c in kept and not is_refused(rules, unit, b, c):
            # a kept clone of a refused function is the link check's own finding (its section is named after it); a
            # kept clone of a replaced function the list does not refuse is not, and is counted here
            bad.append('clone %s (kept)' % c)
    if replaced:
        opts = flags_of(obj)
        if opts is None:
            bad.append('replaced functions (%s) but no recorded flags (-frecord-gcc-switches)' % ', '.join(sorted(replaced)[:4]))
        else:
            on = [o for o in NOIPA if opts.get(o) is not False]   # on at -O2 unless turned off
            if on:
                bad.append('replaced functions (%d: %s) in a unit compiled with -f%s on (game/Makefile SPLIT_NOIPA_UNITS)'
                           % (len(replaced), ', '.join(sorted(replaced)[:3]) + (' ...' if len(replaced) > 3 else ''),
                              ' -f'.join(on)))
    # dedupe (the report repeats an inlining per call site), keep the order
    seen, out = set(), []
    for b in bad:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out


def load_map(path):
    """-> (hosted objects {path: unit}, definer {demangled symbol: object path}) from the GNU ld map"""
    objs = {}
    definer = {}
    with open(path, errors='replace') as f:
        lines = f.read().splitlines()
    for ln in lines:
        if ln.startswith('LOAD '):
            p = ln[5:].strip()
            u = cl.unit_of(p)
            if u is not None and re.search(r'/h/', p.replace('\\', '/')):
                objs[p] = u
    try:
        i = next(k for k, ln in enumerate(lines) if ln.startswith('Cross Reference Table'))
    except StopIteration:
        return objs, None
    sym = None
    for ln in lines[i + 1:]:
        if not ln.strip() or (ln.startswith('Symbol') and 'File' in ln):
            continue
        if not ln[0].isspace():
            m = re.match(r'^(.*?)\s{2,}(\S+)$', ln) or re.match(r'^(.*\S)\s+(/\S+\.o)$', ln)
            if m:
                definer[m.group(1).strip()] = m.group(2)
                sym = None
            else:
                sym = ln.strip()
            continue
        if sym is not None:
            definer[sym] = ln.strip()
            sym = None
    return objs, definer


def comdat_of(obj):
    """the demangled names of the object's COMDAT group signatures (header inlines and template instances)"""
    r = subprocess.run([tool('readelf'), '-gW', obj], capture_output=True, text=True)
    sigs = re.findall(r"COMDAT group section \[\s*\d+\] `[^']*' \[(\S+)\]", r.stdout)
    if not sigs:
        return set()
    if tool('c++filt').startswith('sh-elf-'):   # the SH toolchain's demangler strips the symbol prefix "_" first
        sigs = ['_' + s if s.startswith('_Z') else s for s in sigs]
    dem = subprocess.run([tool('c++filt')], input='\n'.join(sigs) + '\n', capture_output=True, text=True).stdout.split('\n')
    return {d for d in dem if d}


def replaced_of(obj, definer, unit, rules):
    """-> (replaced, odr): the base names of the functions obj defines whose image definition is an engine object's.
    replaced: made weak in this object (not a COMDAT copy), or a COMDAT copy the link check refuses (an engine body
    under the original's name, as the engine pool's cManager members); odr: a COMDAT copy of a header inline the link
    check allows, taken from an engine object that includes the same header (the same source: not a replacement)"""
    rep, odr = set(), set()
    defined, _ = symbols(obj)
    comdat = comdat_of(obj)
    for dem in defined:
        d = definer.get(dem)
        if d is None or os.path.normpath(d) == os.path.normpath(obj):
            continue
        if cl.unit_of(d) is not None:
            continue   # another original object's copy
        b = cl.base_name(dem)
        if dem in comdat and not is_refused(rules, unit, b, dem):
            odr.add(b)
        else:
            rep.add(b)
    return rep, odr


def check_image(map_path, rules):
    """-> {unit: (object, [problems], replaced)} for every hosted object the map loads"""
    objs, definer = load_map(map_path)
    res = {}
    if definer is None:
        for o, u in objs.items():
            res[u] = (o, ['no cross reference table in the map (-Wl,--cref): replaced functions unknown'], set())
        return res
    kept = {}
    for f in cl.functions(cl.parse_map(map_path)):
        kept.setdefault(f['unit'], set()).update((f['dem'], cl.base_name(f['dem'])))
    for o, u in sorted(objs.items(), key=lambda x: x[1]):
        if not os.path.exists(o):
            res[u] = (o, ['object missing: %s' % o], set())
            continue
        rep, odr = replaced_of(o, definer, u, rules)
        ODR[u] = sorted(odr)
        res[u] = (o, check_unit(o, u, rules, rep, kept.get(u, set())), rep)
    return res


ODR = {}   # unit -> the header inlines whose image copy is an engine object's (reported, not a problem)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map')
    ap.add_argument('--obj')
    ap.add_argument('--unit')
    ap.add_argument('--weak', nargs='*', default=[])
    ap.add_argument('--allowed', default=os.path.join(HERE, '..', '..', 'engine', 'game', 'allowed_original.txt'))
    ap.add_argument('--json')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    rules, _ = cl.load_list(a.allowed)
    if a.map:
        res = check_image(a.map, rules)
        if not res:
            print('split_check: %s: no hosted object loaded (wrong map?)' % a.map)
            sys.exit(2)
    elif a.obj and a.unit:
        weak = set()
        probs = []
        if a.weak:
            # the symbols as the object names them (SH-ELF: a leading "_"); each must be a weak definition there
            kinds = {}
            for ln in subprocess.run([tool('nm'), a.obj], capture_output=True, text=True).stdout.splitlines():
                p = ln.split()
                if len(p) >= 2:
                    kinds.setdefault(p[-1], set()).add(p[-2])
            for s in a.weak:
                k = kinds.get(s, set())
                if not k & {'W', 'V'} or k & {'T', 't', 'D', 'd'}:
                    probs.append('not weak: %s (%s)' % (s, ','.join(sorted(k)) or 'absent'))
            dem = subprocess.run([tool('c++filt')], input='\n'.join(a.weak) + '\n', capture_output=True,
                                 text=True).stdout.split('\n')
            weak = {cl.base_name(d[1:] if d.startswith('_') and not d.startswith('_Z') else d) for d in dem if d}
        res = {a.unit: (a.obj, probs + check_unit(a.obj, a.unit, rules, weak), weak)}
    else:
        ap.print_usage()
        sys.exit(2)
    nbad = sum(len(p) for _, p, _ in res.values())
    if not a.quiet:
        for u, (o, probs, rep) in sorted(res.items()):
            print('  %-16s %-5s replaced %3d  %s' % (u, 'FAIL' if probs else 'clean', len(rep),
                                                      '; '.join(probs[:6]) + (' ...' if len(probs) > 6 else '')))
        print('split_check: %s: %d hosted units, %d with replaced functions, %d problem(s): %s' % (
            a.map or a.obj, len(res), sum(1 for v in res.values() if v[2]), nbad, 'FAIL' if nbad else 'PASS'))
    if a.json:
        import json
        with open(a.json, 'w') as f:
            json.dump({u: {'object': o, 'problems': p, 'replaced': sorted(r), 'odr_copies': ODR.get(u, [])}
                       for u, (o, p, r) in res.items()}, f, indent=1)
    sys.exit(1 if nbad else 0)


if __name__ == '__main__':
    main()
