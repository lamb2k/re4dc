# Root decision proposal — UNKNOWN only, no source-positive state

This file is a proposal. Nothing here is implemented or allocated.

1. Keep existing SourceUse, ReplayUse, ActorSourceScope geometry selection,
   member_accept and payload_accept unchanged. Geometry and Weapon masks stay
   exact. Do not add Motion to member/payload masks or call emitted_checked(Motion)
   from the emitter. Do not modify the required/wired coverage masks.
2. Introduce a separate small by-value **classification receipt**, with no source
   pointers/digests/catalog handles: a 32-bit reason mask. `0` means missing route,
   which fails to Unknown, never N/A. Nonzero bits name fixed unknown cohorts such
   as ModelPose, ViewTrack, DelayedModel, UnclassifiedWorld, Impostor, DerivedRoot,
   MissingRoute and StaleContext. No positive or N/A value is supported in the
   first shared API. It does not claim which asset was used or that current pose
   is bound. A fixed Unknown constant is already a frozen classification; it is
   unaffected by source/pose generations or a current pointer's reuse.
3. Suggested API shape: `motion_accept_unknown(frozen_reason_bits, accepted_units)`.
   Zero units do nothing. A valid call only latches a bounded reason OR and a
   saturating accepted-event/unit count in renderer-owned memory. Missing/invalid
   receipt records Unknown/MissingRoute, never silently returns. Keep overflow
   sticky. No lookup, scan, FS, hash, allocation, log, lock, wait or callback.
   Accepted units are vertex records (or explicitly named logical direct slots),
   not unique triangles/assets/evaluations. Counts across layered leaf/chunk hooks
   must be exclusive, not added twice. Exact diagnostic names must say UNKNOWN.
4. Snapshot the classification in a standalone pending Motion word when preparing
   a packet/direct interval. Do not reuse Geometry's source model-match rules or
   copy its token to manufacture a Motion receipt. Source/model dispatch and
   actor OneWindow supply fixed Unknown even with no selected Geometry proof.
   RAII saves/restores the standalone classification for nesting. Restore does
   not erase previously latched output. A material switch accounts previous
   vertices before changing the pending word.
5. Every actor Frame/SkinEntry/owned/hand/cache hit is Unknown unconditionally.
   Therefore **no added fields in SkinEntry, Frame, owner pool or pose arrays are
   necessary** at this stage. Pending model merge and generic deferred model-node
   branches can use a fixed DelayedModelUnknown classification, independent of
   ambient source. Impostor batch uses fixed ImpostorUnknown for only the quads
   packed. No per-node/per-quad identity or source-positive pose metadata is
   needed while all these branches refuse N/A and positives. The tag must remain
   fixed Unknown through cache/replay; future exemptions require a new reviewed
   transport design and cannot simply inspect the replay-time current model.
6. OneWindow direct chunks latch only each chunk's nonzero new slots. Mark the
   window as chunk-accounted (or select one explicit accounted end API) so its
   total direct_end does not double-count. A simple fixed Unknown bit OR could be
   idempotent, but numeric counts still need this ownership. Ordinary direct_end,
   PS2 batched account, Leon header switch, packet prefix/final commits and quad
   batches must have one accepted owner each. Do not change rendering arithmetic.
7. Flush the small renderer-owned latch at existing **unlocked** gcasset_flush /
   frame/visit boundaries. Drain before old visit END and before scope reset, then
   label any accepted unknown as an unresolved Motion failure. Coalesced output
   is acceptable; event counts must be retained and overflow explicit. Existing
   unresolved() logs, so call it only here. Do not claim checked/wired Motion or
   change `motion=0` into a zero-use assertion. Separate detector statistics are
   needed because current emitted_checked deliberately refuses Motion before its
   emissions counter. No current counter is repurposed into a success signal.
8. Renderer output is main-thread state: do not pretend a non-atomic shared
   latch is safe from workers. Prove each supported accepted hook's ownership;
   asynchronous/custom-thread alternatives must refuse support until separately
   bounded. G2 audio is not a Motion accepted-output producer. No existing audio
   ticket/Geometry token provides Motion ownership. Queues erased/cancelled before
   output produce no use; queues whose prefix already emitted retain Unknown.

## Budget and scope boundary

