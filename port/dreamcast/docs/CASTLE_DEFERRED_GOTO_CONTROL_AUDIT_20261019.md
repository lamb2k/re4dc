# Held destination commands: current control and consumer audit, 2026-10-19

The original r207 source sends D3/D4/D5 and immediately gives them walking
orders. A held wrapper currently drops setGoto, and ckGoto reports zero.
The retained original-route observation binds released D4 to mode zero and a
zero secondary target. A setter-only repair would preserve a destination,
but would still let route scripts advance before that movement happens.
No Goto runtime change is implemented by this checkpoint.

## Frozen current controls

Both controls are built from clean, pushed 2c0e3dc0474165164af5ce90e5b4f977a294d692,
which contains upstream f2555097, the qualified deferred-flag fix, and the
current chapter recipe. SOURCE_DATE_EPOCH is 1760000000; builds ran serially
at -j4. These replace the historical 7adb/AP0 controls for new work.

| Control | ELF SHA256 | Raw program SHA256 | End | Actor plan / deferred flags |
|---|---|---|---|---|
| Literal T15 c32gtbrP | 4e6aab0eb46077dcbd3d1958b5588d227b7eb390191a04aa59443fa0a7a6f5ac | 2d02cc44e3056769c89ac309193df1e9f64456a333c3a4c7506d5bd2e2aa4376 | 8c4061d8 | 0 / 0 |
| Chapter c32gtbmW | 6f081a5699c793d49adb435227b8bdef6aec37ff1a1222cea34e513ea39d22da | 0b16b889c1cd7d2fa4b71952cea0319397c6186da2fe08952ded6eabb79e29d2 | 8c4710d8 | 1 / 1 |

Both use FOLIAGE_TRIM=2 and VIEW_DIST_BOOT=1. ENEMY_VIS_CULL is absent from
this frozen source. An attempted explicit zero was rejected before compilation;
the retained retry omits the nonexistent knob and emits no cull definition.
The actual compiler census contains em_set plus four T15 or eight chapter
wrapper objects (st1_0..3 and st2_0..3). No stage3/stage4 wrapper is in the
chapter control. v2/v3 wrappers must still be checked by preprocessing if
the shared implementation changes. No candidate identity or runtime pass is
claimed yet.

Evidence root: C:/Flycast-Evidence/re4-dreamcast/castle18-20261018/workers/ch32/deferred-goto.
Read build-proof.json, baseline-inputs.json, baseline-compiler-proof.json,
programs-route.json, and builds/<label>. The rejected precompile attempt is
retained under invalid-c32gtbmW-before-compile.

## Approved queue storage and original setter ordering

Proposed default-off ALIVE_CAP_DEFER_GOTO requires ALIVE_CAP_DEFER_FLAGS.
Each of 64 queue slots gets a 24-byte record: copied Vec, int mode, validity,
and flags present before its first Goto. This costs 1,536 bytes when enabled,
without changing the 12-byte wrapper ABI. Latest target/mode wins; mode zero
is valid. Shared handles refer to the same queue entry. All compaction,
destroy, failed allocation, four successful creation paths, and room reset
must preserve or discard this metadata exactly with the existing held entry.

Delivery must follow original first AI initialization, preserve its flags,
OR the first-Goto flag snapshot, call the original typed setter once with the
latest target/mode, then OR the final pending flags. It must not preapply the
final OR mask. cEm10::setGoto (em10.cpp:24277) reads actor flag 0x40 and can
permanently clear work bit 0x100. Goto, then OR40, then Goto must retain that
earlier clear. It also honors protected work bit 0x4000 and performs the
original floor lookup. Source-extracted tests must cover these operations,
base flag40 already set, missing floor, mode zero, and every retry/lifetime
path. Capture and delivery eligibility must match isNormalGanade exactly:
ids 0x10..0x20 except 0x18. Novistadors must never receive a Ganado virtual call.

## Pending getter and cutscene audit: review remains open

