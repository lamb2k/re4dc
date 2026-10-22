# Pooled object/storage lifetime: bounded repair proposal

Source pin `720b75381a68f51636b17031f82fd762e72e05d3`, main tree read-only.
No runtime/shared source, build, guest or old-window retest. Main owns repair and
integration; this is source analysis, not issue52 fault proof or whole A11 closure.

**Confirmed contract:** allocated slot bytes can outlive a polymorphic object.
Source manager bookkeeping accesses those bytes through T members before placement
construction and after destruction. A retained address and a zero be_flag do not
extend T's object lifetime. Existing strict-event diagnostics already expose the
post-delete case; they were not rerun or suppressed here.

## Exact ownership and source entry paths

| Source | Entry / transition | Evidence and bound |
|---|---|---|
| include/cManager.h16..36 | cUnit owns flags/link/virtual destructor | Destructor clears0x601; sized operator delete is empty. `delete p` destroys the object but intentionally retains pool storage. |
| include/cManager.h287..296 | generic arrayAlloc | Frees old array, allocates `size*n`, byte-clears it; does not construct n objects. pArray/nArray identify storage, not live T objects. |
| include/cManager.h313..318 | dieCheck | Reads typed flags on every backed slot; later `delete p; p->be_flag=0` stores through a dead T. Dying0x200 first arms0x400; a later dieCheck performs destruction. |
| include/cManager.h339 | countActiveWork | Typed flag read also visits never-constructed and reused dead slots. |
| include/cManager.h363..374,401..408,538..557 | create / indexed create / createBack | Typed free-flag test precedes byte clear and placement construction. Only then is the object linked. Indexed overload ignores construct's return; its observed EmMgr call is player id0/slot0, so a failing enemy constructor through that overload is not established. |
| include/cManager.h477..491 | destroy | deleteList / custom alive predicate, then immediate delete+typed zero or deferred flags. The post-destructor zero clears all bits; it cannot simply be removed because cUnit's destructor only clears0x601. |
| parts_bridge.cpp20..43,198..240 | native sparse Pool/Chunk storage | cParts/cModelInfo/cObj/cEm can use slot tables. Header and runs are byte-cleared allocations; pool captures heap index/handle. array_free discards runs and frees header with captured handle; caller owns destruction/order. roomInit can instead forget a pool after source heap retirement. |
| parts_bridge.cpp50..62,254..301 | run liveness / reclaim | `alive` reads `parts()[i].be_flag` before proving object lifetime. cObj/cEm slots are retained until pool teardown; cParts/cModelInfo fully dead runs can be reclaimed. This protects addresses under its source condition, not dynamic T lifetime or heap epoch. |
| game.cpp659..661 → event.cpp2257..2273 | normal Event storage setup | roomInit→arrayAlloc(2)→myRoomInit. myRoomInit builds tables and clears keys; it constructs no Events. Unconstructed slots therefore exist on ordinary source paths. |
| event.cpp280..289,2225..2246,3016 | Event lifetime begins | `create(0)` calls placement `new(p) Event(id)`; Event initializes cUnit(1), later its destructor clears Type and base destructor clears live bits. Only the selected slot is constructed. create's countActiveWork can inspect the other unconstructed slot. |
| event.cpp2291,2310,2370,2808 | direct EventMgr scans | DelAll, Run, IsAliveEvt and the EvtReadExec failure reader census call `isAlive()` on every slot. These need the same storage treatment as the template; fixing only post-delete stores or only template scans is incomplete. StatusFlag/Name/pData reads belong after successful live-object admission. |
| sce_sys.cpp151..171 | ordinary scenario dispatch | ScenarioMove calls EvtMgr.Run when the scenario/event stop gates allow it. This is an ordinary entry to the raw-slot scan, not an injected destructor callback. |
| em.cpp89..211 | cEm constructor protocol | `p->subArc=EmReadSearch(...)` is written before EmInitFunc placement-constructs the enemy; serial/Guid is published afterward. This pre-constructor typed write is another lifetime boundary, separate from Event bookkeeping. Native em12_set.cpp46..55 uses default-initialization to preserve the prewritten bytes. Moving subArc after arbitrary constructors without review is not an equivalent general fix. |
| em.cpp261..288 / cManager.h487..491 | character release | cEmMgr policy2 calls push cleanup, unlinks and marks0x200. It does not immediately destroy cEm10. Slots retain addresses, but a later destructor/reuse can change dynamic type and serial. |
| src/st/em_wrap.cpp57..66 | raw room handle | emWrapLive checks wrapper alive, nonnull pointer and `(be_flag&0x201)==1`. It has no serial or current-pool allocation receipt. A normal stale-handle ABA sequence remains unproved; do not label flag-only checks a generation lease. |

