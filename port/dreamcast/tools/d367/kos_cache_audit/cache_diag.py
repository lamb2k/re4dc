"""Build-local instrumentation of the pinned whole-cache helper; no SDK edits."""
import hashlib
from pathlib import Path

BASE_HELPER_SHA256 = "15837af526978b9aa943be6903ceec88d68b851a81d50cb0ce898aa377cff0dc"
TIMER_INPUTS = {
    "kernel/arch/dreamcast/kernel/timer.c": "f83f610d000f416f0f88030491a93f8934c85d02905c1de1ebdf54abede5416b",
    "kernel/arch/dreamcast/include/arch/timer.h": "10a76441f05c82e6d941d94f5215ef92575430001d9a20e354da2b1e5cc57b28",
    "include/kos/timer.h": "969784ade6c7556607ba33fd27794662677050bac8a7579a2721d51406efcb13",
}
TMU2_RELOAD = 12468720
TICK_HZ_NOMINAL = 12468720


def validate_timer(kos):
    for relative, expected in TIMER_INPUTS.items():
        if hashlib.sha256((Path(kos) / relative).read_bytes()).hexdigest() != expected:
            raise ValueError("KOS_CACHE_P2_DIAG unsupported timer source: " + relative)


def increment(offset, bit, label):
    return f"""    mov.l @({offset},r4),r0
    add #1,r0
    mov.l r0,@({offset},r4)
    tst r0,r0
    bf .Ldiag_{label}_ok
    mov.l @(28,r4),r0
    or #{bit},r0
    mov.l r0,@(28,r4)
.Ldiag_{label}_ok:
"""


BEGIN = """    /* TMU2 is read-only; no clock API/ISR callback or wait in this helper.
       r1 alone survives the original sweep (caller-saved, otherwise unused).
       -1 = unavailable clock, -2 = pending underflow. */
    mov.l .Ldiag_tcnt,r0
    mov.l @r0,r1
    mov.l .Ldiag_reload,r0
    cmp/hs r1,r0
    bf .Ldiag_begin_unavailable
    mov.l .Ldiag_tstr,r0
    mov.b @r0,r0
    tst #4,r0
    bt .Ldiag_begin_unavailable
    mov.l .Ldiag_tcor,r0
    mov.l @r0,r2
    mov.l .Ldiag_reload,r0
    cmp/eq r0,r2
    bf .Ldiag_begin_unavailable
    mov.l .Ldiag_tcr,r0
    mov.w @r0,r0
    tst #7,r0
    bf .Ldiag_begin_unavailable
    mov.l .Ldiag_unf,r2
    tst r2,r0
    bf .Ldiag_begin_rejected
    bra .Ldiag_begin_done
    nop
.Ldiag_begin_unavailable:
    mov #-1,r1
    bra .Ldiag_begin_done
    nop
.Ldiag_begin_rejected:
    mov #-2,r1
.Ldiag_begin_done:
"""


def end():
    # No counter write occurs until after the original complete sweep + gap.
    # Consequently a dirty startup P1 BSS alias cannot overwrite these P2 stores.
    return """    mov.l .Ldiag_tcnt,r0
    mov.l @r0,r2
    mov.l .Ldiag_state,r4
    mov.l .Lp2_mask,r0
    or r0,r4
""" + increment(0, 1, "calls") + """    /* Original r3 is 512 normally,128 for each of two OC-RAM blocks. */
    mov #2,r0
    shll8 r0
    cmp/eq r0,r3
    bf .Ldiag_ram
""" + increment(32, 32, "full") + """    bra .Ldiag_mode_done
    nop
.Ldiag_ram:
""" + increment(36, 64, "ram") + """.Ldiag_mode_done:
    mov #-1,r0
    cmp/eq r0,r1
    bt .Ldiag_unavailable
    mov.l .Ldiag_tstr,r0
    mov.b @r0,r0
    tst #4,r0
    bt .Ldiag_unavailable
    mov.l .Ldiag_tcor,r0
    mov.l @r0,r0
    mov.l .Ldiag_reload,r3
    cmp/eq r3,r0
    bf .Ldiag_unavailable
    cmp/hs r2,r3
    bf .Ldiag_unavailable
    mov.l .Ldiag_tcr,r0
    mov.w @r0,r0
    tst #7,r0
    bf .Ldiag_unavailable
    mov.l .Ldiag_unf,r3
    tst r3,r0
    bf .Ldiag_rejected
    mov #-2,r0
    cmp/eq r0,r1
    bt .Ldiag_rejected
    cmp/hs r2,r1
    bf .Ldiag_rejected
    sub r2,r1
""" + increment(4, 2, "timed") + """    mov.l @(16,r4),r0
    clrt
    addc r1,r0
    mov.l r0,@(16,r4)
    mov.l @(20,r4),r0
    mov #0,r3
    addc r3,r0
    mov.l r0,@(20,r4)
    bf .Ldiag_sum_ok
    mov.l @(28,r4),r0
    or #16,r0
    mov.l r0,@(28,r4)
.Ldiag_sum_ok:
    mov.l @(24,r4),r0
    cmp/hs r1,r0
    bt .Ldiag_finish
    mov.l r1,@(24,r4)
    bra .Ldiag_finish
    nop
.Ldiag_rejected:
""" + increment(8, 4, "rejected") + """    bra .Ldiag_finish
    nop
.Ldiag_unavailable:
""" + increment(12, 8, "unavailable") + """.Ldiag_finish:
"""


LITERALS = """.Ldiag_tcnt:
    .long 0xffd80024
.Ldiag_tstr:
    .long 0xffd80004
.Ldiag_tcor:
    .long 0xffd80020
.Ldiag_tcr:
    .long 0xffd80028
.Ldiag_reload:
    .long 12468720
.Ldiag_unf:
    .long 0x100
.Ldiag_state:
    .long _re4dc_cache_p2_diag_counters
"""


def instrument(source, enabled=False):
    if not enabled:
        return source
    if hashlib.sha256(source.encode()).hexdigest() != BASE_HELPER_SHA256:
        raise ValueError("KOS_CACHE_P2_DIAG helper pin changed")
    begin = "    ldc r0,sr\n"
    finish = "    ldc r7,sr\n"
    size = "    .size _arch_dcache_wback_all_p2,.-_arch_dcache_wback_all_p2\n"
    assert source.count(begin) == source.count(finish) == source.count(size) == 1
    return source.replace(begin, begin + BEGIN).replace(finish, end() + finish).replace(size, LITERALS + size)
