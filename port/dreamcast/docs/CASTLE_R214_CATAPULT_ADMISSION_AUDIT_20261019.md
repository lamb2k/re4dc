# r214 catapult admission audit — 2026-10-19

The smallest local protection is a two-stage preflight **before the cutscene**, under the proposed default-off deferred-Goto feature. It must distinguish a cap hold from death, then let the ordinary admission queue resolve held event actors before their poses are sampled. This prevents the event from freezing its own admission. **A preflight does not guarantee capacity or completion:** E0 and the three catapult crews consume all four slots, and the original actors are not removed by this function.

This is a read-only source audit of Castle main `2c0e3dc0474165164af5ce90e5b4f977a294d692`. The seven audited files had no working-tree changes. No implementation, build, capture, cap exception or progression acceptance is included. The new deferred-Goto implementation is not part of this source pin.

## Source sequence and failure

All paths below are repository-relative; line numbers refer to that pin.

| Source | Relevant behavior |
|---|---|
| `src/st2/r214.cpp:209–240` | Initialization sends E4/EC/ED/EE/EF; EC and ED patrol. Rsf3 changes initialization, while Rsf0 determines whether area9 registers the catapult event. |
| `src/st2/r214.cpp:627–647` | The event sets Rsf3 first, binds EC/ED, prefers EC if its HP is positive, otherwise ED. The chosen branch sends/fetches E0 and ends that patrol. If neither has positive HP, the original five sends and `SceExit()` run. |
| `src/st/em_wrap.cpp:143–158` | `EndControl()` stops the patrol and returns its actor to normal AI. It does not destroy EC/ED, transfer their identity to E0 or free a slot. |
| `src/st2/r214.cpp:648–660` | E9/EA/EB are sent; their original positions/angles are sampled; Rsf0, stream, cancellation and event start follow, in that order. |
| `src/st2/r214.cpp:662–686` | E0 is posed and ordered to move, with a `ckGoto()` wait inside the event. The three crews are subsequently posed and ordered home. |
| `src/game/sce_sys.cpp:172–177`; `src/game/em_set.cpp:738–743` | Admission runs after the scenario scheduler, but refuses while an event, item pickup or pause is active. It also requires fewer than four live actors and the existing 30-frame spacing. |

A newly deferred E0 movement command could make the wait at r214:668 persist while event state prevents E0 admission. The current unmodified `ckGoto()` instead returns zero on a non-live wrapper (`src/st/em_wrap.cpp:1010–1020`), which can falsely advance the event. This audit does not claim that the proposed implementation has already produced either result in r214.

There are earlier failures to prevent. Held `getHp()` returns zero (`src/st/em_wrap.cpp:664–670`), so a held patrol can be mistaken for a dead one. Held `getPos()` / `getAng()` save zero vectors (`src/st/em_wrap.cpp:790–799,833–842`), and held `setPos`, `setAng` and `setNoSuspend` do not apply. A wait inserted only immediately before r214:660 is too late to protect the saved crew poses.

## Smallest local preflight

1. Keep Rsf3 at r214:627 and both original bindings at 632–633. Before evaluating EC's HP at line 634, yield `SceSleep(1)` **only while EC is cap-held**. If EC is then non-positive, perform the equivalent held-only wait for ED before its HP test at line 638. Keep EC priority and the original both-dead exit. Do not treat held `isAlive()` as proof of admission: it intentionally returns one.
2. Keep the selected E0 send/fetch, selected `EndControl()`, and E9/EA/EB sends in their current order. Insert one held-only loop **after r214:650 and before line 651**, checking E0 and all three crew wrappers together. Yield one frame while any is still held. Use the existing non-creating held predicate (`EM_WRAP_HELD_NOW`, `include/em_wrap.h:200–207`), not `getPtr()`. No sends, patrol termination or Rsf writes belong inside that retry loop.
3. Only after the preflight continue the existing position/angle snapshots, Rsf0, stream, cancellation registration, `SceEventStart(0)` and all original camera/pose/Goto/end code. Do not register cancellation or freeze the player during the wait. In particular, the end callback at r214:573–591 calls `SceEventEnd(0)` and must not be used as a preflight abort callback before an event has begun.

The loop tests **held**, not “pointer absent.” Once ordinary admission occurs, the next wrapper method resolves the existing actor (`src/st/em_wrap.cpp:42–69`). A dropped/dead entry must follow the original branch/no-op behavior rather than wait forever for a dead actor. A non-cap creation failure is a separate failure, not evidence that a held entry is ready.

`getPtr()` is unsuitable as an admission probe: `src/st/em_wrap.cpp:460–463` calls `re4dc_aliveCapTake(no,0)`, whose creation path deliberately sets `aliveCapReleasing` (`src/game/em_set.cpp:456–489`). That can create over the cap. No getter, general admission or queue-policy change is proposed.

## Capacity limit and required room proof

E0 + E9 + EA + EB require four live slots. Any remaining live E4/EC/ED/EE/EF leaves fewer than four available; r214 is explicitly excluded from parking with `PS2_CH4_ENEMY` (`src/game/em_set.cpp:623–630`). The original selected patrol remains live after `EndControl()`. Neither a one-frame yield nor a fixed timeout creates capacity, and admission chooses the farthest held entry rather than reserving this quartet (`src/game/em_set.cpp:744–783`).

The preflight leaves ordinary gameplay and admission running, so source deaths can free slots; it **does not prove** that the original route lets the player free every necessary slot, that no other held actor wins admission, or that all four required actors survive the wait. Do not label a pending cutscene as a passed progression gate. If the original route cannot make those slots available, this local preflight is insufficient: return the exact room/admission dependency to the owner rather than delete actors, fabricate deaths, force admission, grant a blanket exception or enter the event with held actors.

The owner must cover EC held / ED live (EC priority), EC dead / ED held, both genuinely dead, E0 and individual crew holds, the full initial crowd, ordinary kills and queue release, death or allocation refusal while waiting, normal event completion and START cancellation after entry. Preserve Rsf3/Rsf0 ordering and room-exit/re-entry behavior: the preflight adds a yielding interval between the existing persistent writes. Pause, item pickup or a separate event can temporarily suspend admission; do not override their busy state. Normal source exit/re-entry must not duplicate sends or replay patrol termination within a pending task.

Exact source SHA256 values, file sizes, audit line ranges and the public document hash are retained privately at `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/r214-catapult-admission-audit-20261019/source-audit.json`. The document changes no source, model, recipe, gate or runtime ownership.
