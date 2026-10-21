# Retirement wrappers: reachability and diagnostic boundaries

Read-only review after `0b45c82527360bf48c8ea5159e1184dcdd2ec9c4`.
`retirement-wrappers-host.json` records24 source controls, complete source
identities, extracted methods/types, generated adapters and service boundaries.
No runtime edit, knob or production recipe change.

The current `platform/mem.cpp` implementation of `re4dc_missing` logs and sleeps
forever. A native guard condition can be reachable while the caller statements
after the diagnostic are not reachable on this target. The strict controls use
a host exception solely to observe that stop boundary. The separate returning
diagnostic controls characterize latent source fallthrough; they are not proof
of target continuation, a recovered gameplay failure or heap destruction.

## Real carrier admission and local preservation

The fixture extracts the complete ReadModule definition and actual
SearchEmModule, then binds forward loading and retirement to the same real
EmReadModule array slot with id0x13. Actual source ARAM load, MemorySwap and
native owner/DMA protocol admit the carrier; actual source_module returns that
exact slot. The provider, allocator, software ARQ and host layout remain explicit
boundaries inherited from the forward fixture.

| Source operation | Executed result |
| --- | --- |
| InitModule for the role1 borrowed enemy0x13 | Real before_free refuses before motion/REL/effect/UI/free/slot-clear; exact module retained |
| carriers_reset and actual DC.initDataUnit while role1 | Real reset preflight refuses; exact unit/carrier and controller reset fields retained |
| EmReadInit over other disjoint modules plus borrowed0x13 | Earlier disjoint module can retire before the0x13 diagnostic stops the loop; returning diagnostic also permits later disjoint retirement |
| Actual complete reverse, then retry | Role2 releases module exclusion; InitModule and real carrier clear/reset succeed; actual DC.initDataUnit clears all32 descriptors |
| Native failed phase2/readers1 after partial second DMA | InitModule/reset refuse, retaining module/carrier/request and the only displaced module bytes |

No local enemy13 slot ownership loss is established by these controls. Partial
outer teardown before a later fatal refusal is possible; no atomic reset
contract is inferred from local preservation.

## Player and weapon wrappers are reachability-negative controls

The forward module query specifically admits loaded enemy0x13. With distinct
valid player/weapon archive pointers, the actual query does not attribute them
to that carrier, before_free accepts them and ReleasePlData/ReleaseWepData
retire normally. Native carriers can also own separately allocated source-unit
MRAM or backing; that does not establish legitimate aliasing with a live
player/weapon archive.

Deliberately copying enemy13's pArc into PL/Wep slots reproduces the apparent
post-void-InitModule metadata changes under a returning diagnostic, but that
duplicates ownership of the same allocation. The native source-module identity
still names enemy13, not the PL/Wep slot. No ordinary allocation/read producer
establishing that alias was found. These are synthetic controls and are not
confirmed player/weapon defects. A strict fatal diagnostic would stop before
their post-call changes as well.

## Heap and reset caller propagation

Actual MemDestroyHeap, MemReplaceHeap and MemClearAllHeap source guards use the
real carrier before_heap/retire_heap predicates. With the borrowed role1 archive
inside the controlled heap range, refusal occurs before OS destroy/create. A
successful reverse/retirement permits the positive heap retry. No outer OS heap
destruction after carrier refusal was observed in these source controls.

Actual gameRoomMemInit executes its native retirement service calls before
MemReplaceHeap. With a strict diagnostic stop, it does not select the heap,
publish room enter or clear global room/status fields after the refusal.
Under the returning diagnostic boundary it ignores replacement0, selects the
heap, calls room enter and clears those fields despite the retained carrier.
That is a latent source error-propagation gap if the diagnostic is ever made
recoverable, not current target fallthrough. Native retirement services here
are controlled calls; their full implementations and earlier weapon/overlay
actions remain main's holistic audit.

Actual systemSoftReset calls media/sound/debug reset services before
MemClearAllHeap. Strict refusal stops before systemResetCommon, reset-keep valid
publication and message reset; no OS heap is destroyed. Returning diagnostics
permit those later common-reset statements despite retained enemy13. The
common wrapper's real EmReadInit/PL/Wep calls execute, while tasks, room REL,
UI/media/sound/debug/OS services use declared boundaries. Earlier subsystem
mutations before the refusal require a whole-operation preflight, which this
unit does not implement.

An optional controlled DLL_Unlink callback admits a global reader after the
module's initial guard. Later real carrier reset refuses. No production REL
epilog admitting that reader was proved; this is a callback contract control,
not an asserted gameplay interleaving or generic snapshot-restoration proposal.

## Source caller map

| Wrapper | Callers reviewed | Consequence / scope |
| --- | --- | --- |
| EmReadInit | systemResetCommon; game door transition; r106/r200 event handlers | Void interface; no accepted set-wide retirement result. r106/r200 first destroy enemies and sleep; live carrier occurrence on those routes is not certified |
| ReleasePlData | systemResetCommon; ReadPlayerData before fixed player destination and REL setup | Post-call null/UI operations reviewed; no real CABIN alias producer established |
| ReleaseWepData | systemResetCommon; weapon load/release/player/Ashley paths; room/movie heap4 helpers | Weapon/UI/heap4 mutation after void call reviewed; real CABIN refusal not established for distinct ownership |
| DC.initDataUnit | door transition before DVD/ARAM cancellation and EmReadInit; room setup | Real reset refusal preserves local unit state; callers have no success result. Source service order is not whole-epoch closure |
| cDvd::Init | boot/reinitialization | Same native reset preflight precedes queue memset; full boot function is reviewed, not executed here |
| gameRoomMemInit | gameRoomInit; gameEnding | Callers proceed without a success result if diagnostics return; full callers not executed here |
| MemClearAllHeap | systemSoftReset before systemResetCommon | Strict native refusal halts; returning-diagnostic common reset control is explicit |

## Evidence and limits

Raw source, generated adapters, binaries and output:
`C:/Flycast-Evidence/re4-dreamcast/cache21-callers-20261021/cache21-callers-retirement-wrappers-20261022-09`.
Earlier scaffold/compile/diagnostic controls01..08 are preserved. The final
unit stays below20MiB and enforces a fresh18GiB plus128MiB compiler floor.
The preparation export also runs the original forward120 OFF controls once;
the modified full-ReadModule adapter's inherited old forward matrix is only
compile closure, not rerun under the substituted module lookup.

RESET_HEAP_FIX's actual ModuleMemFree body executes on successful wrapper frees.
Heap descriptors/OS lists and allocation identities remain controlled services;
this is not a real allocator or linked-program test. Synthetic ARAM_FREE_BASE
and controlled unit allocator-reset helpers are sufficient for the exercised
reset path; shooting-range fixed-address swap branches are unexecuted.

All runtime files and shared-file claims remain unchanged/read-only. No Count
is treated as a lease, no generic saved-state restoration is introduced and no
new runtime repair is proposed here. Main owns reset/admission architecture and
implementation; Claude retains production merge/release. No full build, stage,
Flycast, release, physical Dreamcast or performance acceptance is claimed.