The proposed classification is four bytes, standalone pending four bytes; a
minimal reason/events/units/overflow latch is four 32-bit words (16B). A selected
OneWindow accounted flag may add up to four bytes to its stack struct. RAII saves
one word on the stack. These are **design costs, not approved/actual allocation**;
final declarations/object/map will need exact pricing. There are zero proposed
per-pose/cache/owner fields, zero new heap allocation, no source slots/digests and
no added per-deferred-node/per-impostor-quad storage in the all-Unknown variant.
Do not add source-positive state under this proposal.

This receipt intentionally cannot diagnose which old Motion/owner/pose generation
was used. StaleContext can be set only when existing lifetime machinery proves
staleness; otherwise classification remains Unknown, not current or clean.
If root requires per-output source visit/pose identity rather than unconditional
Unknown, that is a different design requiring separately budgeted frozen fields
and invalidation, not a pointer-only shortcut or current-pose recapture.

No model/world N/A exemption is proposed. Fixed-screen Movie example stays under
its existing local output route and does not inherit an ambient Motion context.
Unclassified raw/UI/effect routes are not automatically model Motion consumers:
first audit their actual consumed inputs, cover derived root/view paths, and leave
overall coverage incomplete for every unresolved alternate. The camera component
must be explicit as parent confirmed; no implicit all-geometry-to-Motion rule.

## Implementation admission and required controls

Root can authorize a small default-off UNKNOWN detector after choosing the route
and counter ownership contract above. Before any Motion coverage bit is considered,
require actual extracted accepted-path tests, not only a model of this API:

| Required adversary/control | Expected result |
|---|---|
| pMot null, stopped Motion, no eval this frame, previous-frame pose, procedural/IK/blend/shape/root history | All actual model accepted prefixes remain Unknown; no exemption. |
| Same geometry token/package/hand slot/PL08 registry, current owner, materialization and skin/frame hits | Unknown unaffected; no source-positive acquisition/catalog IO. |
| OneWindow chunk A emits; B emits; C culls; D partially emits then aborts | A+B+D prefixes counted once; C/header-only zero; close never reattributes or doubles slots. |
| Ordinary direct vs world-batched SQ account, Leon switch, header cache hit, native generic prefix+final, non-fast actor | Exact accepted ownership at real boundaries, previous interval classified before switch; no log/scan under SQ. |
| Deferred A saved; ambient B replaces it; replay A; nested replay; cancelled/dropped/room-retired queue | Actual A output fixed Unknown; no ambient recapture, nested scope restored; cancelled zero, prior accepted prefix retained. |
| Model merge cached concat vs unmerged fallback; prepared retained arrays; atlas/backface/LOD split | Same Unknown classification at actual accepted prefixes, not preparation/enqueue/cull. |
| Native impostor quad batch plus payload_quads_accept early return; multiple source owners, capacity drop, begin failure | Packed quad records counted only once; Motion hook not bypassed by Geometry early return; missing Geometry proof still Unknown. |
| Baked world with dynamic/root mode, no-dynamic owner bypass, source hierarchy fallback, ordinary vs chunked picks | No whole-output N/A; retained view/camera Unknown separate from object-pose branch; no last-pending receipt inheritance. |
| External camera stopped/null after influence, extra-camera swap, camera blend/quake/debug override, no update | No no-history claim from current pointer; scope/exemption needs actual complete overwrite proof. Pure code math is not an asset assertion. |
| Optional MV/blob/lake/raw TR or fast actor disabled | Either real accepted route Unknown hooks or explicit unsupported admission; no claimed full coverage. |
| Fixed-screen movie quad vs model submit while Movie UI is active | Local fixed-screen route does not globally suppress Motion; subsequent model still Unknown. |
| Missing/invalid reason, nested scope, UINT_MAX counts/overflow, visit close with pending latch, source/catalog retire | Unknown/error preserved; saturation sticky; flush old scope before reset; no positive Motion token ever emitted. |
| Forbidden-operation tripwires around SQ/G2/LH; FS/hash/logger/allocator mocks that fail on call | Acceptance only memory-latches. Flush invoked after unlocking; no source scans in accepted path. |
| Default-off full preprocessing/object identity and strict supported Make alternatives | No default-off ABI/BSS/code change; unsupported alternatives fail closed. Runtime/source/object/hardware claims stay separate. |

The current readback controls merely verify eight source facts and detect eight
counterfactual source edits. They do not execute the proposed detector, any renderer
or SDK code, and cannot satisfy the implementation controls above.
