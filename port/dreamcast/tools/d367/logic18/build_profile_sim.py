#!/usr/bin/env python3
"""Build a separate, charge-preserving current hwsim attribution executable.

The source is copied, never edited in place. Each anchor must match exactly once.
L18_SYMBOLS enables the exporter; ordinary timing outputs must remain byte-identical.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'Expected one anchor, got {source.count(old)}: {old[:100]}')
    return source.replace(old, new, 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    original = a.source.read_bytes()
    s = original.decode().replace('\r\n', '\n')
    patches = [
        ('static void charge(PcStat *s, int cat, double c)',
         '#include "profile_context.h"\nstatic void charge(PcStat *s, int cat, double c)'),
        ('    s->cyc[cat] += (u64)llround(c * 16.0);   /* 1/16 cycle fixed point */',
         '    s->cyc[cat] += (u64)llround(c * 16.0);   /* 1/16 cycle fixed point */\n'
         '    l18_charge(l18_charge_token, s == &other ? 0 : 0x8c000000U + 2U * (u32)(s - ps), (u64)llround(c * 16.0));'),
        ('    u16 op = ram_valid(pc) ? code_at(pc) : 0x0009;',
         '    u16 op = ram_valid(pc) ? code_at(pc) : 0x0009;\n    l18_before(pc, op);'),
        ('        int cat = C_BASE; PcStat *cs = s;',
         '        int cat = C_BASE; PcStat *cs = s; unsigned l18_cost_token = l18_current;'),
        ('if (floor_t > t) { t = floor_t; cat = floor_cat; cs = PS(floor_pc); }',
         'if (floor_t > t) { t = floor_t; cat = floor_cat; cs = PS(floor_pc); l18_cost_token = l18_floor_token; }'),
        ('if (dep > t) { t = dep; cat = dcat; cs = s; }',
         'if (dep > t) { t = dep; cat = dcat; cs = s; l18_cost_token = l18_current; }'),
        ('if (lockt > t) { t = lockt; cat = C_FLOCK; cs = s; }',
         'if (lockt > t) { t = lockt; cat = C_FLOCK; cs = s; l18_cost_token = l18_current; }'),
        ('if (tf > t) { t = tf; cat = icat; cs = s; }',
         'if (tf > t) { t = tf; cat = icat; cs = s; l18_cost_token = l18_current; }'),
        ('        charge(s, C_BASE, b0 - t_prev);',
         '        l18_charge_token = l18_current;\n        charge(s, C_BASE, b0 - t_prev);\n        l18_charge_token = l18_cost_token;'),
        ('    floor_t = 0; floor_cat = C_BASE;',
         '    floor_t = 0; floor_cat = C_BASE; l18_charge_token = l18_current;'),
        ('if (stall > 0) { floor_t = t + stall; floor_cat = C_MEMMIX; floor_pc = pc; memcpy(fl_comp, acc, sizeof(fl_comp)); }',
         'if (stall > 0) { floor_t = t + stall; floor_cat = C_MEMMIX; floor_pc = pc; memcpy(fl_comp, acc, sizeof(fl_comp)); l18_floor_token = l18_current; }'),
        ('if (r > floor_t) { floor_t = r; floor_cat = C_BRANCH; floor_pc = (br_pc == pc - 2) ? br_pc : pc; }',
         'if (r > floor_t) { floor_t = r; floor_cat = C_BRANCH; floor_pc = (br_pc == pc - 2) ? br_pc : pc; l18_floor_token = (br_pc == pc - 2) ? l18_branch_token : l18_current; }'),
        ('if (d->kind & (K_BRCD | K_BRU | K_BRREG)) { br_t = t; br_kind = d->kind; br_pc = pc; }',
         'if (d->kind & (K_BRCD | K_BRU | K_BRREG)) { br_t = t; br_kind = d->kind; br_pc = pc; l18_branch_token = l18_current; }'),
        ('    double t0 = t_prev;', '    double t0 = t_prev;\n    l18_begin(path);'),
        ('    tot_cycles += frame_cycles;', '    tot_cycles += frame_cycles;\n    l18_end();'),
        ('    load_elf(elf);', '    load_elf(elf);\n    l18_init(getenv("L18_SYMBOLS"), OUT);'),
    ]
    for old, new in patches:
        s = replace_once(s, old, new)
    h = Path(__file__).with_name('profile_context.h')
    shutil.copyfile(h, a.out / h.name)
    (a.out / 'hwsim.original.c').write_bytes(original)
    generated = a.out / 'hwsim_profile.c'
    generated.write_text(s)
    command = ['cc', '-O2', '-Wall', '-Wextra', str(generated), '-lm', '-o', str(a.out / 'hwsim_profile')]
    subprocess.run(command, check=True)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    manifest = dict(source=str(a.source), source_sha256=sha(original),
                    generated_sha256=sha(generated.read_bytes()),
                    header_sha256=sha(h.read_bytes()), anchors=len(patches), command=command)
    (a.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