The pool's captured heap handle does not prove it is the same heap allocation
after a reset. Raw byte operations still require currently allocated readable
storage; they must not be used to make arbitrary/stale pointers look safe.
Allocation/read-destination epochs and whole archive-reader drain remain main's
separate open contract, as qualified in e9fcf5e98/92812cb2a.

## Minimum coherent first repair for main review

Recommend a separate native **default0 `EVENT_MANAGER_STORAGE_FLAGS`** proposal,
initially scoped to cManager<Event> and EventMgr. No flag or implementation was
added. This is smaller and more supportable than changing every source manager:
Event has no cEm-style pre-constructor subArc protocol, and its ordinary two-slot
setup proves raw-slot scans are reachable.

1. Add representation-level be_flag load/store/RMW helpers using unsigned-byte
   addresses plus memcpy, with the actual compiler's checked member offset/width
   and alignment. Do not hard-code the old PPC field offset or form a T member
   access merely to compute that offset. ABI/layout, storage addresses and all
   flag masks remain unchanged.
2. Use those helpers for **all** Event manager bookkeeping which can see raw/dead
   storage: free scans, count, deferred-delete tests/marks, immediate/deferred
   post-delete zero, and the relevant deleteList/destroy alive predicate. Both
   create directions and the indexed overload must follow the same policy.
   The four direct EventMgr scans above also require the helper. Access remaining
   Event fields/virtuals only after the live-phase precondition holds.
3. Preserve source sequencing: destructor and member cleanup run first, cUnit
   destructor's bit-clearing stays visible, then the original full-zero bytes are
   written to retained storage. Preserve0x200→0x400→destruction timing and list
   order. Do not manufacture a base object, replace derived dispatch, flatten
   custom type predicates or change indexed-constructor semantics in this unit.
4. Qualify first allocation/one-of-two slots, success, failed Event::init,
   immediate destroyNow, deferred two-step destruction, nested events and same-slot
   recreation with actual source and strict vptr diagnostics. Include destructor
   observed flags and exact final bytes/list order. Require whole disabled
   preprocessing/object identity before any program/target adoption; no sanitizer
   suppression or default/recipe change.

This bounded repair would address Event's **storage-bookkeeping** violation.
It would not establish heap/reset/read admission epochs, active-object pinning
across yielding constructors, whole cEm/cObj lifetime, stale wrapper safety or
issue52's hardware cause. Extending it to other managers requires their own
constructor/destructor protocol review; cSat::isAlive additionally tests m_Flag4
and must not be replaced by a generic flag-only predicate.

## Issue52 narrowing and unproved triggers

Exact path: R10cInit (r10c.cpp122) preloads enemy0x12 before registering the area1
event. For an unchanged loaded module, EmReadSearch (read.cpp758..770) returns
pArc without entering its yielding loader. EmSetFromList2 (em_set.cpp832..885)
creates the enemy, invokes its first virtual move, then returns it. r10c.cpp406
immediately calls setNoSuspend at409 with no source sleep in between. If first
cEm10::move hits its model-init failure, em10.cpp2716..2719 calls EmMgr.destroy;
policy2 only marks deferred deletion. That failure alone therefore does not free
the slot or end cEm10 lifetime before the immediate setNoSuspend. R10c's bad-vptr
candidate cannot be explained by simply calling that source path a use-after-free.
This assumes unchanged module/pool ownership; a hardware memory writer remains
separate evidence work.

Conversely a missing module can yield during readEmData before publishing pArc,
while create has not yet linked a successfully constructed object. The source
does not provide an explicit construction/admission receipt. A second creator,
module replacement or heap retirement in that exact interval is an open
precondition, not a demonstrated normal collision. The r10c preload means that
specific first-vcall path does not itself establish the missing-module interval.

Requested issue52 lane coordination is pending; earlier source constraints are
preserved and no runtime ownership was taken. `audit_manager_storage_contract.py`
pins21 complete source-object hashes and emits28 static checks plus exact
function/line excerpts in manager-storage03-receipt.json. The earlier02 receipt
is preserved and03 adds the normal ScenarioMove entry. It does not compile or
execute C++ or repeat earlier sanitizer fixtures. Run01 found that alternative
PPC/native opening braces cannot be balanced together; final extraction masks
only known PPC alternatives with offsets preserved, and is explicitly not a full
preprocessor. Report/tool/receipt and mirrors stay below2MiB. No physical read,
timing, Flycast, release or hardware acceptance claim. Window restoration stays
disabled; no work was repeated on that finished negative result.
