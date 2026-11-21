#!/usr/bin/env python3
"""r119_split_check.py (lane eng-e2c): the hosted r119 object hands its thunder to the engine.

    r119_split_check.py <h/st1/r119.o> [--nm sh-elf-nm] [--objdump sh-elf-objdump]

r119.cpp's three thunder functions (r119_ThunderMove, r119_ThunderFlagOn, r119_ThunderFlagOff) are `static`; the boss
image compiles the unit with services/boss/r119_weak.h force-included so they are weak global symbols that the engine's
bodies (services/boss/r119_thunder.cpp) replace. That only works when nothing reaches the original code another way.
Checked on the object:
  1. each of the three is a weak symbol (nm W);
  2. no relocation anywhere names one of their sections (a section-relative reference would keep the original body
     reached whatever the symbol resolves to);
  3. no other function references what only the thunder calls (SceSndCallThunder, EffSetToolStateCallBack,
     EffGetToolState): a copy inlined into R119Init or another task would show it.
Exit 0 PASS, 1 FAIL (each failing rule printed), 2 usage. Control: the object built without the force-include (the
image's R119_ORIG=1) fails rules 1 and 2.
"""
import re
import subprocess
import sys

FUNCS = ['_ZL16r119_ThunderMovev', '_ZL18r119_ThunderFlagOnv', '_ZL19r119_ThunderFlagOffv']
ONLY_THUNDER = ['SceSndCallThunder', 'EffSetToolStateCallBack', 'EffGetToolState']


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    nm, od = 'sh-elf-nm', 'sh-elf-objdump'
    if '--nm' in args:
        nm = args[args.index('--nm') + 1]
    if '--objdump' in args:
        od = args[args.index('--objdump') + 1]
    obj = args[0]
    syms = subprocess.run([nm, obj], capture_output=True, text=True, check=True).stdout.splitlines()
    relo = subprocess.run([od, '-r', obj], capture_output=True, text=True, check=True).stdout.splitlines()
    bad = []
    for f in FUNCS:
        kinds = [ln.split()[-2] for ln in syms if ln.split()[-1].lstrip('_') == f.lstrip('_')]
        if kinds != ['W']:
            bad.append('rule 1: %s is %s, not one weak symbol' % (f, kinds or 'absent'))
    sec = None
    for ln in relo:
        m = re.match(r'RELOCATION RECORDS FOR \[(.*)\]:', ln)
        if m:
            # debug information names every section it describes: not a reference that reaches code
            sec = None if m.group(1).startswith(('.debug', '.eh_frame', '.comment')) else m.group(1)
            continue
        parts = ln.split()
        if len(parts) < 3 or sec is None or not re.match(r'^[0-9a-f]+$', parts[0]):
            continue
        val = parts[2].split('+')[0]
        own = any(sec.endswith(f) for f in FUNCS)
        if any(val == '.text.' + f for f in FUNCS):
            bad.append('rule 2: section %s names %s by its section' % (sec, val))
        if not own and any(val.lstrip('_') == c for c in ONLY_THUNDER):
            bad.append('rule 3: section %s calls %s (a thunder body outside the thunder functions)' % (sec, val))
    for b in bad:
        print(b)
    print('r119_split_check: %s: %s' % (obj, 'FAIL' if bad else 'PASS'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
