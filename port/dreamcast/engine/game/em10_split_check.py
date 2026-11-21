#!/usr/bin/env python3
"""em10_split_check.py (lane eng-e2b): refuse a hosted em10 object in which a caller could still reach an original body
of one of em10's service functions after those are made weak and the engine's own are linked.

    em10_split_check.py --nm <nm tool> --obj <em10.o> --inline <opt-info file> --weak <symbol>...

em10's service functions (the 40 of lane eng-e2a's classification table, docs/engine/lanes/eng-e2a.md) are replaced at
link time: the hosted object's copies are made weak and the engine's strong ones win. That only works when every call
reaches the global symbol. The object is refused (exit 1) when:
  - a clone of one of the 40 exists (GCC's partial inlining, constant propagation or argument reduction: a local copy
    "[clone .part.0]" the callers call instead, which weakening cannot redirect);
  - the compiler's own report (-fopt-info-inline-optimized) shows one of the 40 inlined into a caller;
  - a symbol of --weak is not a weak definition in the object (the objcopy step did not take).
The image builds em10.o with the interprocedural optimisations off (game/fight.mk EM10_NOIPA); the control build
EM10_IPA=1 keeps them and this check must fail on it. Exit 2 on a missing input.
"""
import re
import subprocess
import sys

SERVICE = set('''Em10SetSeTbl em10BehindSeCk em10BreathSe em10CallVoiceSe em10CallVoiceSe2 em10CsawSignSe em10FootSe
em10SetDamageVoice em10BloodSet em1cBloodSet em10KickHitMark em10SetDmWaterEff em10SetWaterEff em10WepSeEffSet
em10NeckMove em10BombNeckMove em10WaistMove em10ScaleCompress em10BlendMotSet em10ClawMove em10GatlingRollMove
em10BowgunMove em10ChainSet em10BeltSet em10ClothPartsSet em10GoodsPartsSet em10SackSet em10MouthPartsReset
em10ModelInit em10SetAccesory em10HandSet em10HeadSet em10CamMove em10CamMove2 em10CamMoveAshley em10CamMoveCri
em10CamMoveTakeaway em10SetCampos2 em10ScreenInCk cEm10::~cEm10'''.split())


def base(demangled):
    """the function's name without its arguments or clone suffix"""
    n = demangled.split('(')[0].split(' [clone')[0].split('/')[0]
    n = re.sub(r'\.(part|constprop|isra|cold|localalias)\.?\d*.*$', '', n)
    return n.lstrip('_') if n.startswith('_em10') or n.startswith('_Em10') else n


def fname(sig):
    """the function name of a signature in GCC's report ("void em10FootSe(cEm10*)", "virtual void cEm10::move()",
    "void _Z16em10CallVoiceSe2P5cEm10ii.part.0(cEm10*, int, int)"): the last word before the arguments, a mangled
    name's identifier taken from its length prefix, a clone suffix dropped"""
    n = sig.split('(')[0].split()[-1] if sig.split('(')[0].split() else sig
    n = re.sub(r'\.(part|constprop|isra|cold|localalias)\.?\d*.*$', '', n)
    m = re.match(r'_Z(\d+)', n)
    if m:
        k = int(m.group(1))
        n = n[len(m.group(0)):len(m.group(0)) + k]
    return n


def main():
    a = sys.argv[1:]
    try:
        nm = a[a.index('--nm') + 1]
        obj = a[a.index('--obj') + 1]
        inl = a[a.index('--inline') + 1]
        weak = a[a.index('--weak') + 1:]
    except (ValueError, IndexError):
        print(__doc__)
        sys.exit(2)
    try:
        dem = subprocess.run([nm, '-C', obj], capture_output=True, text=True, check=True).stdout.splitlines()
        raw = subprocess.run([nm, obj], capture_output=True, text=True, check=True).stdout.splitlines()
        report = open(inl, errors='replace').read().splitlines()
    except (OSError, subprocess.CalledProcessError) as e:
        print('em10_split_check: missing input: %s' % e)
        sys.exit(2)
    bad = []
    for ln in dem:
        p = ln.split(None, 2)
        if len(p) < 3:
            continue
        name = p[2]
        if re.search(r'\[clone |\.(part|constprop|isra|cold)\.', name) and base(name) in SERVICE:
            bad.append('clone %s' % name)
    for ln in report:
        # GCC's report: "Inlined <ret> <name>(<args>)/<n> into <ret> <name>(<args>)/<n> ..." (or "Inlining ... into")
        m = re.search(r'Inlin(?:ing|ed) (.*?)/\d+ into (.*?)/\d+', ln)
        if not m:
            continue
        what, into = fname(m.group(1)), fname(m.group(2))
        # a function's own split part put back into it (partial inlining undone) is not a copy in a caller
        if what in SERVICE and what != into:
            bad.append('inlined: %s' % ln.strip()[:200])
    kinds = {}   # symbol -> the kinds of its entries (a defined one and, after a redefinition, an undefined one)
    for ln in raw:
        p = ln.split()
        if len(p) >= 2:
            kinds.setdefault(p[-1], set()).add(p[-2])
    for s in weak:
        k = kinds.get(s, set())
        if not k & {'W', 'V'} or k & {'T', 't', 'D', 'd'}:
            bad.append('not weak: %s (%s)' % (s, ','.join(sorted(k)) or 'absent'))
    if bad:
        print('em10_split_check: FAIL %s: %d problem(s)' % (obj, len(bad)))
        for b in bad[:40]:
            print('  ' + b)
        sys.exit(1)
    print('em10_split_check: PASS %s: no clone or inlined copy of em10\'s %d service functions; %d symbols weak' % (
        obj, len(SERVICE), len(weak)))


if __name__ == '__main__':
    main()