The source census retains 47 occurrences across shared wrappers and all
stages in goto-consumer-census.json, each with its source hash and owner.
A pending getter must expose the actual queued mode without spawning an actor.
Changing generic isActive or fabricating getPos is excluded.

| Current linked consumer | Source behavior and requirement |
|---|---|
| Shared cEmPatrol, cEmRouteRun, cEmRouteExec, cEmGuard | No held guard protects their movement waits. Current held ckFindPL=0/isActive=1 allows route advancement. A pending mode must prevent false arrival. Live paths remain exact. Other dropped mutators are outside this command fix and require separate evidence. |
| r104 patrol, r106 post | Ordinary patrol/area tasks; no local event owns the wait. Pending mode can wait for ordinary admission. |
| r201 reset wave | Normal task/area action; repeated point waits occur outside its own event. |
| r202/r203 patrol and wandering | Ordinary recurring tasks. r203 escape already waits for actual ckFindPL before its movement wait. The key event sends targets immediately. |
| r207 ToPos / CkDist | CkDist accepts held isActive and gets zero position. Proposed explicit held exclusion before this position query prevents choosing a nonexistent actor; no invented position. ToPos then waits on the pending mode. |
| r207 EnemySet | Starts an event before sending D3, then waits on D3 mode8. Returning pending8 would deadlock because admission is disabled while busy. Proposed existing aliveCapFull preflight after the final source sleep, immediately before Rsf11/SceEventStart. The first original D3 send then has a free slot; all sends remain inside the original event. No over-cap admission or busy bypass. Requires room claim and review. |
| r208 movement waves | Movement loop follows the original event end; pending modes prevent early next-target commands. |
| r209 leader / bowgun paths | Leader has original getPtr-backed attachment; its unbounded wait after the pointing scene explicitly follows SceEventEnd. Bowgun paths are ordinary tasks. |
| r206 leader | Original head attachment calls getPtr before the event and its movement wait. This existing pointer exception is not introduced by the new fix. |
| r214 catapult | E0 may remain held; posing uses setPos/setAng without getPtr, then an event waits indefinitely. A source preflight is required. Its early Rsf3 write makes death/Continue while waiting an explicit review concern. Independent source review is in progress; no room edit is authorized yet. |
| r223 patrol | Ordinary recurring task. |
| r226 statue entrance | Event movement wait is bounded to 90 ticks, so it cannot indefinitely block admission; scene correctness still needs its own gate. |

Island and bonus-mode consumers remain in the census, but their wrappers are
not linked in this chapter control. This does not certify enabling the new
knob for those recipes. No chapter recipe will enable it until the complete
current consumer contract, off identity, and matched release/movement gate
pass. A delayed command under cap4 is not proof of identical uncapped timing.

## Ordering proof and r214 follow-up

`test_original_goto_order.py` extracts the original cEm10 setter unchanged
and checks 8,192 sequences under ASan/UBSan. All first-Goto reductions agree;
using the last-Goto flag snapshot instead produces 160 counterexamples.
This validates the proposed ordering reduction, not an unwritten queue.
Run `python3 port/dreamcast/tools/d367/castle18/test_original_goto_order.py`.

The r214 review confirms that EndControl does not destroy EC/ED. The source
catapult scene creates E0 plus E9/EA/EB while original E4/EC/ED/EE/EF may
remain alive. A wait-only preflight therefore cannot guarantee four slots.
Held getHp also returns zero and can incorrectly select the both-dead branch.
Treat this as an explicit source capacity/ownership requirement; do not
force admission, fabricate health/positions, or add a pending getter that
can deadlock the original event. Main/parent are reviewing the complete
contract before runtime edits. No new room file is claimed at this checkpoint.

## Reviewed r207-only implementation checkpoint

