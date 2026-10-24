# Actual SH4ZAM arithmetic in the fused backface emitter

`room/backface_sh4zam.hpp` calls the actual pinned SH4ZAM `shz_vec2_sub`
and `shz_fmaf` APIs. `generate.py` compiles that body with the Dreamcast
GCC 15.2.0 single-precision ABI. It verifies all compiler-selected
instructions and six float-argument ABI probes before mechanically adapting
registers into `platform/backface_sh4zam_area.inc`. The checked-in generated
macro is consumed by the generic AND streaming `FAST_STEP` paths in
`platform/backface_sh4.S`; both world and actor calls therefore execute the
SDK-compiled arithmetic inline, with no per-triangle function call.

The adapter preserves live projected coordinates and maps the result to FR2.
For the fast path it partitions the compiler-selected dependency DAG around
the existing SQ stores: independent subtractions are reordered and a register
move is exchanged with independent FNEG. There is no replacement determinant
formula or hand-selected approximate FIPR. The compiler rounds the second
product, negates it and FMACs the first product onto it, matching the actual
CPU_BACKFACE=1 world AND actor target objects. A register barrier prevents
reverse fusion. The finite cancellation witness in the kernel tests matters:
a mathematically collinear triangle is accepted by actual target FMAC while
a strict two-product C host expression would reject it.

The run/parity state machine, material/clip decisions and SQ burst scheduling
remain the existing bespoke emitter; SH4ZAM does not provide those game rules.
Its `shz_sq_memcpy32_1` is deliberately not used: it fires PREF internally,
requires actor command flags prepared in advance, and toggles FSCHG per vertex.
That would undo the fused emitter's scheduling. A discarded wrapper prototype
is retained only in external owned draft evidence; it is not a runtime source.

## Build contract

Run `python3 ../tools/d367/backface_sh4zam_sdk/generate.py --check` before
assembling backface_sh4.o. Cwd does not matter. The default compiler is
/opt/toolchains/dc/sh-elf/bin/sh-elf-g++; `--compiler` or SH4_CXX overrides it.
SDK pin 33fa4850cacb30dd0ad35485ef035526ec4ce782, a clean SDK tree, compiler
15.2.0, argument ABI, selected instructions, generator/header source identities
and exact committed macro are checked. A mismatch fails closed. The parent
owns the CPU2-only Make dependency and selectors; CPU0/CPU1 are untouched here.

By default the checker creates a fresh Python TemporaryDirectory under TMPDIR
(or /tmp), writes four small probe assembly/object files, and removes only
that owned temporary directory. It never edits the SDK or committed macro in
--check mode. Build-slot ownership is inherited from the parent build.
`--objects <owned-dir>` and `--receipt <owned-file>` retain explicit evidence;
those options overwrite only the named probe outputs/receipt and must not be
pointed at another run. Generation without --check writes only the owned
backface_sh4zam_area.inc. No game assets or programmes are generated.

## Accepted evidence and remaining gates

Actual trace-off/on SH4 objects were interpreted by the existing kernel
opcode interpreter against the original C strip algorithm with its single
determinant expression lowered to the verified target FMAC order. 4,220
comparisons / 2,110 cases and 32 FR/SZ/PR/DN entry combinations passed; exact
vertex words, actor flags, EOL, parity, complete SQ bursts, all opposite-bank
sentinels, callee registers, FPSCR and adversarial trace clobbers passed.
This is host interpretation of actual target opcodes, not Flycast execution.

This direct SDK binding does not make the generic shz_fmaf API intrinsically
faster: it is inline a*b+c at this pin. The fast-path arithmetic instructions
are unchanged from the qualified FMAC assembly; the generic arithmetic order
changes only by independent scheduling. The requested <=4 incremental cycles
is still open. Caller-inclusive MODELLED schedules, actual C/ASM pixels,
KOS 48 KiB, r100 s30 heap4 and physical acceptance are separate remaining gates.
