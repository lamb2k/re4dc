#!/usr/bin/env python3
"""pcs_table.py <serial> <elf> [--scene N] [--expect-top FUNCTION] [--nm sh-elf-nm]

The sampling profiler's table (lane eng-crash1; core/pc_sampler.cpp, lab arm PCSAMPLE; build_console_disc.sh's
PCSLEON and PCSSPIN scenes). Reads the image's "E1 PCS samples ..." and "E1 PCS top <rank> pc <pc> samples <n>" lines
(the N-th PCS block of the log with --scene N, 1 = the first) and resolves each pc against the image's symbol table
(sh-elf-nm -n on the ELF the disc was built with): rank, pc, samples, share of the kept samples, function + offset; then
the same samples summed by function. Flycast runs are function evidence, never a timing (the sampler shows where the
SH-4 spends its time, not how long a picture takes).
--expect-top F: PASS only if F is the function with the most samples (the control: PCSSPIN spends 10 ms of every 33 ms
in e1_pcs_spin, so it must be on top; on PCSLEON, which has no spin, the same expectation must FAIL).
"""
import argparse, bisect, re, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument('serial'); ap.add_argument('elf')
ap.add_argument('--scene', type=int, default=1)
ap.add_argument('--expect-top')
ap.add_argument('--nm', default='sh-elf-nm')
a = ap.parse_args()
text = open(a.serial, errors='replace').read().replace('\r', '').split('\n')
blocks, cur = [], None
for l in text:
    m = re.search(r'E1 PCS samples (\d+) kept (\d+) hz (\d+)', l)
    if m:
        cur = dict(head=l[m.start():], kept=int(m.group(2)), top=[]); blocks.append(cur); continue
    m = re.search(r'E1 PCS top (\d+) pc ([0-9a-f]+) samples (\d+)', l)
    if m and cur is not None: cur['top'].append((int(m.group(1)), int(m.group(2), 16), int(m.group(3))))
    m = re.search(r'E1 PCS timers: .*', l)
    if m and cur is not None: cur['timers'] = m.group(0)
if len(blocks) < a.scene:
    print(f'PCS blocks in the log: {len(blocks)}, asked for {a.scene}'); print('PCSTABLE FAIL'); sys.exit(1)
b = blocks[a.scene - 1]
syms = []
for l in subprocess.run([a.nm, '-n', '-C', a.elf], capture_output=True, text=True, check=True).stdout.split('\n'):
    p = l.split(' ', 2)
    if len(p) == 3 and p[1] in 'TtWw':
        syms.append((int(p[0], 16), p[2]))
addrs = [s[0] for s in syms]


def where(pc):
    i = bisect.bisect_right(addrs, pc) - 1
    return (syms[i][1], pc - syms[i][0]) if i >= 0 else ('?', 0)


print(b['head'])
if 'timers' in b: print(b['timers'])
kept = b['kept'] or 1
byfn = {}
print(f"{'rank':>4} {'pc':>8} {'samples':>7} {'share':>6}  function")
for rank, pc, n in b['top']:
    fn, off = where(pc)
    byfn[fn] = byfn.get(fn, 0) + n
    print(f'{rank:>4} {pc:08x} {n:>7} {100.0 * n / kept:5.1f}%  {fn}+0x{off:x}')
print('by function (the top pcs summed):')
order = sorted(byfn.items(), key=lambda x: -x[1])
for fn, n in order:
    print(f'  {n:>7} {100.0 * n / kept:5.1f}%  {fn}')
ok = bool(b['top'])
if a.expect_top:
    top = order[0][0] if order else '-'
    ok = ok and (top == a.expect_top or top.startswith(a.expect_top + '('))
    print(f'expect top {a.expect_top}: top is {top}')
print('PCSTABLE', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