The integration and parent reviews deliberately reduced scope to
`ALIVE_CAP_DEFER_GOTO_R207=0` by default. The only runtime/build files are
`src/game/em_set.cpp`, `src/st/em_wrap.cpp`, `src/st2/r207.cpp` and the game
Makefile. The switch requires the existing alive cap and DEFER_FLAGS=1.
Capture, pending-mode reads and delivery each require exact room207 and a
normal Ganado ID (10..20 except18); Novistadors are never cast as Ganados.
Other rooms keep their previous movement behavior. In particular, r214 is
an unresolved capacity/ownership exception and has no edits.

The enabled queue uses 64 records of 24 bytes (1,536 bytes), retaining the
original 12-byte wrapper ABI. Each record owns a copied Vec, latest mode,
separate validity and the first Goto's pending-OR snapshot. Mode0 is valid.
All original slot creation, compaction, Take, automatic release, retries,
drop and room-reset paths carry or discard the matching metadata. Failed
creation retains order and commands. Delivery follows successful original
first AI initialization: first snapshot OR, original typed virtual setter,
then final OR mask. It never writes work offsets directly or admits an
actor merely to deliver a command. The actual original setter still owns
floor adjustment, protected-work refusal and motion flags.

R207's distance selector skips held handles before reading position, while
source alive/wave counts remain unchanged. Its leader event waits for one
free slot in ordinary gameplay, immediately before RoomSeCall2/Rsf11/event
start. There is no new yield between that check and original D3 send. D4/D5
still follow normal admission and may remain held. No busy override, cap
exception, fabricated position, forced kill or new recovery shortcut exists.

`test_deferred_goto_r207.py` extracts the actual queue, four creators,
wrapper members and original cEm10 setter. Both feature states pass under
ASan/UBSan:128 creation/order/floor/protected-work cases per state, shared
handles, copied target lifetime, valid0, repeated commands, null and nonnull
failed creation, full64 middle retry, every compaction/drop/reset path,
already-live exact setter, and other-room/ID invariance. The unchanged flag
suite still passes both states. The separate exhaustive original-setter
suite passes8,192 sequences and retains160 wrong-last-snapshot negatives.

`test_r207_goto_event_guards.py` compiles the actual distance/event functions
against bounded scheduler/cap stand-ins: held positions are not read; a
full cap waits before flags/busy/sends; D3 receives the first free slot;
D4/D5 remain queued; missing leader keeps original behavior; interruption
before busy leaves no new persistent state. Nine actual Makefile cases
cover default/off/on, invalid values, prerequisites and room/wrapper object
definitions. These are host checks, not guest progression or Continue proof.

The15 actual compiler commands from the frozen current T15/CH4 controls
produce identical C++ preprocessing tokens for baseline/default/explicit0.
Fourteen are byte-identical too; the CH4 em_set output differs only in line
whitespace around the conditional parameter/calls. That difference is
recorded, not described as byte identity. Compiled boot/overlay/allocated
ELF identity and a fresh current AP1 r207 full-cap/event/death/Continue gate
remain required before this switch can be enabled in a chapter recipe.
Private receipts: `deferred-goto/r207-source-tests.json` and
`deferred-goto/r207-off-preprocessing.json`. No candidate game build or
runtime acceptance is claimed at this checkpoint.

## Frozen candidate compiled identity

Reviewed source `8bab3d5b9` was built cleanly in one serial `-j4` slot,
with the existing source date epoch and exact frozen `2c0e3dc0` controls.
All three builds have no missing symbols. The disabled T15 arm matches
all 11 boot/overlay payloads and the raw program byte for byte. The disabled
CH4 arm matches all 23 payloads and the raw program byte for byte.
All allocated ELF sections, their addresses, sizes, alignment and content,
and every generated header are exact in both comparisons. Whole ELFs differ
in nonallocated debug sections only; this is not whole-ELF identity.

