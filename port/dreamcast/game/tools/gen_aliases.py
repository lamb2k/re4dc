#!/usr/bin/env python3
"""Generate the linker assignments that bind the recovered sources' PowerPC link
names to the SH-4 symbols that define them.

The sources declare a number of functions and globals by their PowerPC link
name as a matching aid: `extern GlobalWork* pG` reached through `asm("pG")`,
`IdUnit* unitPtrI(...) asm("unitPtr__8IDSystemUcUc")` (a GCC 2.95-mangled
member), `void EstSetB(...) asm("EstSet")` (an extern "C" overload). On
`sh-elf` a C symbol carries a leading underscore and members use Itanium
mangling, so those names stay unresolved although their definitions compiled.
This tool reads the undefined names without an underscore, decodes the GCC 2.95
mangling, finds the matching SH-4 definition and writes one `name = _symbol;`
line per alias for the linker (a script that contains only assignments augments
the default one).

    gen_aliases.py <undefined-names> <nm-pairs> <out.ld>

<undefined-names>: one name per line (from `sh-elf-nm`, ' U ' entries).
<nm-pairs>: lines "<mangled>\t<demangled>" of every defined symbol.
"""
import re
import sys

undef = [l.strip() for l in open(sys.argv[1]) if l.strip()]
pairs = {}
for line in open(sys.argv[2], encoding="utf-8", errors="replace"):
    m, _, d = line.rstrip("\n").partition("\t")
    pairs.setdefault(d, []).append(m)
mangled_set = {m for ms in pairs.values() for m in ms}

# ---- GCC 2.95 (gnu v2) mangling, the subset the sources use -----------------
V2_BASIC = {"i": "int", "f": "float", "d": "double", "c": "char", "s": "short", "l": "long",
            "v": "void", "b": "bool", "x": "long long", "w": "wchar_t"}

def v2_args(s):
    """Decode a v2 argument list to a list of Itanium-demangled type strings."""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "N":  # N<count><index>: repeat parameter <index> <count> times
            cnt = int(s[i + 1]); idx = int(s[i + 2]); i += 3
            out.extend([out[idx - 1]] * cnt); continue
        if c == "T":  # T<index>: same as parameter <index>
            idx = int(s[i + 1]); i += 2
            out.append(out[idx - 1]); continue
        quals = []
        while s[i] in "PRCUS":
            quals.append(s[i]); i += 1
        if s[i] == "F" and quals == ["P"]:
            # P F <args> _ <return>: a pointer to function (r318 SetCallBack__7cObjScrPFP4cObj_v, ROUTE_CH3).
            j = s.index("_", i + 1)
            inner = v2_args(s[i + 1:j])
            if inner == ["void"]:
                inner = []
            ret = v2_args(s[j + 1:j + 2])[0] if s[j + 1] in V2_BASIC else None
            if ret is None:
                raise KeyError(s[j + 1:])
            out.append("%s (*)(%s)" % (ret, ", ".join(inner))); i = j + 2
            continue
        if s[i].isdigit():
            n = int(re.match(r"\d+", s[i:]).group(0))
            i += len(str(n))
            base = s[i:i + n]; i += n
        else:
            base = V2_BASIC[s[i]]; i += 1
        # sign/unsigned apply to the base
        if "U" in quals:
            base = "unsigned " + base
        if "S" in quals:
            base = "signed " + base
        if "C" in quals:
            base = "const " + base
        for q in reversed(quals):
            if q == "P":
                base += "*"
            elif q == "R":
                base += "&"
        out.append(base)
    return out

def norm(t):
    return t.replace(" *", "*").replace(" &", "&")

def v2_decode(name):
    """'unitPtr__8IDSystemUcUc' -> 'IDSystem::unitPtr(unsigned char, unsigned char)';
    '__5EventUc' -> 'Event::Event(unsigned char)'; 'dispSaveInfo__FiP8SaveInfoUci' -> free function."""
    m = re.match(r"^(.*?)__(F|\d+)(.*)$", name)
    if not m:
        return None
    fn, kind, rest = m.groups()
    if kind == "F":
        args = v2_args(rest)
        return "%s(%s)" % (fn, ", ".join(args))
    n = int(kind)
    cls = rest[:n]; rest = rest[n:]
    if fn == "":
        fn = cls  # constructor
    if rest.startswith("F"):
        rest = rest[1:]
    args = v2_args(rest) if rest else []
    if args == ["void"]:
        args = []
    return "%s::%s(%s)" % (cls, fn, ", ".join(args))

def itanium_sig(dem):
    """Normalise an Itanium demangled signature for comparison: strip const on
    the function, collapse spaces."""
    dem = re.sub(r"\)\s*const$", ")", dem)
    return norm(dem)

lines = []
unresolved = []
for name in undef:
    # SH-4 C symbols carry one underscore, Itanium names start with __Z; a v2
    # constructor name (`__5EventUc`) starts with two underscores and a digit.
    if name.startswith("_") and not re.match(r"^__\d", name):
        continue
    target = None
    if "_" + name in mangled_set:
        target = "_" + name          # plain C name: the underscore-prefixed symbol
    else:
        sig = v2_decode(name)
        if sig:
            want = norm(sig)
            for dem, ms in pairs.items():
                if itanium_sig(dem) == want:
                    target = ms[0]; break
            if target is None:
                # constructors: Itanium has C1/C2; demangled text is the same, allow a
                # loose match on the class::name and argument count
                cand = [ms[0] for dem, ms in pairs.items()
                        if itanium_sig(dem).split("(")[0] == want.split("(")[0]
                        and itanium_sig(dem).count(",") == want.count(",")]
                if len(cand) == 1:
                    target = cand[0]
    if target:
        lines.append("%s = %s;" % (name, target))
    else:
        unresolved.append((name, v2_decode(name)))

with open(sys.argv[3], "w", newline="\n") as f:
    f.write("/* generated by gen_aliases.py: PowerPC link names -> SH-4 symbols */\n")
    for l in sorted(lines):
        f.write(l + "\n")
print("aliases: %d, unresolved: %d" % (len(lines), len(unresolved)))
for n, d in unresolved:
    print("  UNRESOLVED", n, "->", d)
