# Issue #52: missing-actor and first-move audit

Base: `ea969bb241f77291d2ca43d706c9dc2d1226ee76` (`origin/t15/int`).
Branch: `codex/dam-crash-audit-20261023`. Code-only; no game data,
disc/image build, real I/O, Flycast run or console result.

**The bad register value has a concrete NULL-pointer explanation.** It does
not by itself prove a corrupt actor or vtable. A separate confirmed source
hole remains after successful allocation: the first move can retire the
Ganado, yet the dam script receives a non-NULL pointer. The new default-off
`R10C_SPAWN_LIVE_GUARD=1` closes that hole in the dam event using its existing
failure recovery. It does not establish the historical console cause.

## 1. Evidence and the malformed address

The retained [public Test21 identity audit](ISSUE52_DAM_CRASH_20261021.md)
binds the photographed program to `fe0efcddc736c49861b51988593629ca04ced336`,
tag `test-fe0efcdd-20261020`, and the final rebuild's overlays. Its relevant
observations are:

| Item | Value |
|---|---|
| PC / PR | `8c890d9a` / `8c890d8c` |
| r1 / fault address | `4328e3ff` / `4328e417` |
| Event | `0e0`, data-address read |
| Candidate st1_2 instruction | offset `42ba`, `mov.l @(24,r1),r1` |
| Candidate st1_2 base | `8c88cae0`, inferred from PC/PR; not independently observed |
| Public program SHA256 | `bd0970c0f745edee5418d17afde33d138ce2ec3d8ec870ef95a3a17e0439c62e` |
| Public st1_2 SHA256 | `f8a2931d0c7b4c463e28b7f74077fc6b81f89a022d02f77af6d09abad2ba96f4` |

Those exact public addresses/hashes are **inherited evidence from that
report**. This workspace did not contain the original public executable or
overlay, and this audit did not independently disassemble those bytes.

The new public-code evidence is more specific than recognizing a suspicious
floating-point-looking value:

