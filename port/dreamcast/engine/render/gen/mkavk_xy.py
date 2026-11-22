"""Lane eng-draw5 (item 2): generates render/avk_xy_sh4.inc, the engine's skinned position kernel without texture
coordinates, m1_avk_pos_skin_xy, from the released kernel's generator.

Lifted from: tools/game30/avk/mkavk.py and pos.tpl (origin/t15/int; the Test 27.2 release assembled
re4dc_avk_pos_skin_u16 from them, flags skin + u16 + pf, ACTOR_MOVCA off). The scheduler, the simulator (sim.py) and
the two-half loop emission are the old tool's, imported unchanged. What changes:
  * the template (render/gen/pos.tpl, written from the old pos.tpl by removing these lines): the uv record word load
    (mov.w @(4,r5),r0; shll2 r0; add r13,r0), the two uv halfword loads and their extu.w, the u, v conversion
    (lds / float twice, fmul fr12 / fr14, fadd fr13 / fr15), the two u, v stores, and the uv prefetch
    (@pf mov.w @(4,r5),r0; shll2 r0; add r13,r0; pref @r0); the store pointer steps 44 bytes a vertex, not 52;
  * the prologue: no first uv load, and r7 = entry + 16 (the first store is 1/w at +12), not entry + 24;
  * the name (m1_avk_pos_skin_xy) and no ACTOR_MOVCA lines (the engine never defines it).
Entries get x, y, 1/w at +4, +8, +12 and the outcode byte as before; words 0 and 4 to 7 are not written. The engine's
emitter (render/stage_sh4.S) reads words 0 to 3 of an entry and takes u, v from the strip corners, so the same
vertex words reach the chip. Same ABI as the old kernel (PositionPass, native_actor.inc): the uv pointer and au..bv are
not read.

Usage (WSL, from the repository root): python3 port/dreamcast/engine/render/gen/mkavk_xy.py
The schedule is cached in render/gen/sched-pos_skin_xy.txt (delete it to reschedule).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))   # port/dreamcast
sys.path.insert(0, os.path.join(ROOT, 'tools', 'game30', 'avk'))
sys.argv = sys.argv[:1] + ['-', '20000']
import mkavk as M   # noqa: E402  (the old tool, unchanged)
M.HERE = HERE       # template and schedule cache from render/gen

NAME = 'pos_skin_xy'


def pos_kernel_xy():
    """mkavk.pos_kernel with flags {skin, pf} and the prologue's uv lines removed (see the module text)."""
    flags = {'skin', 'pf'}
    lines = M.load_tpl(os.path.join(HERE, 'pos.tpl'), flags)
    cyc, order = M.get_schedule(NAME, lines, True, 'pos')
    seq = [lines[k] for k in order]
    em = M.Emitter(NAME)
    L = em.lab
    o = ['/* m1_avk_%s: scheduled loop %.2f model cycles per vertex (sim.py) */' % (NAME, cyc),
         '        .align  5', '        .global _m1_avk_%s' % NAME, '        .type   _m1_avk_%s, @function' % NAME,
         '_m1_avk_%s:' % NAME]
    ins = M.PUSH + ['mov     r4,r0', 'add     #40,r0'] + ['fmov.s  @r0+,fr%d' % f for f in range(8, 16)]
    ins += ['mov.l   @(0,r4),r5', 'mov.l   @(4,r4),r6', 'mov.l   @(8,r4),r12', 'mov.l   @(12,r4),r13',
            'mov.l   @(16,r4),r7', 'mov.l   @(20,r4),r8', 'mov.l   @(24,r4),r11']
    ins += ['mov.w   @r5,r1', 'shll2   r1', 'add     r1,r1', 'add     r12,r1', 'mov.w   @(6,r1),r0',
            'mov     r0,r14', 'mov.l   @(36,r4),r2', 'cmp/hs  r2,r0', 'bf      1f', 'mov     #0,r0', '1:',
            'mov.l   @(32,r4),r2', 'mov.b   @(r0,r2),r2', 'tst     r2,r2', 'bf      3f',
            'bra     %s' % L('exit'), 'nop', '3:', 'shll2   r0', 'shll2   r0', 'shll2   r0',
            'mov.l   @(28,r4),r2', 'add     r2,r0']
    ins += M.XMTRX_LOAD
    ins += ['mov.w   @r5,r1', 'add     r11,r5', 'shll2   r1', 'add     r1,r1', 'add     r12,r1']
    ins += ['mov.w   @r1+,r2', 'mov.w   @r1+,r3', 'mov.w   @r1,r1', 'lds     r2,fpul', 'float   fpul,fr0',
            'lds     r3,fpul', 'float   fpul,fr1', 'lds     r1,fpul', 'float   fpul,fr2', 'fldi1   fr3',
            'add     #16,r7', 'bra     %s' % L('rA'), 'nop']
    o += M.fmt(ins)
    tramp, stubs = [], []
    tgtA = {'end': L('deA'), 'switch': L('dsA')}
    tgtB = {'end': L('deB'), 'switch': L('dsB')}
    o += ['        .align  5', '%s:' % L('hA')]
    o += M.render(em, seq, (0, 4), tgtA, tramp, stubs)
    o.append('%s:' % L('hB'))
    bodyB = M.render(em, seq, (4, 0), tgtB, tramp, stubs)
    last = bodyB[-1]
    if not last.endswith(':') and not re.match(r'\s*(bt|bf|bra)', last):
        o += bodyB[:-1] + ['        bra     %s' % L('hA'), last]
    else:
        o += bodyB + ['        bra     %s' % L('hA'), '        nop']
    M.flush(o, tramp)
    part = [x for x in seq if not x[1]]
    o.append('%s:' % L('rA'))
    o += M.render(em, part, (0, 4), {'end': L('deR'), 'switch': L('dsR')}, tramp, stubs)
    o += ['        bra     %s' % L('hB'), '        nop']
    M.flush(o, tramp)
    o += M.drains(em, L, seq, True, (('A', (0, 4), seq), ('B', (4, 0), seq), ('R', (0, 4), part)), tramp, stubs)
    for sl, rl, ds in stubs:
        o += M.fmt(['%s:' % sl, 'mov.l   r2,@-r15', 'mov.l   r3,@-r15', 'mov     r0,r14', 'mov.l   @(8,r15),r2',
                    'mov.l   @(36,r2),r3', 'cmp/hs  r3,r0', 'bf      1f', 'mov     #0,r0', '1:', 'mov.l   @(32,r2),r3',
                    'mov.b   @(r0,r3),r3', 'tst     r3,r3', 'bt      2f', 'shll2   r0', 'shll2   r0', 'shll2   r0',
                    'mov.l   @(28,r2),r3', 'add     r3,r0'] + M.XMTRX_LOAD +
                   ['mov.l   @r15+,r3', 'bra     %s' % rl, 'mov.l   @r15+,r2', '2:', 'mov.l   @r15+,r3',
                    'bra     %s' % ds, 'mov.l   @r15+,r2'])
    o.append('%s:' % L('exit'))
    o += M.fmt(M.EXIT)
    o.append('        .size   _m1_avk_%s, .-_m1_avk_%s' % (NAME, NAME))
    stores = sum(1 for x in o if re.match(r'\s*fmov\.s\s+fr\d+,@-r7\s*$', x))
    assert stores and stores % 3 == 0 and not any(re.search(r'(?<![\w])r(9|10|13)', x) for x in o
                                                  if not x.strip().startswith(('mov.l   r', 'mov.l   @r15+', 'mov.l   @(12,r4)'))), \
        'a uv register is still used'
    return o, cyc


def main():
    o, cyc = pos_kernel_xy()
    head = ['/* render/avk_xy_sh4.inc -- GENERATED by render/gen/mkavk_xy.py (lane eng-draw5) from render/gen/pos.tpl and the',
            ' * released kernel generator tools/game30/avk/mkavk.py; edit the template or the script, not this file.',
            ' * m1_avk_pos_skin_xy(PositionPass*): re4dc_avk_pos_skin_u16 without the texture coordinates (x, y, 1/w and the',
            ' * outcode byte per record; entry words 0 and 4 to 7 untouched). Included by render/stage_sh4.S. */', '']
    path = os.path.join(HERE, '..', 'avk_xy_sh4.inc')
    open(path, 'w', newline='\n').write('\n'.join(head + o) + '\n')
    print('%s %.2f cycles/vertex (model, no misses); released pos_skin_u16 37.50' % (NAME, cyc))


if __name__ == '__main__':
    main()
