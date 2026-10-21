# SetEvd parent/bin admission transaction

Base: current `origin/t15/int` at `54cef5d1560c41d074beee05ffa1ecd38f2ee642`.
This is an independent side branch; it does not import the six-fix or capacity
candidate. `EVD_ADMISSION_TXN` defaults to zero and applies only to Dreamcast
`event.o`. No recipe is enabled. The recovered PPC path remains outside the guard.

## Defect and repair

The exact H064 fixture reproduces a parent plus first bin registered by a failed
`SetEvd`. After more bin capacity becomes available, retry returns success at
`EvdTbl.ChkDat` without admitting the missing bin. Baseline and disabled tests
retain that characterization.

The guarded `SetEvd` journals successful bin-reference increments and newly
created slots, within the existing 320-slot `myRoomInit` capacity. It publishes
the parent only after all required `SetBin` operations succeed. If any child or
the final parent registration fails, it subtracts only the recorded reference
deltas and clears only newly created slots whose count is now zero. Existing
bin data, debug allocation owners, flags and other references are preserved.
The journal uses 680 stack bytes and no persistent state or allocation.

Calling `DelEvd` on the failed partial parent would also delete unadmitted bins.
Calling ordinary `DelDat` would leave new permanent rows published at count zero
and could free a shared debug owner. Neither is used for rollback. The attempt
never acquired ownership of the caller's `dat2` on failure and does not free it.
New child entries borrow their parent and always have `dat2 == 0`.

A duplicate parent is checked against its **registered** header and required bin
names/types/negative source addresses. A complete resident parent retains the
existing name-reuse semantics and reference counts, including when a different
valid incoming header uses the same name. A legacy partial parent is refused
without mutation. Existing tables cannot establish which missing/shared bin
references that legacy parent acquired, so this patch does not invent a repair
for its prior incomplete state. The signed `DelDat` count range is checked before
adding another shared-bin reference.

## Actual-source host qualification

`test_event_admission_txn.py` exports the exact H064 test, constructor and selector
from `d396bd9e70f7953866e2055b392dda39e0087644`. Baseline and OFF run the unchanged
H064 event test. ON includes that fixture with its old main renamed and extends
only host declarations, logger/memory observation boundaries and test cases.
Every runtime method body is extracted from the selected actual source. There
is no replacement admission or refcount model.

The guarded suite passes 70 cases under UBSan:

- Every child failure in a six-bin admission and the final parent-capacity
  failure, for permanent and debug-retired flags; immediate retry and duplicate
  success; no partial parent publication and no caller-buffer free.
- Real invalid child addresses, every child-name failure position, parent-name
  failure, invalid inputs/table bounds and zero-bin success.
- Shared prior bin owners with counts 0/1/7, both flag classes, repeated names,
  signed-count saturation refusal and exact rollback; new-slot mask edges
  0/31/32/63/64/319.
- Full 320-bin rollback on the 321st admission, then a complete 320-bin retry.
- Legacy incomplete-parent refusal, complete resident-parent reuse, unrelated
  complete parents and shared bins preserved through failure/retry, and actual
  `GetEvd`/`DelEvd` controls.
- Actual `ToolCoreEvdDel`, table `init`/`end`, and `myRoomInit` retirement/reinit
  controls. Old permanent-row behavior remains explicit. These are table
  lifecycle controls, not an execution of global soft reset.

The host uses a fixed `0x90000000` mapping to preserve the source's signed
32-bit address guard. ASan's ShadowGap disallows that region; this test uses
UBSan only. Projected host class layout is not target ABI. Debug frees and table
heap operations are recorded host boundaries, and transport is a refused stub.
168 observations at actual table-clear boundaries confirm no parent was
published during fresh child preparation/rollback. The original H064 fixture's
asset-free header constructor is reused.

Run in a fresh output directory:

```sh
python3 port/dreamcast/tools/d367/cache21-fixes/test_event_admission_txn.py \
  --out /root/probe/cache21-event-admission-host-fresh
```

## Actual SH4 object qualification

Whole `event.o` is compiled using each arm's actual Makefile, generated headers
and selected KOS toolchain, with the same snapshot source path and debug stripped
for comparison. `CABIN_SOURCE=0` and `1` use the same valid route/native/audio
prerequisites. Only this small object is compiled; no overlay or whole program
is linked. `-fstack-usage` records the compiler's static frame size.

| Cabin | Baseline = OFF SHA256 | ON SHA256 |
| --- | --- | --- |
| 0 | `cbb29914d2d746dab7900cfe66abdf2541c808a1c61f06477953ee50df22adcf` | `fded74d94da28183f33eb591f9e44a87ddf6c081f66f31afcfc290e8e83c3d58` |
| 1 | `bd46343f42ea3107ce8d4082dde337e4b7a13f9b545d64afa5d10debe1070882` | `bcce4e402761218d6349ea83b9595dc8c04b390f7bcb182f5ff8f3e82429d77a` |

ON adds 940 text bytes in each configuration. Data/BSS remain 4/640. `SetEvd`'s
static frame is 44 bytes baseline/OFF and 752 ON. Current native source task
stacks have a 12 KiB floor (`GetStackSize`), but no whole-call-chain target
high-water or final image/arena budget is claimed. Invalid knob values 2/-1/yes
are rejected. The retained small-object guard is 16 GiB + 128 MiB start and
16 GiB + 64 MiB stop with 4 MiB logs; full-build floors remain unchanged.

```sh
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
source port/dreamcast/kos-env.sh
python3 port/dreamcast/tools/d367/cache21-fixes/qualify_event_admission_txn_sh4.py \
  --out /root/probe/cache21-event-admission-sh4-fresh
```

## Ownership and acceptance boundaries

This transaction assumes the existing serialized source manager call. It adds
no yield, asynchronous admission, reader lease, global lock, teardown policy or
generation identifier. `DatTbl` holds a name, borrowed `Dat`, debug `dat2`, flags
and count; it does not carry a generic backing-generation certificate. Name,
address or child presence cannot certify that old backing remains alive after a
heap release, including same-address reuse. Existing same-name/different-header
reuse is deliberately unchanged; replacement policy needs a separate decision.

The actual inspected contracts are pinned in the host receipt. `GetEvd` exposes
the registered pointer; `DelEvt` destroys the event before `DelEvd`, and
`EvtFree` clears/releases the loaded file through the source data unit. Cabin
carriers separately check their unit, generation, allocation/module, active event
and readers before reverse/free. Those selected-cabin guards do not turn generic
EvdTbl/BinTbl registrations into generation-checked owners.

Global `systemSoftReset` destroys heaps before `systemResetCommon` clears tasks;
room heap retirement/reinit and that broader ordering are unchanged. Likewise,
the source `SetEvt(data)` can register successfully then fail `create(0)` in
`SetEvt(name)` without unregistering; its caller may reach `EvtFree`. The tool's
`GetEvd` also owns cleanup of its newly debug-read buffer after a failed SetEvd.
These caller/generation lifetime policies are separate review items. The patch
does not claim to fix them, recover legacy partial parents, or make a whole EVS
bundle transactional.

Receipts: `event-admission-host.json`, `event-admission-sh4.json`. Raw actual
source, projections, commands, generated headers, logs, objects and earlier
unsuccessful scaffold outputs are retained privately under
`C:/Flycast-Evidence/re4-dreamcast/cache21-fixes-20261021/event-admission`.
No linked-program acceptance, stage, guest, screenshot, hardware, gameplay I/O
or timing improvement, release/issue/SD action is claimed. Root reviews/selects
integration; Claude alone merges production, tags and publishes.
