# Inventory actor lifetime: bounded implementation proposal

This is a read-only design at Castle main `27db38be01708a40ec86c3a15b7a564700951949`, including e86 upstream. It proposes no recipe enable and contains no implementation, build or fresh runtime reproduction. The frozen746 Ashley healing observation and boss lifecycle audit remain the evidence for the problem, not current-source acceptance. Worker A's a808 Goto pair is separate and immutable.

The relevant bridge, menu, HUD, condition and reset functions are unchanged from the audited2c0 baseline. Current item.cpp and sscrn.cpp have quick-weapon additions; their original healing and backing-close ordering remain intact. The fresh source inventory has12 exact file hashes, including subscreen.mk, at `workers/ch32/healing/source-scope-inventory.json`, SHA256 e11b8d691949279d5440a37cb432aa65d758a0bfb84829e5b37fdc2af12cd9af.

## Proposed files and switch

| File | Narrow responsibility |
| --- | --- |
| port/dreamcast/game/sscrn_bridge.cpp | Own the frozen actor view and pending successful-Use reset targets in resident storage; capture and verified close lifecycle. |
| port/dreamcast/game/subscreen.mk | `SS_ACTOR_LIFETIME ?= 0`; accept only0/1 and requireSUBSCREEN1; define it only for the actual bridge, cockpit, pl_npc and Sscrn ss_pzzl objects. |
| src/Sscrn/ss_pzzl.cpp | WHO presence lookup and the three existing successful-Use motion-reset call sites only. |
| src/game/cockpit.cpp | The two partner-id reads and two player-stat reads used by the inventory HUD/bullet helpers only. |
| src/game/pl_npc.cpp | Substitute frozen inputs inside SubCharGetCondition during the backing interval while retaining its original decision order and live global branch. |
| include/re4dc_subscreen_actor.h (new) | Small read-only view and target-reset request declarations, included only under the new switch. No existing structure ABI changes. |

No item.cpp, pl_sub.cpp, sscrn.cpp, main.cpp, renderer, registry, model, package, resident-list or release recipe edit is proposed. Exact helper names and the new header are worker-owned; the five existing files require central claims before edits. Main Makefile is not needed because it already includes subscreen.mk. Disabled preprocessing, actual objects and loaded program bytes must remain exact.

## Transaction contract

The snapshot contains only actor-derived facts: whether pSUB exists and has id3, partner wait/move flag inputs, partner stat and routine0/1 inputs, and player stat. Keep identity metadata privately with it: original pG/pPL/pSUB, room, SubScreenWork/window and the active session. Do not copy health, max health, ammo, weapon selection, ItemMgr target or a precomputed final partner-condition word into frozen state.

Capture after the existing backing-save succeeds and temporary packing scratch has been restored, before memset clears the window. Task0 is already suspended. State lives in the resident bridge, outside the swapped window and Sscrn overlay; actual link/symbol placement must prove this. A rejected second open must leave the first session intact. A backing open which never succeeds must not create a usable session.

During the swap, WHO uses the captured id3 predicate. Preserve the pre-swap wk->healing values0/-1/1 and their original too-far/busy/eligible messages. Source ItemMgr.use, global healing/max-life clamps, item decrement, UI rehash and sound order remain immediate. Only a successful existing Use call requests its actual target's reset; a later mutable m_to_whom cannot retarget it. Failed Use and WHO cancel add nothing. A later cancel does not cancel an earlier successful heal/reset request.

HUD partner presence uses the same actor view. SubCharGetCondition keeps the source precedence: actor wait/stat produces1or2, live Status_flg[1] bit0x10000 then returns with8, actor move flag adds0x20, then original routine0/ladder13..14 adds0x10. The view supplies actor inputs only. Bullet helpers use frozen player stat; live weapon and ammo globals remain unchanged. The existing nonvirtual life-level helper reads pG and stays live.

A two-target pending mask coalesces repeated successful uses on frozen actors. Both original reset bodies only change their own routine/reset fields and are idempotent on the frozen state; neither changes health, item counts or the other actor. The enabled source-extracted tests must demonstrate that reduction, including mixed targets. Outside the active backing interval, reset requests call the original functions immediately.

Drain only at the end of swap_close after restored-span hash equality, pool thaw, dead screen-motion cleanup and certificate unpark. `swapped=false` occurs earlier and is not the proof of restored validity. Check room/session/window and original actor/global identities before applying any request; never apply to replacements. On hash or identity failure, clear pending metadata and fail closed without calling resets or resuming through the helper. Source reset guards remain original: player routine0 with boat/crouch exclusions, partner routine0/0or1 only. No direct actor-byte reset substitute.

