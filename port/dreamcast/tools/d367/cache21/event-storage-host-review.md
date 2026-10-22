# Independent Event storage lifetime validation

Reviewed source: `f3149dfc7a8e9bbf317eae6d192d9665b9568ce5`, parent
`720b75381a68f51636b17031f82fd762e72e05d3`. Main's runtime files stayed read-only;
all worker runtime claims remain released. The bounded Event storage repair
passes the independent strict host qualification: **23 groups /108 assertions**
with the guard enabled; **10 isolated OFF controls fail** on expected vptr/type
lifetime diagnostics. No sanitizer suppression was used.

The fixture uses the complete actual cManager header and complete actual
DatTbl/Event/EventMgr declarations. Source methods executed include Event
constructor/destructor/init, EventMgr constructor/destructor/construct/SetEvt,
destroyNow, DelAll, Run and IsAliveEvt, plus the exact EvtReadExec reader loop.
All generic Event manager methods those paths invoke come from the actual header.
Hashes/lines of every extracted fragment and complete source-object hashes are
in event-storage-independent04-receipt.json.

Host ABI differences are explicit: fixed-width u32, standard host placement new,
and the actual header's otherwise-empty sized delete argument changes only from
unsigned int to std::size_t for the64-bit host. The unadapted header is saved.
Source32-bit addresses are mapped at0x8c000000. The actual Event declaration has
the host compiler's pointer layout; it is not presented as the SH4 layout.
DatTbl allocation/end, frame-validation services, logging and Event run/end
services are boundary stubs. Failed init exercises the unchanged actual init and
SetEvt cleanup bodies under EVD_START_CLEANUP1; it is not a packet-decoder test.
The fourth direct scan is its unchanged actual loop in an explicit host wrapper,
not execution of the whole EvtReadExec transport. CABIN is0 in this fixture.

## Executed controls

- Two byte-cleared raw slots; free/count/dead scans before construction, after
  destruction and after reuse. Additional raw-storage canaries verify that
  helper load/store/RMW touch exactly the four flag bytes, even with invalid
  bytes in the unconstructed vptr storage. These synthetic canaries are a byte
  width control, not a claimed normal gameplay state.
- Front, indexed and back creation; full/out-of-range refusal; exact active-list
  order and same-address recreation. Indexed construct-return behavior remains
  the original source behavior; no failing constructor was injected into it.
- Immediate destroyNow, manager policy restoration, deferred0x200 marking,
  later0x400 arming, destruction only on the next dieCheck, and no second
  destructor on later scans.
- Destructor-member cleanup sees the original high flag bits and source Type0
  before cUnit clears0x601. A separate actual destructor call verifies exactly
  that masked residual; manager deletion verifies the subsequent full32-bit flag
  zero. This does not mean the whole Event is cleared after destruction.
- Actual failed table-init and failed total-frame validation cleanup, preserving
  a byte-identical pre-existing Event/list; successful nested event creation,
  parked-name lookup and same-slot reuse.
- Live and raw/dead EventMgr Run, live/empty DelAll, IsAliveEvt, and positive /
  negative / dead-slot read-owner census. These cover all four changed direct
  scans; run/end service stubs are stated above.
- The actual cSat::isAlive body over a projected cSat field declaration preserves
  its extra m_Flag4 condition through the generic policy. No non-Event deletion
  path is executed or claimed repaired. The generic destroyAll predicate and
  flag1 branch are source-reviewed rather than separate runtime groups here.

OFF cases are raw-count, front create, indexed create, back create, immediate
delete, deferred delete, dead-count, direct DelAll, direct IsAliveEvt and the
reader census. Each runs in a separate process with strict undefined/vptr
sanitization and no recovery. The first diagnostic terminates that control; it
is not an execution of subsequent hypothetical fallthrough. For example OFF's
immediate delete reports the actual header's post-destructor member access;
raw-count reports the actual raw-slot flag read. These are source/host diagnostics,
not Dreamcast crash measurements or issue52 causation.

## Independent review and preconditions

No defect found in this bounded implementation. Event's byte helpers compute the
offset from the compiler's cUnit layout, enforce four-byte u32 and independently
check the actual Event offset/width in event.cpp. They do not form a typed Event
member access to load dead/raw flags. The specialization is only Event; generic
other-manager alive predicates remain typed/custom. Destructor, list, reserved
flags, full-zero and deferred ordering are preserved. The omitted/zero macros
retain the original source expressions.

Main separately qualified the actual full Event/game SH4 TUs at this same pin:
baseline/omitted/explicit0 token/object identity, enabled Event text+560B with
data/BSS0, enabled game object unchanged, and consistent GAME/PLATFORM defines.
The accepted target receipts are event-storage-event-sh4.json and
event-storage-game-sh4.json in the main candidate. This worker reviewed those
source checks and did not repeat target compilation or promote their object
delta to whole-programme cost.

The live-phase precondition remains material: storage must still be allocated
and be the intended pool slot. An alive-bit byte test is not an allocation epoch,
constructor-completion receipt or active-reader lease. A constructor sets base
flags before it returns; a member destructor intentionally observes the old
flags before base destruction clears them. A reentrant manager dispatch during
those phases could therefore pass the byte predicate. No normal such callback
path is established by these fixtures; no arbitrary callback is called a target
defect. The repair fixes Event's out-of-lifetime bookkeeping accesses, not those
broader ownership obligations, heap reset, stale handles/ABA, cEm preconstruction
protocol or the hardware issue52 candidate.

## Evidence and resource bounds

`test_event_storage_lifetime.py` and event_storage_lifetime_host.cpp reproduce the
qualification from the pinned Git objects. Compiler flags include
`-fsanitize=undefined,vptr -fno-sanitize-recover=all`; no `-fno-sanitize=vptr`,
no-sanitize attributes or diagnostic bypasses. `-fpermissive` permits the declared
32-bit source pointer ABI casts on the64-bit host; it does not disable vptr.

Attempt01 retained a host-link failure from a missing logging stub. Attempt02
passed19/93;03 added canaries and passed21/102;04 adds live Run/DelAll and is the
final23/108 receipt. All attempts and negative diagnostics are preserved.
Combined outputs933,216B including the final disposition; projected mirrors plus
80,000B tools/report reserve are1,946,432B, below the2MiB unit cap and inside main's shared source-peer allocation.
No further compile is needed for this unit. Raw outputs are mirrored in
cache21-callers-20261021/event-storage-independent01..04. No runtime/shared edit,
full programme, stage, guest, release, SD or physical hardware action. The negative
window candidate remains disabled and was not retested.