| Arm | ELF SHA-256 | Raw SHA-256 | End |
| --- | --- | --- | --- |
| T15 disabled | 0d35819e3eeaa385560df080567aba1fe44545fdefbbc4f11ef17a27c41cf825 | 2d02cc44e3056769c89ac309193df1e9f64456a333c3a4c7506d5bd2e2aa4376 | 8c4061d8 |
| CH4 disabled | acad2ab2b128db0356970f77e32224fa36b10666e984339b611a5fc0d5ec9059 | 0b16b889c1cd7d2fa4b71952cea0319397c6186da2fe08952ded6eabb79e29d2 | 8c4710d8 |
| CH4 enabled | 21f3ca1551db719fa1f36853431697057b9e267937ac73d0d5f009afd0f41b46 | 65c8ea449317bfe5192513a9bb01f9f4069d8f3984ebd2e2b0d960e479428051 | 8c471ad8 |

The enabled image adds 2,560 bytes overall. Its held-command buffer is exactly
1,536 bytes. Actual compiler commands verify the enabled definition in all
eight linked stage wrappers, `em_set` and `r207`; controls omit it. The only
scalar resolved setting difference between the CH4 arms is
`ALIVE_CAP_DEFER_GOTO_R207=0/1`. Build-path substitutions and derived Make
variables are retained separately rather than mistaken for knob changes.
The first proof-script attempt rejected build-directory differences in those
derived variables; normalizing only the two exact output roots resolved that
harness assertion without any game source or binary change.

Private proof is `workers/ch32/deferred-goto/build-proof.json` and
`r207-build-details.json`, beside the sealed ELFs, logs, symbols, programs,
headers and resolved settings. The full source/test receipts remain adjacent.
These are isolated f255-era patch/control results. New upstream a737/a808
inventory and weapon changes arrived during the frozen builds and are not
claimed by this comparison. Integrated current programs, exact staged payload
checks and actual r207 full-cap/event/death/Continue validation remain pending.
The chapter recipe keeps the new Goto switch disabled until that gate passes.

## Current upstream integrated candidate

The current main `25d66518` control incorporates upstream a808, including
ACTOR_PLAN, quick weapon/manual changes and TEX_PKG_SKIP_LISTED. Worker
`c2dfc30f1` has identical runtime/build source, differing only in this document.
Main's fresh literal-current Disc1 off identity proof is preserved as
`I014-current/current-off-identity-and-chapter-build-proof.json`, SHA256
`1e1ac03444eb587975ccbf245a6750188b1d19ef6f694bfcb528ee792674b5e5`.
Its CH4 Goto-disabled arm is reused; no duplicate control was built.

The matching enabled arm `c32giumW` completed in one serial `-j4` slot with no
missing symbols. ELF `e445ed8db922490cfb14253cc8990302b71c675069a63a1dd287bd4409f2923a`,
raw `f1e6053b8a48c471210a5fe9fc24d660459c95c76f032b9e7f59b864672758c6`,
end `8c472278`. The reused control ELF is
`23a6d5b59b99cc4a2554312e2639b69f09042aa8dc1bf87288381426541d2245`,
end `8c471878`. The increase remains 2,560 bytes; the actual linked command
buffer is 1,536 bytes.

All 45 generated headers, including the three nested model headers, match
exactly. Actual commands for em_set, eight stage wrappers and r207 verify the
new definition only in the enabled arm, with deferred flags present in both.
The only scalar setting difference is the new Goto switch. Output/check-out
path differences are normalized explicitly and derived settings are retained.
`workers/ch32/deferred-goto/current-integrated-build-proof.json` holds the full
receipt. Its first sealing attempt assumed an absent `obj/generated` layout;
the final inventory uses the actual 42 root and three nested headers. No game
source or binary was altered to repair that evidence script.

The earlier frozen inventory was also supplemented with those three nested
headers: `frozen-all45-header-proof.json` confirms all 45 match for both off
pairs and the CH4 enabled arm. This closes the inventory gap without another
build. Runtime command delivery, full-cap event, death and Continue acceptance
remain pending; the recipe still leaves Goto disabled.


