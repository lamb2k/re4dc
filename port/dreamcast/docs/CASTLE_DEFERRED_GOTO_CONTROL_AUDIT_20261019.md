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
