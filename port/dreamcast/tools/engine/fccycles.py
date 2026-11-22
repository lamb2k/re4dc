#!/usr/bin/env python3
"""fccycles.py <elf> <opcode list> <range> [<range>...] [--clock 70] [--section <name>]: what the calibrated tier charges for a code path.

Lane eng-draw1. The calibrated tier (console-build Flycast, dynarec, [config] Sh4Clock 70) charges time by block, not by
memory or cache: when the dynarec compiles a block it adds, per instruction, the opcode table's issue cycles unless the
instruction pairs with the one before it (different units, neither CO, not both the same non-MT unit), plus 2 for each of
the first three memory instructions of the block; the block's sum is scaled by 200 / Sh4Clock and rounded (core/hw/sh4/
sh4_cycles.cpp countCycles, dyna/decoder.cpp dec_DecodeBlock, flycast-console f06da2d8). A block ends after a branch (and
its delay slot) and after a conditional branch; an FPSCR write ends it only on the decoder's fallback path (fschg and
frchg have decoders of their own and do not end a block).

<opcode list> is that build's core/hw/sh4/sh4_opcode_list.cpp (masks, issue cycles, unit and execution type per opcode).
A <range> is start-end (hex, end exclusive): the instructions executed in order for one pass of the path (an iteration of a
loop, a branch not taken). Prints each Flycast block (instructions, issue cycles, memory charge, scaled cycles) and the
total in 200 MHz cycles and in microseconds, which is what the tier's clock advances for that path.

Control: --selftest runs three hand-made blocks with known charges (a pair that issues together, a CO instruction that
never pairs, four memory loads of which three are charged) and exits 1 if any differs."""
import re, subprocess, sys

MASKS = {'Mask_n_m': 0xF00F, 'Mask_n_m_imm4': 0xF000, 'Mask_n': 0xF0FF, 'Mask_none': 0xFFFF, 'Mask_imm8': 0xFF00,
         'Mask_n_imm8': 0xF000, 'Mask_n_ml3bit': 0xF08F, 'Mask_nh3bit': 0xF1FF, 'Mask_nh2bit': 0xF3FF}
UNITS = ['MT', 'EX', 'BR', 'LS', 'FE', 'CO']
MEM_EX = {2, 3, 5, 6, 7, 12, 17, 18, 19, 22, 23, 25, 27, 29, 31, 33, 35}
WRITES_PC, DELAY, WRITES_SR, WRITES_FPSCR = 2, 4, 8, 16
TYPE = {'Normal': 0, 'ReadsPC': 1, 'WritesPC': 2, 'Delayslot': 4, 'WritesSR': 8, 'WritesFPSCR': 16, 'Invalid': 128,
        'UsesFPU': 2048, 'FWritesFPSCR': 2048 | 16, 'ReadWritePC': 3, 'WritesSRRWPC': 8 | 3, 'Branch_dir': 3, 'Branch_rel': 3,
        'Branch_dir_d': 7, 'Branch_rel_d': 7}


def load_table(path):
    rx = re.compile(r'\{\s*([\w]+)\s*,\s*\w+\s*,\s*(Mask_\w+)\s*,\s*(0x[0-9A-Fa-f]+)\s*,\s*([\w|]+)\s*,\s*"([^"]*)"\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*(\d+)')
    t = []
    for l in open(path, errors='replace'):
        m = rx.search(l)
        if not m: continue
        ty = 0
        for part in m.group(4).split('|'): ty |= TYPE.get(part, 0)
        # an FPSCR write ends the block only on the decoder's fallback path (no decoder of its own, no generic decode)
        fallback = m.group(1) == '0' and 'dec_' not in l[m.end():]
        t.append(dict(mask=MASKS[m.group(2)], rez=int(m.group(3), 16), type=ty, name=m.group(5), issue=int(m.group(6)),
                      unit=UNITS.index(m.group(8)), ex=int(m.group(9)), fallback=fallback))
    return t


def lookup(table, op):
    for e in table:
        if op & e['mask'] == e['rez']: return e
    return None


