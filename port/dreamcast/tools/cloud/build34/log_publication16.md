EF16 bounded publication profile
===============================

`LOG_PUBLICATION16=0` is the default. The enabled profile requires exactly
`LOG_ATOMIC16=1 OT_WALK_CHECK=0`; `LOG_RECORD16=0` and `1` both compose. The new
define reaches only `platform/mem.o` and `platform/fault.o`. Old OFF preprocessing
and host objects are compared byte-for-byte to parent
`115c6105369f777e5cf883f5b6d69aeab264f1ad`, including existing RECORD16, ring-header,
old atomic, and crash-test compositions. No existing observer/judge is changed.

Publication and refusal
-----------------------

One compiler-atomic, nonblocking writer claim covers each entire raw call or
engine formatting call. A competing writer refuses immediately; it never waits,
spins for an owner, steals ownership, or interleaves bytes into an accepted call.
There is no heap allocation, queue, deferred spool, or recovery manager. The
fixed state is 416 bytes in the inspected SH-4 object. An owner that never returns
is never reaped: later calls remain refused, with copied terminal evidence still
available independently of that owner.

Unmasked thread raw calls retain arbitrary valid lengths. Copies use at most
255 byte stores in each IRQ window, restoring the exact incoming SR between
windows. Calls entered inside an interrupt or with nonzero SR.IMASK accept at
most 255 bytes and refuse larger inputs before reading the source. This bound
does not bound time spent already masked by a caller, the compiler-atomic
exception restart, or target instruction latency. Ring/head aliases retain the
old bytewise forward reads and publications, including wrap of the 32-bit head.
There is no source snapshot, bulk-tail substitution, or truncation of raw data.

`re4dc_log_write16` returns accepted, busy, context, invalid, terminal, or
abandoned. Device `ringWriteBuffer` returns the supplied length only on complete
acceptance. Invalid signed/null inputs retain EINVAL/EFAULT; busy uses EAGAIN,
oversized masked/IRQ input uses EMSGSIZE, terminal/abandoned uses EIO. There is no
partial-success receipt. A terminal interruption can leave a published prefix;
if a synthetic handler returns, the owner stops and reports abandoned. No later
normal call can append after terminal stop. Each outcome has an idempotent
sticky seen flag; evidence loss is also sticky. There are no diagnostic counts
to wrap or separate overflow markers that an abandoned owner could fail to set.
Legacy void `re4dc_log_raw`/`re4dc_log` expose refusal through this state, not a new ABI.

The engine formatter claims before `vsnprintf`. Masked/interrupt contexts refuse
before formatting, and reentry never enters libc. Normal formatting retains the
old 255-byte truncation; formatter failure refuses. Console output remains after
successful ring acceptance and outside the writer claim. Crash-test append
counts include accepted raw, actual device, and engine formatter calls, with
ownership released before the intentional halt hook.

Terminal evidence and consumer boundary
--------------------------------------

The logger records in actual `onFault` and `re4dc_halt` bypass formatting. A fixed encoder attempts one
bounded ring row, retaining `FAULT code=` and `HALT stop:` markers. Fault capture
copies all 16 registers, PC/PR/SP/SR, EXPEVT/TEA, interrupt/thread/stack context;
halt copies line/frame/SR/thread and a 63-byte file prefix. File truncation and
missing-file flags are explicit. The selected compiler lowers aggregate zeroing
to bounded, reentrant `memset`; no formatting call is used in this path.

Two slots are first-claim, release-published, and immutable after ready. A reader
must acquire-load ready before inspecting a payload. A nested fault can use the
second slot while the first is unfinished. A third claim sets explicit sticky
lost state, without a counter or overflow. An unfinished slot is never readable or
stolen. Published evidence is never overwritten. A main-ring refusal does not
claim that a fault row exists: copied evidence and busy/lost state are separate.
The existing ring reader does not decode these slots, and its raw-RAM/cache and
full-memory judge remain unchanged. New state is not a relaxed memory PASS.
Existing crash-screen/context, VMU and terminal stage/mask/park hooks remain.
The initial crash-screen context hook only copies scalars. The retained screen
fault/halt hooks call `snprintf` and `show()` after the copied evidence, ring
attempt, and final IRQ disable. Their external formatter reentry and screen
completion are outside the logger guarantee; immutable evidence is captured
before them. Keeping the hooks does not certify their libc context behavior.