The drain point returns to SubScreenExitCore before room relink/model-manager reassignment, equipment/costume reinitialization and TaskSignal(0). The original reset functions do not require those later model-manager steps. systemResetCommon already calls this core close before TaskAllClear/ReleasePlData, so no additional main reset hook is proposed. After a valid close, clear all metadata once so close/reopen and the next room cannot inherit requests.

## Required evidence before adoption

1. Reproduce the current-source problem first using a fresh frozen e86 control and real normal injury/Use inputs. Show the before-open actor identity/position, precomputed healing value, swapped interval, WHO behavior and unchanged global target health/item count. No historical snapshot retarget, forced health, fabricated inventory or actor writes. Coordinate one shared control build so main and workers do not duplicate it.
2. Source-extracted tests run actual original condition/reset/healing/menu decision bodies against the enabled snapshot path. Cover absent, nearby, far and busy Ashley; live global condition precedence; ammo/stat displays; both heal targets; full/failed Use; yellow-max-life mixtures; repeated/mixed target use; WHO cancel; close after Use; normal close/reopen; rejected second open; backing/hash failure; actor/room/session replacement; and system reset while open. Assert successful-Use target capture and reset-before-equipment/resume ordering, with no health/ammo snapshot regression.
3. Prove disabled source preprocessing and fresh literalT15/CH4 loaded-program identity, including boot and every overlay, with all current defaults and exact private generated headers. Whole-ELF debug-only changes, if any, must be named separately. Verify real compile definitions on all four linked consumers and no generated-stub binding for the new bridge API. Build serially in one-j4 slot after reviewed/pushed source.
4. Matched fresh enabled control: normal Ashley injury, WHO target choice, successful Ashley healing, item decrement, immediate global/HUD updates, exact backing restore, original guarded reset, and resumed ordinary follow/combat. Also normal Leon healing, a failed/full-use or cancel case, close/reopen, and system reset lifecycle as reachable. Preserve every source-state and per-generation residency failure; a good final reload cannot hide an earlier one.

Public performance or chapter-complete claims are outside this correctness repair. The current full-cap movement switch remains independently default-off until main accepts its own evidence and remaining limits. No new image, build or shared edit is authorized by this proposal itself.


## Fresh current control and reset invariance

Unmodified current runtime source is exact to `27db38be` (e86 upstream, including SCENERY_CHUNK=1), built from clean pushed `d0d91273`. No healing implementation or synthetic feature definition is present. Serial -j4 baseline builds produced literal T15 `c32hbrP` (11 payloads, ELF `1aac9f7587f92fa536354cb4ef63d1b9bd8299450dcf56405a8f551c26aafb87`) and diagnostic CH4 `c32hbmW` (23 payloads, ELF `aba62141866a24763657bfe11a07ab1a369b6e32f6bd94989e1d389817470394`). Each preserves all 45 generated headers, resolved knobs, raw program/ELF, compiler log, exact input recipes and all overlays. These are reusable future off controls; no off/on comparison is claimed yet.

Actual source bodies of SubCharGetCondition, PlMotionReset and SubCharMotionReset were extracted into an ASan/UBSan host test. It passed 1,572,864 partner cases and 196,608 player cases, covering every routine-byte value, relevant status/flag families, live Status[1] priority and repeated resets. Original partner reset only changes eligible routine1 to0; the condition function distinguishes13/14, so its returned view is unchanged. Player reset does not change player stat. Repetition is byte-idempotent under the original guards. This answers the frozen HUD-input question for these exact reset bodies; it does not yet prove a snapshot implementation, real actor layout or runtime healing. Health and the global status priority remain live.

The actual current CH4 close routine compares restored hash r11 to open_hash at0x8c2650ec. Mismatch branches to0x8c265116 and calls the strong re4dc_missing at0x8c21374c. Its compiled thd_sleep(1000) loop never returns, so the effective restore predicate is more than a log message. The proposed helper must preserve that existing failure/task-resume policy and must not invent a global resume/stop path. No runtime memory-corruption injection was performed.

Fresh doorway control `cx-r207-walk-healcontrol01` stages all23 exact programs on disc `662818ca6a000ea0c6f41113ac90bdc34b4ef588fddf7f52113b5530e8e3313a`; original radio and genuine normal-input injury/WHO reproduction are in progress. The partner-init diagnostic precondition remains disclosed. No historical746 or a808 snapshot is retargeted. This checkpoint is preparation and source proof only, not a healing fix or current-source reproduction pass.