## Fresh current off-arm original release proof, 2026-10-19

The current a808-integrated Goto-off program `23a6d5b59b99cc4a2554312e2639b69f09042aa8dc1bf87288381426541d2245` now reproduces the lost movement command after ordinary gameplay. Seven bounded captures retain the same disc `21aa5e8b32822f51cfd2db2acfbb520c3fb4eb16899e7c7137b21012007f26d0`, all selected payloads and exact saved-state lineage. This is a disclosed fresh room-entry diagnostic with the Ashley-init precondition and source chapter0; it is not the original no-warp chapter6 save path.

The full original radio and upper-floor enemy event run unskipped. Normal Wait and the original stairs place Leon upstairs; the event admits D3 and queues D4/D5 behind four live enemies. Ordinary handgun fire and a normal reload kill original DA, confirmed by HP0, the source death bit and chapter kill counter0→1. D4 releases at frame4301, leaving only D5 held. Seven actual read-only samples through frame4330 show D4 `Goto_mode=0`, `Goto_pos=(0,0,0)`, despite the original mode13 argument `(-1834,4149,-11795)` at r207_EnemySet. The original typed setter's floor adjustment is separate from that authored input. Leon1440/Ashley600 remain unchanged; no health, ammunition, position, source flag, process or save edits are used.

The private proof is `workers/ch32/deferred-goto/current-r207-off-release-proof.json`, SHA25652fd3b7df907e323e84faa1979dca84654376d21554d5a5fb736a1a1062554ff. Private observer/controller failures before useful input and the normal process-exit guard are retained in `current-controller-invalid-attempts.json`; they are not guest failures. The first enabled-arm gameplay comparison, original death/Continue and whole-room progression are still pending. The switch stays default-off and is not enabled in a chapter recipe by this control proof.


## Current enabled arm: original kill and deferred delivery, 2026-10-19

The matching enabled program `e445ed8db922490cfb14253cc8990302b71c675069a63a1dd287bd4409f2923a` now delivers the original held movement command after a normal source kill. Ten bounded captures retain the exact same on-disc image and saved-state lineage. All 6,579 nonprogram payloads match the disabled control; the 23 program payloads are the explicitly paired build inputs. These arms are frozen to the a808 integration, not newer e86 source.

Original radio, normal stairs and the original upper event complete. D4/D5 retain copied mode13 and authored target(-1834,4149,-11795) while held. Normal handgun fire/reload advances the source kill counter0→1 at frame3000. D4 allocates at2969; that single routine0 sample still has the original spawn and zero Goto fields, as expected before original first AI initialization. All38 subsequent samples from2970 through3000 have mode13 and the typed setter's floor-adjusted target(-1834,4199.16162109375,-11795). Its position advances toward that destination. The remaining D5 command survives queue compaction exactly. Max live Ganados stays4; Leon1440/Ashley600 remain intact. Raw allocation and initialized samples are all retained. The first host seal assertion incorrectly included pre-init allocation; its original script and correction receipt remain private, with no guest/runtime edit.

This contrasts with the disabled control's seven post-init D4 observations retaining mode0/zero destination. It proves the narrow delivery fix, not frame-identical gameplay or a performance gain. The fresh room-entry/Ashley-init/source chapter0 precondition and compiled default inventory remain disclosed; no kill rig or guest health/ammo/flags/position writes are used.

Private proof: `workers/ch32/deferred-goto/current-r207-on-release-proof.json`, SHA2567625f9dec3d7741ce6d87840b35f1a63267ed1fc8b834b1bbe29c438e9c594af. Public compact receipt: `tools/d367/castle18/r207-current-goto-on-release-20261019.json`. Joined ten-run logs retain exact49152 reserve/min31080 and aggregate native Leon8651/Ashley5269/em114786, all GC0. Specific released-D4 native rendering still needs its unchanged-disc tail. Official room residency still fails one late load in this covered window; do not compare it as an improvement against the longer off-arm29. Death/Continue, the pre-event cap-full wait branch, whole fight and no-warp chapter acceptance remain open. The switch stays default-off and no chapter recipe is enabled here.