* [DC_MiSTer, pinned source](https://github.com/ElectronAsh/DC_MiSTer/blob/50d619cb98025ee7b753ab1ab491910eb6fb25dc/S32X.sv)
  records the first word of `mpr-21931.ic501` as `32'h4328E3FF` at offset 0.
  The two little-endian SH instructions are `e3ff` (`mov #-1,r3`) and
  `4328` (`shll16 r3`). No BIOS image is included in this change.
* [MAME 0.249's Dreamcast implementation](https://github.com/mamedev/mame/blob/mame0249/src/mame/sega/dccons.cpp)
  maps `00000000..001fffff` as BIOS ROM and identifies `mpr-21931.ic501`
  as v1.01d, CRC32 `89f2b1a1`, SHA1
  `8951d1bb219ab2ff8583033d2119c899cc81f18c`.
* An independently compiled **current-source** probe using the real `cEm`
  declaration emits `mov.l @r4,r1`, then `mov.l @(24,r1),r1` for
  `em->setNoSuspend(1)`. This is fresh SH4 GCC output, not the public Test21
  object. The source ABI puts the vptr at the first word on SH4.

Under that ROM mapping, a NULL `em` gives the following exact arithmetic:

1. `r4 = em = 0`; the first load reads the ROM word `4328e3ff`.
2. The virtual dispatch loads at `4328e3ff + 24 = 4328e417`.
3. That address is not 4-byte aligned. It matches the photographed address
   and the data-read address exception. The pinned KOS header
   `kernel/arch/dreamcast/include/arch/irq.h` names `00e0`
   `EXC_DATA_ADDRESS_READ`.

This is a **conditional reconstruction**, not a claim that the reporter's
ROM/version, NULL return or module relocation was observed. It explains why
an ordinary missing actor can produce this particular nonzero "vtable"
value. It does not identify why creation failed: an absent mapping, actual
read failure, pool/preparation failure and other admission refusals are
distinct paths. The existing issue comments' failed-read diagnosis is not
additional register/ownership evidence in this audit.

## 2. Confirmed hole after construction

The actual source sequence is:

1. [`EmSetFromList2`](../../../src/game/em_set.cpp) creates and initializes
   the work, sets the ESL entry's admitted bit (`be_flag |= 2`), and runs
   `em->move()` **before returning**.
2. [`em10_R0_Init`](../../../src/em10/em10.cpp) sets `r_no_0 = 0xff` if
   `Em10SetFunc` is missing or `em10ModelInit` fails. The latter returns 0
   when `cModel::modelInit` fails.
3. `cEm10::move` sees `r_no_0 == 0xff`, calls `EmMgr.destroy(this)` and
   returns. [`cEmMgr`](../../../src/game/em.cpp) uses manager deletion
   policy 2: [`destroy`](../../../include/cManager.h) unlinks the work
   and sets `be_flag |= 0x200`; destruction is deferred by `dieCheck`.
4. `EmSetFromList2` still returns the same non-NULL pointer. The current
   `em == 0` room check accepts it, then invokes `setNoSuspend`, attaches
   an effect and installs a motion on an actor already scheduled for
   destruction. Later event cleanup retains that raw pointer across sleeps.

This proves use of a retired actor; it does not prove an immediate invalid
vptr load. With deferred deletion its vptr can initially remain valid. In
particular, this failure path has not been shown to explain the original
photograph's `4328e3ff`.

### Narrow repair

`R10C_SPAWN_LIVE_GUARD ?= 0` in `game30.mk` adds a direct, non-virtual
`(em->be_flag & 0x201) == 1` check immediately after the first list-2
attempt and after each retry. It runs before the caller sleeps or uses
the result. A returned but retired work becomes the existing missing-actor
outcome. NULL remains NULL; successful live results are unchanged.

The knob requires `EM_READ_RETRY=1` and accepts only 0/1. Its define is
limited to both module and ordinary/census r10c object paths. It adds no
global factory behavior, new retry policy or list-flag reset.

**Admission state is deliberately preserved.** After initial-move failure,
the ESL entry still has bit 2 set. Subsequent `EmSetFromList2` attempts
return `ALREADY_SET`; they do not allocate duplicate actors. The current
room loop still waits at most two 30-frame intervals and takes its skip
path, clearing `set` and requesting bank entries 3/4. The manager retains
its existing deferred cleanup. The tests cover failure on attempt 1, 2
and 3 and verify one initial move, no event/motion/effect use of the
retired actor, unchanged admission bits, and both bank spawn requests.

This check relies on the factory's returned work still being backed at the
immediate caller boundary. Native enemy pages are retained until room-owner
teardown (`parts_bridge.cpp`). It is not validation of arbitrary pointers,
vptr contents or a stale pointer from a later frame. The richer
`ISSUE52_ACTOR_DIAG` collector remains unchanged: its factory return record
can show the raw returned pointer, while the room's phase-3 note reflects
the filtered usable result.

## 3. Other boundaries reviewed

| Path | Finding and limit |
|---|---|
| r10c list 2, read/construction refusal | Existing Test22 retries and NULL skip cover this. New controls verify that successful recovery and permanent missing-actor behavior remain identical. |
| r10c drained-pool ambush, lists 6..12 | `ROUTE_CH21_FULL=1` already checks each pointer before `setNoSuspend` at both begin and exit. That flag is present in the derived public room recipe. These are NULL checks, not lifetime validation across the cutscene. |
| r11c C8, r11d PS2 sends, r100 trap motions | Existing `!=0` / `!=errEm` tests protect the immediate pointer accesses inspected. No new guard added. |
| r22c shooting targets | `shootMain` dereferences `EmMgr.create(0x3e)` directly; `funcUfo` and `r22cGateCtrl` also immediately use unguarded returned target pointers. The global read retry can still exhaust, and it cannot prevent pool failure. These are confirmed source hazards outside the dam patch, with minigame counters/gate behavior requiring a separate recovery design. No claim of a reproduced public-console failure. |
| `EM_MUST` | Its helper retries `EmCreate` only. Earlier list-admission refusals and first-move retirement are outside that retry loop. It uses a global request flag across sleeps. This is why changing all factory returns to NULL after first-move failure would require a broader caller/ownership change. No global change made. |
| Manager construction during a module miss | Source `create` clears a slot before a constructor whose module read may sleep; the slot is not explicitly reserved during that interval. The scheduler can run other tasks after the sleep. This is an interleaving frontier, not proof of the dam crash. `R10cInit` prereads em12, and the normal cached lookup does not yield before the initializer. |
| Indexed `create(id,no)` | The generic helper ignores `construct`'s return, but the inspected `EmMgr` indexed caller is player slot 0 (`game.cpp`), not the dam spawn. No speculative generic manager repair. |

The reviewed set is the dam creation/lifetime chain and the named neighboring
raw-return callers; this is not a claim to have qualified every later use of
every enemy handle in the game.

## 4. Qualification

The [reproduction tools](../tools/d367/dam_audit/README.md) require source and
the public compiler/headers only. Aggregate hashes/results are in
[`receipt.json`](../tools/d367/dam_audit/receipt.json).

* **Host:** 10 scenarios in each of baseline, absent, explicit 0 and enabled
  arms (40 scenario executions), with UBSan. Actual `EmSetFromList2`, complete
  r10c event/exit, the actual Ganado initialization failure prefix and move
  retirement branch, and `cManager::destroy` are extracted from production.
  Model/I/O/scheduler/camera/audio/effect services are controlled boundaries.
  OFF behavior is identical. Six successful/existing-missing/seen controls
  match exactly when enabled; four first-move failure controls stop retired
  uses. The action fingerprint includes order, sleep frames, state and
  counters; this is not a TA/render comparison.
* **Target:** complete r10c translation units compile under their actual
  Make-expanded Test22 public room recipes, including generated module
  declarations and `ROUTE_CH21_FULL=1`. Baseline, absent, explicit Make 0
  plus CPP 0, and enabled arms compile with diagnostics 0 and 1. OFF `-E -P`
  output and complete objects are byte-identical in both diagnostic variants.
  Debug records/line markers are excluded as in the prior public-profile
  controls. No full program/overlay link or library patch gate was run.
* **Wiring:** the enabled room recipe contains exactly its new define;
  `em_set.o` flags do not change. The ordinary/census room path also gets
  the define. Knob 2 and enabled-with-retry-0 are rejected by Make.

| Complete r10c object | OFF | ON | Delta |
|---|---:|---:|---:|
| Executable section bytes, diagnostics 0 | 14,560 | 14,592 | +32 |
| Allocated bytes, diagnostics 0 | 14,801 | 14,833 | +32 |
| `r10c_EmEvent` static stack, diagnostics 0 | 60 | 64 | +4 |
| Executable section bytes, diagnostics 1 | 14,792 | 14,832 | +40 |
| Allocated bytes, diagnostics 1 | 15,033 | 15,073 | +40 |
| `r10c_EmEvent` static stack, diagnostics 1 | 64 | 64 | 0 |

BSS stays 36 bytes in all four settings. These are object/static-stack
figures, not final overlay placement, peak stack or frame-time measurements.

## 5. What would settle the historical cause

Keep the current retry/NULL guard. On a matching failing diagnostic build,
retain the observed module base, phase-3 actor pointer and the collector's
completed attempt/read/refusal fields. A zero returned actor plus the
reporter's actual BIOS word/mapping would close the NULL-to-ROM explanation;
a nonzero returned actor would instead direct the investigation to that
actor's ownership/lifetime. A real negative read or a named admission refusal
must be observed separately. None is inferred merely from the bad r1 value,
the existing fix preventing a crash, or these code-only controls.