The selected KOS `kernel/debug/dbgio.c` has an external `dbgio_printf` formatter:
it uses a static buffer, formats before the device callback, skips its lock in
IRQ context, ignores the callback result, and returns the formatting length.
The actual `dbgio_write_buffer[_xlat]` path propagates the new device refusal;
`dbgio_printf`'s preceding formatter and false upstream status are explicitly
outside this profile's guarantee. The host suite retains that false-success
witness as an exclusion, not as a successful publication. `OT_WALK_CHECK`'s
external fault formatter is therefore excluded by a Make/source dependency.
The existing full-play crash rule and hwready comparison both consume
`FAULT code`; their markers, HALT matching, and the ring reader are preserved.

Compiler/exception dependency
-----------------------------

The inspected GCC 15.2 SH-4 TUs use `-matomic-model=soft-gusa`: flag claim is a
restartable byte load/store with r15=-4, metadata uses idempotent stores,
and release is a byte store. No libatomic helper or dynamic initializer
is required. This relies on the selected KOS exception entry, not custom ASM.
The installed `libkallisti.a` and a retained linked ELF both contain the same
entry bytes through +0xcf: rollback test +0x12/+0x14, rollback +0xbc..+0xcc,
rejoin +0x18, before dispatch +0x34. The authority tool reads archive/ELF only.

Tests and remaining gates
------------------------

Run from the repository root (fresh output directories):

```sh
python3 port/dreamcast/tools/cloud/build34/log_publication16_host.py \
  --kos /root/work/kos-re4dc-d367 --output /root/probe/ef16-host
python3 port/dreamcast/tools/cloud/build34/log_publication16_host.py \
  --kos /root/work/kos-re4dc-d367 --sanitize --output /root/probe/ef16-san
python3 port/dreamcast/tools/cloud/build34/log16_host.py --output /root/probe/ef16-old-raw
python3 port/dreamcast/tools/cloud/build34/log_record16_host.py --output /root/probe/ef16-old-record
```

The new fixtures extract the actual publisher, raw/formatter/device callbacks,
fault/halt builders and terminal handlers, plus the selected KOS device wrappers.
For actual terminal handlers only, MMIO reads are substituted and the final park
throws in the host; crash-screen/context/VMU hooks still execute. Deferred IRQ and
forced returning schedules cover every ring publication and window edge. Tests
cover input lengths through 262157, cursor/ring wrap, live ring/head aliases,
all 16 IMASK values, interrupt entry, formatting/reentry/failure, actual device
error propagation, terminal interruption and sticky loss without overflow. A separate local
copy instrumentation expands the evidence assignment into equivalent byte
stores to interrupt every copy and ready edge; readers reject partial evidence.
The normal actual helper remains uninstrumented in the main fixture.

The old raw/record suites retain their original corruption witnesses, including
all six forced returning synchronous/NMI counterexamples. New tests prove safe
coherent publication or explicit refusal; they do not rename old corruption.
Enabled full host TUs cover RECORD16, ring header, crash-test, and optional
crash-screen/VMU hooks. Primary Make tests cover exact expanded 0/1, whitespace,
invalid values, dependencies and target-only macro scope.

Source/host and compile-only target evidence do not qualify target IRQ duration,
raw-RAM/cache visibility, full-memory acceptance, an NMI/bypass entry, stack
exhaustion from arbitrary nested faults, or hardware/runtime behavior. Any
future target profile must recheck its compiler lowering and selected exception
archive. No throughput or speed claim is made.