### Native follow-through and the second release

The unchanged on10 tail now proves both original queued actors complete their movement to the upper floor and naturally clear mode13 to0, retaining the typed destination. Exact immutable-state native counters record D4:114 admitted frames,2970–3196,declines0; D5:59 admitted frames,3008–3124,declines0. These are per-source-actor pointer/appearance records after native acquisition and transaction selection, not aggregate or crowd-skip rows. Both remain HP1000; Leon/Ashley1440/600.

The second slot is separately accounted: D9 is inactive status0x108 at saved frame3000, while HP0 D8 remains ACTIVE status0x28 and still consumes a slot. Original D8 death advances the kill counter1→2 at3006; D5 releases3007 and admits natively3008. At3198 both original dead actors are inactive0x108 and exactly D3/D4/D5/DA are active. Thus the second release follows a second source death, not parking. No cap policy or source script changed.

Private follow-through proof SHA256c2904a0fe3bc902f2663bd3f1660c3b32b5417087d5ae0a8254dcb821b2fb4eb. The original native-state receipt4ba8cd18 remains byte-exact alongside the extended status-field receipt966bda22. Death/Continue and the pre-event cap-full waiter branch still remain open.


## Recovery and original preflight scope, 2026-10-19

The enabled arm now completes an ordinary enemy-caused death and the original Continue menu. Normal A confirms Continue; the original source backup restores room207 at frame880, phase3/Stop0, Leon1440/Ashley600, with all three Continue counters incremented to1. All64 deferred command records (1,536 bytes), all64 pending flag slots and the held list are zero after the verified reload. The original successful release/arrival checkpoint is preserved separately. This death occurred after both held actors had released, so it does not prove an actual queued-command death branch by itself.

A separate exact-state branch starts at frame2836 with both D4/D5 still held. Normal approach and bounded no-input windows retain both mode13 commands byte-exact through frame6304, with zero kills and unchanged1440/600 health. Original Find/Catch routines advance, but no death occurs. Every sampled source phase remains3/0 and Stop0; the receipt retains nearest live enemy and player positions, vertical differences, routines and closest distances for each attempt. Same-floor proximity is not treated as a successful hit. That stronger guest branch is therefore unexercised; it is neither a recovery pass nor a runtime failure. Its checkpoint remains resumable and source-extracted queued-reset tests remain separate evidence. No death, health, inventory, flag or position was fabricated.

The original selected entry cannot reach the preflight guard with four live actors: its exact selected ESL has only D8/D9/DA initially enabled, confirmed by the untouched pre-event EmMgr census. All six exec areas are bound by source to sword/check/shelf callbacks; none sends enemies before that guard. Original D3 then supplies the fourth actor, with D4/D5 held, which is the actual full-cap event already observed. The guard's true branch remains guest-unexercised; full-cap wait/release and failure ordering are covered by source-extracted host tests. This reachability claim is restricted to the selected original entry, not arbitrary modified states.

Residency remains a separate failure. Splitting the joined log at the actual Continue boundary preserves41 official late uploads before recovery and0 after the new preload. The pre-Continue raw ledger contains50 distinct first sightings/49 unlisted keys; source ownership remains unclassified. A final-generation green result must not erase the earlier failure. No parser, filter or resident list changed.

Private proof `workers/ch32/deferred-goto/current-r207-recovery-preflight-proof.json`, SHA2567e6cc008365fa756642e1df98c4d1cbde6fe41cc81732c237f41cbb7d36683f6. Public receipt `tools/d367/castle18/r207-current-goto-recovery-preflight-20261019.json` binds every state link and source proof. The a808 off/on programs remain frozen; latest-upstream integration, held-death guest branch, complete fight and no-warp chapter acceptance remain open. This checkpoint does not enable the chapter recipe.