def charge(table, ops, clock):
    """ops: list of 16-bit opcodes in execution order -> list of blocks (n, issue, mem, scaled)"""
    blocks = []; cur = None; pending_end = False
    for op in ops:
        if cur is None: cur = dict(n=0, issue=0, mem=0, last=5, memops=0, names=[])
        e = lookup(table, op)
        if e is None: raise SystemExit('unknown opcode %04x' % op)
        c = 0
        if e['ex'] in MEM_EX:
            cur['memops'] += 1
            if cur['memops'] < 4: c += 2; cur['mem'] += 2
        if cur['last'] == 5 or e['unit'] == 5 or (cur['last'] == e['unit'] and cur['last'] != 0):
            cur['last'] = e['unit']; c += e['issue']; cur['issue'] += e['issue']
        else:
            cur['last'] = 5
        cur['n'] += 1; cur['c'] = cur.get('c', 0) + c; cur['names'].append(e['name'])
        end = pending_end
        pending_end = False
        if e['type'] & WRITES_PC:
            if e['type'] & DELAY: pending_end = True
            else: end = True
        if e['type'] & WRITES_FPSCR and e['fallback']: end = True
        if end:
            blocks.append(cur); cur = None
    if cur: blocks.append(cur)
    for b in blocks: b['scaled'] = max(1, round(b.get('c', 0) * 200.0 / clock))
    return blocks


SECTION = None


def ops_from_elf(elf, ranges):
    ops = []
    for r in ranges:
        a, b = [int(x, 16) for x in r.split('-')]
        sec = ['-j', SECTION] if SECTION else []   # --section: an object file whose sections all start at 0
        txt = subprocess.run(['sh-elf-objdump', '-d'] + sec + ['--start-address=0x%x' % a, '--stop-address=0x%x' % b, elf],
                             capture_output=True, text=True).stdout
        for l in txt.splitlines():
            m = re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{2}) ([0-9a-f]{2})\s', l)
            if m: ops.append(int(m.group(3) + m.group(2), 16))
    return ops


def main():
    clock = 70
    args = sys.argv[1:]
    if '--clock' in args: i = args.index('--clock'); clock = int(args[i + 1]); del args[i:i + 2]
    global SECTION
    if '--section' in args: i = args.index('--section'); SECTION = args[i + 1]; del args[i:i + 2]
    if args and args[0] == '--selftest':
        t = load_table(args[1])
        # add r1,r2 (EX) + mov.l @r3,r4 (LS): pair -> 1 issue + 2 mem; fschg alone: 1; four loads (LS never pairs with
        # LS): 4 issue, 3 of them charged; a conditional branch (bf) ends the block, so a load after it is charged again
        cases = [([0x321c, 0x6432], 1 + 2), ([0xf3fd], 1), ([0x6432, 0x6532, 0x6632, 0x6732], 4 + 6),
                 ([0x6432, 0x6532, 0x6632, 0x8bfe, 0x6732], 9 + 0 + 3)]   # bf (BR) pairs with the load before it
        bad = 0
        for ops, want in cases:
            got = sum(b['c'] for b in charge(t, ops, 200))
            print('selftest', ['%04x' % o for o in ops], 'charged', got, 'expected', want, 'ok' if got == want else 'WRONG')
            bad |= got != want
        sys.exit(bad)
    elf, tab, ranges = args[0], args[1], args[2:]
    t = load_table(tab)
    blocks = charge(t, ops_from_elf(elf, ranges), clock)
    tot = sum(b['scaled'] for b in blocks)
    for i, b in enumerate(blocks):
        print('block %d: %d instructions, issue %d, memory %d, charged %d -> %d at %d MHz  [%s .. %s]' % (
            i, b['n'], b['issue'], b['mem'], b.get('c', 0), b['scaled'], clock, b['names'][0], b['names'][-1]))
    print('TOTAL %d instructions, %d charged cycles, %d cycles of 200 MHz = %.3f us at Sh4Clock %d' % (
        sum(b['n'] for b in blocks), sum(b.get('c', 0) for b in blocks), tot, tot / 200.0, clock))


if __name__ == '__main__':
    main()
