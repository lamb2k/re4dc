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
